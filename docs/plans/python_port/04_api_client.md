# Porting Plan — `04_api_client`: Ruby → Python (delta only)

**Status:** plan only. No Python written yet.
**Source:** `week1_baseline/ruby/04_api_client/` (ExamPro reference, not to be modified)
**Target:** `week1_baseline/python/04_api_client/` — already exists, confirmed by
`diff -rq` to be a byte-identical copy of the finished `week1_baseline/python/03_prompt_builder/`
tree (`__pycache__/` excluded).

---

## Context

`03_prompt_builder` is done in both languages and is **not re-ported**. `04_api_client` adds
exactly one new concept — actually sending the payload `PromptBuilder` assembles and getting a
raw response back — plus the small edits elsewhere needed to wire that in.

Two decisions were made before this plan and are **not reopened** here:

1. **`PROMPTS_DIR` stays untouched.** Ruby's `04_api_client/lib/boukensha/config.rb` only
   changes a comment (`"shipped alongside the gem/library code"` → `"shipped alongside this
   step"`) — the `PROMPTS_DIR` path itself (`File.expand_path("../../prompts", __dir__)`,
   two directories up from `lib/boukensha/`) is unchanged in the current, already-fixed Ruby
   source. You separately corrected an earlier broken three-up version on the Ruby side; that
   fix is not part of this delta. Python's `Config.PROMPTS_DIR` (`Path(__file__).resolve().parent.parent
   / "prompts"`, also two-up) was already correct and stays untouched — **`boukensha/config.py`
   gets no edit at all in this step** (see §3.1).
2. **Standard-library HTTP only.** No `requests`, no `httpx`, no third-party package —
   matching Ruby's deliberate use of `net/http` with zero gems. `requirements.txt` is
   unaffected.

Grounding documents used to write this plan:
- `docs/plans/python_port/03_prompt_builder.md` — establishes the precedent this plan
  follows: `Config.PROMPTS_DIR` shape, the `boukensha/__init__.py` re-export pattern,
  `ValueError` for Ruby's `ArgumentError`, `"Boukensha"` Title Case banner (not Ruby's
  all-caps `"BOUKENSHA"`) per that plan's §3.10 point 8.
- `docs/study_notes/ruby_idiom_ledger.md` — committed idiom translations reused here
  (`ENV.fetch` → `os.environ[...]`, `case/when` → `if/elif/else`, `.freeze` has no true
  Python equivalent, `raise X, "msg"` → `raise X("msg")`).

---

## 1. What the Ruby delta actually is

Confirmed by diffing `ruby/04_api_client` against `ruby/03_prompt_builder`:

| Change | File |
|---|---|
| new | `lib/boukensha/client.rb` — `Client`: takes a `PromptBuilder`, POSTs the payload over `net/http`, retries transient errors and retryable status codes, raises `ApiError` on final failure |
| edited | `lib/boukensha/errors.rb` — adds `ApiError < StandardError` |
| edited | `lib/boukensha/config.rb` — comment-only; **no Python counterpart** (see Context, point 1) |
| edited | `lib/boukensha/tasks/base.rb` — (a) error message typo fix `settings.yml` → `settings.yaml` (Python already says `.yaml`, no-op there); (b) `fetch` now guards `settings.is_a?(Hash)` before indexing it, returning `nil` for anything else |
| edited | `lib/boukensha.rb` — drops the now-redundant top-level `require_relative "boukensha/backends/base"` (each backend already requires `"base"` itself — confirmed in `anthropic.rb`); adds `require_relative "boukensha/client"` |
| edited | `examples/example.rb` — rewritten: registers `read_file`/`list_directory` (no `look`/`move`), seeds a single user message instead of a scripted 3-message history, builds a `Client` from the `PromptBuilder`, moves the banner print, actually calls `client.call` and prints the raw response |
| edited | `prompts/system.md` — new system prompt text (data file, not code) |
| edited | `README.md` — full rewrite: new intro, Updated Files table, `Client` method table, response-shape JSON examples (Anthropic/Ollama), a Ruby-specific OpenSSL-certificate-path aside, output transcript |

Not touched (confirmed byte-identical Ruby↔Ruby): `lib/boukensha/context.rb`, `tool.rb`,
`message.rb`, `registry.rb`, `prompt_builder.rb`, `backends/base.rb`, `backends/anthropic.rb`,
`backends/gemini.rb`, `backends/ollama.rb`, `backends/ollama_cloud.rb`, `backends/openai.rb`,
`tasks/player.rb`, `Gemfile`.

---

## 2. File-by-file mapping

| Ruby file | Python counterpart | Action |
|---|---|---|
| `lib/boukensha/client.rb` | `boukensha/client.py` | create |
| `lib/boukensha/errors.rb` | `boukensha/errors.py` | edit — add `ApiError` |
| `lib/boukensha/tasks/base.rb` | `boukensha/tasks/base.py` | edit — dict-guard in `_fetch` (see §3.2) |
| `lib/boukensha.rb` | `boukensha/__init__.py` | edit — add `Client` re-export (see §3.3) |
| `examples/example.rb` | `examples/example.py` | edit — rewritten body (see §3.5) |
| `prompts/system.md` | `prompts/system.md` | edit — new prompt text, copied verbatim |
| `README.md` | `README.md` | edit — rewrite (see §3.6) |
| `lib/boukensha/config.rb` | `boukensha/config.py` | **no edit** — comment-only Ruby change, no Python counterpart (see Context, point 1) |
| — | `week1_baseline/bin/python/04_api_client` | create — new launcher, copy of `03_prompt_builder`'s style |

Not touched: `boukensha/context.py`, `boukensha/tool.py`, `boukensha/message.py`,
`boukensha/registry.py`, `boukensha/prompt_builder.py`, `boukensha/backends/*.py`,
`boukensha/tasks/player.py`, `requirements.txt`.

---

## 3. Design decisions

### 3.1 `boukensha/config.py` — untouched

Ruby's only change to `config.rb` in this delta is a code comment. There is no behavior to
port, and `PROMPTS_DIR` itself is explicitly out of scope per the decision already made (see
Context, point 1). `boukensha/config.py` is not opened for this step.

### 3.2 `boukensha/tasks/base.py` — `_fetch` guards against non-dict settings

Ruby:

```ruby
def fetch(settings, key)
  return nil unless settings.is_a?(Hash)

  settings[key.to_s] || settings[key.to_sym]
end
```

Python's existing `_fetch` is `return settings.get(key)`, which raises `AttributeError` if
`settings` is anything but a dict (e.g. `None`, when a task section is missing from
`settings.yaml` entirely). Port the guard directly:

```python
@classmethod
def _fetch(cls, settings, key):
    if not isinstance(settings, dict):
        return None
    return settings.get(key)
```

The `settings.yml` → `settings.yaml` typo fix in the same Ruby method is a no-op for
Python — `tasks/base.py`'s `provider`/`model` error messages already say `.yaml`.

### 3.3 `boukensha/__init__.py` — re-export `Client`

Ruby's `boukensha.rb` drops the standalone `require_relative "boukensha/backends/base"` line
(dead weight — every backend file already requires `"base"` itself) and adds
`require_relative "boukensha/client"`. The dropped line never had a Python counterpart
(backends were deliberately kept un-flattened and never re-exported from `__init__.py`, per
`03_prompt_builder.md` §3.3), so nothing to remove on the Python side. The added line does
have a counterpart: `Client` sits at the same namespace level as `PromptBuilder`/`Registry` in
Ruby (`Boukensha::Client`, not `Boukensha::Backends::Client`), so it gets the same top-level
re-export treatment those already have:

```python
from .config import Config
from .tasks.player import Player
from .tool import Tool
from .message import Message
from .context import Context
from .errors import UnknownToolError, ApiError, UnsupportedModelError
from .registry import Registry
from .prompt_builder import PromptBuilder
from .client import Client
```

(`ApiError` inserted between the other two error names, matching Ruby's own declaration
order in `errors.rb` — see §3.4.)

### 3.4 `boukensha/errors.py` — add `ApiError`

```python
class UnknownToolError(Exception):
    pass


class ApiError(Exception):
    pass


class UnsupportedModelError(Exception):
    pass
```

Same shape as the existing two — no message-formatting logic on the class, the string is
built at each `raise` call site, per the ledger's `raise X, "msg"` → `raise X("msg")` row.
Inserted in the middle to match Ruby's own file order.

### 3.5 `boukensha/client.py` — the new HTTP client

#### 3.5.1 Choosing the stdlib mechanism: `urllib.request`

Ruby's `Client` uses `Net::HTTP.new(host, port)` + `http.request(request)` — a **session-level**
API that returns the response object regardless of status code; retry logic then inspects
`response.code` itself. Python has two stdlib candidates:

- `urllib.request.urlopen(...)` — the higher-level, `open-uri`-like convenience wrapper. It
  **raises `HTTPError`** for any non-2xx status, which would force the retry loop to recover
  the status code from an exception instead of reading it off a normal return value — a
  structural mismatch with how Ruby's loop is written (`retryable_response?(response)` reads
  `response.code` directly, no exception involved for HTTP-level failures).
- `http.client.HTTPConnection` / `HTTPSConnection` — the lower-level connection API.
  `.getresponse()` returns a response object with `.status` **regardless of status code**,
  exactly like `Net::HTTP#request`. Structurally the closer match to Ruby's loop.

**Decision:** use `urllib.request`, not `http.client`. This project follows the instructor's
baseline exactly, and the instructor's own Python port uses `urllib.request` — matching that
choice is the actual bar here, not structural resemblance to Ruby's `net/http`. Behavioural
equivalence (same retries, same final error) is achievable with either module; the baseline
has already picked one.

This is honestly a place where Python forces a structure Ruby did not need. Ruby's
`Net::HTTP#request` hands back one response object no matter the status code, so
"did the transport fail" and "did the server return an error status" are just two fields to
check on the same value. `urllib.request.urlopen` instead **raises** `HTTPError` for any
non-2xx response, so those two questions arrive down two different code paths — one normal
return, one exception — that have to be reunited before the shared retry decision can be
made (see §3.5.3). Ruby's `Client` has no equivalent branch to reconcile; this is a genuine
structural cost of the instructor's chosen stdlib module, not a stylistic preference.

#### 3.5.2 Mapping Ruby's `TRANSIENT_ERRORS` to Python exception types

This is the one piece of this delta with no mechanical one-to-one translation — Ruby's list is
built from `net/http`'s and Ruby's own exception hierarchy; Python's transport errors come from
a different set of stdlib modules (`urllib`, `socket`, `ssl`, and built-in `OSError`/exception
types). Each entry below is chosen for the **category of failure**, not the class name:

| Ruby exception | Failure category | Python equivalent | Why |
|---|---|---|---|
| — (no single Ruby counterpart) | The request never completed at all — `urlopen` failed before any response could be read | `urllib.error.URLError` | `urllib.request` wraps many lower-level connection failures (refused connections, DNS failures, TLS failures raised through the url-opening machinery) in `URLError` rather than always letting the underlying exception propagate directly. Catching it is how `urllib.request` callers guard against "never got a response" as a category, independent of which specific underlying cause triggered it. `HTTPError` is a subclass of `URLError` — see the ordering constraint in §3.5.3. |
| `Errno::ECONNREFUSED`, `Errno::ECONNRESET` | Nothing listening at the target host/port, or the peer reset the connection mid-request | `ConnectionError` | Python's built-in `ConnectionError` is the parent of `ConnectionRefusedError`, `ConnectionResetError`, `ConnectionAbortedError`, and `BrokenPipeError` — catching the parent covers the same two Ruby `Errno` cases (and the two related ones Ruby didn't enumerate) in one type. |
| `EOFError` | Connection closed unexpectedly while reading a response | `EOFError` | Same built-in name, same meaning in both languages: the peer closed the stream before a complete response was read. |
| `Net::OpenTimeout`, `Net::ReadTimeout`, `Timeout::Error` | Connect timed out, read timed out, or a generic timeout | `TimeoutError` | `urlopen(..., timeout=...)` (see §5.b below) takes one timeout value covering both connect and read; hitting it raises `TimeoutError` (Python 3.10+; `socket.timeout` is now an alias of this built-in). Ruby's three-way split (open vs. read vs. generic) collapses to one Python type because Python's stdlib socket layer doesn't distinguish connect-phase from read-phase timeouts at the exception-class level the way `net/http` does — an honest, unavoidable narrowing, not an oversight. |
| `OpenSSL::SSL::SSLError` | TLS handshake or negotiation failure | `ssl.SSLError` | Direct one-to-one: Python's `ssl` module wraps the same underlying OpenSSL library, and raises this (or a subclass, e.g. `SSLEOFError`, `SSLZeroReturnError`) for any TLS-layer failure. Catching the parent class catches all of them, same as Ruby catching `OpenSSL::SSL::SSLError`. |
| `SocketError` | Low-level socket/address failure — in practice here, DNS resolution failure | `socket.gaierror` | Ruby's `SocketError` is a broad catch-all for socket construction failures; the case this guards against in an API-client retry loop is almost always DNS (`getaddrinfo` failing for the target host). `socket.gaierror` is the exact Python exception for that — narrower than Ruby's `SocketError`, an accepted deliberate narrowing rather than reaching for the much broader `OSError` (which would also swallow unrelated bugs). |

Resulting Python constant:

```python
TRANSIENT_ERRORS = (
    urllib.error.URLError,
    TimeoutError,
    ConnectionError,
    ssl.SSLError,
    EOFError,
    socket.gaierror,
)
```

No workaround for Ruby's commented-out `ca_file` / `OpenSSL::X509::DEFAULT_CERT_FILE` block is
needed on the Python side: `urllib.request`'s HTTPS handling uses `ssl.create_default_context()`
by default, which locates the OS's trusted CA store automatically and portably (Linux, WSL2,
macOS). Ruby's README aside about manually pointing at a cert file is a `net/http`-specific
wrinkle that doesn't carry over — noted as dropped content in §3.6, not silently lost.

#### 3.5.3 Full class

```python
import json
import socket
import ssl
import time
import urllib.error
import urllib.request

from .errors import ApiError


class Client:
    RETRYABLE_STATUS_CODES = {408, 409, 429, 500, 502, 503, 504}
    TRANSIENT_ERRORS = (
        urllib.error.URLError,
        TimeoutError,
        ConnectionError,
        ssl.SSLError,
        EOFError,
        socket.gaierror,
    )
    MAX_RETRIES = 3
    BASE_RETRY_DELAY = 0.5
    TIMEOUT = 30

    def __init__(self, builder):
        self._builder = builder

    def call(self, max_output_tokens=1024):
        body = json.dumps(self._builder.to_api_payload(max_output_tokens)).encode("utf-8")
        request = urllib.request.Request(
            self._builder.url(),
            data=body,
            headers=self._builder.headers(),
            method="POST",
        )

        attempts = 0
        status = None
        response_body = None

        while True:
            attempts += 1

            try:
                # HTTPError MUST be caught before TRANSIENT_ERRORS. HTTPError is a
                # subclass of URLError, which is itself one of the transient errors
                # below — if URLError were checked first, it would also match every
                # HTTPError, so every non-2xx response would be misclassified as a
                # transient network failure instead of reaching the status-code
                # check below.
                with urllib.request.urlopen(request, timeout=self.TIMEOUT) as resp:
                    status = resp.status
                    response_body = resp.read().decode("utf-8")
            except urllib.error.HTTPError as e:
                # Records status and body only — does not retry here. Whether this
                # status is retryable is decided once, below, after both the
                # success path and this path have converged.
                status = e.code
                response_body = e.read().decode("utf-8")
            except self.TRANSIENT_ERRORS as e:
                if attempts > self.MAX_RETRIES:
                    raise ApiError(
                        f"API request failed after {attempts} attempts: {type(e).__name__}: {e}"
                    ) from e
                time.sleep(self._retry_delay(attempts))
                continue

            if status in self.RETRYABLE_STATUS_CODES and attempts <= self.MAX_RETRIES:
                time.sleep(self._retry_delay(attempts))
                continue

            break

        if not (200 <= status < 300):
            plural = "" if attempts == 1 else "s"
            raise ApiError(f"API request failed after {attempts} attempt{plural} ({status}): {response_body}")

        return json.loads(response_body)

    def _retry_delay(self, attempt):
        return self.BASE_RETRY_DELAY * (2 ** (attempt - 1))
```

Notes on individual lines:
- `RETRYABLE_STATUS_CODES` as a `set`, not a `list` — same values, `in` membership check is
  the only use, a set is the idiomatic Python container for that (no ordering or duplicates
  matter here, unlike `MODELS` tables in `03_prompt_builder` which are ordered dicts of real
  data).
- `TIMEOUT = 30` — a class constant with no Ruby counterpart (Ruby's `net/http` has separate
  `open_timeout`/`read_timeout` defaults of its own that this port never touches). It has to
  exist here: `TimeoutError` is listed in `TRANSIENT_ERRORS`, but nothing raises it unless
  `urlopen` is given an explicit `timeout=` — without this, that branch of the retry logic
  would be dead code.
- The two `except` clauses and their order are load-bearing, not stylistic — see the inline
  comment in the code and the ordering constraint called out in §3.5.2's `URLError` row.
- `raise ApiError(...) from e` — Python's explicit exception-chaining syntax; no Ruby
  equivalent needed in the ledger since Ruby doesn't have this distinction, but it's the
  idiomatic way to preserve the original transient error as context without changing the
  raised type.
- Retry math (`BASE_RETRY_DELAY * (2 ** (attempt - 1))`) and control flow (loop, `attempts`
  counter, `attempts > MAX_RETRIES` on transient errors vs. `attempts <= MAX_RETRIES` on
  retryable status codes) are ported statement-for-statement, including the asymmetric
  `>`/`<=` comparison Ruby itself uses in the two branches.

### 3.6 `examples/example.py` rewrite (mirrors `example.rb`)

Changes from `03_prompt_builder`'s version, in order:

1. **Tools:** `look`/`move` removed. Two new tools registered:
   ```python
   @registry.tool("read_file",
       description="Read the contents of a file from disk",
       parameters={"path": {"type": "string", "description": "The file path to read"}})
   def read_file(path):
       return Path(path).read_text()


   @registry.tool("list_directory",
       description="List files in a directory",
       parameters={"path": {"type": "string", "description": "The directory path to list"}})
   def list_directory(path):
       return "\n".join(name for name in os.listdir(path) if not name.startswith("."))
   ```
   `read_file` uses `Path(path).read_text()` (not `open(path).read()`) — consistent with
   `Path` already being the established idiom elsewhere in this port (`Config.PROMPTS_DIR`,
   `_read_file` in `tasks/base.py`). `list_directory` uses `os.listdir(path)`, not
   `Path(path).iterdir()` — `os.listdir` already excludes `.`/`..` the way Ruby's
   `Dir.entries` does *after* its `.reject { |f| f.start_with?(".") }` filter; the explicit
   `not name.startswith(".")` filter is still needed for other dotfiles, matching Ruby's
   `reject` exactly. Both converge on the same filtered set (iteration order isn't asserted by
   either language's example).
2. **History seeding:** the scripted 3-message exchange is removed. Only:
   ```python
   ctx.add_message("user", "What files are in the current directory?")
   ```
3. **Banner moved, and reworded per established precedent:** Ruby moves
   `puts "=== BOUKENSHA Step 4: API Client ==="` from right after `ctx`/`registry` setup to
   right before the `Config`/`Provider`/`Model` prints (after `client` is built). Python
   ports the *position* change and keeps applying the casing precedent
   `03_prompt_builder.md` §3.10 point 8 already established (Title Case `"Boukensha"`, not
   Ruby's all-caps `"BOUKENSHA"`, but keeping the `===` markers, matching
   `03_prompt_builder/examples/example.py`'s existing
   `print("=== Boukensha Step 3: Prompt Builder ===")`):
   ```python
   print("=== Boukensha Step 4: API Client ===")
   ```
   placed where Ruby now places its banner line, not where the Python file previously had it.
4. **Provider branch:** same five branches, same logic, reordered to match Ruby's new
   ordering (anthropic, openai, gemini, ollama, ollama_cloud) purely for line-by-line
   diffability against the Ruby source — no behavioral difference.
5. **`Client` wiring, replacing the final print block:**
   ```python
   builder = PromptBuilder(ctx, backend)
   client = Client(builder)

   print("=== Boukensha Step 4: API Client ===")
   print()
   print(f"Config: {config}")
   print(f"Provider: {provider}")
   print(f"Model: {model}")
   print(f"Sending request to {builder.url()}...")
   print()

   response = client.call()
   print("Raw response:")
   print(json.dumps(response, indent=2))
   ```
   No API call was ever made before this step — this is the first point in the Python port
   where a real network request happens.
6. `from boukensha import Config, Context, Player, PromptBuilder, Registry` gains `Client`;
   `import os`, `import json` stay; `from pathlib import Path` stays (already imported,
   now also used by `read_file`).

### 3.7 `prompts/system.md`

Data file, copied verbatim, no ledger translation needed:

```
You are Boukensha, an autonomous player exploring a CircleMUD world.

Use available tools to observe the world, act deliberately, and explain only what matters for the current turn.
```

### 3.8 `README.md` — rewrite following Ruby's new structure, with two deliberate omissions

Follow Ruby's new sections (intro on what the API Client does, New Files / Updated Files
tables, `Client` architecture diagram, `Client` method table, Task Configuration section
carried forward, No Dependencies section, "What the Response Looks Like" JSON examples for
Anthropic and Ollama, Output example, Considerations) but:

- Title: `# 04 · The API Client (Python port)`, matching the `# 03 · ...` precedent, and
  reference this plan file at the top the same way `03_prompt_builder`'s README does.
- File paths and class references use the real Python paths/names
  (`boukensha/client.py`, `Client`, `ApiError`), not `Boukensha::`-prefixed Ruby forms.
- **Ruby's "OpenSSL Certificate" section is dropped, not translated.** It's a `net/http`-
  specific, largely macOS-specific wrinkle (manually locating a cert file). Python's
  `urllib.request` finds system CA certs automatically via `ssl.create_default_context()`
  (see §3.5.2) — there is nothing to work around, so nothing to document as a workaround.
  Replaced with a short paragraph pointing at this plan's §3.5.2 exception-mapping table,
  since that (not a cert-path aside) is this port's actual stdlib-HTTP judgment call worth a
  reader's attention.
- The "Output eaxmple" section header typo is fixed to "Output example" in the Python
  README — a plain spelling correction to source prose being copied, not a reopened design
  decision. The transcript itself is adapted (Python launcher invocation, same illustrative
  point that the agent has no `list_directory` tool and says so) and kept clearly illustrative
  — actual output depends on the configured provider/model/API key, same caveat that already
  applies to every non-deterministic example in this port.
- Considerations section: port the `ApiError`-on-failure bullet and add a note about the
  retry behavior (transient errors and retryable status codes retried up to `MAX_RETRIES`
  times) — Ruby's own Considerations section is silent about the retry logic it already
  implements in `client.rb`; the Python README documents it since the exception-mapping work
  in §3.5.2 makes it worth surfacing, not because Ruby's behavior changed.
- Run Example points at `./week1_baseline/bin/python/04_api_client`.

---

## 4. Launcher: `week1_baseline/bin/python/04_api_client`

New file, copy of `bin/python/03_prompt_builder` verbatim except the step-name path segments:

```bash
#!/usr/bin/env bash

cd "$(dirname "$0")/../../python/04_api_client"

REPO_ROOT="$(git rev-parse --show-toplevel)"
VENV_PYTHON="$REPO_ROOT/.venv/bin/python"

if [ ! -x "$VENV_PYTHON" ]; then
  echo "Missing shared virtualenv at $REPO_ROOT/.venv" >&2
  echo "Create it with:" >&2
  echo "  python3 -m venv $REPO_ROOT/.venv" >&2
  echo "  $REPO_ROOT/.venv/bin/pip install -r $(pwd)/requirements.txt" >&2
  exit 1
fi

"$VENV_PYTHON" -m examples.example
```

Must be marked executable (`chmod +x`) after creation.

---

## 5. Verification

1. `cd week1_baseline/ruby/04_api_client && bundle exec ruby examples/example.rb` — requires a
   real, working API key for whichever provider `settings.yaml` configures (this step makes an
   actual network call). Re-run only if the Ruby source changes, to sanity-check reference
   behavior.
2. `chmod +x week1_baseline/bin/python/04_api_client && ./week1_baseline/bin/python/04_api_client`
   — should print `Config`, `Provider`, `Model`, `Sending request to ...`, then a
   pretty-printed raw JSON response from the real API.
3. Confirm `ApiError` fires correctly:
   - Temporarily use an invalid API key, run the launcher, and confirm `ApiError` is raised
     with the attempt count and status code in the message.
   - If feasible, simulate a transient failure (e.g. stop `ollama serve` mid-run for the
     `ollama` provider) and confirm retries happen (visible delay, matching
     `BASE_RETRY_DELAY * 2**(attempt-1)` backoff) before the final `ApiError`.
4. Confirm the two new tools are registered correctly (`ctx.tools.keys()` shows `read_file`
   and `list_directory`, not `look`/`move`), and that calling `list_directory(".")` /
   `read_file(<some file>)` by hand through `registry.dispatch` returns sane output.
5. `git status` — confirm only the intended files are new/changed
   (`boukensha/client.py`, `boukensha/errors.py`, `boukensha/tasks/base.py`,
   `boukensha/__init__.py`, `examples/example.py`, `prompts/system.md`, `README.md`,
   `bin/python/04_api_client`) and that `boukensha/config.py` is untouched, with no stray
   `__pycache__/`, `.pyc`, or venv/`.env` files staged.

---

## 6. Constraints honoured

- Nothing added, renamed, or deleted at the repository root.
- All code lands under `week1_baseline/python/04_api_client/` plus the one launcher file
  under `week1_baseline/bin/python/`.
- `week1_baseline/ruby/**` is not modified.
- `context.py`, `tool.py`, `message.py`, `registry.py`, `prompt_builder.py`, `backends/*.py`,
  `tasks/player.py` are not touched — confirmed unchanged on the Ruby side too.
- `boukensha/config.py` is deliberately left untouched — the `PROMPTS_DIR` decision was made
  before this plan and is not reopened (see Context, point 1).
- Standard-library HTTP only (`urllib.request`, `urllib.error`, `socket`, `ssl`) — no
  third-party package added, `requirements.txt` unchanged, matching Ruby's own `net/http`-only
  choice, and matching the instructor's own Python baseline's choice of `urllib.request`.
- The transient-error mapping (§3.5.2) is the one place this delta required genuine judgment
  rather than mechanical translation; every Python exception chosen is justified by failure
  category, not by name resemblance, and the one unavoidable narrowing (three Ruby timeout
  classes collapsing into Python's single `TimeoutError`) is called out explicitly rather than
  silently absorbed.
- This plan was written before implementation, in `docs/plans/python_port/`, per project
  rules.
