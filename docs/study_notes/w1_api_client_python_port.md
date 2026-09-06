# API Client Python Port — TLDR

**Job:** put the same sender into Python. Same behaviour, not same text.

**Big picture:** four of the five decisions were already made on the Ruby side and only had
to be carried across — the retry policy, the attempt cap, the backoff, the fail-loud. One
decision was new, because Python disagrees with Ruby about what a failed HTTP response *is*.
That one decision is the whole lesson.

**THE CHAIN:**
`builder` (`prompt_builder.py`, holds context + adapter) → handed to `client`
(`client.py`, holds only the builder) → sends → reply parsed → returned, **or** `ApiError`.
Trap: `TRANSIENT_ERRORS` and `RETRYABLE_STATUS_CODES` are WORDS declared at the top of the
client file, not files. `ApiError` is a word too.

**The 5 decisions:**

1. **Don't port the broken path.** Ruby 04 moved the default-prompt lookup one level too
   high, onto a folder that doesn't exist. It fails silently — no error, empty system
   prompt, request still sends. Andrew ruled on camera: it should work in both, so fix it.
   Python was already correct, so the port changes nothing here; the fix landed on the Ruby
   side instead. Cost: the two languages briefly disagreed and I had to know which was right.
2. **Port the category, not the spelling.** Ruby names eight low-level failure types worth
   retrying. Python files the same real-world events under different names, and groups where
   Ruby splits — six Python entries cover more ground than Ruby's eight. Copying Ruby's names
   wouldn't even load: `NameError: name 'Errno' is not defined`. Cost: no checkable
   one-to-one, so a wrong pick only shows up when that exact fault happens.
3. **MONEY SHOT — Python raises where Ruby returns.** Ruby hands back a response object for
   every status, including 500, and you read the number off it. Python's `urlopen` throws
   `HTTPError` instead, so the status only exists *inside* a catcher. That forces a structure
   Ruby never needed: two catch clauses, `HTTPError` first, transient second. Order is
   load-bearing — `HTTPError` is a kind of `URLError`, and `URLError` is in the transient
   tuple, so reversing them makes every server error look like a dropped connection.
   Cost: two clauses in a deliberate order, and nothing about the wrong order looks wrong.
4. **One retry decision, not two.** The `HTTPError` clause records the status and body and
   does nothing else. Whether that status earns a retry is decided once, after the success
   path and the failure path have converged on a status number. The transient clause is the
   exception — it retries inside itself, because there is no status number to defer with.
   Cost: the asymmetry looks inconsistent until you see why.
5. **Fail loud, and the `return` sits below the guard.** Anything outside 200–299 raises
   `ApiError` carrying the attempt count, the status and the provider's own error text.
   Nothing downstream can ever receive a failure — that's structural, not documented.
   Cost: a new error type to define and let bubble up.

**Boot order:** copy python/03 forward → port plan → generate → activate venv → run →
compare against Ruby → commit.

**The verification that mattered:** input tokens were **651 in both languages**. Identical
count means both built a byte-equivalent payload. Output differed (65 vs 53) only because
the model phrased its reply differently — that's the model, not the code.

**Two additions beyond Andrew's baseline (deliberate, logged):**
- `TIMEOUT = 30`. Andrew sets none. Without it `TimeoutError` is in the retry list but
  nothing can ever raise it — dead policy.
- The two catch clauses carry comments explaining why the order is load-bearing.

**One divergence caught and reversed:** the generated plan first chose `http.client` over
`urllib.request`, arguing structural similarity to Ruby. Both are standard library, so the
constraint held — but `http.client` returns the status for every response, which designs
decision 3 out of existence. Reversed to `urllib.request` to match Andrew's baseline.

---

# API Client Python Port — study note

> Personal learning note. NOT graded documentation. Graded docs live in `docs/journal/`.
> Iteration 04 of the agent, Python side. Written language-neutral: concepts, not syntax.

---

## Spine sentence

The client takes the builder's finished request, sends it, retries the temporary failures a
few times with a growing wait, raises on a real failure, and returns the parsed reply.

---

## D1 — The prompts path Ruby broke

Every step folder carries its own `prompts/` folder. The config file points at it. Step 03
pointed correctly, two levels up from where the config file sits. Step 04 changed it to three
levels up — outside the step folder entirely, at a directory that does not exist.

