# W1 — The Registry Python Port

## What this step does

Ruby already had iteration 02, the Registry. Python stopped at 01. This lesson
creates `week1_baseline/python/02_the_registry` and brings it up to the same
behaviour, so both languages print the same trace at the same step.

Andrew does not hand-write the Python. He writes a plan file at
`docs/plans/python_port/02_the_registry.md`, reads it, then has Claude Code
execute it. Reading the plan is where mistakes get caught — before any code
exists.

---

## D1 — Starting point: copy forward, in the same language

**The problem.** `week1_baseline/python/02_the_registry` does not exist. Something
has to be put there before anything can be edited.

**Why this is even a question.** Each numbered folder is a *snapshot*: a complete,
runnable program at that step, not a list of changes. So folder 02 cannot start
empty — it has to start as a whole working program and then be edited.

**The two candidates, and what is actually inside each:**

```
ruby/02_the_registry/          python/01_struct_skeleton/
  examples/example.rb            examples/example.py
  lib/boukensha/registry.rb      boukensha/context.py
  lib/boukensha/errors.rb        boukensha/tool.py
  Gemfile                        requirements.txt
```

Ruby 02 has the *content* I want but in the wrong language. Python 01 has the
*language* I want but is one step behind.

**Chosen: copy Python 01.** Correcting the step number is a small edit. Correcting
the language is not an edit at all — it is a rewrite.

**What copying Ruby 02 actually produces:**

```
$ python3 examples/example.py
can't open file '.../python/02_the_registry/examples/example.py': [Errno 2] No such file or directory
```

There is no `.py` file in the folder. Point Python at the `.rb` file that is
there and it refuses that too:

```
$ python3 examples/example.rb
    require_relative "../lib/boukensha"
                     ^^^^^^^^^^^^^^^^^^
SyntaxError: invalid syntax
```

**The rule this establishes:** Ruby 02 is what I **read** to learn the delta.
Python 01 is what I **copy** to stand on. Read across languages, copy along one.

**What I inherit on purpose.** Straight after the copy the folder runs perfectly
and prints the *Step 1* output — its README still says Step 1, its example still
registers one tool directly onto `Context`, and there is no registry anywhere.
That is not a mistake. Closing that gap is the whole lesson.

---

## D2 — Money shot: how a tool's body gets attached

**The problem.** Registering a tool means storing three pieces of description
(name, description, parameters) plus a fourth thing that is not data at all —
a chunk of code to run later. Every language needs some way to hand over that
chunk.

**Ruby's answer** — a trailing block, the code sitting between `do` and `end`:

```ruby
registry.tool("move", description: "...", parameters: { direction: { type: "string" } }) do |direction:|
  "You move #{direction} into a torch-lit corridor."
end
```

**Python's answer** — a decorator, the `@` line sitting above a `def`:

```python
@registry.tool("move", description="...", parameters={"direction": {"type": "string"}})
def move(direction):
    return f"You move {direction} into a torch-lit corridor."
```

**What I need to be able to read, and no more:** a line starting with
`@registry.tool(...)` directly above a `def` means *a tool is being registered
right here*, and the `def` beneath it is that tool's body.

**The thing that is easy to get wrong.** Reaching the `def` does **not** run the
body. It only files it away. Proof, from a stripped-down version of the real
registry where the body prints a line whenever it runs:

```
t0 tools: {}
t1 tools: {'move': '#<Tool name=move block=move>'}
t2 nothing has run yet - notice no BODY RUNNING line above
t3 dispatching...
   >>> BODY RUNNING NOW
   result: You move north into a torch-lit corridor.
```

At t1 the tool is registered and the body is sitting inside the `Tool` object.
No output from it. The body only wakes up at t3, when `dispatch` calls it.
That gap between registering and running is the entire reason a Registry exists.

**The rejected alternative** — a literal argument-for-argument port that passes
the body as a `lambda`:

