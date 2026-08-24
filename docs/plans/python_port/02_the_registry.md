# Porting Plan — `02_the_registry`: Ruby → Python (delta only)

**Status:** plan only. No Python written yet.
**Source:** `week1_baseline/ruby/02_the_registry/` (ExamPro reference, not to be modified)
**Target:** `week1_baseline/python/02_the_registry/` — already exists, confirmed by
`diff -rq` to be a byte-identical copy of the finished `week1_baseline/python/01_struct_skeleton/`
tree (including that README's title, still "00 · Configuration" — an inherited
documentation debt from `01_struct_skeleton`, not part of this step's delta).

---

## Context

`01_struct_skeleton` is done in both languages and is **not re-ported**. `02_the_registry`
only adds a `Registry` class and an `UnknownToolError`, and changes how a tool's body
gets attached. `context.py` (formerly `context.rb`) is untouched — Ruby's README flags
that `Context` still owns `tools{}` while `Registry` is a thin facade over it, and defers
the fix to a later step. This plan reproduces that, unfixed.

Grounding documents used to write this plan, not re-derived from scratch:
- `docs/study_notes/ruby_idiom_ledger.md` — committed idiom translations
  (custom-error class, `raise`/`rescue`, `hash[key]`, decorator-vs-block, `transform_keys`)
- `docs/study_notes/w1_the_registry_python_port.md` — personal walkthrough notes for
  this exact step, including the design decisions in §2–§4 below

---

## 1. What the Ruby delta actually is

Per the task brief, confirmed by reading `ruby/02_the_registry` against `ruby/01_struct_skeleton`:

| Change | File |
|---|---|
| new | `lib/boukensha/registry.rb` — `Registry` class: `tool(name, description:, parameters:, &block)`, `dispatch(name, args)` |
| new | `lib/boukensha/errors.rb` — `UnknownToolError < StandardError` |
| edited | `lib/boukensha.rb` — 2 new `require_relative` lines (`registry`, `errors`) |
| edited | `examples/example.rb` — rewritten to build a `Registry`, register two tools (`move`, `shout`) through it instead of directly on `Context`, dispatch three calls (two hits, one miss caught) |
| edited | `README.md` — documents `Registry`/`UnknownToolError`, the block→symbol-keys gotcha, and (twice) the unfixed `Context`/`Registry` tool-ownership overlap |

`context.rb` / `context.py`, `tool.rb` / `tool.py`, `message.rb` / `message.py`,
`config.rb` / `config.py` are **not touched** by this step in either language.

### Live reference output

Captured from the Ruby README's "Expected Output" section (`ruby/02_the_registry/README.md`):

```
=== BOUKENSHA Step 2: Tool Registry ===

Context: #<Context turns=0 tools=2 budget=8192>
Tools:
  #<Tool name=move description="Move the player in a direction (north, south, east, west, up, down)" params=[:direction]>
  #<Tool name=shout description="Shout a message so everyone in the zone can hear it" params=[:message]>

Dispatching 'shout' with message='dragon spotted'...
Result: DRAGON SPOTTED

Dispatching 'move' with direction='north'...
Result: You move north into a torch-lit corridor.

UnknownToolError caught: No tool registered as 'flee'
```

As with `01_struct_skeleton`, the README's `Context` line is aspirational —
`context.rb` has no `budget` field and its real `to_s` (unchanged from step 1) prints
`#<Context task=... turns=... tools=...>`. The actual `Config`/`Context` header lines
in the Python port should follow the real `example.rb` output, not the README's,
matching the precedent set in the `01_struct_skeleton` plan (§1 there).

---

## 2. File-by-file mapping

| Ruby file | Python counterpart | Action |
|---|---|---|
| `lib/boukensha/registry.rb` | `boukensha/registry.py` | create |
| `lib/boukensha/errors.rb` | `boukensha/errors.py` | create |
| `lib/boukensha.rb` | `boukensha/__init__.py` | edit — add 2 exports (`Registry`, `UnknownToolError`) |
| `examples/example.rb` | `examples/example.py` | edit — rewritten body |
| `README.md` | `README.md` | edit — describe `Registry`/`UnknownToolError`, keep the ownership-overlap caveat |
| — | `week1_baseline/bin/python/02_the_registry` | create — new launcher, no Ruby counterpart to map from |

Not touched: `boukensha/context.py`, `boukensha/tool.py`, `boukensha/message.py`,
`boukensha/config.py`, `boukensha/tasks/*.py`, `prompts/system.md`, `requirements.txt`.

---

## 3. Design decisions (already resolved by prior study notes)

### 3.1 `UnknownToolError` — plain `Exception` subclass

Ledger row: `class X < StandardError; end` → `class X(Exception): pass`. So
`boukensha/errors.py`:

```python
class UnknownToolError(Exception):
    pass
```

No message-formatting logic lives on the class — same as Ruby, the message string is
built at the `raise` call site (`raise UnknownToolError, "No tool registered as '#{name}'"`
→ `raise UnknownToolError(f"No tool registered as '{name}'")`), per the ledger's
`raise X, "msg"` → `raise X("msg")` row.

### 3.2 `Registry` — plain class wrapping a `Context`

Mirrors Ruby's `Registry`: holds one `@context` reference, no state of its own.

```python
class Registry:
    def __init__(self, context):
        self.context = context

    def tool(self, name, description, parameters=None):
        def decorator(fn):
            t = Tool(name, description, parameters or {}, fn)
            self.context.register_tool(t)
            return fn
        return decorator

    def dispatch(self, name, args=None):
        tool = self.context.tools.get(name)
        if tool is None:
            raise UnknownToolError(f"No tool registered as '{name}'")
        return tool.block(**(args or {}))
```

Design notes, each already settled by prior study:

- **`tool()` returns a decorator, not a direct registration call.** Ruby attaches a
  tool's body via a trailing block (`registry.tool(...) do |direction:| ... end`).
  Python's twin for "a chunk of code handed to a call, to be run later" is a decorator
  sitting on the `@` line directly above a `def` — ledger row `method(...) do |x:| ... end`
  → `@decorator` line above a `def`. A `lambda=` keyword argument was considered and
  rejected (see `w1_the_registry_python_port.md` §D2): a `lambda` holds exactly one
  expression, so the first tool needing a multi-line body would stop compiling. The
  decorator's body is an ordinary `def` with no such ceiling.
- **`parameters=None` then `parameters or {}`**, not `parameters={}` — ledger row
  `def f(parameters: {})` → avoids Python's shared-mutable-default-argument trap
  (same category of bug as the `Context.messages` default flagged in the
  `01_struct_skeleton` plan §3.2, applied here to a keyword argument instead of a
  dataclass field).
- **`self.context.tools.get(name)`, not `self.context.tools[name]`** — ledger row
  `hash[key]` → `dict.get(key)`. Ruby's `@context.tools[name.to_s]` returns `nil` on a
  miss and the very next line checks for that with `unless tool`; Python's `.get()` is
  the direct twin, returning `None` on a miss, checked with `if tool is None`.
- **`tool.block(**(args or {}))`, not `tool.block.call(**args)`** — Ruby's `.call` is
  needed because `block` is a `Proc` object; Python functions are already callable, so
  the call is `tool.block(...)` with no intermediate method. Ledger row
  `block.call(**args)` → `fn(**args)`.

### 3.3 The `transform_keys(&:to_sym)` line is deleted, not translated

Ruby's `dispatch` does:

```ruby
tool.block.call(**args.transform_keys(&:to_sym))
```

`transform_keys(&:to_sym)` exists only because Ruby has two unrelated kinds of hash
key (string vs. symbol) and a block declared `do |direction:|` accepts only symbol
keys, while dispatch args arrive as string keys. Python has exactly one kind of
dict key — strings — so the dict already carries the exact labels `**` will turn into
argument names. There is nothing to adapt, so the line has no Python equivalent and
is dropped outright, per the ledger's `hash.transform_keys(&:to_sym)` row
(`n/a — Python dict keys stay strings`).

`registry.py`'s `dispatch` gets a short comment recording *why* the line is absent —
the reason is ported even though the code is not (`w1_the_registry_python_port.md`
§D3):

```python
def dispatch(self, name, args=None):
    tool = self.context.tools.get(name)
    if tool is None:
        raise UnknownToolError(f"No tool registered as '{name}'")
    # Ruby converts string keys to symbol keys here (`transform_keys(&:to_sym)`)
    # because its block syntax only accepts symbol keyword args. Python dict
    # keys are always strings already, so no conversion is needed.
    return tool.block(**(args or {}))
```

### 3.4 Faithful port: reproduce the unfixed `Context`/`Registry` overlap

`Registry.tool()` calls `self.context.register_tool(t)` — the tool table stays on
`Context`, exactly as in Ruby. `Registry` remains a facade: it offers the verbs but
stores nothing itself. **Do not** move `tools{}` onto `Registry` or otherwise "fix"
the overlap the Ruby README flags twice under "Considerations." Ruby corrects this in
a later step, which is its own lesson; fixing it early in Python would leave nothing
to port when that step arrives and the two tracks would diverge for good
(`w1_the_registry_python_port.md` §D4).

`context.py` is not opened for editing at all in this step.

### 3.5 `README.md` — document the real behaviour, correct only what's documentation

Follow the Ruby README's structure (New Files table, "How It Works", `Registry` /
`UnknownToolError` reference tables, Considerations section on the tool-ownership
overlap, Run Example) but:

