# 02 · The Tool Registry (Python port)

Python port of `week1_baseline/ruby/02_the_registry`. Behaviour matches the
Ruby version; see `docs/plans/python_port/02_the_registry.md` for the full
porting plan and the reasoning behind every place Python required a
different choice than Ruby.

The Tool Registry is how BOUKENSHA manages what capabilities the agent can
use. It has two jobs:
  1. storing tools
  2. dispatching tools when asked

## New Files

| File | Description |
|---|---|
| `boukensha/registry.py` | The `Registry` class — registers tools and dispatches calls |
| `boukensha/errors.py` | BOUKENSHA-specific error classes |

## How It Works

The agent NEVER calls a tool directly.
It emits a structured request (name and args) and the Registry looks up the tool and runs it.

```
Agent:    "Hey registry call move with direction='north'"
Registry: "looking up 'move' in the tool table"
Registry: "Found it, now calling the function with the provided args"
Registry: "Here's the result"
Agent:    "Thanks buddy"
```

## `boukensha.Registry`

| Method | Description |
|---|---|
| `tool(name, description, parameters=None)` | Decorator — registers the function beneath it as a tool on the context |
| `dispatch(name, args=None)` | Looks up a tool by name and calls it with the provided args |

## `boukensha.UnknownToolError`

Raised when `dispatch` is called with a name that has no registered tool.
A harness needs explicit error boundaries — an unrecognised tool name should
never silently fail.

**Example:**
```
UnknownToolError: No tool registered as 'flee'
```

## Expected Output

```
=== Boukensha Step 2: Tool Registry ===

Config:  #<Config dir=... tasks=player>
Context: #<Context task=player turns=0 tools=2>
Tools:
  #<Tool name=move description=Move the player in a direction (north, so params=['direction']>
  #<Tool name=shout description=Shout a message so everyone in the zone c params=['message']>

Dispatching 'shout' with message='dragon spotted'...
Result: DRAGON SPOTTED

Dispatching 'move' with direction='north'...
Result: You move north into a torch-lit corridor.

UnknownToolError caught: No tool registered as 'flee'
```

This is the real output of `example.py`, not aspirational — `Context` has no
`budget` field (same as the `01_struct_skeleton` port).

## Considerations

Attaching a tool's body works differently here than in Ruby. Ruby passes a
trailing block; Python uses a decorator — the `@registry.tool(...)` line
sitting directly above a `def` hands that function to the registry the
moment it's defined:

```python
@registry.tool("move", description="...", parameters={"direction": {"type": "string"}})
def move(direction):
    return f"You move {direction} into a torch-lit corridor."
```

Ruby's `dispatch` also has to convert string-keyed args into symbol keys
before calling the stored block, because its block syntax only accepts
symbol keyword arguments. Python dict keys are always strings, and a
function's keyword arguments are matched by string name already, so no such
conversion step exists here — `dispatch` just unpacks the args dict directly.

We now register tools with the Registry, but our code still has `Context`
holding the actual `tools{}` table while `Registry` only offers the verbs
(`tool`, `dispatch`) — it stores nothing itself. This is a known overlap,
carried over unchanged from Ruby's own step 2. `Context` should really own
only the tools it's currently using, with the full table living on
`Registry`. We'll correct this in a future step, in both languages, and
leave it in place for now.

## Run Example

Requires a shared virtualenv at the repo root with the dependencies in
`requirements.txt` installed (same environment as `01_struct_skeleton`).

```sh
./week1_baseline/bin/python/02_the_registry
```
