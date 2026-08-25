# Prompt Builder — TLDR

**Job:** turn the conversation into the exact request one provider wants. Return it. Never send it.

**Big picture:** builder = socket, adapter = plug.
The builder knows no vendor. It asks 5 fixed questions and forwards each to the one adapter it was handed. Five adapters, one per provider. Add a sixth provider = add one file, touch the socket zero times.

**THE CHAIN (memorise this):**
`runner` (`examples/example.rb` — the file you run) reads the `provider` (a WORD in settings.yaml) → builds the matching `adapter` (ONE FILE per vendor, e.g. `backends/anthropic.rb`) → builds the `context` (the conversation) → hands context + adapter to the `builder` (ONE FILE, `prompt_builder.rb`).
Trap: provider is a word, not a file. The runner picks the adapter; the builder just receives it.

**The 5 decisions:**

1. **Build, don't send.** Pure step: same conversation in → same request out, no network, no cost. You inspect the request before any transport exists. (Doesn't prove it's *correct*.)
2. **MONEY SHOT — five adapters, not one branching builder.** Vendor knowledge lives in five separate plugs, not in one big if/else. Cost: 3 adapters duplicate code, and the contract isn't actually enforced.
3. **Builder receives the adapter, doesn't pick it.** The runner reads settings, builds the adapter, hands it in. The vendor branch fires once, at startup, at the edge.
4. **Unknown model = refuse at startup**, listing every valid model. Point isn't cost — it's that the error names the fix. Model table also carries context window + prices.
5. **Providers differ in WHERE things sit, not what they're called.** System prompt is top-level for Anthropic/Gemini, folded into the message list for OpenAI/Ollama (3 messages vs 4). A rename table can't move an item into a list → that's why D2 was necessary.

