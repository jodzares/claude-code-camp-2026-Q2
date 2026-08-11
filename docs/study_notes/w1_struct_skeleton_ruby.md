# Struct Skeleton (Ruby)

## What this builds / doesn't build
- Builds: 3 data shapes (Tool, Message, Context).
- Does NOT build: model call, game connection, loop. Just shapes.

## The three shapes
- Tool: name, description, parameters, block(code).
- Message: role, content, tool_use_id. Roles = user / assistant / tool_result.
- Context: system, messages, tools. Holds everything for one run.

## D1 — Struct for Tool & Message
- Fixed named slots. Typo'd slot raises an error; a hash typo returns nil silently.

## D2 — class for Context (money shot)
- Nouns → Struct. Context has verbs (register_tool, add_message) → class.

## D3 — turn count derived (money shot)
- turn_count = messages.size. No stored counter → one source of truth, no drift.

## D4 — tool code as lambda
- block stores runnable code as a value. .call'd later by the agent loop. String can't run.

## D5 — custom to_s
- Each shape prints one legible, truncated line.

## The run
- bin launcher → loads config → builds Context → registers tool → adds 2 messages
  → prints Config/Context/Tool/Messages → idle. turn_count = 2.

## Spine
- Fixes 3 shapes so every later module passes state in one container, not loose args.


┌─────────────────────────────────────────┐
   │ Context  (class: holds everything)       │
   │   system   ← from config                 │
   │   tools    ← register_tool(Tool)  ──┐     │
   │   messages ← add_message(...)  ──┐  │     │
   │   turn_count ⟵ derived: messages.size │  │     │
   └──────────────────────────────────┼──┼─────┘
                                      ▼  ▼
                           Message      Tool
                           (Struct)     (Struct + lambda payload)