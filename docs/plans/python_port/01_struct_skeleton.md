# Porting Plan — `01_struct_skeleton`: Ruby → Python (delta only)

**Status:** plan only. No Python written yet.
**Source:** `week1_baseline/ruby/01_struct_skeleton/` (ExamPro reference, not to be modified)
**Target:** `week1_baseline/python/01_struct_skeleton/` — already exists, seeded by copying
the finished `week1_baseline/python/00_config/` tree verbatim.

---

## Context

`00_config` is done in both languages and is **not re-ported**. `01_struct_skeleton`
only adds data structures on top of it: `Tool`, `Message`, `Context`. This plan
covers only that delta.

Two grounding documents already exist and were used to write this plan rather than
re-deriving the design from scratch:
- `docs/study_notes/ruby_idiom_ledger.md` — committed idiom translations
  (`Struct.new` → `@dataclass`, `def x = ...` → `@property`, etc.)
- `docs/study_notes/w1_struct_skeleton_python_port.md` — personal walkthrough notes
  for this exact step, including one flagged bug to avoid repeating (see §3.3)

---

## 1. What the Ruby delta actually is

Diffing `ruby/00_config` against `ruby/01_struct_skeleton` directly (not just reading
the 3 files named at kickoff) surfaced a **4th new file** and **3 edited files**,
not 1:

| Change | File |
|---|---|
| new | `lib/boukensha/tool.rb` — `Tool` struct: `name, description, parameters, block` |
| new | `lib/boukensha/message.rb` — `Message` struct: `role, content, tool_use_id` |
| new | `lib/boukensha/context.rb` — `Context` class: holds `task, system, messages, tools`; verbs `register_tool`, `add_message`, `tool_count`, `turn_count` |
| edited | `lib/boukensha/config.rb` — `PROMPTS_DIR` constant **deleted** |
| edited | `lib/boukensha.rb` — 3 new `require_relative` lines |
| edited | `examples/example.rb` — rewritten wholesale to build a `Context`, register one tool, add two messages, and print them, instead of dumping config |

`PROMPTS_DIR` is deleted because the new `example.rb` no longer calls
`Tasks::Player.system_prompt` with a `default_prompts_dir:` argument — the example's
settings already have `prompt_override.system: true` and a matching user prompt file,
so the override branch fires and the default-prompt fallback path is never exercised
this step. Nothing else in the codebase referenced the constant.

### Live reference output

Captured by running `bundle exec ruby examples/example.rb` in
`ruby/01_struct_skeleton/`:

```
=== Boukensha Step 1: Struct Skeleton ===

Config:   #<Boukensha::Config dir=/home/jpopovic/claude-code-camp-2026-Q2/.boukensha tasks=player>
Context:  #<Context task=player turns=2 tools=1>
Tool:     #<Tool name=move description=Move the player in a direction (north, so params=[:direction]>
Messages:
  #<Message role=user content=Explore north and tell me what you find....>
  #<Message role=assistant content=Sure, let me head north and take a look....>
```

This is the source of truth for verification, not the README — the README's
`Context` field table mentions a `token_budget` field that **does not exist** in
`context.rb`. The README describes a later/aspirational shape; the code is what
this step actually ports.

---

## 2. File-by-file mapping

| Ruby file | Python counterpart | Action |
|---|---|---|
| `lib/boukensha/tool.rb` | `boukensha/tool.py` | create |
| `lib/boukensha/message.rb` | `boukensha/message.py` | create |
| `lib/boukensha/context.rb` | `boukensha/context.py` | create |
| `lib/boukensha/config.rb` | `boukensha/config.py` | edit — delete `PROMPTS_DIR` |
| `lib/boukensha.rb` | `boukensha/__init__.py` | edit — add 3 exports |
| `examples/example.rb` | `examples/example.py` | edit — rewritten body |

No launcher changes needed — `bin/python/00_config`'s shared-venv pattern from the
00_config plan (§3.3–3.4 there) still applies; a `bin/python/01_struct_skeleton`
launcher is a one-line copy of it once implementation starts.

---

## 3. Design decisions (already resolved by prior study notes)

### 3.1 `Tool` / `Message` — `@dataclass`

