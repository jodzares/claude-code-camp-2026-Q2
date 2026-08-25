# Porting Plan — `03_prompt_builder`: Ruby → Python (delta only)

**Status:** plan only. No Python written yet.
**Source:** `week1_baseline/ruby/03_prompt_builder/` (ExamPro reference, not to be modified)
**Target:** `week1_baseline/python/03_prompt_builder/` — already exists, confirmed by
`diff -rq` to be a byte-identical copy of the finished `week1_baseline/python/02_the_registry/`
tree (`__pycache__/` excluded).

---

## Context

`02_the_registry` is done in both languages and is **not re-ported**. `03_prompt_builder`
adds exactly one new concept — turning a `Context` into the exact JSON one LLM provider
expects — plus the five provider adapters that make that possible. `context.py`, `tool.py`,
`message.py`, `registry.py`, `tasks/base.py`, `tasks/player.py` are untouched: confirmed by
diffing the Ruby files behind each (only a trailing-newline diff in `context.rb`, otherwise
byte-identical to `02_the_registry`).

Grounding documents used to write this plan, not re-derived from scratch:
- `docs/study_notes/ruby_idiom_ledger.md` — committed idiom translations, rows through
  "w1 Prompt Builder Ruby" (`def self.foo`, `MODELS = {...}.freeze`, `const_get`,
  `NotImplementedError`, `ENV.fetch`/`ENV[...] ||=`, `hash.fetch`, `case/when`, `.map`,
  `.values`, `.keys.sort.join`, symbol-as-value, digit separators, string interpolation,
  `.inspect`, `JSON.pretty_generate`)
- `docs/study_notes/w1_prompt_builder_ruby.md` — the five design decisions (D1–D5) behind
  this step, in particular D2 (five adapters, not one branching builder — and the arity
  crack that comes with it) and D3 (the builder receives an adapter, it never picks one)
- `docs/study_notes/w1_prompt_builder_diagramming.md` — confirms the architecture shape
  (Context → PromptBuilder → one of five Backends → dotted, not-yet-built API)
- Two open questions were resolved with you before writing this plan (§3.4 `model_info`,
  §3.3 backend namespace) — both decisions are recorded below with the reasoning you gave.

---

## 1. What the Ruby delta actually is

Confirmed by diffing `ruby/03_prompt_builder` against `ruby/02_the_registry`:

| Change | File |
|---|---|
| new | `lib/boukensha/prompt_builder.rb` — `PromptBuilder`: holds a `Context` + one backend, forwards 5 questions |
| new | `lib/boukensha/backends/base.rb` — shared model-table validation + cost math, abstract `MODELS` contract |
| new | `lib/boukensha/backends/anthropic.rb`, `gemini.rb`, `ollama.rb`, `ollama_cloud.rb`, `openai.rb` — one adapter per provider |
| edited | `lib/boukensha/errors.rb` — adds `UnsupportedModelError < StandardError` |
| edited | `lib/boukensha/config.rb` — adds `PROMPTS_DIR` (default prompts dir shipped with the code) |
| edited | `lib/boukensha.rb` — 7 new `require_relative` lines (errors moved before registry, then `prompt_builder`, then the 6 backend files) |
| edited | `examples/example.rb` — rewritten: registers `look` + `move` (no `shout`), seeds 3 messages by hand instead of dispatching, builds one backend from `settings.yaml`'s provider, builds a `PromptBuilder`, prints the pretty-printed API payload |
| edited | `README.md` — full rewrite: architecture diagram, backend reference tables, per-provider JSON shape comparisons, no "Expected Output" section this time |

Not touched: `context.rb`/`.py`, `tool.rb`/`.py`, `message.rb`/`.py`, `registry.rb`/`.py`,
`tasks/base.rb`/`.py`, `tasks/player.rb`/`.py`, `Gemfile`/`requirements.txt`
(no new dependency — nothing here calls the network).

---

## 2. File-by-file mapping

