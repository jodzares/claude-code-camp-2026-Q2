# 04 · The API Client (Python port)

Python port of `week1_baseline/ruby/04_api_client`. Behaviour matches the
Ruby version; see `docs/plans/python_port/04_api_client.md` for the full
porting plan and the reasoning behind every place Python required a
different choice than Ruby.

The API Client takes the payload assembled by `PromptBuilder` and sends it
to the API. One HTTP POST, one response. No tool loop yet — just proving
the round trip works.

## New Files

| File | Description |
|---|---|
| `boukensha/client.py` | Makes the HTTP request and parses the response |
| `boukensha/backends/base.py` | Shared backend model validation and model metadata helpers |
| `boukensha/tasks/base.py` | Shared task configuration helpers for provider, model, and prompts |
| `boukensha/tasks/player.py` | Player task definition |
| `prompts/system.md` | Default system prompt used when the player task does not override it |

## Updated Files

| File | Change |
|---|---|
| `boukensha/errors.py` | Added `ApiError` for failed HTTP requests |
| `boukensha/tasks/base.py` | Task settings that aren't a dict (e.g. missing entirely) resolve to `None` instead of raising |
| `boukensha/backends/*.py` | Backends own supported model tables with context windows and cost metadata |

## How It Works

```
PromptBuilder
      ↓
Client
      ↓
POST to API endpoint
      ↓
Raw JSON response
```

## `boukensha.Client`

| Method | Description |
|---|---|
| `call(max_output_tokens=1024)` | POSTs the payload and returns the parsed JSON response |

## Task Configuration

This step uses the task-based configuration introduced in the earlier baseline steps:

```yaml
tasks:
  player:
    provider: anthropic
    model: claude-haiku-4-5
    prompt_override:
      system: true
```

When `prompt_override.system` is true, Boukensha reads `.boukensha/prompts/player/system.md`.
Otherwise it falls back to this step's shipped `prompts/system.md`.

Each backend validates the configured model at construction time. Unsupported model names raise `UnsupportedModelError`, and supported models expose backend-owned metadata such as `context_window`, `usage_unit`, and token cost estimates for later logging steps.

## No Dependencies

`Client` uses Python's standard `urllib.request` library. No third-party HTTP package, no `pip install` beyond what's already in `requirements.txt`. This is intentional — the HTTP call itself is trivial and should be visible, not hidden behind a library.

## What the Response Looks Like

The raw response shape differs between backends. This is what you get back from `client.call()` before any processing:

### Anthropic
```json
{
  "id": "msg_01XY",
  "type": "message",
  "role": "assistant",
  "content": [
    { "type": "text", "text": "Sure, let me read that file." }
  ],
  "stop_reason": "end_turn",
  "usage": { "input_tokens": 42, "output_tokens": 18 }
}
```

### Ollama
```json
{
  "model": "llama3.2",
  "message": {
    "role": "assistant",
    "content": "Sure, let me read that file."
  },
  "done_reason": "stop",
  "done": true
}
```

When the model wants to call a tool the response looks different. Anthropic uses `stop_reason: "tool_use"` and adds a `tool_use` block to `content`. Ollama adds a `tool_calls` array to `message`. Handling those differences is the job of step 5 — the Agent Loop.

## Output example

```
$ ./week1_baseline/bin/python/04_api_client
=== Boukensha Step 4: API Client ===

Sending request to https://api.anthropic.com/v1/messages...

Raw response:
{
  "model": "claude-opus-4-5-20251101",
  "id": "msg_01Y3zL8dZKrdLqry6BoiyC4r",
  "type": "message",
  "role": "assistant",
  "content": [
    { "type": "text", "text": "I don't have a function available to list directory contents. I can only read files if you provide me with the specific file path.\n\nCould you either:\n1. Tell me which specific file(s) you'd like me to read\n2. Provide me with a list of the files in your directory\n\nIf you're working in a terminal, you can run `ls` (on Mac/Linux) or `dir` (on Windows) to see what files are available, and then let me know which ones you'd like me to look at!" }
  ],
  "stop_reason": "end_turn",
  "usage": { "input_tokens": 585, "output_tokens": 118 }
}
```

> The response is what we'd expect from Claude: it got the message, saw the `read_file` tool, but told us it can't list directory contents because we only gave it a `read_file` tool, not a `list_directory` tool.

Actual output depends on the provider/model/API key configured in `settings.yaml` — this transcript is illustrative, not a fixed reference result.

## Considerations

**The client raises `ApiError` on failure.** A non-2xx response means something went wrong — bad API key, malformed payload, server error. Boukensha surfaces this explicitly rather than returning a confusing `None` or partial response.

**Transient failures and retryable status codes are retried automatically.** `Client` retries up to `MAX_RETRIES` times, with exponential backoff, for both low-level transport failures (connection refused/reset, DNS failure, TLS failure, timeout) and retryable HTTP status codes (`408`, `409`, `429`, `500`, `502`, `503`, `504`). Mapping Ruby's transient-error list onto Python's `urllib`/`socket`/`ssl` exception types required real judgment, not mechanical translation — see `docs/plans/python_port/04_api_client.md` §3.5.2 for the full category-by-category reasoning.

**SSL is handled automatically.** `urllib.request` finds the OS's trusted CA store on its own via `ssl.create_default_context()` — there's no cert-path workaround to configure, on Linux, WSL2, or macOS.

## Run Example

Requires a shared virtualenv at the repo root with the dependencies in
`requirements.txt` installed (same environment as `03_prompt_builder`), plus a
`.env` in `.boukensha/` with the configured provider's API key present and
`.boukensha/settings.yaml` pointing `tasks.player.provider`/`model` at a
supported combination. This step makes a real network call.

```sh
./week1_baseline/bin/python/04_api_client
```