```python
registry.tool("move", description="...", parameters={...},
              block=lambda direction: f"You move {direction} into a corridor.")
```

A `lambda` can hold exactly one expression. The first tool that needs two lines
of body stops compiling. The decorator has no such ceiling — its body is an
ordinary `def` and can be any length.

---

## D3 — One Ruby line is deleted, not translated

**Start with the mechanism, because the decision only makes sense after it.**

`dispatch` receives the arguments as a dict. The tool body is a normal function
with named parameters. `**` is what joins the two:

```python
args = {"direction": "north"}
        └── KEY ──┘  └VALUE┘

tool.block(**args)      is exactly the same as      move(direction="north")
```

Read it as: **each key becomes an argument name, each value becomes that
argument's value.** The key is not free text — it has to match the parameter
name in the `def`. Rename it and Python says so:

```
$ python3 demo.py
You move north into a torch-lit corridor.          <- {"direction": "north"}
TypeError: move() got an unexpected keyword argument 'dir'   <- {"dir": "north"}
```

That error is the receipt: the dict key *is* the argument name.

**Now the Ruby problem.** Ruby has two different kinds of hash key and treats
them as unrelated:

```ruby
{ "direction" => "north" }   # string key
{ direction: "north" }       # symbol key
```

In the Ruby example the args arrive as **strings**, but the block header
`do |direction:|` accepts only **symbols**. Mismatch. So Ruby needs an adapter
line to rewrite the keys just before the call:

```ruby
tool.block.call(**args.transform_keys(&:to_sym))
                  └──────── adapter ────────┘
```

**The decision.** Python has only one kind of key. The dict already carries the
exact labels the function wants. So the adapter has nothing to adapt, and the
line is **deleted**, not converted:

```python
return tool.block(**(args or {}))
```

**What happens if it is ported literally** — the method does not exist in Python
and never did:

```
AttributeError: 'dict' object has no attribute 'transform_keys'
```

**What survives the deletion.** A two-line comment in `registry.py` recording
why the step is absent. The *reason* is ported even though the *code* is not.

**The general lesson.** Some source lines exist only to work around a quirk of
the source language. Those lines do not have a target-language twin; the right
port is to remove them and leave a note.

---

## D4 — Faithful port: copy the known defect on purpose

**The situation.** `Context` still owns the `tools` dict. `Registry` is a facade:
it offers the verbs (`tool`, `dispatch`) but stores nothing itself. The Ruby
README flags this twice and defers the fix to a later step.

**The temptation.** An AI reading a documented flaw will fix it. That produces a
Python 02 that is *better* than Ruby 02:

```
Ruby 02   : Context owns tools[] , Registry borrows      <- deferred debt
Python 02 : Registry owns tools[] , Context is clean     <- "improved"
```

**Why that is a failure, not an improvement.** The whole course is two parallel
tracks that must line up snapshot for snapshot. Ruby repairs this ownership in a
later iteration, and that repair is its own lesson. If Python has already fixed
it, there is nothing left to port at that lesson and the tracks diverge for good.

**So the plan orders the defect reproduced.** The bar for a port is *same
behaviour as the source*, including its known flaws — not *the best code I can
write*.

**The plan carries a second fence too:** no API client, no agent loop, no test
suite. Left unfenced, the AI builds forward and folder 02 stops being a snapshot
of the Registry step.

**One exception — documentation.** The Ruby README advertises an output its own
code does not produce:

```
README says:  #<Context turns=0 tools=2 budget=8192>
code prints:  #<Context task=player turns=0 tools=2>
```

The Python README uses the real one. Docs get corrected; code does not.

---

## D5 — Launcher

**The problem.** Running a snapshot by hand means remembering a long path and
which Python interpreter to use. A launcher — a tiny bash script under `bin/` —
removes both.

`bin/python/02_the_registry` sits *outside* the iteration folder, so the D1 copy
does not produce it. It is a separate new file:

```
bin/ruby/   00_config  01_struct_skeleton  02_the_registry
bin/python/ 00_config  01_struct_skeleton  ???              <- the gap this fills
```

Mine follows my own 01 pattern — resolve the repo root with `git rev-parse`, and
fail with a helpful message if `.venv` is missing — rather than Andrew's
hardcoded `../../..`. Consistency inside my own repo wins over matching his text.

**The step that is easy to forget.** A newly written script is not runnable until
it is marked as such:

```
$ ./week1_baseline/bin/python/02_the_registry
bash: ./week1_baseline/bin/python/02_the_registry: Permission denied

$ chmod +x week1_baseline/bin/python/02_the_registry
$ ./week1_baseline/bin/python/02_the_registry
=== BOUKENSHA Step 2: Tool Registry ===
```

---

## Assembled picture

```
example.py
   |
   |  @registry.tool("move", ...)      <- D2: registration, body stored not run
   |  @registry.tool("shout", ...)
   v
Registry ---- register_tool ----> Context
   |                                { "move": Tool, "shout": Tool }   <- D4: tools still live HERE
   |                                          ^
   |  dispatch("move", {...})                 |
   +---- lookup ------------------------------+
   |         miss -> raise UnknownToolError   (errors.py)
   +---- hit  -> tool.block(**args)           <- D3: keys become argument names, no conversion
                        |
                        v
                 "You move north into a torch-lit corridor."
```

Docking onto earlier steps: `Config` and `Tasks::Player` (00) supply the system
prompt; `Tool`, `Message`, `Context` (01) carry forward untouched.

---

## The run, t0..tN

```
t0  ./bin/python/02_the_registry     launcher cds in, picks the .venv python
t1  import boukensha                 Registry + UnknownToolError now exported
t2  Config()                         reads .boukensha, builds the system prompt
t3  Context(task=Player, ...)        tools = {}, messages = []
t4  Registry(ctx)                    holds a reference to ctx, owns nothing
t5  @registry.tool("move")           Tool built and filed into ctx.tools; body NOT run
t6  @registry.tool("shout")          same; ctx.tools now has 2
t7  print Context                    #<Context task=player turns=0 tools=2>
t8  dispatch("shout", {...})         hit -> body runs -> DRAGON SPOTTED
t9  dispatch("move", {...})          hit -> body runs -> You move north...
t10 dispatch("flee")                 miss -> UnknownToolError -> caught by try/except
t11 exit 0                           the script survives the error, by design
```

Two things this trace proves. The gap between t5 and t8 is the point of the
Registry: registration and execution happen at different times. And t10 to t11
is the point of `UnknownToolError`: an unknown tool is an ordinary, catchable
outcome, not a crash.

---

## One-liners

- A port inherits from the previous snapshot in the same language; the other
  language is read, never copied.
- `**dict` turns keys into argument names and values into their values — which
  is why Ruby's key-converting line has nothing to do in Python.
- Faithful port means same behaviour including known defects; only docs get
  corrected.

---

## Spine sentence

Copy Python 01 forward, add `Registry` and `UnknownToolError`, attach tool bodies
with `@registry.tool(...)` instead of a Ruby block, delete the key-conversion
step, and prove it by printing the same trace the Ruby snapshot prints.

---

## Glossary

- **snapshot / iteration folder** — a numbered folder holding a complete working
  program at that step, not a list of changes.
- **delta** — only what changed between two snapshots.
- **decorator** — a line starting with `@` above a `def`; it hands that function
  to something else the moment Python reads it. Here it hands the tool body to
  the registry.
- **`**args`** — unpack a dict into named arguments: each key becomes an argument
  name, each value becomes that argument's value.
- **facade** — an object offering verbs but storing nothing itself; `Registry` is
  one over `Context`.
- **launcher** — a small bash script under `bin/` that runs one snapshot.
- **chmod +x** — mark a file runnable.
- **smoke test** — run it once end to end and see whether it works; no formal
  test suite in this course.