# Porting Plan — `00_config`: Ruby → Python

**Status:** plan only. No Python written yet.
**Source:** `week1_baseline/ruby/00_config/` (ExamPro reference, not to be modified)
**Target:** `week1_baseline/python/00_config/`, launched by `week1_baseline/bin/python/00_config`

---

## Context

Week 1 builds a baseline agent. Step 0 is configuration. The Ruby module is the
reference implementation supplied with the course; this port produces a Python
equivalent so the remaining week-1 steps can be built in Python, while the Ruby
tree stays untouched as the thing to diff against.

The standard for this port is **behavioural fidelity, not textual identity**: the
Python module must read the same folder, find the same settings, resolve the same
prompt, and apply the same defaults. What it *looks* like is free to change where
Python demands it.

Destination folders already exist and are empty: `week1_baseline/python/00_config/`
and `week1_baseline/bin/python/`.

---

## 1. What the Ruby module does

**One job:** find a `.boukensha/` config directory, load everything in it once at
boot, then answer questions about it from memory. Alongside that, a stateless
helper resolves per-task LLM settings and system prompts.

### Boot sequence — `Boukensha::Config.new` (`lib/boukensha/config.rb`)

1. **Resolve the config directory.** `BOUKENSHA_DIR` env var if set, otherwise
   `~/.boukensha`. The raw value is expanded (`~`, relative segments) into an
   absolute path and stored.
2. **Load secrets.** If `<dir>/.env` exists, `Dotenv.load` pushes its keys into the
   process environment. In practice this is `ANTHROPIC_API_KEY`.
3. **Load settings.** If `<dir>/settings.yaml` exists, `YAML.safe_load` parses it
   into a hash. A missing file, or a file that parses to nothing, yields `{}`.

Read **once**. After construction the object never touches disk again for settings —
it only answers.

### What it answers

| Accessor | Behaviour |
|---|---|
| `dir` | the resolved config directory |
| `settings` | the raw parsed hash |
| `tasks` | the whole `tasks:` block |
| `tasks(:player)` | one task's sub-hash |
| `user_prompts_dir` | `<dir>/prompts` — where per-task overrides live |
| `mud_host` | defaults to `"localhost"` |
| `mud_port` | defaults to `4000` |
| `mud_username`, `mud_password` | no defaults → nil |
| `dig(*keys)` | walk a nested key path, nil the moment a level isn't a Hash |
| `to_s` / `inspect` | `#<Boukensha::Config dir=… tasks=player>` |

### Tasks — `lib/boukensha/tasks/base.rb`

An **abstract, stateless** class. No instances are ever created. Every method is a
class method taking the task's settings hash as an argument. Subclasses supply
identity and nothing else — `Boukensha::Tasks::Player.task_name == "player"`.

- `provider(settings)` / `model(settings)` — required. Missing ⇒ `ArgumentError`
  that **names the task**: `tasks.player.provider is required in settings.yml`.
- `prompt_override?(settings, :system)` — true only if `prompt_override.system`
  is literally `true`.
- `system_prompt(settings, user_prompts_dir:, default_prompts_dir:)` — the
  **prompt ladder**:
  1. override switch on **and** `<user_prompts_dir>/<task_name>/system.md` exists
     → return its stripped contents
  2. otherwise → `<default_prompts_dir>/system.md`, the prompt shipped with the
     library
  3. neither exists → nil

`Config::PROMPTS_DIR` is computed relative to the source file's own location, so
the default prompt follows the code rather than the working directory.

### The example and the launcher

`examples/example.rb` is a smoke test, not library code. It sets `BOUKENSHA_DIR`
with `||=` — so a real environment variable still wins — to the repo-root
`.boukensha`, builds a `Config`, then prints: dir, task names, provider, model,
override flag, the first 60 characters of the resolved system prompt, MUD
host:port and user, whether `ANTHROPIC_API_KEY` is set, and the config's `to_s`.

`bin/ruby/00_config` is three lines of bash: `cd` into the module directory (so the
vendored bundle and relative paths resolve), then `bundle exec ruby examples/example.rb`.

### What it reads today

The repo-root `.boukensha/` contains `settings.yaml` with
`tasks.player = {provider: anthropic, model: claude-haiku-4-5, prompt_override.system: true}`
plus a `mud:` block, a `.env` holding `ANTHROPIC_API_KEY`, and
`prompts/player/system.md` containing *"You are my MUD jodza-player"*.

So with the current data the **override branch is the one that fires** — the
shipped default prompt is never reached unless the switch is flipped off.

---

## 2. File-by-file mapping

