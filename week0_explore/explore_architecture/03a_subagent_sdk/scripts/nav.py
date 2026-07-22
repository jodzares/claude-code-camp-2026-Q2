#!/usr/bin/env python3
"""World map: parse room output, maintain the graph, plan routes with BFS.

Feed it raw MUD output and it does the bookkeeping deterministically, so the
agent can spend its attention on *where to go and why* rather than on
re-deriving a flood fill every loop.

    nav.py look   --file out.txt        # record the room you are standing in
    nav.py move   --dir north --file out.txt   # record a move (success or refusal)
    nav.py exits  --file out.txt        # learn neighbour titles without walking
    nav.py route  --to "The Temple Of Midgaard"
    nav.py frontier                     # nearest unexplored exits
    nav.py seal   --dir north           # door closed since we mapped it
    nav.py unseal --dir north
    nav.py note   --text "shopkeeper sells daggers, 30 gold"
    nav.py render                       # rewrite world.md from world.json
    nav.py status

Room identity is hash(title + description), NOT the title and NOT the
coordinates. Midgaard has several distinct rooms all titled "Main Street",
so titles merge rooms that are not the same. Coordinates are dead-reckoned
and kept as an attribute: when one room turns up at two different readings
the world is non-Euclidean there, which we record as a seam rather than
pretend it away.
"""

import argparse
import hashlib
import json
import re
import sys
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "data/world.json"
RENDER = ROOT / "data/world.md"

DIRS = ["north", "east", "south", "west", "up", "down"]
ABBREV = {"n": "north", "e": "east", "s": "south", "w": "west", "u": "up", "d": "down"}
REVERSE = {"north": "south", "south": "north", "east": "west",
           "west": "east", "up": "down", "down": "up"}
DELTA = {"north": (0, 1, 0), "south": (0, -1, 0), "east": (1, 0, 0),
         "west": (-1, 0, 0), "up": (0, 0, 1), "down": (0, 0, -1)}

PROMPT_RE = re.compile(r"^\s*\d+H \d+M \d+V[^>\n]*>\s*$")
VITALS_RE = re.compile(r"^\s*\[hp=\d+\s+mana=\d+\s+move=\d+\]\s*$", re.I)
EXITS_LINE_RE = re.compile(r"\[\s*Exits:\s*([^\]]*)\]", re.I)
EXITS_CMD_RE = re.compile(r"^(north|east|south|west|up|down)\s*-\s*(.+?)\s*$", re.I)
BLOCKED_RE = re.compile(
    r"alas, you cannot go that way|you cannot go|is closed|blocks your way", re.I)


def load():
    if STATE.exists():
        return json.loads(STATE.read_text())
    return {"rooms": {}, "current": None, "seams": [], "log": []}


def save(w):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(w, indent=2))


def room_id(title, desc):
    norm = re.sub(r"\s+", " ", f"{title}|{desc}").strip().lower()
    return hashlib.sha1(norm.encode()).hexdigest()[:8]


def parse_room(text):
    """Pull title / description / exits / contents out of a look or move reply."""
    lines = [l.rstrip() for l in text.splitlines()
             if not PROMPT_RE.match(l) and not VITALS_RE.match(l)]
    ex_idx = next((i for i, l in enumerate(lines) if EXITS_LINE_RE.search(l)), None)

    if ex_idx is None:
        title = next((l.strip() for l in lines if l.strip()), None)
        return {"title": title, "desc": "", "exits": None, "contents": []}

    start = ex_idx - 1
    while start > 0 and lines[start - 1].strip():
        start -= 1
    block = [l for l in lines[start:ex_idx] if l.strip()]
    title = block[0].strip() if block else None
    desc = " ".join(l.strip() for l in block[1:])

    raw = EXITS_LINE_RE.search(lines[ex_idx]).group(1)
    exits = [ABBREV[c] for c in raw.lower().split() if c in ABBREV]
    contents = [l.strip() for l in lines[ex_idx + 1:] if l.strip()]
    return {"title": title, "desc": desc, "exits": exits, "contents": contents}


