# w1 — Config Ruby (Step 0)

*Personal learning notes. Not graded documentation. In my own words.*

**Spine:** `Config` boots once — resolves the config folder, loads secret `.env`
and shareable `settings.yaml` — then acts as the single gatekeeper every other
component asks for its values, while stateless `Tasks` walks the
override-else-default prompt ladder on demand.

---

## The problem this whole step solves: exile

Config is the adjustable knobs a program reads at startup instead of baking them
into the source. The step exists because four things must NOT be hardcoded into
`config.rb` — but not all four for the same reason:

```
            exile from code
             /          \
        SECRET         PREFERENCE
     (never public)   (user can change)
     API key          model name
     MUD password     system prompt
     (MUD username = not secret, but rides along in settings)
```

- **Secret** → leaks money/access if pushed to public GitHub (API key, password).
- **Preference** → user should change it without editing Andrew's code (model, prompt).

**Named pattern:** *externalised configuration* — adjustable values live in files
outside the code, so the code never has to change to reconfigure.

---

## Box 1 — The two channels (why `.env` vs `settings.yaml`)

**Why it exists:** the split is about **Git**, not scope. One file must be hidden
from version control, the other must be committed.

```
.env          → the real secret: ANTHROPIC_API_KEY   → gitignored, never pushed
settings.yaml → model / prompt choice / mud{} block  → committed, travels with repo
```

- `.gitignore` = list of files Git pretends don't exist → never committed.
- The MUD `username`/`password` sit in `settings.yaml` here only because it's a
  throwaway practice server (`helloworld`). The API key is the one *true* secret
  the `.env` channel exists for.

**Delete-test:** delete `.env` from gitignore → your real API key gets pushed to
public GitHub the next commit → leaked. That's why the channel split exists.

---

## Box 2 — Where the folder lives (default + override)

