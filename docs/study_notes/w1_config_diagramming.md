# Config Diagramming — study notes

> Personal learning notes (my words), not graded documentation. See docs/journal/ for graded work.

## What this lesson actually is

No code. Andrew takes the Config machine I already built and turns it into a
**picture** — a few boxes for the classes, a few for the files, lines between
them. The whole lesson is one question: **what earns a box, and what kind of
line connects them?**

---

## The core rule: draw things, not actions

A box = something that **permanently exists** in the project (a class, a file).
Left off = the **momentary actions** those things perform at runtime.

- `Config` the class → box (permanent fixture).
- `resolve_dir`, `load_env`, `load_settings` → **no box** (they're actions that
  fire for a flash at boot, then they're over). They get swallowed *inside* the
  Config box.

Analogy: a light switch is a fixture (box). "Flipping the switch" is an action
(no box). The switch *contains* the ability to be flipped, the way Config
contains resolve_dir.

This is why last lesson's entire star — the boot order — **disappears** here.

---

## Structure vs. time (the money shot)

Two photographs of the same machine:

- **Time diagram** (last lesson): one path, in order. `boot → resolve → load_env
  → load_settings`. Arrows mean "happens next."
- **Structure diagram** (this lesson): all relationships at once, no clock.
  Arrows mean "connects to."

**A class diagram trades sequence for relationships.** You lose the order, you
gain the ability to show every relationship side by side.

The clock test — is there a "before/after" in the sentence?
- "resolve_dir runs **before** load_env" → TIME (has a clock) → can't go on structure diagram.
- "Config **reads** settings.yaml" → USES (no clock, permanently true) → box + solid line.
- "Player **is a kind of** Base" → FAMILY (no clock) → family line.

That's why I keep BOTH a boot story and an assembled diagram every lesson — two
different photos of one machine.

---

## The three honest line types

Arrow style is a **truth claim**. Drawing the wrong one misleads a future reader.

- **Solid** = direct use / reads. `Config ──reads──> settings.yaml`.
- **Family** = "is a kind of". `Player ──> Base`.
- **Dotted** = related, but NOT direct. `Player ····· player: slice`.

The dotted line matters because `Tasks::Player` does **not** open the file —
**Config is the one class that touches disk**, and hands data to the tasks. A
solid line from Player to the file would lie: it would send a reader hunting
inside Player for file-opening code that actually lives in Config.

---

## Per-box: why each one exists

- **Config** — the one stateful class. Reads disk once at boot, then idle.
  Holds every task's settings in memory. Resolves the directory, loads .env,
  loads settings.
- **Tasks::Base «Abstract»** — never used alone. Holds the shared loading code
  so I don't rewrite it for every future task (mapper, risk-assessor). The word
  `«Abstract»` is a kindness: it tells a reader "don't try to use this directly."
- **Tasks::Player** — tiny concrete subclass. Its only unique piece is its
  **name** = "player". That name is the key it uses to pull `tasks["player"]`
  from settings — just its own slice, ignoring every other task's slice.
- **./boukensha dir** — the folder holding all agent config: settings.yaml,
  .env (uncommitted, secrets), prompts/<task>/system.md.

### Abstract, plainly
Base is the **blueprint**, Player is the **house** built from it. The plumbing
(loading code) is described in the blueprint but only actually runs when a house
is built. So Base's loading code runs **the moment a Player is created** — never
on its own, always wearing a Player's face.

---

## Named patterns

- **Delete-test** — if I can remove something and the architecture still stands
  whole, it was never part of the architecture. Delete `example.rb` → Config
  still resolves its directory the same way → so example.rb is a disposable
  *caller*, not structure. It gets no box.
- **Fixture vs. transition** — `BOUKENSHA_DIR` is an env var: not a class, not a
  file. It gets no box; it lives as a **label on the arrow** (the transition)
  from Config to the folder.
- **Name after contents** — the folder holds only `system.md`, so it's called
  `prompts/`, not `tasks/`. "tasks" would over-promise (a task = prompt +
  settings, but the settings live in settings.yaml, not this folder). Like
  labelling a sock drawer "SOCKS" not "CLOTHES".

### The two ".boukensha" paths (don't conflate)
- `~/.boukensha` → the real default Config computes on every run → belongs on
  the diagram (arrow label).
- `../../../../.boukensha` → relative string in example.rb only, because the
  demo script sits several folders deep and must climb out. Demo scaffolding,
  fails the delete-test → never on the diagram.

**The act of drawing exposed an imprecision the code hid** — Andrew had to sort
out on camera whether the folder box was a vague "somewhere" or a literal path.
A diagram isn't just documentation; it's a *test* of understanding.

---

## Assembled diagram

```
┌─────────────────┐
│ Config          │──resolve_dir──> [ BOUKENSHA_DIR || ~/.boukensha ]
│ (loads config + │                          │
│  .env secrets)  │                          v
└─────────────────┘                 ┌──────────────────────┐
   │  │                             │ ./boukensha dir      │
   │  └──reads──> .env (secrets)    │  settings.yaml       │──> tasks:
   │                                │  .env (uncommitted)  │      player:
   └──reads──> settings.yaml ───────│  prompts/<task>/     │        provider
                                    │         system.md    │        model
                                    └──────────────────────┘        prompt_override

┌────────────────────────┐
│ Tasks::Base «Abstract»  │  (shared loading code; never run alone)
└────────────────────────┘
     │ family
     v
┌────────────────────────┐
│ Tasks::Player           │·······dotted·······> player: slice
│ (name="player")         │   (related, not direct — Config does the reading)
└────────────────────────┘
```

Lines: solid = direct use · family = is-a · dotted = related-but-indirect.

## Boot / run story (t0..tN) — the time this diagram drops, restored

Scenario: I launch the agent to play the MUD.

```
t0  I run the agent.
t1  Config created. resolve_dir fires FIRST → BOUKENSHA_DIR not set →
    falls back to ~/.boukensha. Config now knows WHERE.
t2  Config reads .env → Anthropic key (secret, never committed).
t3  Config reads settings.yaml → holds every task's settings in memory.
t4  Tasks::Player created. Player IS a Base (family) → Base's loading code runs,
    wearing Player's face.
t5  That code uses Player's name "player" → pulls tasks["player"] slice →
    provider, model, prompt settings.
t6  Prompt ladder: prompt_override.system true AND prompts/player/system.md
    exists? → use mine. Else → shipped default. (Silent either way.)
t7  Config idle — read disk once at boot, never touches it again. Player ready.
```

## The one-liners this scenario earns

- Config touches disk once, at boot, then goes idle — everyone else gets handed data.
- A task never reads the file; it inherits Base's loader and pulls its own slice by name.

## Spine sentence

This lesson draws the Config machine as a picture using only the parts that
permanently exist, connected by three line types (solid / family / dotted), and
it drops the boot order because a structure diagram can't show time.