#!/usr/bin/env python3
"""Long-lived tbaMUD session held by a background daemon.

Each shell command is its own process, so a telnet socket opened by one
cannot survive into the next. This daemon owns the socket and exposes it
over a unix socket, so `mud.py send look` works across separate calls
while the MUD still sees one continuous session.

    mud.py start [--host H] [--port P] [--name N] [--password P]
    mud.py send "look"          # send one command, print the reply
    mud.py send --raw ""        # send a bare newline (menus/prompts)
    mud.py vitals               # last known hp/mana/move, no traffic
    mud.py status
    mud.py stop

Everything sent and received is appended to <state>/transcript.log, which
is the raw evidence for a player-journey report.
"""

import argparse
import json
import os
import re
import signal
import socket
import sys
import threading
import time
from pathlib import Path

DEFAULT_HOST = os.environ.get("MUD_HOST", "localhost")
DEFAULT_PORT = int(os.environ.get("MUD_PORT", "4000"))
DEFAULT_NAME = os.environ.get("MUD_NAME", "dummy")
DEFAULT_PASSWORD = os.environ.get("MUD_PASSWORD", "helloworld")
STATE_DIR = Path(os.environ.get("MUD_STATE_DIR", "data"))

IAC, SB, SE = 0xFF, 0xFA, 0xF0
WILL, WONT, DO, DONT = 0xFB, 0xFC, 0xFD, 0xFE

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
# tbaMUD's default prompt carries live vitals, e.g. "23H 100M 84V (news) > ".
# Every response ends with one, which is why the agent rarely needs `score`.
PROMPT_RE = re.compile(r"(\d+)H (\d+)M (\d+)V[^>\n]*>\s*")
# `score` is the only place the MAXIMUM shows up: "You have 13(23) hit, ...".
SCORE_HP_RE = re.compile(r"you have (\d+)\((\d+)\) hit", re.I)
SLEEP_OK_RE = re.compile(r"you (go to sleep|lie down and sleep)", re.I)
REST_OK_RE = re.compile(r"you (sit down and rest|rest your tired bones)", re.I)
HUNGRY_RE = re.compile(r"you are (hungry|thirsty)", re.I)


def strip_iac(data: bytes) -> bytes:
    """Drop telnet negotiation. We never negotiate, we just refuse to be confused by it."""
    out = bytearray()
    i = 0
    while i < len(data):
        b = data[i]
        if b != IAC:
            out.append(b)
            i += 1
            continue
        nxt = data[i + 1] if i + 1 < len(data) else None
        if nxt is None:
            break
        if nxt == IAC:
            out.append(IAC)
            i += 2
        elif nxt in (WILL, WONT, DO, DONT):
            i += 3
        elif nxt == SB:
            j = i + 2
            while j < len(data) - 1 and not (data[j] == IAC and data[j + 1] == SE):
                j += 1
            i = j + 2
        else:
            i += 2
    return bytes(out)


def clean(text: str) -> str:
    return ANSI_RE.sub("", text)


