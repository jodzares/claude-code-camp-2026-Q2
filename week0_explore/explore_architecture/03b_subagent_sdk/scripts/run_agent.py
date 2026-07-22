#!/usr/bin/env python3
"""Interactive driver for the `play-mud` subagent via the Claude Agent SDK.

Reads .claude/agents/play-mud.md at runtime (frontmatter + prompt body) and
registers it as an SDK AgentDefinition, so the subagent's behavior stays
defined in one markdown file instead of being duplicated here.
"""

import asyncio
from pathlib import Path

from claude_agent_sdk import (
    AgentDefinition,
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    TextBlock,
    ToolUseBlock,
)

ROOT_DIR = Path(__file__).resolve().parent.parent
AGENT_MD_PATH = ROOT_DIR / ".claude" / "agents" / "play-mud.md"

ALLOWED_TOOLS = [
    "Agent",
    "Bash",
    "Read",
    "Write",
    "Edit",
    "Glob",
    "Grep",
    "Bash(python3 scripts/mud.py *)",
    "Bash(python3 scripts/nav.py *)",
    "Bash(tee *)",
    "Bash(cat /tmp/*)",
]


def parse_agent_markdown(path: Path) -> tuple[str, list[str], str]:
    """Split a .claude/agents/*.md file into (description, tools, prompt body)."""
    text = path.read_text()
    _, frontmatter, body = text.split("---", 2)

    fields = {}
    for line in frontmatter.strip().splitlines():
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()

    tools = [t.strip() for t in fields["tools"].split(",")]
    return fields["description"], tools, body.strip() + "\n"


def build_options() -> ClaudeAgentOptions:
    description, tools, prompt = parse_agent_markdown(AGENT_MD_PATH)
    play_mud = AgentDefinition(description=description, prompt=prompt, tools=tools)
    return ClaudeAgentOptions(
        agents={"play-mud": play_mud},
        allowed_tools=ALLOWED_TOOLS,
        cwd=str(ROOT_DIR),
    )


def describe_tool_use(block: ToolUseBlock) -> str:
    if block.name == "Bash":
        command = block.input.get("command", "")
        return f"running: {command}"
    if block.name == "Agent":
        subagent = block.input.get("subagent_type", "?")
        return f"invoking subagent: {subagent}"
    return f"{block.name} {block.input}"


async def main() -> None:
    options = build_options()
    async with ClaudeSDKClient(options=options) as client:
        while True:
            try:
                user_input = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if user_input.lower() in {"exit", "quit"}:
                break
            if not user_input:
                continue

            await client.query(user_input)
            async for msg in client.receive_response():
                if not isinstance(msg, AssistantMessage):
                    continue
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        print(block.text, end="", flush=True)
                    elif isinstance(block, ToolUseBlock):
                        print(f"\n→ {describe_tool_use(block)}")
            print()


if __name__ == "__main__":
    asyncio.run(main())
