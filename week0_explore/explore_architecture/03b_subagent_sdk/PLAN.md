# Plan: convert `play-mud` from a filesystem subagent to an SDK `AgentDefinition`

## Goal
Stop relying on Claude Code's automatic `.claude/agents/*.md` discovery for
this folder's subagent. Instead, build the same agent explicitly in Python
using the Claude Agent SDK's `AgentDefinition`, and drive it from a small
standalone interactive script — with no change in the agent's actual
behavior, tools, or prompt content.

## What stays the same
- `.claude/agents/play-mud.md` stays exactly where it is and keeps its
  current content (YAML frontmatter + prompt body). It becomes the *source
  file* that `run_agent.py` reads at runtime — nothing here gets hardcoded
  as a Python string.
- `scripts/mud.py`, `scripts/nav.py`, `data/` are untouched.
- Tools stay `Bash, Read, Write, Edit, Glob, Grep` — confirmed against the
  script: the agent's only way to run `mud.py` / `nav.py` is via shell
  invocation (`python3 scripts/mud.py ...`), which is exactly what the
  `Bash` tool provides. There is no separate "run Python" tool in the SDK;
  `Bash` is correct and sufficient. Read/Write/Edit/Glob/Grep remain for
  editing `data/player.md`, tailing `/tmp` output files, etc.
- The permission allow-list currently in `.claude/settings.local.json`
  (`Bash(python3 scripts/mud.py *)`, `Bash(python3 scripts/nav.py *)`,
  `Bash(tee *)`, `Bash(cat /tmp/*)`) is ported into `allowed_tools` on the
  SDK options, so the auto-allow behavior is identical.
- `allowed_tools` must ALSO list the base tool names the agent uses —
  `Bash`, `Read`, `Write`, `Edit`, `Glob`, `Grep` — plus `Agent`, not only
  the narrow `Bash(...)` patterns above. The narrow patterns cover specific
  Bash invocations; without the base names too, invoking `play-mud` via the
  `Agent` tool (and any tool call that falls outside those four exact Bash
  patterns) hits a permission prompt and stalls the run, since there's no
  human at the keyboard in this script to approve it.

## New file: `scripts/run_agent.py`
An executable, standalone script (`chmod +x`, `#!/usr/bin/env python3`)
that:

1. **Loads the prompt from markdown at runtime.**
   Reads `.claude/agents/play-mud.md`, splits off the `---`-delimited YAML
   frontmatter, and uses:
   - `description` and `tools` from the frontmatter to build the
     `AgentDefinition`
   - the remaining body text, verbatim, as `AgentDefinition.prompt`
   Frontmatter here is flat scalars (`name`, `description`, `tools` as a
   comma-separated list) — parsed by hand with simple string splitting, no
   new dependency (e.g. `PyYAML`) required for something this simple.

2. **Defines the agent:**
   ```python
   AgentDefinition(
       description=<parsed description>,
       prompt=<parsed body>,
       tools=<parsed tools list>,   # ["Bash", "Read", "Write", "Edit", "Glob", "Grep"]
   )
   ```
   registered as `agents={"play-mud": ...}` on `ClaudeAgentOptions`, so it's
   invokable via the Agent tool exactly like today's filesystem subagent —
   including being triggered implicitly by matching the user's request
   against its `description`, without the user having to name it.

3. **Configures `ClaudeAgentOptions`:**
   - `agents={"play-mud": agent_def}`
   - `allowed_tools=[...]` — `Agent`, `Bash`, `Read`, `Write`, `Edit`,
     `Glob`, `Grep`, plus the four narrow `Bash(...)` patterns from
     `.claude/settings.local.json`, so both the subagent invocation itself
     and every tool call it makes are auto-approved
   - `cwd=<the 03b_subagent_sdk directory>` — set explicitly (not inherited
     from wherever the script happens to be launched) so `scripts/mud.py`
     and `data/*` resolve the same way they do today
   - everything else left at SDK defaults, so the top-level session behaves
     like a normal Claude Code session with one extra subagent registered —
     this keeps behavior identical rather than introducing a new bespoke
     top-level system prompt

4. **Runs an interactive loop** using `ClaudeSDKClient` (the SDK's
   bidirectional/multi-turn client — `query()` is for one-shot use and
   doesn't fit a REPL):
   ```python
   async with ClaudeSDKClient(options=options) as client:
       while True:
           user_input = input("> ")
           if user_input.strip().lower() in {"exit", "quit"}:
               break
           await client.query(user_input)
           async for msg in client.receive_response():
               # print assistant text as it streams in, plus tool-use
               # events (see below)
   ```
   Wrapped in `asyncio.run(...)`. Ctrl-C / EOF also exits cleanly.

   **Turn-by-turn tool visibility.** The loop prints tool-use events, not
   just streamed text, so you can see what the agent (and the `play-mud`
   subagent it invokes) is actually doing as it runs — not just its prose.
   Walking `msg.content` on each `AssistantMessage`:
   - `TextBlock` → print the text as today.
   - `ToolUseBlock` (`.name`, `.input`) → print a one-line summary before
     the call resolves, e.g. for `Bash` print
     `→ running: python3 scripts/mud.py send "look"` (its `input["command"]`);
     for `Agent` print `→ invoking subagent: play-mud`; for other tools
     print `→ {name} {input}` generically.
   - `ToolResultBlock` (on the following `UserMessage`) is left unprinted
     for now — only the call itself is surfaced, to keep output readable;
     can be added later if needed.

## Requirements / prerequisites (not code changes, but needed to run it)
- `claude_agent_sdk` isn't installed in this project yet (only found in an
  unrelated venv elsewhere on this machine). Plan assumes a venv gets set
  up in this folder with `pip install claude-agent-sdk` before running.
- The SDK shells out to the `claude` CLI binary, which is already on
  `PATH` (`/home/jpopovic/.local/bin/claude`) — no extra setup needed there.

## Out of scope for this change
- No changes to `scripts/mud.py`, `scripts/nav.py`, or anything in `data/`.
- No change to the actual MUD-playing prompt content/behavior.
- Not deleting `.claude/agents/play-mud.md` or `.claude/settings.local.json`
  — `run_agent.py` reads the former at runtime; the latter is left in place
  for reference/parity but is no longer what grants permissions once
  running through the SDK script (that's `allowed_tools` now).

## Resolved: tool-use visibility
Decided: surface tool-use events in the loop (see step 4 above), not just
raw streamed text — turn-by-turn visibility into what the agent is doing
was the point of the exercise.