class MudConnection:
    def __init__(self, host, port, transcript: Path):
        self.host = host
        self.port = port
        self.sock = None
        self.buf = ""
        self.lock = threading.Condition()
        self.last_recv = 0.0
        self.closed = False
        self.transcript = transcript
        self.vitals = {"hp": None, "mana": None, "move": None}

    def log(self, tag, text):
        try:
            with self.transcript.open("a", encoding="utf-8") as fh:
                fh.write(f"\n--- {tag} {time.strftime('%H:%M:%S')} ---\n{text}")
        except OSError:
            pass

    def open(self):
        self.sock = socket.create_connection((self.host, self.port), timeout=10)
        # Back to blocking. create_connection leaves a 10s timeout on the
        # socket, which makes recv raise once the MUD is merely quiet -- that
        # would tear down a perfectly healthy session between commands.
        self.sock.settimeout(None)
        threading.Thread(target=self._reader, daemon=True).start()

    def _reader(self):
        while True:
            try:
                chunk = self.sock.recv(4096)
            except OSError:
                break
            if not chunk:
                break
            text = strip_iac(chunk).decode("utf-8", "replace")
            with self.lock:
                self.buf += text
                self.last_recv = time.monotonic()
                self.lock.notify_all()
        with self.lock:
            self.closed = True
            self.lock.notify_all()

    def take_pending(self):
        """Lift anything that arrived on its own since the last command.

        The MUD talks unprompted -- arrivals, combat rounds, hunger. That text
        carries its own prompt, so if it were left in the buffer the next read
        would return it and stop, handing back the previous moment's news as
        though it were this command's reply. Every read after that would be one
        behind. We take it out of the way and hand it back separately.
        """
        with self.lock:
            out, self.buf = self.buf, ""
        text = clean(out)
        if text.strip():
            self.log("ASYNC", text)
        return text

    def send(self, line):
        self.sock.sendall(line.encode("utf-8") + b"\r\n")
        self.log("SENT", line + "\n")

    def read(self, quiet=0.4, timeout=10.0, need_prompt=True):
        """Collect output until the MUD goes quiet after a prompt.

        Stopping at the first prompt loses async text: a move returns its room
        description and a prompt, and only then does "You are hungry." arrive
        with a prompt of its own. So we wait for a prompt AND a lull.
        """
        deadline = time.monotonic() + timeout
        with self.lock:
            while True:
                now = time.monotonic()
                if now >= deadline or self.closed:
                    break
                has_prompt = bool(PROMPT_RE.search(self.buf)) if need_prompt else bool(self.buf)
                if has_prompt and self.buf and (now - self.last_recv) >= quiet:
                    break
                self.lock.wait(min(0.1, max(0.01, deadline - now)))
            out, self.buf = self.buf, ""
        text = clean(out)
        self.log("RECV", text)
        for m in PROMPT_RE.finditer(text):
            self.vitals = {"hp": int(m.group(1)), "mana": int(m.group(2)), "move": int(m.group(3))}
        return text

    def read_until(self, pattern, timeout=15.0):
        rx = re.compile(pattern, re.I)
        deadline = time.monotonic() + timeout
        with self.lock:
            while True:
                if rx.search(clean(self.buf)):
                    break
                remaining = deadline - time.monotonic()
                if remaining <= 0 or self.closed:
                    break
                self.lock.wait(min(0.1, remaining))
            out, self.buf = self.buf, ""
        text = clean(out)
        self.log("RECV", text)
        return text

    def login(self, name, password):
        """Walk the login dance. Two paths, and the difference matters.

        A fresh login lands on a menu that needs a keypress then "1". A
        character who is still linkdead gets "Reconnecting." and is dropped
        straight into the world -- sending "1" there is a game command, and
        the MUD answers "Huh!?!".
        """
        self.read_until(r"name.*\?", timeout=15)
        self.send(name)
        self.read_until(r"password", timeout=10)
        self.send(password)
        out = self.read(quiet=0.5, timeout=12, need_prompt=False)
        if re.search(r"wrong password", out, re.I):
            raise RuntimeError("wrong password")
        if re.search(r"reconnect", out, re.I):
            return "reconnected"
        # Fresh login: acknowledge the motd, then pick "enter the game".
        if not PROMPT_RE.search(out):
            self.send("")
            out += self.read(quiet=0.5, timeout=10, need_prompt=False)
        if not PROMPT_RE.search(out):
            self.send("1")
            out += self.read(quiet=0.5, timeout=10, need_prompt=False)
        if PROMPT_RE.search(out):
            return "logged in"
        raise RuntimeError(f"login did not reach a game prompt; last output:\n{out[-500:]}")

    def _exchange(self, line, quiet=0.4, timeout=8.0):
        self.send(line)
        return self.read(quiet=quiet, timeout=timeout)

    def max_hp(self):
        """Ask `score` for the ceiling. The prompt only ever shows current hp."""
        m = SCORE_HP_RE.search(self._exchange("score"))
        return int(m.group(2)) if m else None

    def recover(self, target=None, timeout=300.0, poll=5.0, stall_after=150.0):
        """Heal to `target` hp, doing all the waiting in here.

        Resting is pure time -- but polling it from outside costs a full
        round trip per sample just to learn one number. The daemon already
        holds the socket and already reads vitals off every prompt, so it
        can watch the bar climb itself and answer once.

        Sleeping regenerates faster than resting, so we always prefer it and
        fall back only if the room refuses. The price of sleep is that you are
        helpless, which is why a drop in hp aborts the whole thing: that is an
        attack, and it is the one signal that means nothing here matters more
        than standing up. Watching hp rather than combat text keeps this honest
        no matter how the MUD words the hit.
        """
        self.take_pending()
        if target is None:
            target = self.max_hp()
            if target is None:
                return {"ok": False, "error": "could not read max hp from score"}

        out = self._exchange("sleep")
        mode = "sleep"
        if not SLEEP_OK_RE.search(out):
            out = self._exchange("rest")
            mode = "rest" if REST_OK_RE.search(out) else "unknown"

        started = time.monotonic()
        hp = self.vitals["hp"]
        best = hp if hp is not None else 0
        last_gain = started
        starved = bool(HUNGRY_RE.search(out))

        def finish(reason):
            self._exchange("wake")
            self._exchange("stand")
            return {"ok": True, "reason": reason, "mode": mode, "target": target,
                    "hp": self.vitals["hp"], "gained": (self.vitals["hp"] or 0) - (hp or 0),
                    "elapsed": round(time.monotonic() - started, 1),
                    "starved": starved, **self.vitals}

        while True:
            if self.closed:
                return {"ok": False, "error": "session dropped mid-recover"}
            if time.monotonic() - started > timeout:
                return finish("timeout")
            time.sleep(poll)
            text = self._exchange("")
            if HUNGRY_RE.search(text):
                starved = True
            now = self.vitals["hp"]
            if now is None:
                continue
            if now < best:
                return finish("interrupted")  # something is hitting us
            if now >= target:
                return finish("reached")
            # Regen lands on a game tick (~60-90s), not continuously, so a flat
            # reading proves nothing on its own -- we poll far faster than the
            # world heals. Only a gap much longer than a tick means regen is
            # genuinely throttled (hunger, thirst), and waiting will not fix it.
            if now > best:
                best = now
                last_gain = time.monotonic()
            elif time.monotonic() - last_gain > stall_after:
                return finish("stalled")