def upsert(w, parsed, coords=None):
    rid = room_id(parsed["title"], parsed["desc"])
    room = w["rooms"].get(rid)
    if room is None:
        room = {"id": rid, "title": parsed["title"], "desc": parsed["desc"],
                "coords": coords, "exits": {}, "contents": [], "notes": [], "visits": 0}
        w["rooms"][rid] = room
    room["visits"] += 1
    if parsed.get("contents"):
        room["contents"] = parsed["contents"]
    if parsed.get("exits") is not None:
        for d in parsed["exits"]:
            room["exits"].setdefault(d, {"to": None, "dest_title": None, "sealed": False})
    if coords is not None:
        if room["coords"] is None:
            room["coords"] = list(coords)
        elif list(room["coords"]) != list(coords):
            # Same room, two readings: the map folds here. Worth reporting.
            seam = {"room": parsed["title"], "id": rid,
                    "known": room["coords"], "reached_at": list(coords)}
            if seam not in w["seams"]:
                w["seams"].append(seam)
    return rid


def link(w, a_id, direction, b_id):
    a, b = w["rooms"][a_id], w["rooms"][b_id]
    a["exits"].setdefault(direction, {"to": None, "dest_title": None, "sealed": False})
    a["exits"][direction].update({"to": b_id, "dest_title": b["title"], "sealed": False})
    rev = REVERSE[direction]
    # Only assume the way back if the room advertises that exit; tbaMUD has
    # one-way passages and inventing a return edge strands the agent.
    if rev in b["exits"] or not b["exits"]:
        b["exits"].setdefault(rev, {"to": None, "dest_title": None, "sealed": False})
        if b["exits"][rev]["to"] is None:
            b["exits"][rev].update({"to": a_id, "dest_title": a["title"], "sealed": False})


def neighbors(w, rid):
    for d, e in w["rooms"][rid]["exits"].items():
        if e["to"] and not e["sealed"] and e["to"] in w["rooms"]:
            yield d, e["to"]


def bfs(w, start, goal_test):
    """Flood from where we actually are. Returns (path_of_dirs, dest_id)."""
    if start is None:
        return None, None
    if goal_test(start):
        return [], start
    came = {start: None}
    q = deque([start])
    while q:
        rid = q.popleft()
        for d, nb in neighbors(w, rid):
            if nb in came:
                continue
            came[nb] = (rid, d)
            if goal_test(nb):
                path = []
                cur = nb
                while came[cur]:
                    prev, dd = came[cur]
                    path.append(dd)
                    cur = prev
                return list(reversed(path)), nb
            q.append(nb)
    return None, None


def resolve(w, needle):
    if needle in w["rooms"]:
        return needle
    hits = [r for r in w["rooms"].values() if r["title"].lower() == needle.lower()]
    if not hits:
        hits = [r for r in w["rooms"].values() if needle.lower() in r["title"].lower()]
    if len(hits) == 1:
        return hits[0]["id"]
    if len(hits) > 1:
        opts = [{"id": h["id"], "title": h["title"], "coords": h["coords"]} for h in hits]
        raise SystemExit(json.dumps(
            {"ok": False, "error": f"{len(hits)} rooms match {needle!r}; pass an id",
             "matches": opts}, indent=2))
    return None


def cmd_look(w, args):
    parsed = parse_room(Path(args.file).read_text() if args.file else sys.stdin.read())
    if not parsed["title"]:
        return {"ok": False, "error": "no room found in that output"}
    cur = w.get("current")
    coords = w["rooms"][cur]["coords"] if cur else [0, 0, 0]
    rid = upsert(w, parsed, coords if cur is None else None)
    if w["rooms"][rid]["coords"] is None:
        w["rooms"][rid]["coords"] = [0, 0, 0]
    w["current"] = rid
    return {"ok": True, "room": parsed["title"], "id": rid,
            "coords": w["rooms"][rid]["coords"], "exits": parsed["exits"]}


def cmd_move(w, args):
    text = Path(args.file).read_text() if args.file else sys.stdin.read()
    d = ABBREV.get(args.dir, args.dir)
    cur = w.get("current")
    if cur is None:
        return {"ok": False, "error": "no current room; run `nav.py look` first"}

    if BLOCKED_RE.search(text):
        # The absence of a link is the record of the wall.
        w["rooms"][cur]["exits"].setdefault(d, {"to": None, "dest_title": None, "sealed": False})
        w["rooms"][cur]["exits"][d]["blocked"] = True
        return {"ok": True, "moved": False, "reason": "blocked",
                "room": w["rooms"][cur]["title"], "id": cur}

    parsed = parse_room(text)
    if not parsed["title"]:
        return {"ok": False, "error": "move produced no room; check output"}

    base = w["rooms"][cur]["coords"] or [0, 0, 0]
    dx, dy, dz = DELTA[d]
    coords = [base[0] + dx, base[1] + dy, base[2] + dz]
    rid = upsert(w, parsed, coords)
    link(w, cur, d, rid)
    w["current"] = rid
    return {"ok": True, "moved": True, "room": parsed["title"], "id": rid,
            "coords": w["rooms"][rid]["coords"], "exits": parsed["exits"],
            "new_room": w["rooms"][rid]["visits"] == 1}