Both are pure data, no verbs, matching the ledger's `Struct.new(:a, :b)` →
`@dataclass` + typed fields rule. `Message.tool_use_id` gets a `= None` default,
mirroring Ruby's struct field being unset (`nil`) unless passed.

### 3.2 `Context` — plain class, not a dataclass

`Context` has behaviour (`register_tool`, `add_message`), so per the ledger's
data-vs-behaviour split it stays a plain class with `__init__`. A dataclass version
would additionally **crash outright**: `messages: list = []` as a dataclass field
default raises `ValueError: mutable default <class 'list'> for field ... is not
allowed` because dataclasses evaluate the default once and share it across every
instance. `__init__` assigning `self.messages = []` avoids this by giving each
`Context` its own list.

### 3.3 Hand-written `__str__`, not Python's default repr

Every new type gets a hand-written `__str__` matching Ruby's `to_s` formatting
byte-for-byte on structure (labels, brackets, ordering), Pythonic only on values.
Two slices need exact bounds because Ruby's range end is inclusive:

- `Tool.description[:41]` — Ruby's `description.to_s[0..40]` is 41 characters
  (0 through 40 inclusive). **Not `[:43]`** — that 2-off variant is a flagged bug
  from the prior walkthrough in `w1_struct_skeleton_python_port.md`, kept here as a
  guardrail against repeating it.
- `Message.content[:61]` — Ruby's `content.to_s[0..60]` is 61 characters, always
  followed by a literal `"..."` regardless of whether truncation actually occurred.

### 3.4 `Context.__str__`'s task field — `hasattr` guard

Ruby: `task&.task_name` — safe-navigation, call `.task_name` only if `task` isn't
`nil`. Python has no `&.`. The ledger already committed to this step's translation:
`task.task_name() if hasattr(task, "task_name") else None`, used here for
consistency with that record rather than the equally-valid `is not None` check.

### 3.5 Parameter/key display — no symbols

Ruby prints `params=[:direction]` (symbol array). Python has no symbols, so
`Tool.parameters` uses string keys and prints as `params=['direction']`. This is the
same category of accepted value-formatting divergence as `dig()`'s string-only keys
in the 00_config port — structural match, cosmetic difference.

---

## 4. `examples/example.py` rewrite (mirrors `example.rb`)

In order:
1. Build `Config()`, fetch `player_settings = config.tasks("player")`.
2. Resolve `system_prompt` via `Player.system_prompt(player_settings, user_prompts_dir=config.user_prompts_dir)` — **no** `default_prompts_dir` argument (see §1).
3. Build `Context(task=Player, system=system_prompt)`.
4. `ctx.register_tool(Tool("move", "Move the player in a direction (north, south, east, west, up, down)", {"direction": {"type": "string", "description": "The direction to move"}}, lambda direction: f"You move {direction} into a torch-lit corridor."))`.
5. `ctx.add_message("user", "Explore north and tell me what you find.")`
6. `ctx.add_message("assistant", "Sure, let me head north and take a look.")`
7. Print the block shown in §1's live reference output, Pythonic values.

No API call, no network — the `move` tool is registered but never invoked. This step
only proves the data structures hold the right shapes.

---

## 5. Verification

1. `cd week1_baseline/ruby/01_struct_skeleton && bundle exec ruby examples/example.rb` — reference output already captured in §1, re-run only if Ruby source changes.
2. `cd week1_baseline/python/01_struct_skeleton && <repo>/.venv/bin/python -m examples.example` — compare line-by-line against §1. Expected differences only: no `Boukensha::` prefix, `params=['direction']` vs `[:direction]`.
3. Confirm `Tool` truncates at exactly 41 chars and `Message` at exactly 61 (count, don't eyeball — this was the one bug already caught once).
4. `git status` — confirm no stray `__pycache__/`, `.pyc`, or venv files staged (the copied `00_config` tree already has `__pycache__/` present per the working tree; exclude it from any commit).

---

## 6. Constraints honoured

- Nothing added, renamed or deleted at the repository root.
- All code lands under `week1_baseline/python/01_struct_skeleton/`.
- `week1_baseline/ruby/**` is not modified.
- `00_config`'s Python module is not re-ported or modified beyond the two edits
  in §2 that Ruby's own delta required (`config.py`, `__init__.py`).
- This plan was written before implementation, in `docs/plans/python_port/`, per
  project rules.