def daemon_main(args):
    state = Path(args.state)
    state.mkdir(parents=True, exist_ok=True)
    sock_path = state / "mud.sock"
    if sock_path.exists():
        sock_path.unlink()

    conn = MudConnection(args.host, args.port, state / "transcript.log")
    conn.open()
    status = conn.login(args.name, args.password)
    (state / "daemon.status").write_text(json.dumps({"status": status, "pid": os.getpid()}))

    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(str(sock_path))
    server.listen(4)

    def shutdown(*_):
        try:
            conn.send("quit")
        except Exception:
            pass
        try:
            sock_path.unlink()
        except OSError:
            pass
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)

    while True:
        client, _ = server.accept()
        try:
            data = client.makefile("r").readline()
            if not data:
                continue
            req = json.loads(data)
            op = req.get("op")
            if op == "send":
                pending = conn.take_pending()
                conn.send(req.get("line", ""))
                text = conn.read(
                    quiet=float(req.get("quiet", 0.4)),
                    timeout=float(req.get("timeout", 10)),
                )
                reply = {"ok": True, "text": text, "async_before": pending,
                         "connected": not conn.closed, **conn.vitals}
            elif op == "recover":
                reply = conn.recover(
                    target=req.get("target"),
                    timeout=float(req.get("timeout", 300)),
                    poll=float(req.get("poll", 5)),
                    stall_after=float(req.get("stall_after", 150)),
                )
            elif op == "vitals":
                reply = {"ok": True, **conn.vitals}
            elif op == "status":
                reply = {"ok": True, "connected": not conn.closed, **conn.vitals}
            elif op == "stop":
                try:
                    score_text = conn._exchange("score")
                    final = {"ok": True, "stopped": True, "final_score": score_text}
                except Exception as e:
                    final = {"ok": True, "stopped": True, "final_score": f"(error: {e})"}
                client.sendall((json.dumps(final) + "\n").encode())
                client.close()
                shutdown()
            else:
                reply = {"ok": False, "error": f"unknown op {op!r}"}
            client.sendall((json.dumps(reply) + "\n").encode())
        except Exception as exc:  # a bad request must not kill the session
            try:
                client.sendall((json.dumps({"ok": False, "error": str(exc)}) + "\n").encode())
            except OSError:
                pass
        finally:
            client.close()


def call(state: Path, req: dict, timeout=30):
    sock_path = state / "mud.sock"
    if not sock_path.exists():
        return {"ok": False, "error": "no session; run: mud.py start"}
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect(str(sock_path))
        s.sendall((json.dumps(req) + "\n").encode())
        return json.loads(s.makefile("r").readline())
    except (OSError, ValueError) as exc:
        return {"ok": False, "error": f"session unreachable: {exc}"}
    finally:
        s.close()