- Point the "Run Example" command at `./week1_baseline/bin/python/02_the_registry`.
- Keep both "Considerations" paragraphs about the unfixed `Context`/`Registry`
  overlap — this is documentation of a real, reproduced property of the code, not
  aspirational content, so it stays.
- Use the real `Context.__str__` output (`#<Context task=... turns=... tools=...>`,
  no `budget` field) in any example output shown, consistent with how the
  `01_struct_skeleton` Python README already diverges from Ruby's aspirational one.
- No mention of `transform_keys`/symbol keys as a *Python* gotcha — that section in
  Ruby's README describes a Ruby-only quirk. Replace it with a short factual note
  that Python dict keys are always strings, so no such conversion step exists.

---

## 4. `examples/example.py` rewrite (mirrors `example.rb`)

In order:

1. Build `Config()`, fetch `player_settings = config.tasks("player")`, resolve
   `system_prompt` — same as `01_struct_skeleton`'s example, unchanged.
2. Build `ctx = Context(task=Player, system=system_prompt)`.
3. Build `registry = Registry(ctx)`.
4. Register `move` via decorator:
   ```python
   @registry.tool("move",
       description="Move the player in a direction (north, south, east, west, up, down)",
       parameters={"direction": {"type": "string"}})
   def move(direction):
       return f"You move {direction} into a torch-lit corridor."
   ```