| Ruby file | Python counterpart | Action |
|---|---|---|
| `lib/boukensha/prompt_builder.rb` | `boukensha/prompt_builder.py` | create |
| `lib/boukensha/backends/base.rb` | `boukensha/backends/base.py` | create |
| `lib/boukensha/backends/anthropic.rb` | `boukensha/backends/anthropic.py` | create |
| `lib/boukensha/backends/gemini.rb` | `boukensha/backends/gemini.py` | create |
| `lib/boukensha/backends/ollama.rb` | `boukensha/backends/ollama.py` | create |
| `lib/boukensha/backends/ollama_cloud.rb` | `boukensha/backends/ollama_cloud.py` | create |
| `lib/boukensha/backends/openai.rb` | `boukensha/backends/openai.py` | create |
| `lib/boukensha/errors.rb` | `boukensha/errors.py` | edit — add `UnsupportedModelError` |
| `lib/boukensha/config.rb` | `boukensha/config.py` | edit — add `PROMPTS_DIR` |
| `lib/boukensha.rb` | `boukensha/__init__.py` | edit — see §3.7 |
| `examples/example.rb` | `examples/example.py` | edit — rewritten body |
| `README.md` | `README.md` | edit — full rewrite |
| — | `boukensha/backends/__init__.py` | create — empty package marker, no Ruby counterpart (mirrors the existing empty `boukensha/tasks/__init__.py`) |
| — | `week1_baseline/bin/python/03_prompt_builder` | create — new launcher, copy of `02_the_registry`'s style |

Not touched: `boukensha/context.py`, `boukensha/tool.py`, `boukensha/message.py`,
`boukensha/registry.py`, `boukensha/tasks/base.py`, `boukensha/tasks/player.py`,
`prompts/system.md`, `requirements.txt`.

---

## 3. Design decisions

### 3.1 `boukensha/errors.py` — add `UnsupportedModelError`

```python
class UnknownToolError(Exception):
    pass


class UnsupportedModelError(Exception):
    pass
```

Same shape as the existing `UnknownToolError` — no message-formatting logic on the class,
the string is built at the `raise` call site, per the ledger's `raise X, "msg"` → `raise X("msg")` row.

### 3.2 `boukensha/config.py` — add `PROMPTS_DIR`

Ruby: `PROMPTS_DIR = File.expand_path("../../prompts", __dir__)` where `__dir__` is
`lib/boukensha/`, landing on `<step_root>/prompts`. `config.py` lives at
`boukensha/config.py`, so its own parent's parent is the step root:

```python
class Config:
    DEFAULT_DIR = Path.home() / ".boukensha"
    PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
```

`Path` is already imported in `config.py`; no new import needed. Class-level attribute,
readable as `Config.PROMPTS_DIR` without instantiating — matches how `example.py` will use
it (§3.8).

### 3.3 `boukensha/backends/` — a real subpackage, not flattened to the root

**Decision (confirmed with you):** the 5 backend classes + `Base` stay reachable only via
`boukensha.backends.<module>`, never re-exported through `boukensha/__init__.py`. This
mirrors Ruby's own choice to keep `Backends` a separate module from the top-level
`Boukensha::` namespace (unlike `Tasks::Player`, which Ruby also nests but the Python port
already chose to flatten to `boukensha.Player`).

Concretely: `boukensha/backends/__init__.py` stays **empty** — a plain package marker, the
same pattern already used by `boukensha/tasks/__init__.py` (confirmed empty). Each backend
is imported from its own submodule, not re-exported anywhere:

```python
from boukensha.backends.anthropic import Anthropic
from boukensha.backends.gemini import Gemini
from boukensha.backends.ollama import Ollama
from boukensha.backends.ollama_cloud import OllamaCloud
from boukensha.backends.openai import OpenAI
```

This is what `examples/example.py` will do (§3.8). No new re-export layer is invented that
doesn't already exist elsewhere in the port.

Class names are ported literally (`Anthropic`, `Gemini`, `Ollama`, `OllamaCloud`, `OpenAI`,
`Base`) — same as Ruby, including the `OpenAI` acronym casing.

### 3.4 `boukensha/backends/base.py` — the `model_info` name collision

Ruby's `Base` has a class method `self.model_info(model)` (look up an entry by name) *and*
an instance method `model_info` (return this instance's cached entry) — different Ruby
namespaces, no collision. Python doesn't separate those namespaces the same way.

**Decision (confirmed with you):** `model_info` stays the one public name, and it stays a
**classmethod only** — that's the documented public surface (the Ruby README's backend
reference table never lists an instance-level `model_info`; it lists `context_window`,
`input_token_cost_per_million`, `output_token_cost_per_million`, `usage_unit`,
`usage_level`, and `estimate_cost`). The resolved entry for *this* instance is cached in a
private `self._model_info`, read directly by the five property methods below — no public
instance accessor shares the name.