def cmd_start(args):
    import subprocess

    state = Path(args.state)
    state.mkdir(parents=True, exist_ok=True)
    if (state / "mud.sock").exists():
        res = call(state, {"op": "status"})
        if res.get("ok"):
            print(json.dumps({"ok": True, "already_running": True, **res}))
            return 0
        (state / "mud.sock").unlink()

    log = (state / "daemon.log").open("a")
    subprocess.Popen(
        [sys.executable, os.path.abspath(__file__), "_daemon", "--host", args.host,
         "--port", str(args.port), "--name", args.name, "--password", args.password,
         "--state", str(state)],
        stdout=log, stderr=log, start_new_session=True,
    )
    for _ in range(150):
        if (state / "mud.sock").exists():
            res = call(state, {"op": "status"})
            if res.get("ok"):
                print(json.dumps({"ok": True, "started": True, **res}))
                return 0
        time.sleep(0.2)
    print(json.dumps({"ok": False, "error": "daemon did not come up; see data/daemon.log"}))
    return 1


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp):
        sp.add_argument("--host", default=DEFAULT_HOST)
        sp.add_argument("--port", type=int, default=DEFAULT_PORT)
        sp.add_argument("--name", default=DEFAULT_NAME)
        sp.add_argument("--password", default=DEFAULT_PASSWORD)
        sp.add_argument("--state", default=str(STATE_DIR))

    common(sub.add_parser("start", help="open the session and log in"))
    common(sub.add_parser("_daemon"))

    sp = sub.add_parser("send", help="send one command and print the reply")
    sp.add_argument("line")
    sp.add_argument("--quiet", type=float, default=0.4, help="lull that marks end of output")
    sp.add_argument("--timeout", type=float, default=10.0)
    sp.add_argument("--json", action="store_true", help="print the full JSON reply")
    sp.add_argument("--state", default=str(STATE_DIR))

    sp = sub.add_parser("recover", help="sleep/rest until healed; waits inside the daemon")
    sp.add_argument("--to", type=int, default=None, dest="target",
                    help="target hp (default: your maximum, read from score)")
    sp.add_argument("--timeout", type=float, default=300.0)
    sp.add_argument("--poll", type=float, default=5.0)
    sp.add_argument("--state", default=str(STATE_DIR))

    sp = sub.add_parser("stop", help="quit the game and close the session")
    sp.add_argument("--state", default=str(STATE_DIR))

    for name in ("vitals", "status"):
        sp = sub.add_parser(name)
        sp.add_argument("--state", default=str(STATE_DIR))

    args = p.parse_args()
    state = Path(getattr(args, "state", STATE_DIR))

    if args.cmd == "_daemon":
        return daemon_main(args)
    if args.cmd == "start":
        return cmd_start(args)
    if args.cmd == "send":
        res = call(state, {"op": "send", "line": args.line, "quiet": args.quiet,
                           "timeout": args.timeout}, timeout=args.timeout + 20)
        if args.json or not res.get("ok"):
            print(json.dumps(res, indent=2))
        else:
            # stdout carries ONLY the room's reply text -- nothing else. This
            # output is meant to be piped straight into nav.py, which expects
            # raw MUD text; any decoration here would corrupt its parsing.
            # Async world text (arrivals, hunger, combat) is real signal too,
            # so it still goes out -- just on stderr, alongside vitals, where
            # a human or the calling agent sees it but a `> file` redirect
            # never captures it.
            if res.get("async_before", "").strip():
                print("[while you were deciding]", file=sys.stderr)
                print(res["async_before"].strip(), file=sys.stderr)
                print("---", file=sys.stderr)
            print(res["text"].strip())
            print(f"[hp={res['hp']} mana={res['mana']} move={res['move']}]", file=sys.stderr)
            if not res.get("connected", True):
                print("[session dropped -- run: mud.py start]", file=sys.stderr)
        return 0 if res.get("ok") else 1
    if args.cmd == "recover":
        # The daemon is deliberately busy for up to `timeout` here, so the
        # client must be willing to wait longer than the rest itself.
        res = call(state, {"op": "recover", "target": args.target,
                           "timeout": args.timeout, "poll": args.poll},
                   timeout=args.timeout + 60)
        print(json.dumps(res))
        return 0 if res.get("ok") else 1
    if args.cmd == "stop":
        res = call(state, {"op": "stop"})
        if res.get("ok"):
            if "final_score" in res:
                print("=== Final Score ===", file=sys.stderr)
                print(res["final_score"], file=sys.stderr)
            print(json.dumps({"ok": True, "stopped": True}))
        else:
            print(json.dumps(res))
        return 0 if res.get("ok") else 1
    res = call(state, {"op": args.cmd})
    print(json.dumps(res))
    return 0 if res.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