**Boot order (each needs the one above):**
Config → Context → provider switch builds+validates one adapter → Builder(context, adapter) → print payload. [send = iteration 04, doesn't exist yet]

**3 landmines:** remove the `.gitignore` line for this module; `BOUKENSHA_DIR` needs 4 levels up; `ANTHROPIC_API_KEY` must exist locally (never called, just present).

# Prompt Builder Ruby — study note

> Personal learning note. NOT graded documentation. Graded docs live in `docs/journal/`.
> Iteration 03 of the agent. Written language-neutral: concepts, not Ruby or Python syntax.

---

## Spine sentence

The Prompt Builder takes the conversation the project already holds, hands it to **one
interchangeable, hand-picked provider adapter**, and gets back the exact request that one
vendor expects — as plain data that is never sent.

---

## What problem this module solves

You have a conversation in memory: a system prompt, a list of messages, a set of tools.
You want to talk to a large-language-model provider. But there are five providers
(Anthropic, Ollama, Ollama Cloud, OpenAI, Gemini), and **each one wants that identical
conversation shaped into a differently-structured JSON request**. Same information, five
incompatible envelopes.

This module builds the right envelope for whichever provider is configured — and then
stops. It does not open a socket. It does not spend a token. It produces the request and
returns it.

**Why stop there?** Because building is a *pure* step: same conversation in → same request
out, every time, with no network and no cost. That means you can run it, print it, and eyeball
it **before any transport layer exists** (that's iteration 04). A bug in the request shows up on
your own screen instead of as a bill or a rejection from a vendor.

The one thing it does NOT give you: proof the request is *correct*. A misspelled field prints
just as prettily as a right one. That lie survives until iteration 04 actually sends it.

---

## The shape of the design (the big picture first)

```
        ┌──────────────────────────────────────────────────────┐
        │  SHARED BUILDER  (prompt_builder.rb)                  │
        │  knows NO vendor. holds a conversation + one adapter. │
        │                                                       │
        │  asks exactly 5 questions, forwards each:             │
        │    1. serialize the messages                          │
        │    2. serialize the tools                             │
        │    3. assemble the full payload                       │
        │    4. what request headers?                           │
        │    5. what endpoint URL?                              │
        └───────────────────────┬──────────────────────────────┘
                                 │ forwards all 5 to →
                                 ▼
        ┌──────────────────────────────────────────────────────┐
        │  ONE PROVIDER ADAPTER  (exactly one of five)          │
        │  Anthropic │ Ollama │ OllamaCloud │ OpenAI │ Gemini   │
        │  each holds: this vendor's envelope shapes            │
        │              + a fixed table of models it accepts     │
        │  all five inherit: model validation + cost maths      │
        │              from a shared parent (backends/base.rb)  │
        └──────────────────────────────────────────────────────┘
```

Read that as: **the builder is a socket, the adapter is the plug.** The builder is written
once and never mentions a vendor by name. Each vendor is a separate plug that fits the same
socket. To support a sixth vendor you make a sixth plug — you do not touch the socket.

Those **five questions are the contract.** "This provider is supported" means precisely:
*some adapter can answer all five questions.* Nothing more, nothing less.

### THE CHAIN — name each part (word / file / role)

```
provider = the WORD in settings.yaml          → a string like "anthropic", NOT a file
adapter  = ONE FILE per vendor                → backends/anthropic.rb, backends/openai.rb, …
builder  = ONE SEPARATE FILE                  → prompt_builder.rb  (holds a Context + one adapter)
context  = ONE FILE                           → context.rb         (holds the conversation)

CHAIN:  provider (word)  →  picks the adapter (one file)  →  handed to the builder (holds context + adapter)
```

The #1 trap: **provider is a word, not a file.** It's the label in settings that decides
*which* adapter file gets built. The builder never picks it — it receives the finished
adapter and just stores it (that's D3).

---

## The five decisions

### D1 — Build the request, or send it too?

**The tension:** "talk to a model" secretly bundles two jobs — *assemble the request* and
*put it on the wire.* Fuse them and you can never inspect the first without paying for the
second.

**The choice:** split. This module assembles only. It returns a data structure and ends.
There is no HTTP anywhere in it.

**Why the other loses — played out:** a fused builder, run today, dies the instant it tries
to transport, because there is no network in the sandbox and no reason to have one yet:

```
Failed to open TCP connection to api.anthropic.com:443 (SocketError)
```

Split, the same run is green: no internet, no token balance, and the finished request
printed to your screen for inspection.

**The honest cost:** nothing here proves the request is *correct*. Wrong field names print
happily and only break in iteration 04.

---

### D2 — MONEY SHOT. One component that knows all five providers, or five that each know one?

**The tension:** every provider wants the same conversation in a different envelope. Where
should the vendor-specific knowledge live — in one big component that branches five ways at
every step, or scattered into five small components that each know exactly one vendor?

**The choice:** five small ones. The shared builder holds **zero** vendor knowledge. It asks
its five questions and forwards each to the one adapter it was handed.

**Why this is the money shot — the extend test:**

| you want to… | one branching component | one adapter per provider |
|---|---|---|
| format the messages | test "which provider?" here | the chosen adapter just knows |
| format the tools | test again | same |
| place the system prompt | test again | same |
| set the headers | test again | same |
| set the endpoint | test again | same |
| **add a sixth provider** | **edit 5 spots in 1 file, miss one → silent bug** | **add 1 file, edit 0** |

Same question, two real answers — the request headers:

```
Anthropic adapter → { Content-Type, x-api-key, anthropic-version }
OpenAI adapter    → { Content-Type, Authorization: "Bearer …" }   ← different scheme entirely
```

**Why the other loses — played out:** a branching component with one branch not-yet-written
(a *what-if*, not in the real code) run for Gemini prints nothing and raises nothing:

```
Headers:
          ← empty. no error, no clue.
```

With one adapter per provider, "does this vendor answer this question?" is decided by
*whether the adapter exists* — a visible, structural fact — not by a branch someone might
forget.

**The honest cost — two of them, both real:**
1. **Duplication.** Three adapters (Ollama, Ollama Cloud, OpenAI) carry byte-identical
   tool-serialization code. Independence is paid for in repetition.
2. **The contract isn't actually enforced.** Two adapters answer the "serialize messages"
   question expecting *one* input; three expect *two*. The builder always passes one. Call
   that method directly on the wrong three and it crashes on argument count. The example
   never calls it directly — it calls the full-payload question, which works — so the crack
   stays hidden this week. (This is *arity*: how many inputs a routine expects.)

---

### D3 — Who picks the provider adapter?

**The tension:** something must turn the word `anthropic` from a settings file into a *live*
adapter object. Should the builder look it up itself, or receive a finished one?

**The choice:** receive. The builder is handed a ready-made adapter at creation time and
never resolves one. Its whole setup is: store the conversation, store the adapter, do
nothing else. This is **dependency injection** — the collaborator is passed in, not
constructed internally.

**Where the five-way choice actually lives:** at the edge, in the example/runner file. It
reads the provider name from settings, builds the matching adapter, and hands it in. That
branch fires **once, at startup** — not at every formatting step.

**Why the other loses — played out:** a self-resolving builder must hard-code every vendor's
construction shape, and they differ (local Ollama takes a host address and *no* key;
Anthropic takes a secret key). Give it the naive uniform guess (`Ollama.new(api_key:…)`, a
*what-if*) and run for Ollama:

```
unknown keyword: :api_key   ← Ollama has no such input; it never takes a key
```

**The honest cost:** the branch didn't vanish. It moved to the runner and now runs exactly
once. Fair trade — the builder stays vendor-blind.

---

### D4 — An unknown model name: pass it through, or refuse to start?

**The tension:** a model name is a string a human typed into a settings file. It can be
misspelled. Do you carry the bad string all the way to the vendor and let *them* complain,
or refuse to even construct the adapter?

**The choice:** refuse, at construction, in code shared by all five adapters — and on
failure, **list every model that would have worked.**

**Why this is the design — it's not about cost:** with a typo `claude-haiku-4.5` (dot,
should be dash):

```
Pass-through:   builds fine, prints fine, shows the typo in the JSON.
                Vendor rejects it later — vaguely, and only in iteration 04.

Refuse-at-build: STOPS immediately —
  "Anthropic does not support model "claude-haiku-4.5".
   Supported models: claude-haiku-4-5, claude-haiku-4-5-20251001,
   claude-opus-4-8, claude-sonnet-4-6"
```

The point isn't that failing is cheaper. It's that **the failure names the fix.** You learn
*when* it's typed and *exactly* what the right options are. That's fail-fast with a helpful
error.

**The table is more than a whitelist.** Each model entry carries: context window,
input price per million, output price per million, and a usage unit. The shared parent
exposes those plus a cost estimator. (Local Ollama reports zero token cost; Ollama Cloud
returns no estimate at all because its pricing is plan-based, not per-token.)

**The honest cost:** the tables are hand-typed static data with prices frozen at one date. A
model released tomorrow is rejected until someone edits a file.

---

### D5 — Do providers differ in what things are CALLED, or in WHERE things sit?

**The tension — and why it justifies D2:** if vendors only disagreed about *spelling*
(this one calls it `system`, that one calls it `instructions`), then one shared formatter
plus a rename table would cover all five, and D2's five separate adapters would be overkill.
They don't. **They disagree about position.** An item that is top-level for one vendor must
become an entry *inside a list* for another.

**Clearest case — the system prompt.** One string, four homes:

| provider | where the system prompt sits | messages-list length |
|---|---|---|
| Anthropic | its own top-level slot | 3 |
| Gemini | its own top-level slot (wrapped) | 3 |
| OpenAI | **first entry inside** the conversation | **4** |
| Ollama | **first entry inside** the conversation | **4** |

The list length changes. That's a **container change**, not a value change.

**Why the other loses — played out:** a rename-table version asked for OpenAI still puts the
prompt in a top-level `system` field OpenAI doesn't have, and leaves the list at 3:

```
{ "model": "gpt-5.5",
  "system": "You are my MUD jodza-player",   ← OpenAI has no such field
  "messages": [ …3 entries… ] }              ← should be 4
```

A rename table can change a label. It cannot move an item into a list. That is why each
adapter assembles its own container from scratch.

**The honest cost:** five hand-written containers, five chances to get one wrong, and no
test in this module that would catch it.

**Three more positional divergences (same reasoning, receipts only):**

| | Anthropic | Ollama | OpenAI | Gemini |
|---|---|---|---|---|
| a tool *result* is… | a `user` message holding a `tool_result` block | its own `tool` role | its own `tool` role | a `user` message holding a `functionResponse` part |
| a tool *definition* is… | name + raw input schema | wrapped in a `function` envelope | same envelope | wrapped in `functionDeclarations` |
| the model's own turn is called… | `assistant` | `assistant` | `assistant` | `model` |

---

## How it boots and runs — the flow, step by step

This is the whole run of the example, in order. The **why** of each step is in brackets.

```
t0   Set BOUKENSHA_DIR → the repo-root .boukensha
        [must be 4 levels up; my config lives at repo root, not inside week1_baseline]
t1   Config loads: reads .env, reads settings.yaml
        [.env only has to EXIST here — the key isn't used to call anything yet]
t2   Read the player task → provider=anthropic, model=claude-haiku-4-5, override=on
t3   Resolve the system prompt → override on, so read MY prompt file
        [not the default shipped one]
t4   Create the Context → empty messages, empty tools
t5   Register tool "look"  (no parameters)
        [the description is stored to be SENT; the code block is stored to run LOCALLY,
         and is never serialized — the model only ever sees the description]
t6   Register tool "move"  (one parameter: direction)
t7   Add message: user  — "I just arrived in the dungeon…"
t8   Add message: assistant — "Let me take a look around first."
t9   Add message: tool_result — "A damp corridor…", tagged toolu_01X
        [the tag ties this result back to the tool call that produced it]
t10  Read provider + model off the task
t11  ── PROVIDER SWITCH (the only vendor branch, at the edge) ──
        build Anthropic adapter(key from env, model)
        ├─ key absent   → STOP: KeyError
        └─ model unknown→ STOP: UnsupportedModelError (lists valid models)
t12  Create the Builder(context, adapter) → stores two references, does nothing else
t13  Builder.to_api_payload → adapter.to_payload(context)
        → adapter serializes tools + messages into ITS envelope
t14  Pretty-print the JSON
t15  Exit. Nothing was sent. The builder is idle until iteration 04.
```

### The boot dependency chain (why the order is forced)

```
settings.yaml + .env
      │  (Config must exist first — everything reads from it)
      ▼
   Config ──► which task? which provider? which model? which prompt?
      │
      ▼
   Context  ◄── system prompt, and later the messages + tools
      │            (the conversation has to exist before it can be shaped)
      ▼
   Provider switch ──► ONE adapter, fully built + model-validated
      │            (must succeed before the builder is worth creating —
      │             this is where a bad key or bad model stops the world)
      ▼
   Builder(context, adapter)
      │            (needs BOTH: nothing to build without a conversation,
      │             no way to build without an adapter)
      ▼
   payload  ──►  printed.   [ send: does not exist yet ]
```

Each arrow is a hard prerequisite: the thing below cannot be created until the thing above
succeeds. That's why validation (D4) sits at t11 — it fails **before** the builder is even
born, so you never build a request around a model that can't work.

---

## What the finished request looks like (my real settings — Anthropic)

```json
{
  "model": "claude-haiku-4-5",
  "system": "You are my MUD jodza-player",
  "max_tokens": 1024,
  "tools": [
    { "name": "look", "description": "…",
      "input_schema": { "type": "object", "properties": {}, "required": [] } },
    { "name": "move", "description": "…",
      "input_schema": { "type": "object",
        "properties": { "direction": { "type": "string", "description": "…" } },
        "required": ["direction"] } }
  ],
  "messages": [
    { "role": "user",      "content": "I just arrived in the dungeon…" },
    { "role": "assistant", "content": "Let me take a look around first." },
    { "role": "user", "content": [
        { "type": "tool_result", "tool_use_id": "toolu_01X", "content": "A damp corridor…" } ] }
  ]
}
```

Switch settings to OpenAI/`gpt-5.5` and the **same run** produces a structurally different
envelope: no top-level `system`, four messages (prompt folded in first), tools wrapped in a
`function` envelope, the tool result under a dedicated `tool` role.

---

## One-liners I earned

- The builder's five questions **are** the contract — a provider is supported exactly when
  some adapter answers all five.
- Provider divergence is **positional, not lexical**, which is the whole reason a rename
  table couldn't do this job and five real adapters had to.
- Validation lives **before construction finishes**, so a bad model name stops the world
  early and *names the fix* instead of failing vaguely at send time.

---

## Landmines this module hit

1. **`.gitignore`** contained `week1_baseline/ruby/03_prompt_builder/` under "future
   lessons". Remove it before committing or the whole module silently won't stage.
2. **`BOUKENSHA_DIR`** in the example needed **four** levels up, not three — my `.boukensha`
   is at repo root. This is the "probably have to go up a directory" fix Andrew makes live.
3. **First lesson where an env key must EXIST.** The example fetches `ANTHROPIC_API_KEY` in a
   form that raises immediately if absent. It's never used to call anything this week — it
   only has to be present. Confirm a local `.env` sets it (the `.env` is gitignored, correctly).

---

## Glossary

- **payload** — the finished request, as plain data, before anything transmits it.
- **serialize** — turn in-memory objects into the flat shape a wire format (JSON) needs.
- **adapter / backend** — a provider-specific component holding one vendor's knowledge only.
- **contract** — the fixed set of questions every interchangeable adapter must answer.
- **dependency injection** — handing a component its collaborator ready-made instead of
  letting it construct one internally.
- **fail-fast** — stop at the earliest moment a problem is knowable, with a clear message.
- **arity** — how many inputs a routine expects; the D2 crack is an arity mismatch.
- **stateless** — the vendor remembers nothing between calls; the whole history is re-sent
  every request. The project carries the state; the provider carries none.