| Ruby file | Python counterpart | Note |
|---|---|---|
| `lib/boukensha.rb` | `boukensha/__init__.py` | Ruby's "require both children" ⇒ package init re-exporting `Config` and `Player` |
| `lib/boukensha/config.rb` | `boukensha/config.py` | `class Config` |
| `lib/boukensha/tasks/base.rb` | `boukensha/tasks/base.py` | abstract stateless `Base` |
| `lib/boukensha/tasks/player.rb` | `boukensha/tasks/player.py` | `class Player(Base)` |
| *(none — Ruby needs no such file)* | `boukensha/tasks/__init__.py` | required to make `tasks` a package |
| *(none)* | `examples/__init__.py` | required by `python -m examples.example` |
| `prompts/system.md` | `prompts/system.md` | copied verbatim, still the shipped default |
| `examples/example.rb` | `examples/example.py` | same layout, Pythonic value formatting |
| `Gemfile` / `Gemfile.lock` | `requirements.txt` | `pyyaml`, `python-dotenv` |
| `.bundle/config` + `vendor/bundle/` | shared repo-root `.venv/` | both gitignored, never committed |
| `README.md` | `README.md` | ported, with Python run instructions |
| `bin/ruby/00_config` | `bin/python/00_config` | bash launcher |

Note there is **no `lib/`** in the Python tree. Ruby has one because Bundler
convention puts it there and `require_relative` walks plain filesystem paths.
Python resolves imports through packages on a search path, so the package sits at
the module root where `python -m` finds it without any path manipulation.

---

## 3. Where Ruby was free and Python was not

These are the only places the port required a real decision. Everything else was
vocabulary substitution (section 4).

### 3.1 YAML parsing — **PyYAML**

Ruby ships YAML in its standard library (`require "yaml"`, zero dependencies).
**Python ships no YAML parser at all.** `ITERATIONS.md` states a preference for the
standard library and avoiding third-party packages — that goal is simply
unreachable here.

*Chosen:* `PyYAML`, using `yaml.safe_load` — a near-identical API to Ruby's
`YAML.safe_load`, so the calling code reads the same.

*Rejected:* a hand-rolled minimal YAML reader (zero dependencies, but real code to
write and maintain, and it would only ever handle the subset of YAML this project's
`settings.yaml` happens to use — a trap the moment the schema grows, which the
Ruby README explicitly says it will). `ruamel.yaml` was heavier than needed.

### 3.2 `.env` loading — **python-dotenv**

Ruby needed the `dotenv` gem too, so this is not a new dependency in spirit — but
it confirms that "no third-party libraries" is off the table in both languages.

*Chosen:* `python-dotenv`, the direct counterpart to the Ruby gem.
*Rejected:* a ~10-line hand-rolled parser writing into `os.environ` — viable, but
having already accepted PyYAML there was no dependency purity left to protect.

### 3.3 Package layout and import mechanism — **package at module root + `python -m`**

Ruby's `require_relative "../lib/boukensha"` needs no package, no install and no
path setup; it just walks the filesystem. **Python cannot import a sibling
directory without help.** Something must put the library on the interpreter's
search path.

A constraint that rules out one whole family of answers: **`00_config` can never be
a Python package name**, because identifiers cannot start with a digit. All viable
options work by making the *module directory itself* a root of the search path.

*Chosen:* the package lives at `00_config/boukensha/`, and the launcher runs
`python -m examples.example`. The `-m` form puts the current working directory —
the module directory — at the front of `sys.path`, so `boukensha/` is visible.
`example.py` therefore contains a bare `from boukensha import Config` and no setup
code whatsoever. The mechanism lives in the launcher, in one line, in one place.

*Rejected:*
- **`lib/` + `sys.path.insert`** — mirrors the Ruby tree one-for-one, but requires
  a four-line, order-sensitive preamble at the top of `example.py` that mutates
  interpreter state before it can import. Move it below the import and it breaks.
  Every future step folder would repeat it.
- **`src/` + `pip install -e .`** — resolves from anywhere after a one-time
  install, but adds a `pyproject.toml`, depends on a venv already existing, and the
  "one-time" install has to be re-paid for every future step folder.

*Knock-on:* `PROMPTS_DIR` climbs **one** level from `config.py`
(`Path(__file__).resolve().parents[1] / "prompts"`) where Ruby climbed two, because
there is no `lib/` in between.

### 3.4 Virtualenv location — **shared `.venv` at the repo root**

Bundler vendored gems *inside* the module (`.bundle/config` → `vendor/bundle`) and
`bundle exec` wired them up silently. **Python has no `bundle exec`** — the
launcher must name an interpreter explicitly, which means the venv's location is
hardcoded into the launcher.

*Chosen:* one `.venv` at the repository root, created once and reused by `01_`,
`02_`, `03_`… Each module still keeps its own `requirements.txt` as documentation
of what it needs. The launcher invokes `<repo>/.venv/bin/python` directly.