```python
from ..errors import UnsupportedModelError


class Base:
    @classmethod
    def models(cls):
        try:
            return cls.MODELS
        except AttributeError:
            raise NotImplementedError(f"{cls.__name__} must define MODELS")

    @classmethod
    def model_info(cls, model):
        return cls.models().get(str(model))

    @classmethod
    def validate_model(cls, model):
        model = str(model)
        if cls.model_info(model):
            return model
        supported = ", ".join(sorted(cls.models()))
        raise UnsupportedModelError(
            f"{cls.__name__} does not support model {model!r}. Supported models: {supported}"
        )

    def _configure_model(self, model):
        self.model = self.__class__.validate_model(model)
        self._model_info = self.__class__.model_info(self.model)

    @property
    def context_window(self):
        return self._model_info["context_window"]

    @property
    def input_token_cost_per_million(self):
        return self._model_info["cost_per_million"]["input"]

    @property
    def output_token_cost_per_million(self):
        return self._model_info["cost_per_million"]["output"]

    @property
    def usage_unit(self):
        return self._model_info["usage_unit"]

    @property
    def usage_level(self):
        return self._model_info.get("usage_level")

    def estimate_cost(self, input_tokens, output_tokens):
        in_cost = self.input_token_cost_per_million
        out_cost = self.output_token_cost_per_million
        if in_cost is None or out_cost is None:
            return None
        return ((input_tokens * in_cost) + (output_tokens * out_cost)) / 1_000_000.0
```

Notes on individual lines, each already settled:
- `cls.models()` uses try/except `AttributeError` for Ruby's `const_get(:MODELS) rescue
  NameError` — ledger row `const_get(:MODELS)` → `getattr(cls, "MODELS")`; a plain
  `cls.MODELS` access inside a `try` is the direct twin of that lookup-or-fail shape.
- `validate_model` drops Ruby's bang (`validate_model!`) — Python has no bang-method
  convention; the name alone (no `!`) is the idiomatic Python spelling of "this may raise."
- `self.__class__.validate_model(model)`, not `self.validate_model(model)` — mirrors
  Ruby's explicit `self.class.validate_model!(model)`, calling the type-level method from
  an instance.
- `model` itself (Ruby's `attr_reader :model`) becomes a plain instance attribute
  `self.model`, no property — ledger row `@foo` → `self.foo`, same as every other plain
  attribute in this port (no need for a property when nothing computes it).

### 3.5 `MODELS` tables — symbols become plain strings, values ported literally

Per the ledger row `:tokens` → `"tokens"` (or an `Enum`, rejected for the same reason
`Final` was rejected below — nothing else in this port uses one): `usage_unit` and
`usage_level` values become plain strings `"tokens"`, `"local_compute"`,
`"ollama_cloud_usage"`, `"medium"`, `"high"`. Hash **keys** were already strings in Ruby
(model name strings like `"claude-haiku-4-5"`), so no translation needed there.

Numbers with digit separators (`200_000`, `1_000_000.0`) are identical in Python — literal
port, per ledger row 38.

No `Final` type hint or other locking mechanism on `MODELS` — Ruby's `.freeze` has no true
Python equivalent (per the ledger's own admission on that row), and nothing elsewhere in
this port (e.g. `Config.DEFAULT_DIR`) uses one either. A plain class-level dict, exactly
like every other class-level constant already in this codebase.

Each of the 5 `MODELS` tables is ported as literal data — same model names, same
`context_window`, same `cost_per_million`, same `usage_unit`/`usage_level` values as the
Ruby source. No values are invented or updated.

### 3.6 Backend constructors — plain params, not keyword-only

Ruby's backend `initialize(api_key:, model:)` uses required *named* arguments (order-
independent, but each must be passed by name). The rest of this port has already
consistently dropped that requirement — `Context.__init__(self, task, system=None)` and
`Registry.tool(self, name, description, parameters=None)` both correspond to Ruby methods
with required keyword args, and both were ported as plain positional-or-keyword Python
params. Backends follow the same established precedent, for consistency:

```python
class Anthropic(Base):
    def __init__(self, api_key, model):
        self._api_key = api_key
        self._configure_model(model)
