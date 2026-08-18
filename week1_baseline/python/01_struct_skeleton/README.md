# 00 · Configuration (Python port)

Python port of `week1_baseline/ruby/00_config`. Behaviour matches the Ruby
version; see `docs/plans/python_port/00_config.md` for the full porting plan
and the reasoning behind every place Python required a different choice than
Ruby.

We want to be able to manage all configurations from an external file eg.
`~/.boukensha/settings.yaml`. We want a dedicated class to handle
configuration: `boukensha.Config`. Configuration will grow with each
iteration; we can hardcode defaults but not configurable values.

Configuration is organised by **task** — a role in the agentic loop bound to
its own LLM. week1_baseline only drives a single `player` task (the main
loop), but a more advanced loop will assign different LLMs to different
tasks. A task is either a "single-task" or a "multi-task" — the latter being
a full agent.

## Design Considerations

Python has no YAML parser in its standard library and no built-in `.env`
loader, so this module depends on `pyyaml` and `python-dotenv` — see
`requirements.txt`.

## Code Layout

| File | Purpose |
|------|---------|
| `boukensha/config.py` | `Config` class |
| `boukensha/tasks/base.py` | abstract `Base` (provider/model + prompt resolution) |
| `boukensha/tasks/player.py` | concrete `Player` (the main loop) |
| `boukensha/__init__.py` | top-level package exports |
| `prompts/system.md` | default system prompt shipped with the library |
| `examples/example.py` | runnable smoke-test |

---

## Config directory resolution

The class looks for a `.boukensha/` directory in this order:

1. **`BOUKENSHA_DIR` env var** — set this to point at any directory you like.
2. **`~/.boukensha`** — the default location for a real install.

## Config directory structure

The class expects the following:

```
.boukensha/
  .env                 # stores credentials eg. LLMs APIs (never committed to repo)
  settings.yaml        # all non-secret settings
  prompts/
    <task>/
      system.md        # per-task override for the default system prompt (optional)
```

---

## Tasks

`boukensha.tasks.Base` is an abstract stateless class. All behaviour is
expressed as classmethods that accept a `settings` dict — no instances are
created. Concrete subclasses define `task_name()`. For now only
`boukensha.tasks.Player` exists; future steps add per-turn ceilings
(`max_iterations`, `max_turn_tokens`, `max_output_tokens`,
`compaction_threshold`) — these are **not** read yet.

`Config.tasks()` returns the raw dict from `settings.yaml` under `tasks:`.
Pass a name to look up a specific task's settings dict, then pass it to the
stateless class:

```python
Player.provider(config.tasks("player"))
Player.system_prompt(
    config.tasks("player"),
    user_prompts_dir=config.user_prompts_dir,
    default_prompts_dir=Config.PROMPTS_DIR,
)
```

## System prompt resolution

Per task, `Player.system_prompt` is resolved in this order:

1. **`.boukensha/prompts/<task>/system.md`** — used when the task's
   `prompt_override.system` is `true` and the file exists.
2. **`prompts/system.md`** — the default system prompt shipped with the
   library.

## Configuration Schema

The following properties so far:
- `tasks`: a map of task name → task config (provider, model, prompt_override).
- `tasks.<name>.prompt_override.system`: when `true`, the task's
  `.boukensha/prompts/<name>/system.md` overrides the default system prompt.
- `mud`: MUD connection information for the main player.

```yaml
tasks:
  player:
    provider: anthropic        # provider name (string)
    model: claude-haiku-4-5
    prompt_override:
      system: true
mud:
  host: localhost
  port: 4000
  username: dummy
  password: helloworld
```

## Run Example

Requires a shared virtualenv at the repo root with the dependencies in
`requirements.txt` installed:

```bash
python3 -m venv .venv
.venv/bin/pip install -r week1_baseline/python/00_config/requirements.txt
```

Then:

```bash
./week1_baseline/bin/python/00_config
```

Expected output (values from your `.boukensha/`):

```
=== Boukensha Step 0: Configuration ===

Config dir:     /home/andrew/Sites/Claude-Code-Camp/.boukensha
Tasks:          player

-- player task --
Provider:       anthropic
Model:          claude-haiku-4-5
Prompt override?True
System prompt:  You are a MUD player assistant. Use the tools available to y...

MUD host:       localhost:4000
MUD user:       dummy

API key set?    True

<Config dir=/home/andrew/Sites/Claude-Code-Camp/.boukensha tasks=player>
```