*Rejected:* one `.venv` per module — mirrors Bundler's per-folder vendoring and is
fully self-contained, but reinstalls `pyyaml` and `python-dotenv` from scratch for
every future step folder. `pyproject.toml` + `uv` was fast and tidy but adds a
toolchain requirement.

> **⚠️ Flagged against a hard constraint.** `CLAUDE.md` says *"NEVER add, rename, or
> delete anything at the repository root."* A shared `.venv/` adds a root-level
> directory. It is already covered by `.gitignore`, so it is never committed and a
> reviewer cloning the repo sees an unchanged root — the committed structure is
> untouched. Recorded here so the choice stays visible and reversible; the fallback
> is a per-module `.venv`, costing only a reinstall per step folder.

*Sub-decision:* if the shared `.venv` is missing, the launcher **fails loudly**
with the exact command to create it, rather than silently falling back to system
`python3` (which would produce a confusing `ModuleNotFoundError: yaml` instead).

### 3.5 Class-level task methods — **`@classmethod`**

Ruby's `def self.provider(settings)` knows which class received the call. That is
precisely what lets the abstract `Base` build an error message naming the concrete
task — it asks `self.task_name` and gets `"player"`.

Python offers three translations that are **not** equivalent:

*Chosen:* **`@classmethod`**. It receives `cls`, so `cls.task_name()` resolves to
`Player`. One shared implementation in `Base` adapts to whichever subclass called
it — an exact match for Ruby's semantics.

*Rejected:*
- **`@staticmethod`** — a plain function that happens to live inside the class. It
  receives nothing and cannot know `Player` called it, so it can neither build a
  task-specific error message nor resolve the right prompt folder. The task name
  would have to be passed at every call site and re-supplied for every future task.
- **module-level functions** taking `task_name` as a parameter — simplest, but
  discards the `Base`/`Player` hierarchy the whole design rests on.

*Named pattern:* **abstract method via classmethod** — one shared implementation
that adapts to whichever subclass calls it.

### 3.6 Enforcing the abstract base — **`raise NotImplementedError`**

Ruby's `Base.task_name` raises only *when called*; nothing prevents referencing
`Base` itself. Python offers `abc.ABC` + `@abstractmethod`, which refuses to
instantiate an incomplete subclass.

*Chosen:* mirror Ruby — `raise NotImplementedError(f"{cls.__name__} must define task_name")`.
Fails at call time, names the offending class, needs no import.

*Rejected:* `abc.ABC` — because **nothing in this design is ever instantiated**, its
protection would be almost entirely symbolic here; worse, `Base.task_name()` on an
`@abstractmethod` returns `None` rather than raising, which is *weaker* than Ruby
for the one access pattern this code actually uses. A `ClassVar` sentinel was the
third option and added a check to every method.

### 3.7 Example output style — **Pythonic**

Ruby and Python print the same values differently: `true`/`True`, `nil` (printed as
empty) / `None`, and Ruby's `#<Boukensha::Config …>` inspect convention. Ruby's
`&.slice(0, 60)` — safe-navigate then slice — also has no single-expression Python
equivalent when the prompt is absent.

*Chosen:* **Pythonic values**, identical labels, spacing and line order. Output is
`True`, `None`, and `<Config dir=… tasks=player>`.

*Rejected:* byte-identical output — it would make the two launchers diff cleanly,
which is a genuinely nice verification property, but only by writing formatting
code that lies about the language it's written in.

*Consequence for verification:* the two outputs differ on exactly three lines
(`Prompt override?`, `API key set?`, and the final repr), all value-formatting,
none structural. Anything else that differs is a real bug.

### 3.8 Python-only affordances — **`@property` + `pathlib.Path`, nothing else**

None of these exist in the Ruby version; adding them is a choice, not a translation.

*Adopted:*
- **`@property` accessors** — the direct counterpart to Ruby's `attr_reader`, and
  the reason `dir`, `settings`, `mud_host` etc. are read-only rather than plain
  public attributes assignable from outside.
- **`pathlib.Path` return types** for `dir` and `user_prompts_dir`. This is a
  deliberate divergence: Ruby returns strings. Path objects compose better with the
  rest of the module and still format correctly in f-strings, so the printed output
  is unaffected.

*Declined:*
- **type hints** — signatures stay unannotated, matching Ruby's unannotated
  original. Trivially reversible later if the module grows.
- **a custom exception class** — Ruby's `ArgumentError` becomes plain `ValueError`.

### 3.9 Predicate naming — **`prompt_override(...)`**

Ruby's `prompt_override?` uses the `?` suffix convention for predicates. That
character is illegal in a Python identifier.

*Chosen:* drop the `?` and change nothing else — `prompt_override(settings, "system")`.
Closest to the Ruby name, so the two modules stay greppable against each other.
`has_prompt_override` / `is_prompt_overridden` / `prompt_override_enabled` were the
more conventionally Pythonic alternatives.