```

**One forced reordering:** Ruby's `Ollama#initialize(host: "http://localhost:11434",
model:)` has a defaulted param before a required one — legal in Ruby because both are
named. Python's positional-or-keyword params can't have a required param after a defaulted
one, so the two are swapped:

```python
class Ollama(Base):
    def __init__(self, model, host="http://localhost:11434"):
        self._host = host
        self._configure_model(model)
```

This never surfaces in `example.py` — the Ollama branch there only ever calls
`Ollama(model)`, no custom host — but the class itself has to compile for someone
instantiating it directly.

### 3.7 The five adapter bodies — literal per-backend port

Each backend's `to_messages`, `to_tools`, `to_payload`, `headers`, `url` are ported
statement-for-statement. Ruby's `case msg.role when :assistant ... when :tool_result ...
else ...` becomes an `if/elif/else` on plain string roles (`"assistant"`, `"tool_result"`,
matching how `ctx.add_message` is already called with plain strings, not symbols — no
symbol-to-string translation needed since Python's `Message.role` was already typed `str`).
Ruby's `.map { |t| ... }` becomes a list comprehension; `.values` becomes `.values()`;
`tool.parameters.keys.map(&:to_s)` becomes `list(tool.parameters.keys())` (already strings).

Anthropic and Gemini's `to_messages(messages)` take one argument; Ollama, OllamaCloud, and
OpenAI's `to_messages(system, messages)` take two — this asymmetry is real in Ruby (see
`w1_prompt_builder_ruby.md` §D2, "honest cost" #2: an arity mismatch) and is **ported as-is,
not fixed**. `PromptBuilder.to_messages()` always calls `self.backend.to_messages(self.context.messages)`
with one argument, so calling it directly against an Ollama/OllamaCloud/OpenAI backend would
raise a `TypeError` — same latent crack Ruby has, never triggered because `example.py`, like
`example.rb`, only ever calls `to_api_payload()` (which each backend's own `to_payload`
calls correctly, with the right arity internally). This is a faithful-port choice, same
category as the `Context`/`Registry` overlap left unfixed in the `02_the_registry` plan
(§3.4 there) — Ruby corrects it later, if at all, and that's its own lesson.

### 3.8 `boukensha/prompt_builder.py` — thin delegator

```python
class PromptBuilder:
    def __init__(self, context, backend):
        self.context = context
        self.backend = backend

    def to_messages(self):
        return self.backend.to_messages(self.context.messages)

    def to_tools(self):
        return self.backend.to_tools(self.context.tools)

    def to_api_payload(self, max_output_tokens=1024):
        return self.backend.to_payload(self.context, max_output_tokens)

    def headers(self):
        return self.backend.headers()

    def url(self):
        return self.backend.url()