Nothing crashes. The lookup finds no folder and returns empty-handed, so the agent boots with
no system prompt and the request still goes out.

That silence is the danger, not the money. A crash names the cause and the place. Silence
means the failure surfaces as *"the agent is behaving oddly"* — the model still answers,
because a request with no system prompt is still a valid request. It just answers as a generic
assistant instead of as Boukensha. You debug the tools, the payload, the model, everything
except a path in a config file three components away.

The three-up path is not a typo. It is an unfinished refactor: twelve step folders each
carrying a duplicate copy of the same prompt file is real duplication, and somebody reached
for a shared location one level up. The shared location was never created. A half-done
improvement behaves identically to a mistake.

Ruling: fix it, don't reproduce it. Creating the shared folder would break each step's
self-containment, so the path goes back to two-up instead. Python was already correct, so
the port touches `config.py` not at all — the edit landed in
`week1_baseline/ruby/04_api_client/lib/boukensha/config.rb`.

**Caught late, and worth knowing why:** Ruby 04 was already committed with the broken path.
The lesson's success test was *"did a real response come back"* — and it did. The bug hid
behind a passing run. *"It ran"* is not *"it's correct."*

**Also worth knowing:** on this machine the fix can't be proven by running it. `settings.yaml`
has `prompt_override.system: true`, so the prompt comes from `.boukensha/prompts/player/` and
`PROMPTS_DIR` is never consulted. Token count was 651 before and after. The fix matters the
moment that override is switched off.

---

## D2 — Which failures deserve a second try

Two flavours of failure, and the whole decision is telling them apart.

*Permanent:* the API key is invalid, the payload is malformed. A second attempt fails exactly
like the first.

*Temporary:* the wifi blipped, the connection reset mid-send, the server was overloaded for
two seconds. Nothing about the request is wrong. Try again in half a second and it works.

Treat everything as permanent and one blip kills the agent. Treat everything as temporary and
a bad key gets retried three times before failing anyway. So the component declares, at the
top of the file, a fixed list of the temporary kind — as data a human can audit, not as logic
buried in a loop.

**The porting problem.** Ruby's list names eight failure types. Python has the same *events*
but files them under different names, and the two sets don't line up. Python's
`ConnectionError` alone covers reset, refused, aborted and broken-pipe — four cases where Ruby
lists two separately. Six Python entries cover more ground than Ruby's eight.

That difference is inherited from the operating system. The OS reports a numbered code; Ruby
exposes those almost raw, one name per code. Python wrapped them into a small family of
friendlier categories. Neither is wrong — different opinions about how much detail a
programmer should handle.

So there is no lookup table. You ask what event each Ruby entry describes, then find whichever
Python name covers that event. Copying the names produces `NameError: name 'Errno' is not
defined` — the file won't even load. That's the lucky version of the mistake.

**Why grouping is safe.** The sender never asks *which* failure happened. It asks one
question: *is this type in the list — yes or no?* All six categories get identical treatment,
so bundling reset and refused together changes nothing. The specific name survives only in the
final error message, for a human to read.

Two questions, in order: **is it in the list** decides *if* we retry; **how long** decides
*when*. The second only runs if the first said yes.

---

## D3 — Python raises where Ruby returns  ← MONEY SHOT

Ruby treats "server said 500" as a normal answer: it hands back a response object and you
inspect the number. Python treats it as a failure event: it throws the error upward and stops
the flow.

```
Ruby:    response.code -> "500"     program still running, you decide next
Python:  urllib.error.HTTPError: HTTP Error 500: Internal Server Error
                                    program stopped, nothing decided
```

Ruby's client can therefore be one straight sequence: send, read the number, decide. Python
cannot. The status only exists inside a catcher, so the port needs a structure the source
never had. This is the only decision here that couldn't be transcribed — every other one was
already made last lesson.

**Two catchers, two different events:**

- `HTTPError` — a response **arrived**. The server answered. The answer was a failure. There
  *is* a status number and a body to read.
- the transient list — **nothing arrived**. Wifi dead, DNS failed, connection reset. There is
  no number, because there is no response.

The mental test is *"is there a number?"* The proof is in what each clause does: the first
reads a code and a body; the second reads nothing, because there is nothing to read from.

**The landmine — order is load-bearing.** `HTTPError` is a *kind of* `URLError`, and
`URLError` is the first entry in the transient tuple. Python takes the first catcher that
matches, not the best match. The relationship runs one way only:

```
every HTTPError IS a URLError        -> URLError-first swallows it
no ConnectionError is an HTTPError   -> HTTPError-first swallows nothing extra
```

Narrow-first is safe *because* it's narrow. Wide-first is fatal *because* it's wide.

Swapped, with a bad key:

```
t0  401 -> caught as transient -> sleep 0.5s, retry
t1  401 -> caught as transient -> sleep 1.0s, retry
t2  401 -> caught as transient -> sleep 2.0s, retry
t3  401 -> attempts exceeded ->
    ApiError: API request failed after 4 attempts: HTTPError: HTTP Error 401
```

3.5 seconds lost, and worse: `status` never got set, so the status check never ran and the
message reads like flakiness. The key was wrong on attempt one and the report doesn't say so.

The swapped version is not a syntax error. It loads, runs, and works perfectly on every
successful request. It misbehaves only when the server returns a failure — exactly when you
need it correct.

**Rule: catch the specific error before the general one.**

---

## D4 — How many retries, and how long to wait

Retrying immediately is the obvious move and the wrong one. The commonest reason for a 503 is
an overloaded server, and an instant retry adds one more request to the pile already crushing
it. So the wait grows: 0.5s, then 1.0s, then 2.0s. Three retries, four attempts total.

Doubling does three things a fixed wait doesn't. It gives an overloaded server progressively
more room. It scales the guess to the evidence — if half a second wasn't enough, that's a
sign the problem is bigger than half a second. And it spreads a thousand clients out instead
of letting them all retry at the same instant and re-flood the server the moment it recovers.
The pattern's name is **exponential backoff**.

**503 twice, then 200:**
```
t0  attempt 1 -> 503, in retry set -> sleep 0.5s
t1  attempt 2 -> 503, in retry set -> sleep 1.0s
t2  attempt 3 -> 200 -> break -> parse and return
    1.5s of added delay. The agent never noticed the outage.
```

**A one-minute outage:** four attempts, about 3.5 seconds, then `ApiError`. That's intended.
Retries paper over a blip; they are not an outage strategy. No client-side wait fixes a
minute of downtime, so failing fast with a clear message beats hanging silently.
**Retries buy seconds, not minutes.**

**The status list, and the rule underneath it.** `{408, 409, 429, 500, 502, 503, 504}`.
A `400` means the payload was malformed and a `401` means the key is wrong — the same request
will fail identically forever, and retrying it costs 3.5 seconds *and* corrupts the
diagnosis: *"failed after 4 attempts"* implies flakiness when the truth was *"your key is
wrong, first try."*

But the rule isn't *"4xx never retries."* `408` and `429` are both 4xx and both on the list.
A 408 means the request didn't arrive in time — nothing wrong with it. A 429 means
rate-limited, which is the server explicitly saying *slow down and try again*; waiting is the
prescribed fix and the doubling wait is exactly what it asked for.

**The real question the list encodes: could this same request plausibly succeed later,
unchanged?** Not *"whose fault was it?"*

**Where the retry decision lives.** The `HTTPError` clause records the status and stops.
Both roads — the normal return and the caught failure — arrive at one shared check holding a
status number, and the retry decision is made there, once. Putting it inside the clause would
duplicate `MAX_RETRIES`, the sleep and the backoff maths in two places; change the cap and
you'd have to remember both. The transient clause is allowed its own retry only because it
has no status number to defer with.

---

## D5 — Fail loud

A 401 doesn't come back empty. It comes back as valid, well-formed JSON:

```json
{ "type": "error", "error": { "type": "authentication_error", "message": "invalid x-api-key" } }
```

It parses cleanly. Nothing about it *looks* broken to a program — it just isn't the shape
anyone expects. Returned as if it were a reply, it travels onward disguised, and the crash
lands somewhere else entirely:

```
t2  example prints the error JSON as "Raw response"
t3  next lesson's agent loop reads reply["content"] -> KeyError: 'content'
```

Different file, one lesson later, and nothing in that error mentions 401 or the API key. You'd
debug the agent loop — the innocent component.

Raising instead:

```
t1  ApiError: API request failed after 1 attempt (401):
      {"type":"error","error":{...,"message":"invalid x-api-key"}}
```

Same crash, wildly different afternoon. **Fail where you know why.** The client is the only
component that ever sees the status number; if it doesn't raise there, that knowledge is gone
and every downstream failure has to be diagnosed without it.

