# API Client — TLDR

**Job:** send the request the builder already assembled. Get the reply back. Don't read it.

**Big picture:** first step that leaves the machine, first step that costs money.
Everything through 03 assembled and printed; a fake key would have passed. The client holds
**one** thing — the builder — asks it three questions (address? headers? body?), sends,
retries what's worth retrying, and hands back the whole reply converted but untouched.

**THE CHAIN (memorise this):**
`launcher` (`bin/ruby/04_api_client`) → `runner` (`examples/example.rb`) → reads `provider`
(a WORD in settings.yaml) → builds the `adapter` (ONE FILE per vendor) → builds the
`context` (the conversation + tools) → `builder`(context, adapter) → `client`(builder) →
sends → reply parsed → printed.
Trap: the client holds ONE thing and it's the **builder**. It never learns the word
`anthropic`. `ApiError` is a word, not a file.

**The 5 decisions:**

1. **Hold the builder, not the adapter.** One thing to hold instead of two — the body can't
   be made from vendor knowledge alone, it needs the conversation. Cost: the client is
   useless without a builder.
2. **MONEY SHOT — clarity over convenience.** No SDK, no HTTP helper library; send using
   only what ships with the language. Five vendors means five libraries that disagree
   (Anthropic's own SDK differs between TypeScript and Python). Cost: I must point at my
   machine's certificate file myself — so the shipped code points at **nothing** and lets
   the OS answer. Verification stays on.
3. **Retry policy declared, not branched.** Four facts at the top: retryable status codes,
   transient connection errors, max attempts, backoff base. The loop just consults them.
   Waiting doubles: 0.5s, 1s, 2s. Cost: one policy for all five vendors.
4. **Two failure kinds, one failure name.** Dead connection and refused request both raise
   `ApiError`; the difference lives in the message text. Nothing downstream would act on
   the difference. Cost: can't branch on kind without reading text.
5. **Convert the reply, don't extract from it.** Turn the characters into navigable data and
   stop. Extracting the answer text would discard the tool call, the stop reason and the
   token counts — on Andrew's run the model called a tool and had no text at all, so
   extraction would have printed `nil`. Shape-flattening is step 05's job.

**Boot order:** config → context + tools → provider word → adapter (model validated) →
builder → client → **[t8: POST leaves, money starts]** → reply parsed → printed.

**3 landmines:** remove the `.gitignore` line for this module *first*; `BOUKENSHA_DIR`
needs 4 levels up, shipped file has 3 (else `task player provider is required in
settings`); `ANTHROPIC_API_KEY` must be **real and funded** — this step actually sends.

**Known flaws Andrew left in:** the client holds state (he wanted stateless); Ollama's host
is hard-coded. Both recorded, neither fixed — the fix would uplift every layer.

---

# API Client Ruby — study note

> Personal learning note. NOT graded documentation. Graded docs live in `docs/journal/`.
> Iteration 04 of the agent. Written language-neutral: concepts, not Ruby or Python syntax.

---

## Spine sentence

The API Client takes the address, headers and body the builder already produces, sends
them itself using only what ships with the language, retries the failures worth retrying,
raises one failure name for everything else, and hands back the vendor's reply as
navigable data — unflattened, unexplained, and for now unused.

---

## What problem this module solves

Everything through step 03 could assemble a request but never send one. The Prompt
Builder produced the address, the headers and the body, and the runner printed them to
the screen — nothing ever left the machine, and a fake API key would have passed every
step so far.

The API Client is the missing half. It takes that assembled request, performs the actual
network call, survives the things that go wrong on a network, and hands back what came
home. This is the first step that talks to a real model, and the first that costs money.

---

## The shape of the design

### THE CHAIN — name each part (word / file / role)

| Part | Word or file? | Role |
|---|---|---|
| `provider` | **WORD** in settings.yaml (`anthropic`) | names which vendor to use |
| launcher | FILE — `bin/ruby/04_api_client` | one-line shim; enters the folder, runs the runner |
| runner | FILE — `examples/example.rb` | the file I actually execute |
| adapter | FILE, one per vendor — `backends/anthropic.rb` | knows one vendor |
| context | FILE — `context.rb` | holds the conversation and the tools |
| builder | FILE — `prompt_builder.rb` | holds the context + the adapter |
| client | FILE, **new this lesson** — `client.rb` | holds the builder; sends |
| `ApiError` | **WORD** naming a failure kind — `errors.rb` | the one name every failure ends as |

**Order:**
launcher → runner → reads the `provider` word → builds the adapter → builds the context →
builder(context, adapter) → client(builder) → client sends → reply parsed → runner prints it.

**Trap:** the client holds ONE thing, and it's the builder. Not the adapter, not the
context, not the settings. It never learns the word `anthropic`.

---

## The five decisions

### D1 — What does the sender need to know?

To send, three facts are needed: the address, the headers, the body. All three are
vendor-specific, and they already have an owner.

- **Option A — hold the builder.** One thing to hold. The client asks it the same three
  questions no matter which vendor is in play; the builder returns vendor-specific
  answers.
- **Option B — hold the adapter directly.** Two things to hold, because the body cannot
  be produced from vendor knowledge alone — it needs the conversation handed in as well.

**Chosen: A.** The builder is the single doorway. The client stays vendor-agnostic and
never learns the word `anthropic`.

**Cost:** the client is useless without a builder. There is no way to push a hand-written
request through it.

---

### D2 — MONEY SHOT. Hand-rolled sending, or the vendor's own library?

**The trade: clarity over convenience.** A prewritten library does the sending for you and
hides how. Doing it yourself means the exact bytes leaving the machine are visible in a
file I can open. Andrew takes the visible version.

Convenience is the only thing the library side is selling, and at five vendors it stops
being convenient. Five vendors means five libraries that disagree with each other —
Anthropic's own Agent SDK ships in TypeScript and in Python and the two do not have the
same features. So "use the SDK" is not one answer, it is five answers with five different
holes. Hand-rolled is one shared sender, and a sixth vendor touches it zero times.
It is also a hard project constraint: raw REST, no provider SDKs.

**Cost — clarity is not free.** Libraries also quietly find the files my machine uses to
verify a secure site is genuine. Doing it myself, I have to point at those files, and the
path is different on macOS and on WSL2. The shipped code deals with this by pointing at
**nothing**: the line naming a certificate path is deliberately commented out, so the
operating system answers the question about itself and the code runs everywhere.
Verification stays switched on — only the hard-coded path is dropped.

---

### D3 — Where does "try again" knowledge live?

Some failures might vanish if you just wait — server busy, connection dropped. Others never
will, like a wrong key. Only the first kind is worth a second attempt.

The real decision is **where that split is written down**. Option A declares it up front as
named facts: which reply codes deserve a retry, which connection failures deserve a retry,
how many attempts, how long to wait. The sending loop then just consults them and holds no
trivia of its own. Option B decides case by case inside the loop, so the policy exists
nowhere you can read it. **Chosen: A** — adding a new retryable code means adding a number
to a list, not editing the sending logic. Waiting doubles each time: 0.5s, 1s, 2s.

**Cost:** one policy for every vendor and every call. I cannot be patient with one vendor
and give up fast on another without changing the file.

---

### D4 — Two failure kinds, one failure name

Two different bad things can happen when sending: the connection never completes, or the
vendor answers with a refusal. Both end as the same named failure, `ApiError`. The
difference is carried in the message text, not in the name.

**Why one name is enough:** nothing downstream would act differently on the two. A caller
only needs to know the send did not work.

**Cost:** I cannot decide "retry network failures, abort on a refusal" from outside the
client without reading the message text.

---

### D5 — How finished should the reply be when handed back?

The reply arrives as one long string of characters. The client converts the **whole** thing
into navigable data and stops. Nothing is pulled out, nothing is discarded, the vendor's
own shape survives.

- **Option A — convert and stop.** What I can then reach for: `["content"][0]["text"]`,
  `["stop_reason"]`, `["usage"]["input_tokens"]`.
- **Option B — extract the answer text here.** Convenient, and it silently discards the
  tool the model wants to call, why it stopped, and the token counts.

**Chosen: A.** Sorting out how the five vendors each shape their replies is step 05's job,
not this one.

**The proof:** on Andrew's run the model did not answer in words at all — it asked to call
a tool. `stop_reason` came back as `tool_use` and there was no text block. Option B would
have printed `nil` on a perfectly good reply.

**Cost:** the printed output is a raw vendor blob. Nothing yet knows the model wanted
`list_directory`, and nothing runs it.

---

## How it boots and runs — t0..tN

```
FREE — nothing has left the machine
┌──────────────────────────────────────────────────────────────────┐
│ t0  launcher enters the module folder, starts the runner         │
│ t1  config read; player settings loaded                          │
│ t2  system prompt hydrated from .boukensha/prompts/player/       │
│ t3  context created; 2 tools registered; user message added      │
│ t4  provider word "anthropic" read → adapter built, model checked│
│ t5  builder built from (context, adapter)                        │
│ t6  client built from the builder                                │
│ t7  client asks builder: address? headers? body? → body → text   │
└──────────────────────────────────────────────────────────────────┘
                              │
                         ═════▼═════  MONEY STARTS HERE
┌──────────────────────────────────────────────────────────────────┐
│ t8  attempt 1 → POST leaves the machine                          │
│ t9  reply 200 → not retryable → loop breaks                      │
│ t10 characters converted to navigable data                       │
│ t11 runner prints the parsed reply; process exits                │
└──────────────────────────────────────────────────────────────────┘

The client is never consulted again after t10.
```

Everything up to t7 is free, offline, and repeatable — a fake key would pass.
From t8 the run needs a real funded key, a network, and returns something
different every time.

---

## What a spoiled run looks like

Same run, but the connection is reset every time.

```
t8   attempt 1 → connection reset → retryable → wait 0.5s
t8'  attempt 2 → connection reset → retryable → wait 1.0s
t8"  attempt 3 → connection reset → retryable → wait 2.0s
t9   attempt 4 → connection reset → attempts exceed the max
t10  ApiError raised — run ends
```

Total wait before giving up: 3.5 seconds across 4 attempts. Nothing partial is returned —
either a parsed reply comes back, or the run stops with a named failure.

---

## One-liners I earned

- The client holds one thing and knows no vendor; every vendor fact reaches it through the builder.
- Not using a helper library buys you visibility and bills you a certificate path.

---

## Landmines this module hit

1. **`.gitignore` blocks this lesson.** The line `week1_baseline/ruby/04_api_client/` must
   be removed before staging, or the whole folder stays invisible to git and nothing
   commits. Check this first, before copying anything in.
2. **Config path.** The shipped `examples/example.rb` line 1 goes three levels up to find
   `.boukensha`. Mine lives at repo root and needs four. Without the fix the run dies with
   `task player provider is required in settings`. Andrew hits the same error on camera
   at 07:46.
3. **Real money.** Every prior step would have passed with a fake key. This one sends.
   `ANTHROPIC_API_KEY` must be real and the account funded. The key is read from
   `<repo root>/.boukensha/.env`, which is already gitignored.
4. **Zone.Identifier files.** WSL download metadata. Already covered by `.gitignore`, but
   delete them anyway to keep the tree clean.

---

## Considerations Andrew recorded but did not fix

He names these on camera as known imperfections, deliberately left alone.

1. **The client holds state.** He wanted these components stateless. This one keeps the
   builder in its own memory. Recorded, not fixed.
2. **Ollama's address is hard-coded** where it should come from an environment variable.
   Recorded, not fixed.

**Why not fix them:** correcting either would mean uplifting every layer around it. The
cost of the fix, right now, outweighs the cost of the flaw.

---

## Glossary

- **HTTP POST** — sending a body to a web address and waiting for a reply.
- **status code** — the number in a reply meaning fine (200) or a named kind of not-fine
  (401 wrong key, 429 too fast, 503 server busy).
- **standard library** — code shipping inside the language itself; no install, no gem.
- **SDK** — a vendor's own prewritten code for talking to their API.
- **retry** — sending the same request again after a failure.
- **backoff** — waiting longer before each retry, so a struggling server isn't hammered.
- **transient failure** — a failure that might not happen on the next attempt.
- **certificate file** — the file a machine uses to verify a secure site is genuine; its
  location differs per operating system.
- **raise** — stopping a run with a named failure the caller can catch by that name.
- **navigable data** — text converted into a structure whose fields can be reached by name.
- **stateless** — holding nothing between calls. The client fails this; Andrew wanted it.
- **client** — new this lesson: the component that sends [client.rb].