```

Holds two references, computes nothing itself — same as Ruby, same as the precedent set by
`Registry` in `02_the_registry` (a facade with no state of its own).

### 3.9 `boukensha/__init__.py` edit

Ruby's `boukensha.rb` diff reorders `errors` before `registry`, then adds `prompt_builder`,
then the 6 backend requires (which stay un-flattened per §3.3, so nothing new is added to
`__init__.py` for them). Apply the matching Python edit:

```python
from .config import Config
from .tasks.player import Player
from .tool import Tool
from .message import Message
from .context import Context
from .errors import UnknownToolError, UnsupportedModelError
from .registry import Registry
from .prompt_builder import PromptBuilder
```

(`errors` moved above `registry`, its import extended to the new class; `prompt_builder`
appended after `registry` — matching Ruby's new require order line-for-line where a Python
equivalent exists.)

### 3.10 `examples/example.py` rewrite (mirrors `example.rb`)

In order:

1. `os.environ.setdefault("BOUKENSHA_DIR", ...)` — unchanged from `02_the_registry`, still
   `parents[4]` (repo root); this step doesn't move the example file, so the path depth is
   unaffected.
2. `config = Config()`, `player_settings = config.tasks("player")`.
3. `system_prompt = Player.system_prompt(player_settings, user_prompts_dir=config.user_prompts_dir, default_prompts_dir=Config.PROMPTS_DIR)`
   — the one call-site change from `02_the_registry`: `default_prompts_dir` is now passed,
   using the new `Config.PROMPTS_DIR` (§3.2). `Base.system_prompt`/`Base.prompt` in
   `tasks/base.py` already accept this parameter and were doing nothing useful with it
   until now (it defaulted to `None`, silently returning `None` from
   `_read_default_prompt`) — no change to `tasks/base.py` itself, this step just finally
   supplies the argument.
4. `ctx = Context(task=Player, system=system_prompt)`; `registry = Registry(ctx)`.
5. Register `look` — no parameters, no-arg function:
   ```python
   @registry.tool("look", description="Look around the current room for details", parameters={})
   def look():
       return "A damp stone corridor stretches north. Torches flicker on the walls."
   ```
6. Register `move` — same as `02_the_registry` but the `direction` parameter gains a
   `"description"` key (matches the Ruby diff):
   ```python
   @registry.tool("move",
       description="Move the player in a direction (north, south, east, west, up, down)",
       parameters={"direction": {"type": "string", "description": "The direction to move"}})
   def move(direction):
       return f"You move {direction} into a torch-lit corridor."
   ```
   `shout` is **removed** — not re-registered, not present anywhere in the new example.
7. Seed history directly (no `registry.dispatch` calls at all this step):
   ```python
   ctx.add_message("user", "I just arrived in the dungeon. What's around me, and can you move north?")
   ctx.add_message("assistant", "Let me take a look around first.")
   ctx.add_message("tool_result", "A damp stone corridor stretches north. Torches flicker on the walls.", tool_use_id="toolu_01X")
   ```
8. `print("=== Boukensha Step 3: Prompt Builder ===")` — "Boukensha" Title Case, not
   "BOUKENSHA", matching the casing precedent already set in `02_the_registry`'s ported
   banner.
9. `provider = Player.provider(player_settings)`; `model = Player.model(player_settings)`.
10. Provider switch — `if/elif/else` per the ledger's `case/when` → `if/elif/else` row,
    each branch importing lazily is unnecessary since all 5 backends are imported at the
    top of the file (§3.3):
    ```python
    if provider == "anthropic":
        backend = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"], model=model)
    elif provider == "ollama":
        backend = Ollama(model=model)
    elif provider == "ollama_cloud":
        backend = OllamaCloud(api_key=os.environ["OLLAMA_API_KEY"], model=model)
    elif provider == "openai":
        backend = OpenAI(api_key=os.environ["OPENAI_API_KEY"], model=model)
    elif provider == "gemini":
        backend = Gemini(api_key=os.environ["GEMINI_API_KEY"], model=model)
    else:
        raise ValueError(f"Unsupported provider for player task: {provider}")
    ```
    `os.environ["KEY"]` (not `.get`) mirrors Ruby's `ENV.fetch("KEY")` — both raise
    immediately if the variable is absent, matching the ledger's `ENV.fetch("K")` row. Ruby's
    `raise ArgumentError` maps to Python's `raise ValueError`, consistent with how
    `tasks/base.py` already translates Ruby's `ArgumentError` (`provider`/`model` required
    checks use `ValueError` there already).
11. `builder = PromptBuilder(ctx, backend)`.
12. Print, in order: `Config`, `Provider`, `Model`, then
    `print(json.dumps(builder.to_api_payload(), indent=2))` — ledger row
    `JSON.pretty_generate(x)` → `json.dumps(x, indent=2)`. `import json` added at the top.

No API call anywhere — same as Ruby, this step only ever builds and prints a payload.

### 3.11 `README.md` — full rewrite following Ruby's new structure

Follow Ruby's new sections (intro on multi-provider LLM access, New Files table, ASCII
architecture diagram, `PromptBuilder` method table, "Backends" section with the model-entry
key table, one subsection per backend naming its endpoint/required env var/`MODELS` table,
System Prompt / Tool Results / Tool Definitions / Message Roles JSON comparisons,
Considerations, Run Example) but:

- Title: `# 03 · The Prompt Builder (Python port)` — matches the `# 02 · ...` precedent.
- Reference this plan file at the top, same sentence pattern `02_the_registry`'s README
  uses (`docs/plans/python_port/03_prompt_builder.md`).
- File paths in the New Files table use `.py` and the real Python paths
  (`boukensha/prompt_builder.py`, `boukensha/backends/base.py`,
  `boukensha/backends/anthropic.py`, etc.).
- Class references use plain Python names (`PromptBuilder`, `Anthropic`, `Ollama`, ...),
  not `Boukensha::`-prefixed ones — matches how `02_the_registry`'s README already writes
  `boukensha.Registry`, `boukensha.UnknownToolError` instead of the Ruby-namespaced form.