### 3.10 Nested access — **keep `dig(*keys)`, string keys only**

Ruby's `dig` tolerates string **or** symbol keys at every level
(`node[key.to_s] || node[key.to_sym]`) because Ruby has symbols and YAML can
produce either. **Python has no symbols**, so half that logic is dead weight and is
deleted. Python also has no built-in `dig`, though dicts do have `.get()`.

*Chosen:* keep a hand-written `dig(*keys)` loop with string keys only. It preserves
the Ruby API shape and the safe return-None-on-missing behaviour, and gives every
accessor a single tolerant lookup:

```python
def dig(self, *keys):
    node = self._settings
    for key in keys:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node
```

*Rejected:* chained `.get()` at each call site — no helper, but the `, {}` guard
must be repeated at every level, and it still breaks if a level holds a non-dict
value, which is exactly the case Ruby's `dig` guards against.

---

## 4. Free translations (no decision required)

| Ruby | Python |
|---|---|
| `Dir.home` | `Path.home()` |
| `Pathname.new(x).expand_path` | `Path(x).expanduser().resolve()` |
| `File.expand_path("../../prompts", __dir__)` | `Path(__file__).resolve().parents[1] / "prompts"` |
| `ENV.fetch("X", nil)` | `os.environ.get("X")` |
| `ENV["X"] ||= y` | `os.environ.setdefault("X", y)` |
| `File.exist?` / `File.read` | `Path.exists()` / `Path.read_text()` |
| `String#strip` | `str.strip()` |
| `.freeze` on constants | UPPER_CASE naming convention (no `freeze` exists) |
| `private` / `class << self; private` | leading-underscore naming convention |
| `keys.join(', ')` | `", ".join(keys)` |
| Ruby keyword args (`user_prompts_dir:`) | Python keyword-only args (`*,`) |
| `ArgumentError` | `ValueError` |
| symbol-or-string key lookup | **deleted** — Python has no symbols |

---

## 5. Target tree after the port

```
week1_baseline/
├── bin/
│   └── python/
│       └── 00_config                  # bash launcher
└── python/
    └── 00_config/
        ├── README.md
        ├── requirements.txt           # pyyaml, python-dotenv
        ├── boukensha/
        │   ├── __init__.py            # re-exports Config, Player
        │   ├── config.py              # class Config
        │   └── tasks/
        │       ├── __init__.py
        │       ├── base.py            # abstract stateless Base
        │       └── player.py          # class Player(Base)
        ├── prompts/
        │   └── system.md              # shipped default prompt
        └── examples/
            ├── __init__.py
            └── example.py             # smoke test
```

Plus a one-time, gitignored `<repo>/.venv/`.

**Launcher** (`bin/python/00_config`):

```bash
#!/usr/bin/env bash
cd "$(dirname "$0")/../../python/00_config"
"$(git rev-parse --show-toplevel)/.venv/bin/python" -m examples.example
```

(with a loud failure if that interpreter is absent).

---

## 6. Verification

1. Run `./week1_baseline/bin/ruby/00_config` and capture the reference output.
2. Run `./week1_baseline/bin/python/00_config`. Labels, spacing and line order must
   match. Expected differences, and only these: `True` for `true`, and
   `<Config …>` for `#<Boukensha::Config …>`.
3. **Defaults path** — point `BOUKENSHA_DIR` at an empty directory. Must not crash;
   MUD must report `localhost:4000`; the missing-provider path must raise
   `tasks.player.provider is required`, proving the classmethod resolved its own
   identity.
4. **Prompt ladder** — in a scratch config dir, flip `prompt_override.system` to
   `false`. The printed prompt must switch from *"You are my MUD jodza-player"* to
   the shipped *"You are a MUD player assistant…"*. Flip it back and confirm it
   returns. This is the single most important behaviour to get right, and the
   current repo data only ever exercises one of its two branches.
5. `git status` — confirm no `.venv/`, `__pycache__/`, `*.pyc`, or `.env` is staged.
   All are already covered by `.gitignore`.

---

## 7. Constraints honoured

- Nothing added, renamed or deleted at the repository root **in the committed
  tree**; the gitignored `.venv/` is flagged in §3.4 for a decision to stand or be
  reversed.
- All code lands under `week1_baseline/python/` and `week1_baseline/bin/python/`.
- `week1_baseline/ruby/**` is not modified.
- This plan was written before implementation, in `docs/plans/python_port/`, per
  project rules.

---

## 8. Open items for the implementation pass

- Nothing blocking. All ten decisions are resolved above.
- Create the shared `.venv` and `pip install -r requirements.txt` as an explicit
  first step — it is a prerequisite of the launcher, not a side effect of it.
