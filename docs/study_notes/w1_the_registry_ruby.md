# The Registry (Ruby)

## What it's for
- The tools table lives on Context. A tool sitting there is just stored — it never runs on its own.
- The Registry builds tools, files them into Context's table, and dispatches them: looks one up by name and runs it.
- Two new files: `registry.rb` (the class) and `errors.rb` (the error type).

## D1 — Tool table stays on Context
- Context owns `@tools` (the data) and `register_tool` (the method that files into it), and prints `tools=`.
- Registry holds only a pointer to Context and files through it.
- Moving the table to Registry = two owners that drift out of sync.

## D2 — Unknown tool name raises (fail-fast)
- Dispatch is the actual running of a tool.
- On a missing tool it raises `UnknownToolError` — a loud, clear stop naming the bad tool.
- Returning `nil` would look like the tool ran fine and hide the bug further down the line.

## D3 — Errors get their own file
- `errors.rb` holds all custom error definitions in one place.
- Any file can raise or rescue them by requiring `errors.rb`, without depending on Registry (the code that throws them).
- One shared definition means a `raise` and its `rescue` always refer to the identical class. Two same-named classes = rescue silently misses.

## D4 — dispatch converts string keys → symbols (MONEY SHOT)
- Model sends args as string keys like `"direction"`; the block declares `|direction:|`, which needs a symbol `:direction`.
- Dispatch converts them because it's the common gateway every tool call passes through — centralize it there, done once, not copied into every tool.
- Convert in each tool instead = N copies, one forgotten = silent break.

## D5 — registry.tool welds build + file
- One `registry.tool` call builds the tool AND files it into Context in a single move.
- Caller never touches `Tool.new` or `register_tool` directly, so it's impossible to build a tool and forget to file it.
- Build recipe lives in one method instead of copied into every caller.

## The run
- bin launcher → loads Config → builds Context → `Registry.new(ctx)` (stores pointer)
  → `registry.tool("move"...)` + `registry.tool("shout"...)` (build + file, ctx.tools=2)
  → prints Context + tools → dispatch "shout" (DRAGON SPOTTED) → dispatch "move"
  → dispatch "flee" raises `UnknownToolError`, rescued and printed → idle.

## Spine sentence
- The Registry builds tools, files them into Context (which still owns the table),
  and dispatches them by name — converting string keys to symbols before running,
  and raising `UnknownToolError` when the name is unknown.

## Known debt (Andrew's note)
- Tools still get registered on Context directly as well as through Registry;
  Andrew flags this as untidy and says the clean split comes in a later step.