- The JSON comparison blocks (System Prompt / Tool Results / Tool Definitions / Message
  Roles) are **copied verbatim** — they're plain JSON, provider wire formats, not Ruby or
  Python code, so nothing about them changes between ports.
- Ruby's README for this step has **no "Expected Output" section** (unlike
  `02_the_registry`'s), so none is invented for the Python port either — a full payload dump
  depends on which provider/model/API-key combination is configured locally, and isn't
  fixed reference data the way `02_the_registry`'s dispatch results were.
- Considerations section: port the three bullets (conversation is stateless; tool results
  are user messages on Anthropic specifically; the agent only sees schemas, never the
  Python function body) — these are true of the ported code exactly as they're true of
  Ruby's, no translation needed.
- Run Example points at `./week1_baseline/bin/python/03_prompt_builder`.

---

## 4. Launcher: `week1_baseline/bin/python/03_prompt_builder`

New file, no Ruby counterpart to map (Ruby's own `bin/ruby/03_prompt_builder` is a
different language's script). Copy `bin/python/02_the_registry` verbatim except the two
path segments naming the step:

```bash
#!/usr/bin/env bash

cd "$(dirname "$0")/../../python/03_prompt_builder"

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

1. `cd week1_baseline/ruby/03_prompt_builder && bundle exec ruby examples/example.rb` —
   requires a local `.env` with at least the configured provider's API key *present* (per
   the Ruby study note's landmine #3, it's never called, just read) and `.boukensha/settings.yaml`
   pointing `tasks.player.provider`/`model` at a supported combination. Re-run only if the
   Ruby source changes, to sanity-check the reference behaviour.
2. `chmod +x week1_baseline/bin/python/03_prompt_builder && ./week1_baseline/bin/python/03_prompt_builder`
   — should print `Config`, `Provider`, `Model`, then a pretty-printed JSON payload shaped
   correctly for whichever provider is configured. Confirm no network call is attempted
   (no delay, no error about connectivity).
3. Confirm the fail-fast paths independently, by temporarily editing `settings.yaml`/env:
   - An unsupported/misspelled model name raises `UnsupportedModelError` listing every
     valid model for that provider (mirrors Ruby's D4).
   - A missing required API key env var raises `KeyError` at the `os.environ[...]` lookup,
     not later.
   - An unsupported provider string raises `ValueError` naming the bad provider.
4. Confirm the two tools (`look`, `move`) print correctly if you inspect
   `ctx.tools.values()` manually, and that `shout` is genuinely gone (no leftover reference
   anywhere in `example.py`).
5. Spot-check one provider switch by hand (e.g. temporarily set `provider: ollama` with
   `ollama serve` running, or just inspect the built payload shape without sending it) to
   confirm the positional-shape differences from §3.7/README hold in the real output:
   `system` top-level for Anthropic/Gemini vs. folded into `messages` for Ollama/OpenAI.
6. `git status` — confirm only the intended files are new/changed
   (`boukensha/prompt_builder.py`, `boukensha/backends/*.py` including `__init__.py`,
   `boukensha/errors.py`, `boukensha/config.py`, `boukensha/__init__.py`,
   `examples/example.py`, `README.md`, `bin/python/03_prompt_builder`) and no stray
   `__pycache__/`, `.pyc`, or venv/`.env` files are staged.

---

## 6. Constraints honoured

- Nothing added, renamed, or deleted at the repository root.
- All code lands under `week1_baseline/python/03_prompt_builder/` plus the one launcher
  file under `week1_baseline/bin/python/`.
- `week1_baseline/ruby/**` is not modified.
- `context.py`, `tool.py`, `message.py`, `registry.py`, `tasks/base.py`, `tasks/player.py`
  are not touched — confirmed unchanged on the Ruby side too, so nothing to re-port.
- No HTTP client, no actual API call, no formal test suite introduced — this step only
  builds and prints a payload, exactly like Ruby.
- The Ollama-only constructor-parameter reorder (§3.6) and the `model_info` split (§3.4)
  are the only two points where Python's syntax forced a structural (not just cosmetic)
  divergence from Ruby; both were surfaced to you and decided before writing this plan.
- The latent arity mismatch in `PromptBuilder.to_messages()`/`to_tools()` against 3 of the
  5 backends (§3.7) is reproduced, not fixed — same category of faithful-port choice as
  the unfixed `Context`/`Registry` overlap from `02_the_registry`.
- This plan was written before implementation, in `docs/plans/python_port/`, per project
  rules.
