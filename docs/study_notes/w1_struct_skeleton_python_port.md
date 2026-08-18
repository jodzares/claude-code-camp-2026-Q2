# w1 — Struct Skeleton Python Port (Step 1)

*Personal learning notes. Not graded documentation. In my own words.*

**Spine:** This is a delta port only. On top of `00_config` we add 3 more shapes —
two data (`Tool` and `Message`) and one class (`Context`).

---

## D1 — copy 00_config, port only the delta  ★ money shot

Because this is a delta port, and `00_config` was already ported. So instead of
porting `01` from scratch, I copy the finished `00_config` folder first, then port
only the 3 new files (`tool`, `message`, `context`).

The trap: Andrew's planning agent didn't know `00_config` was done, so its plan
re-ported work already committed. He re-prompted — "you only have to port the new
changes." The copy has to happen *before* the agent plans, or the plan is wrong on
arrival.

## D2 — data vs behaviour

`Tool` and `Message` just store data — no verbs, no functions — so they become
dataclasses. `Context` has verbs (`register_tool`, `add_message`), which is exactly
why it stays a plain class. Same split as Ruby.

Receipt: a naive dataclass `Context` won't even load — Python raises
`ValueError: mutable default list is not allowed`, because a dataclass writes its
defaults once and every context would share one message list. A plain class dodges
this by doing `self.messages = []` inside `__init__`, fresh per object.

## D3 — what the program actually does

The program is `examples/example.py`, run by the launcher. In order it:

- creates the `Config` object and loads settings + system prompt
- creates a fresh `Context` (empty box)
- registers one tool (`move`)
- adds two messages (`user`, `assistant`)
- prints everything, then stops

What it does NOT do: no API, no network. The `move` tool is stored like a recipe
card in a drawer — never run. This lesson only proves the box holds the right shapes.

## D4 — hand-written display strings

Hand-write the text form (`__str__`) so the Python output matches the Ruby output
exactly. We need the outputs to line up 100%, because that side-by-side match is the
only proof the port is faithful. If I let Python print its own way, the formats
wouldn't line up and I couldn't compare them.

(Small imperfection: Andrew's `Tool` truncation is `[:43]`, 2 chars off Ruby's
`[0..40]` = 41. Matching Ruby exactly means `[:41]`. Cosmetic, nothing breaks.)

## D5 — the package export line

The `__init__.py` line hands `Context` over from the `context` file:
`from .context import Context`. `__init__.py` is the folder's front desk — Python
runs it automatically whenever the folder name is imported. So when `example.py`
says `from boukensha import Config, Context, Player, Tool`, the folder can only
hand those over because `__init__.py` published each one. Skip the line and the
program crashes with `ImportError`, even though `context.py` is right there.

This lesson adds 3 such lines — one each for `Tool`, `Message`, `Context`.

---

## What the README told me that the tour didn't

The README's field descriptions point forward, past this lesson. `Tool.block` is
"the callable that will eventually run when the tool is called" — stored now, run
later. `Message.tool_use_id` links a tool result back to the specific tool call
that produced it. The README even shows a third message role I never built:
`#<Message role=tool_result [toolu_01X] ...>`. This lesson only builds `user` and
`assistant` and leaves `tool_use_id` empty (`None`); a later lesson fills that slot.
The empty field has a job coming.