def cmd_exits(w, args):
    """Record neighbour titles from the `exits` command.

    tbaMUD prints "north - The Weapon Shop", so a room's neighbours can be
    named without walking into them. We store the title as a signpost; the
    edge stays unresolved until we actually arrive and can hash the room.
    """
    text = Path(args.file).read_text() if args.file else sys.stdin.read()
    cur = w.get("current")
    if cur is None:
        return {"ok": False, "error": "no current room; run `nav.py look` first"}
    found = {}
    for line in text.splitlines():
        m = EXITS_CMD_RE.match(line.strip())
        if m:
            d, dest = m.group(1).lower(), m.group(2).strip()
            e = w["rooms"][cur]["exits"].setdefault(
                d, {"to": None, "dest_title": None, "sealed": False})
            e["dest_title"] = dest
            found[d] = dest
    return {"ok": True, "room": w["rooms"][cur]["title"], "signposts": found}


def cmd_route(w, args):
    cur = w.get("current")
    target = resolve(w, args.to)
    if target is None:
        return {"ok": False, "error": f"no mapped room matching {args.to!r}",
                "hint": "explore toward it: nav.py frontier"}
    path, dest = bfs(w, cur, lambda r: r == target)
    if path is None:
        return {"ok": False, "error": "unreachable with what we know",
                "hint": "explore unmapped exits: nav.py frontier"}
    return {"ok": True, "steps": len(path), "path": path,
            "to": w["rooms"][dest]["title"], "id": dest}


def cmd_frontier(w, args):
    cur = w.get("current")
    if cur is None:
        return {"ok": False, "error": "no current room; run `nav.py look` first"}
    unexplored = {rid for rid, r in w["rooms"].items()
                  if any(e["to"] is None and not e.get("blocked") and not e["sealed"]
                         for e in r["exits"].values())}
    if not unexplored:
        return {"ok": True, "frontier": [], "note": "every known exit is mapped"}
    path, dest = bfs(w, cur, lambda r: r in unexplored)
    out = []
    if path is not None:
        room = w["rooms"][dest]
        dirs = [d for d, e in room["exits"].items()
                if e["to"] is None and not e.get("blocked") and not e["sealed"]]
        out.append({"room": room["title"], "id": dest, "steps": len(path),
                    "path": path, "unexplored": dirs,
                    "signposts": {d: room["exits"][d]["dest_title"] for d in dirs
                                  if room["exits"][d]["dest_title"]}})
    return {"ok": True, "nearest": out,
            "rooms_with_unexplored_exits": len(unexplored)}


def cmd_seal(w, args):
    cur = w.get("current")
    d = ABBREV.get(args.dir, args.dir)
    e = w["rooms"][cur]["exits"].get(d)
    if not e:
        return {"ok": False, "error": f"no {d} exit here"}
    e["sealed"] = not args.unseal
    return {"ok": True, "room": w["rooms"][cur]["title"], "dir": d,
            "sealed": e["sealed"],
            "note": "BFS will route around it; unseal if it opens again"}


def cmd_note(w, args):
    cur = w.get("current")
    if cur is None:
        return {"ok": False, "error": "no current room"}
    w["rooms"][cur]["notes"].append(args.text)
    return {"ok": True, "room": w["rooms"][cur]["title"], "notes": w["rooms"][cur]["notes"]}


def cmd_status(w, args):
    cur = w.get("current")
    mapped = sum(1 for r in w["rooms"].values()
                 for e in r["exits"].values() if e["to"])
    open_exits = sum(1 for r in w["rooms"].values()
                     for e in r["exits"].values()
                     if e["to"] is None and not e.get("blocked"))
    return {"ok": True, "rooms": len(w["rooms"]),
            "current": w["rooms"][cur]["title"] if cur else None,
            "current_id": cur, "edges": mapped, "unexplored_exits": open_exits,
            "seams": len(w["seams"])}