5. Register `shout` via decorator:
   ```python
   @registry.tool("shout",
       description="Shout a message so everyone in the zone can hear it",
       parameters={"message": {"type": "string"}})
   def shout(message):
       return message.upper()
   ```
6. Print, in order: banner, `Config`, `Context`, `Tools:` followed by one line per
   `ctx.tools.values()` (ledger row `hash.each_value { |t| ... }` →
   `for t in dict.values():`).
7. `registry.dispatch("shout", {"message": "dragon spotted"})`, print the result.
8. `registry.dispatch("move", {"direction": "north"})`, print the result.
9. `try: registry.dispatch("flee") / except UnknownToolError as e: print(...)` —
   ledger row `begin/rescue/end` → `try/except ... as e:`.

No API client, no agent loop, no network call — `move` and `shout` are registered
and dispatched locally only, proving the Registry's lookup-and-call mechanism.

---

## 5. `boukensha/__init__.py` edit

Add two lines, following the existing import order (data types after tasks, so
`Registry`/`UnknownToolError` go after the `01_struct_skeleton` imports):

```python
from .registry import Registry
from .errors import UnknownToolError
```

Matches the ledger row `require_relative "errors"` → `from .errors import UnknownToolError`.

---

## 6. Launcher: `week1_baseline/bin/python/02_the_registry`

New file, no Ruby counterpart to map — Ruby's `bin/ruby/02_the_registry` exists but is
a different language's script. Copy the exact style of `bin/python/01_struct_skeleton`
verbatim except for the two path segments naming the step:

```bash
#!/usr/bin/env bash

cd "$(dirname "$0")/../../python/02_the_registry"

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

Must be marked executable (`chmod +x`) after creation — an unmarked script fails with
`Permission denied` on first run.

---

## 7. Verification

1. `cd week1_baseline/ruby/02_the_registry && bundle exec ruby examples/example.rb` —
   compare against §1's captured output (re-run only if Ruby source changes).
2. `chmod +x week1_baseline/bin/python/02_the_registry && ./week1_baseline/bin/python/02_the_registry`
   — compare line-by-line against §1. Expected differences only: no `Boukensha::`
   prefix, `params=['direction']` / `params=['message']` vs `[:direction]` / `[:message]`,
   and the real `Context` line (`task=... turns=... tools=...`, no `budget`) instead of
   the README's aspirational one.
3. Confirm the `UnknownToolError` path: the `flee` dispatch must raise, get caught, and
   the script must still exit 0 (the `try/except` must not let the exception propagate).
4. Confirm `dispatch` accepts string-keyed dicts directly with no key conversion step,
   and that removing the (absent) conversion didn't silently break anything — i.e. the
   `move`/`shout` calls succeed with plain `{"direction": "north"}` / `{"message": "dragon spotted"}` dicts.
5. `git status` — confirm only the intended files are new/changed
   (`boukensha/registry.py`, `boukensha/errors.py`, `boukensha/__init__.py`,
   `examples/example.py`, `README.md`, `bin/python/02_the_registry`) and no stray
   `__pycache__/`, `.pyc`, or venv files are staged.

---

## 8. Constraints honoured

- Nothing added, renamed or deleted at the repository root.
- All code lands under `week1_baseline/python/02_the_registry/` plus the one launcher
  file under `week1_baseline/bin/python/`.
- `week1_baseline/ruby/**` is not modified.
- `context.py` is not touched — the `Context`/`Registry` tool-ownership overlap
  the Ruby README flags twice is reproduced unfixed, not corrected early.
- No API client, no agent loop/runtime, no formal test suite is introduced.
- Ruby's `args.transform_keys(&:to_sym)` is dropped, not translated, with a short
  comment in its place explaining why (§3.3).
- This plan was written before implementation, in `docs/plans/python_port/`, per
  project rules.