**Why it exists:** the code must know which folder holds `.env` + `settings.yaml`.
Real tools drop a hidden dotfolder in `~` (home dir): `~/.claude`, `~/.ssh`. Ours
follows the convention: `~/.boukensha`. But the bootcamp keeps config *inside the
repo* (so it's version-controlled + gradable), which the default would miss — so
there's an override.

```
BOUKENSHA_DIR set?
   yes → use that path        ← override (bootcamp / testing points here)
   no  → use ~/.boukensha     ← default (a real install)
```

- env var = a named value the OS hands the program at startup, set outside the code.
- `BOUKENSHA_DIR` is **not** a grading hook — it's the standard "override my default
  location" escape hatch any professional tool ships. Bootcamp just leans on it.

**Named pattern:** *override-wins-else-default* — the shape reused for the prompt.

**Delete-test:** unset `BOUKENSHA_DIR` while running from the repo → Config looks in
`~/.boukensha`, finds nothing, loads empty settings.

---

## Box 3 — The prompt ladder (override, gated by a switch)  ★ money shot

**Why it exists:** Andrew wants a working default prompt on a fresh clone AND lets
me override with my own — without editing his files. Same override-else-default
shape as the folder, but guarded by a switch so overriding is deliberate.

```
system prompt resolution:
   prompt_override.system == true ?
       yes → file at prompts/player/system.md exists ?
                yes → use MY prompt
                no  → fall back to default
       no  → use default: prompts/system.md (shipped in library)
```

**THE LANDMINE:** the fall-through is **silent**. If the switch is off, or the file
is misnamed, the agent uses the default and prints a happy result — no error. You
only catch it because the printed prompt is the wrong one. So the path must be
EXACTLY:

```
prompts/player/system.md
   │       │       └ filename = system.md
   │       └ subfolder = the task name ("player")
   └ folder = exactly "prompts"
```

**Delete-test:** rename `prompts/` to `tasks/` → switch still true, file not found
→ silent fall-through to default. (This is the bug Andrew hit on screen.)

---

## Box 4 — The tasks shape (why `tasks:` / `player:` nesting)

**Why it exists:** the multi-role future. Today one role (`player`); later a mapper,
a risk-assessor — each its own provider/model. Nesting gives each role a
self-contained named block, so new roles slot in without renaming anything or
writing new lookup code.

```yaml
tasks:
  player:                 # today's only role, self-contained
    provider: anthropic
    model: claude-haiku-4-5
    prompt_override: { system: true }
  # mapper: ...           # future role → new block, zero disruption
mud:
  host / port / username / password
```

- task = one role in the agent loop, bound to its own LLM.
- Future per-task ceilings (`max_iterations`, ...) drop in as new lines *inside* a
  role's block — disturbing zero existing settings.
- The nesting also gives the code a **uniform address** — `tasks.<name>` — so
  `config.tasks(:mapper)` works with no new code.

**Delete-test:** flatten `provider`/`model` to top level → adding a second role
collides (whose `provider:`?) → forces a rename of everything.

---

## Box 5 — The gatekeeper `Config` class (stateful) + `Tasks` (stateless)

**Why Config exists:** two reasons.
1. **Speed** — reading/parsing `settings.yaml` off disk is slow; do it ONCE, hold
   in memory, hand out from there.
2. **One source of truth** — one class owns the reading; everyone else asks *it*,
   so nothing disagrees. One door in, one answer out.

This is the ONE stateful class in the codebase (holds `@settings`). Everything else
is kept stateless by default.

- class = blueprint bundling data + operations. instance = one object from it.
- stateful = remembers data after built; stateless = remembers nothing, you pass
  it everything each call.
- namespace = labeled container for names; `Boukensha::Config` = the Config
  belonging to Boukensha.

**Boot order (must be this order):**
```ruby
def initialize
  @dir      = resolve_dir      # 1. BOUKENSHA_DIR ? else ~/.boukensha
  load_env                     # 2. open @dir/.env  → secrets into ENV
  @settings = load_settings    # 3. read @dir/settings.yaml once → held
end
```
`resolve_dir` FIRST because steps 2 and 3 both build their file path out of `@dir`
(`File.join(@dir, ".env")`), so the folder must be known before either can find
its file.

**Config plays two roles:**
```
LIBRARIAN (stored data):  tasks(:player) · mud_host · mud_port
SIGNPOST  (computed paths, reads nothing):  dir · user_prompts_dir
```
`user_prompts_dir` just returns `@dir/prompts` — an ADDRESS. Config never reads the
prompt file itself.

**Tasks::Base (abstract, stateless) vs Tasks::Player (concrete):**
```
Base   (ABSTRACT) ── holds ALL shared behaviour, never called directly
   provider · model · system_prompt (the ladder) · file readers
   task_name → raises "must define"   ← abstract = template only
        ▲ inherited by
Player (CONCRETE) ── the one you call; its only unique piece:
   task_name → "player"
```
- inherit = a class built on top of another gets its methods for free (`< Base`).
- abstract class = never used directly, exists only to be inherited from.
- Base holds **behaviour**, not data or field-names: it knows *how to fetch*
  `provider` from whatever settings hash you pass. Data lives in `settings.yaml`;
  stored data lives in Config's `@settings`; Base is the hands that reach in.
- provider/model are **required** (missing = error — too important to guess); the
  **prompt is defaulted** (the ladder's whole point). mud host/port defaults live
  in Config, not Base.

**Why Config stateful, Tasks stateless:** the test is *"if I call this twice, does
it need to remember anything from call #1?"*
- Config: yes → the parsed settings (don't re-read disk) → STATEFUL.
- Tasks: no → each call is handed everything it needs → STATELESS.
Principle: *stateless by default; hold state only where it earns its keep.*

**Delete-test (Config):** remove the `@settings` caching, make every getter re-read
the file → correct output but slow, and N parsers can disagree. The class exists to
prevent exactly that.

---

## Assembled picture

```
                    ┌──────────────── Boukensha::Config (STATEFUL) ───────────────┐
   Config.new ─────►│ boot: 1 resolve_dir→@dir  2 load_env→ENV  3 load_settings→@settings │
                    └───────────────────────────┬─────────────────────────────────┘
                          reads from ONE folder (@dir):
                    ┌───────────────┬────────────┴──────────┬──────────────────────┐
                 .env (secret)  settings.yaml           prompts/system.md   prompts/player/
                 API_KEY        tasks: player:{...}      (DEFAULT prompt)     system.md
                 (gitignored)   mud:{host/port/user/pass}                     (MY override)
                          │
             ┌────────────┴──── Config answers ─────────────┐
             │ LIBRARIAN: tasks(:player) · mud_host/port     │
             │ SIGNPOST : dir · user_prompts_dir             │
             └────────────┬─────────────────────────────────┘
                          │ hands settings + paths to
                          ▼
              Tasks::Player < Base  (STATELESS)
                  provider/model → from settings hash
                  system_prompt  → ladder: switch true AND file exists?
                                    yes → prompts/player/system.md (mine)
                                    no  → prompts/system.md (default)
```

## Boot / run story (t0 … t4)

Scenario: `./bin/00_config` from repo root, override switch ON, my `system.md` exists.

```
t0  RUNNER  → cd into module → runs example.rb; line 5 sets BOUKENSHA_DIR = repo .boukensha
t1  CONFIG BOOTS (Config.new)
      resolve_dir → BOUKENSHA_DIR set → @dir = repo/.boukensha (override won)
      load_env    → @dir/.env → ANTHROPIC_API_KEY into ENV
      load_settings → @dir/settings.yaml read ONCE → @settings held
      (Config is now built; from here it only ANSWERS)
t2  config.tasks(:player) → returns player block FROM MEMORY (no disk read)
t3  Tasks::Player.system_prompt → switch true, file exists → returns MY prompt
t4  example.rb prints; program ends. Config did its whole job at t1, then idle.
```

## The one-liners this scenario earns

- Config reads the disk exactly once (t1); every later question is answered from
  memory. That's why it's the one stateful class.
- `resolve_dir` must run first — `load_env` and `load_settings` both build their
  path out of `@dir`.
- The override's failure is silent — wrong switch/filename gives the default prompt
  and a happy printout, no error.

---

## Ruby idioms met (twins in the ledger)

- `@foo` (instance variable, per-object memory) ↔ Python `self.foo`
- `class Player < Base` (inheritance) ↔ Python `class Player(Base):`

## Deferred to Config Python Port (line-level read)

- `dig` walking nested keys (`reduce` + `case/when`), symbol-or-string key lookup,
  `attr_reader`, `Pathname.expand_path`. Concept understood; syntax parsed later.