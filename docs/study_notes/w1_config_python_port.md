# w1 — Config Python Port (Step 0)

*Personal learning notes. Not graded documentation. In my own words.*

**Spine:** Because I already understood the architecture, porting Config to Python
was cosmetic — the shape stayed, only the spelling changed. The rule was to match
what the code *does*, not what it looks like.

---

## What porting actually means here

Porting Config meant keeping the behaviour identical while the textual form was free
to change — same folder read, same settings found, same output printed. The rule
was **behavioural fidelity, not textual identity**: match what the code *does*, not
what it looks like.

The workflow was: point Claude at the Ruby files → have it write a *plan* first and
raise questions → answer the questions → let it execute the plan → review and run.
The plan step is where the real decisions surfaced.

*(fidelity = faithfulness, staying true to something.)*

---

## The forced decisions (Python made me choose; Ruby didn't)

Most of the port was pure cosmetic — Ruby spelling swapped for Python spelling
(those twins live in the idiom ledger, not here). A port has *fewer* decisions than
a build, and that's the point. Three spots forced an actual choice:

### D1 — classmethod vs staticmethod for the abstract task  ★ money shot

**The problem:** Ruby writes the task methods as `self.method` — a class-level
method with no instances ever created. Python has *two* ways to translate that, and
they are not the same:

- `@classmethod` — the method automatically receives *which class called it*
  (`Player`, or some future `NPC`).
- `@staticmethod` — a plain function that happens to live inside the class. It gets
  nothing; it has no idea who called it.

**Chosen: `@classmethod`.** One method serves every task, because it can look up its
own identity. That's how the error `tasks.player.provider is required` fills in the
right task name by itself — the method asks *"who am I?"* and gets `player`.

**What breaks with `@staticmethod`:** the method is blind. It can't know it was
`Player` that called it, so it can't build a task-specific error message or resolve
the right prompt folder. You'd have to hardcode `"player"` in every place, and add
it again for every new task. classmethod knows its identity; staticmethod is blind.

*(This is the one Andrew wavered on out loud in the video — he kept saying "wouldn't
it be staticmethod?" That hesitation is exactly why it's the money shot.)*

**Named pattern:** *abstract method via classmethod* — one shared implementation
that adapts to whichever subclass calls it.

### D2 — one shared `.venv` vs one per folder

**The problem:** Python needs a virtual environment (an isolated box holding the
project's installed libraries). Where does it live — one per iteration folder, or
one shared at the repo root?

**Chosen: one shared `.venv` at the repo root.** Future iterations (`01`, `02`,
`03`…) all reuse the same environment instead of each rebuilding its own.

**What breaks with one-per-folder:** every new step folder would need its own
`.venv` created and its own libraries reinstalled — slow, repetitive, and more to
keep in sync. The shared one is set up once and every folder points at it.

*(venv = a private folder holding this project's Python libraries, kept separate
from the system Python so projects don't collide. It's gitignored — never pushed.)*

### D3 — splitting the launcher into `bin/ruby` + `bin/python`

**The problem:** before the port there was one launcher script that ran the Ruby
version. Now two languages exist and both need to be runnable.

**Chosen: split `bin` into `bin/ruby/` and `bin/python/`.** Each language gets its
own launcher; `bin/python/00_config` cd's into the Python module and runs its
`example.py`.

**What breaks with one shared launcher:** one script can't run both languages
cleanly — it would need branching logic to guess which one you meant. Two folders
keep it obvious: the path tells you the language.

*(This is the only decision that lives **outside** `config.py` — it's about how the
project is launched, not how config works.)*

---

## What did NOT change (and why that's the point)

These behaviours are identical to the Ruby version — proof the port was cosmetic:

- Config resolves the folder once at boot, then answers everything from memory.
- `BOUKENSHA_DIR` env var overrides the default `~/.boukensha`.
- `.env` secrets loaded, `settings.yaml` read once.
- The prompt ladder: override-if-switch-on-and-file-exists, else default.
- Same printed output when you run the example.

The one thing Python *forced*: loading `.env` needs an **external library**
(`python-dotenv`), because Python's standard toolkit has no built-in `.env` reader.
Not a decision — there was only one option.

---

## Debt paid from Config Ruby

My Ruby note deferred four idioms to "read at port time." Here's what each became:

- `dig` (walk nested keys) → a plain `dig(*keys)` method looping `node.get(key)`.
- symbol-or-string key lookup → gone; Python dict keys are just strings.
- `attr_reader` (auto getter) → `@property` for read-only accessors like `mud_host`.
- `Pathname.expand_path` → `Path(raw).expanduser().resolve()`.

---

## Assembled picture

Same structure as the Config Ruby note — only the names changed to Python:

```
                    ┌──────────────── boukensha.Config (STATEFUL) ────────────────┐
   Config() ───────►│ boot: 1 _resolve_dir→self.dir  2 _load_env→ENV  3 _load_settings→self.settings │
                    └───────────────────────────┬─────────────────────────────────┘
                          reads from ONE folder (self.dir):
                    ┌───────────────┬────────────┴──────────┬──────────────────────┐
                 .env (secret)  settings.yaml           prompts/system.md   .boukensha/prompts/
                 API_KEY        tasks: player:{...}      (DEFAULT prompt)     player/system.md
                 (gitignored)   mud:{host/port/user/pass}                     (MY override)
                          │
             ┌────────────┴──── Config answers ─────────────┐
             │ LIBRARIAN: tasks("player") · mud_host/port    │
             │ SIGNPOST : dir · user_prompts_dir             │
             └────────────┬─────────────────────────────────┘
                          │ hands settings + paths to
                          ▼
              tasks.Player(Base)  (STATELESS, all @classmethod)
                  provider/model → from settings dict (raise if missing)
                  system_prompt  → ladder: override switch true AND file exists?
                                    yes → .boukensha/prompts/player/system.md (mine)
                                    no  → prompts/system.md (default)
```

## Boot / run story (t0 … t4)

Scenario: `./bin/python/00_config` from repo root, override switch ON, my
`system.md` exists.

```
t0  LAUNCHER → bin/python/00_config cd's into python/00_config → runs example.py
      example.py sets BOUKENSHA_DIR = repo .boukensha
t1  CONFIG BOOTS (Config())
      _resolve_dir  → BOUKENSHA_DIR set → self.dir = repo/.boukensha (override won)
      _load_env     → self.dir/.env → ANTHROPIC_API_KEY into ENV
      _load_settings→ self.dir/settings.yaml read ONCE → self.settings held
      (Config is now built; from here it only ANSWERS)
t2  config.tasks("player") → returns player block FROM MEMORY (no disk read)
t3  Player.system_prompt → switch true, file exists → returns MY prompt
t4  example.py prints; program ends. Config did its whole job at t1, then idle.
```

## The one-liners this earns

- Once the architecture is understood, the language is cosmetic — the port is
  spelling, not shape.
- classmethod knows its own identity; staticmethod is blind. That's why the
  abstract task is classmethod.
- The interesting decisions in a port are only where the target language had no free
  translation — everything else is idiom-ledger vocabulary.

## Ruby → Python equivalents met (twins in the ledger)

- `self.method` (class-level, no instances) ↔ `@classmethod`
- `attr_reader :foo` ↔ `@property def foo`
- `dig(...)` ↔ hand-written `dig(*keys)` loop
- `Pathname.expand_path` ↔ `Path(...).expanduser().resolve()`