Note where the `return` sits — *below* the raise, unreachable unless the status check passed.
The promise is enforced by shape, not by a comment that can drift out of date. Downstream can
assume any value it receives is a real reply from the provider.

**What that promise does not cover:** whether the reply is any *good*. A 200 can carry a
refusal, a ramble, or a request for a tool that was never registered. Transport is the
client's business; meaning is the agent loop's. That split is the component's boundary.

**Pattern name: guard clause.** Check the bad case, exit immediately, and everything below
runs in the known-good world.

---

## Assembled picture

```
Config ─ Context ─ Registry(tools) ─ PromptBuilder(+ adapter)
                                          │  builds url / headers / JSON
                                          ▼
                                    ┌───────────┐
                                    │  Client   │  ← this step
                                    │  .call()  │
                                    └─────┬─────┘
                              retry loop  │  → network → provider
                                          ▼
                                   parsed reply  ──►  ??? (Agent Loop, step 05)
```

---

## The run, t0..tN

```
t0  boot; Config loads .env + settings.yaml
t1  build Context, register read_file / list_directory
t2  provider word -> pick adapter -> build PromptBuilder
t3  Client(builder) created
t4  call(): build request from builder.url / headers / payload
t5  send -> 200
t6  in the 2xx band -> parse -> return
t7  example prints the reply -> CLIENT GOES IDLE (nothing consumes it yet)
```

---

## Three rules that repeated across all five decisions

- **Fail where you know why.** D1's silence, D3's mis-ordered catcher and D5's `KeyError` are
  the same crime — a report that doesn't match the cause.
- **Declare policy as data, not as logic.** Constants at the top; one decision point, not two.
  It makes the policy auditable by someone who doesn't read code, changeable in one line, and
  comparable across the two languages without reading either implementation.
- **Port the category, not the spelling.** Behavioural equivalence is the bar; identical text
  is not. And the interesting part of any port is wherever the target language forces a
  decision the source never had — everything else is typing.

---

## Landmines

- `.gitignore` hid the 04 module during the Ruby lesson. Checked before committing this time;
  the root `.gitignore` lists only *Ruby* future-lesson folders, so nothing blocked
  `python/04_api_client/`.
- The generated plan's first draft picked `http.client` over `urllib.request` and would have
  designed D3 out of the port. Both are standard library, so the "no third-party" constraint
  didn't catch it — only comparing against Andrew's baseline did.
- `TimeoutError` sat in the transient list with no `timeout=` configured, so nothing could
  ever raise it. Dead policy, caught in plan review.
- Andrew built a Claude skill for porting, found it slow, and deleted it on camera. Not part
  of the path.

---

## Glossary

- **standard library** — code shipped inside the language; nothing to install.
- **transient failure** — a fault that might succeed if tried again.
- **backoff** — waiting longer between each retry so a struggling server gets room.
- **exception (raised)** — an error the language throws upward, stopping normal flow until
  something catches it.
- **`HTTPError` / `URLError`** — the server answered with a failure status / the request never
  completed. `HTTPError` is a kind of `URLError`, which is why catch order matters.
- **2xx band** — status numbers 200–299, meaning success.
- **guard clause** — check the bad case and exit early, so the rest of the code runs in a
  known-good world.
- **virtual environment (`.venv`)** — a private Python for this project with its own
  installed packages, so nothing is installed machine-wide. Gitignored; recreated per machine.
- **`source`** — run a script inside the current shell so its changes stick, rather than in a
  new one.

---

## Ruby → Python equivalents (this lesson)

| Ruby | Python |
|---|---|
| `Net::HTTP` | `urllib.request` (both standard library) |
| `http.request` returns a response for all codes | `urlopen` raises `HTTPError` for non-2xx |
| `rescue *ERRORS => e` | `except ERRORS as e` |
| `ARRAY.freeze` | tuple `(...)` is immutable; `{...}` is a set literal |
| `response.is_a?(Net::HTTPSuccess)` | `200 <= status < 300` |
| `JSON.parse(s)` / `x.to_json` | `json.loads(s)` / `json.dumps(x).encode("utf-8")` |
| `sleep n` | `time.sleep(n)` |
| `loop do ... end` | `while True:` |
| `URI(str)` | `urllib.request.Request(url, ...)` takes the string directly |