def cmd_render(w, args):
    lines = ["# World Map", "",
             f"Rooms mapped: **{len(w['rooms'])}**  ",
             f"Current: **{w['rooms'][w['current']]['title'] if w.get('current') else 'unknown'}**", ""]

    zs = sorted({(r["coords"] or [0, 0, 0])[2] for r in w["rooms"].values()})
    for z in zs:
        on_z = [r for r in w["rooms"].values() if (r["coords"] or [0, 0, 0])[2] == z]
        if not on_z:
            continue
        lines += [f"## Level {z}" if len(zs) > 1 else "## Map", "", "```"]
        xs = [r["coords"][0] for r in on_z if r["coords"]]
        ys = [r["coords"][1] for r in on_z if r["coords"]]
        if xs and ys:
            grid = {}
            for r in on_z:
                if r["coords"]:
                    grid[(r["coords"][0], r["coords"][1])] = r
            for y in range(max(ys), min(ys) - 1, -1):
                row = ""
                for x in range(min(xs), max(xs) + 1):
                    r = grid.get((x, y))
                    if not r:
                        row += "    "
                    elif r["id"] == w.get("current"):
                        row += "[@] "
                    else:
                        row += "[#] " if any(e["to"] is None and not e.get("blocked")
                                             for e in r["exits"].values()) else "[.] "
                lines.append(row.rstrip())
        lines += ["```", "",
                  "`[@]` you · `[#]` has unexplored exits · `[.]` fully mapped", ""]

    lines += ["## Rooms", ""]
    for r in sorted(w["rooms"].values(), key=lambda r: r["title"]):
        here = " ← **you are here**" if r["id"] == w.get("current") else ""
        lines.append(f"### {r['title']} `{r['id']}`{here}")
        lines.append(f"Coords: `{r['coords']}` · visits: {r['visits']}")
        lines.append("")
        for d in DIRS:
            e = r["exits"].get(d)
            if not e:
                continue
            if e["sealed"]:
                state = "sealed"
            elif e.get("blocked"):
                state = "wall"
            elif e["to"]:
                state = f"→ {w['rooms'][e['to']]['title']}"
            else:
                state = f"unexplored → {e['dest_title']}" if e["dest_title"] else "unexplored"
            lines.append(f"- **{d}**: {state}")
        if r["contents"]:
            lines.append("")
            lines.append("Contents: " + "; ".join(r["contents"]))
        if r["notes"]:
            lines.append("")
            for n in r["notes"]:
                lines.append(f"> {n}")
        lines.append("")

    if w["seams"]:
        lines += ["## Non-Euclidean seams", "",
                  "Rooms reached at coordinates other than where we first mapped them.",
                  "The map folds here; a player drawing it on paper would get lost.", ""]
        for s in w["seams"]:
            lines.append(f"- **{s['room']}**: known `{s['known']}`, reached at `{s['reached_at']}`")
        lines.append("")

    RENDER.parent.mkdir(parents=True, exist_ok=True)
    RENDER.write_text("\n".join(lines))
    return {"ok": True, "written": str(RENDER), "rooms": len(w["rooms"])}


def main():
    global STATE, RENDER
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--state", default=str(STATE))
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("look"); sp.add_argument("--file")
    sp = sub.add_parser("move"); sp.add_argument("--dir", required=True); sp.add_argument("--file")
    sp = sub.add_parser("exits"); sp.add_argument("--file")
    sp = sub.add_parser("route"); sp.add_argument("--to", required=True)
    sub.add_parser("frontier")
    sp = sub.add_parser("seal"); sp.add_argument("--dir", required=True)
    sp.add_argument("--unseal", action="store_true")
    sp = sub.add_parser("unseal"); sp.add_argument("--dir", required=True)
    sp = sub.add_parser("note"); sp.add_argument("--text", required=True)
    sub.add_parser("render")
    sub.add_parser("status")

    args = p.parse_args()
    STATE = Path(args.state)
    RENDER = STATE.parent / "world.md"

    w = load()
    fn = {"look": cmd_look, "move": cmd_move, "exits": cmd_exits, "route": cmd_route,
          "frontier": cmd_frontier, "seal": cmd_seal, "unseal": cmd_seal,
          "note": cmd_note, "render": cmd_render, "status": cmd_status}[args.cmd]
    if args.cmd == "unseal":
        args.unseal = True
    res = fn(w, args)
    save(w)
    print(json.dumps(res, indent=2))
    return 0 if res.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
