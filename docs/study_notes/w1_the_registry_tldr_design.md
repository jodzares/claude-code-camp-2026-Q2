# Design TLDR — The Registry (language-agnostic)

This describes *what* is being built, not how it's spelled in Ruby or Python.
Written so an engineer in any language can follow it without knowing either.

## The problem

An agent needs to call named "tools" (actions like `move`, `shout`) without the
core loop hard-coding every action by name. So: build a lookup table that maps
a tool's **name** to its **behavior**, plus one function that runs a tool by
name instead of calling it directly.

## The shape of a Tool

A record with 4 fields:

```
Tool:
  name           : string
  description    : string          # human-readable, for a future LLM prompt
  parameters     : map(name -> spec)  # what arguments this tool expects
  body           : callable         # the actual code that runs
```

Nothing new here — this record already existed before this step (previous
step). This step is only about what manages a collection of these.

## The Registry — two operations only

```
Registry:
  holds: a reference to some shared state that owns the tool table
         (NOT its own table — see "Known design debt" below)

  operation REGISTER(name, description, parameters, body):
      build a Tool record from the 4 inputs
      store it in the shared tool table, keyed by name
      # note: body is NOT executed here. It is only filed away.

  operation DISPATCH(name, args):
      tool = look up `name` in the shared tool table
      if not found:
          raise a NamedError("no tool registered as '<name>'")
      else:
          run tool.body, passing `args` as its inputs
          return whatever tool.body returns
```

That's the whole mechanism. Everything else in this step is plumbing around
these two operations.

## The key insight: registration and execution are two different moments

```
t0:  REGISTER("move", ...)     -> Tool is built and stored. body has NOT run.
t1:  REGISTER("shout", ...)    -> same.
t2:  ... arbitrary time passes, table now has 2 tools, nothing has executed ...
t3:  DISPATCH("shout", {message: "dragon spotted"})
         -> lookup succeeds -> body runs NOW -> returns "DRAGON SPOTTED"
t4:  DISPATCH("flee", {})
         -> lookup fails -> NamedError raised -> caller catches it, keeps going
```

The entire point of a Registry is that gap between t1 and t3: *describing* a
capability and *invoking* it are decoupled. Whatever language you're in, look
for its version of "store a reference to a not-yet-called function" — that's
the one piece of syntax this step is really testing (Ruby: a trailing block.
Python: a decorator. Your language: whatever its closure/callback mechanism is).

## Error handling shape

- One custom error type, carrying just a message. No special fields, no
  hierarchy beyond "this is a distinct, catchable kind of error."
- Raised on exactly one condition: dispatching a name with no matching entry.
- The caller wraps a dispatch call in a try/catch, prints the error, and
  **keeps running** — an unknown tool name is treated as an expected,
  recoverable outcome, not a crash.

## Known design debt — reproduced on purpose

The tool table conceptually belongs to the Registry, but in this step it
still physically lives on the *other* object (the one holding conversation
state) — the Registry only borrows a reference to it and offers `register`/
`dispatch` as a thin front end.

This is a **known, flagged flaw**, not an oversight: a later step moves
ownership properly onto the Registry. This step's job is only to introduce
the two operations above — not to also fix where the data lives. If you're
implementing this from the pseudocode above, resist the urge to "clean this
up" — matching the flaw is part of the spec for this exact step.

## Explicitly out of scope for this step

- No network/API client of any kind.
- No agent loop (nothing decides *which* tool to call — a human/test still
  picks the name and args explicitly).
- No formal automated test suite — verification is "run it once, read the
  output."

## One-sentence summary

Add a small facade — `register(name, description, parameters, body)` and
`dispatch(name, args)` — that turns named, stored-but-not-yet-run behavior
into something callable by string, with one dedicated error for "that name
doesn't exist," while deliberately leaving the underlying storage location
un-refactored.
