# Iterations Walkthrough — Inner Ring (my notes)

> My own understanding from the guided walkthrough. NOT the official ExamPro
> study notes, and NOT committed as graded technical documentation.

---

## The spine: the agent loop (the heart)

Everything hangs off this. Learn this and the rest is "a thing one of these
3 steps needs."

```
1. Agent asks the LLM   -> sends the whole Context (conversation so far)
2. LLM decides          -> "call tool X"  OR  "end_turn"
3. If tool: run it, append result to Context, GOTO 1
   If end_turn: stop
   + safety net: MAX_ITERATIONS stops a runaway loop even if LLM never says end_turn
```

Two beats carry the whole insight:
- **Who decides:** the LLM decides (brain). The Agent only *reacts* to
  `stop_reason` (hands). Agent obeys, can't overrule.
- **Why resend everything:** the LLM has NO memory between calls. Each API call
  is a blank slate -> must resend the full conversation every loop.

---

## The 6 inner-ring boxes, and why each exists

Discovered by finding a gap in the loop and asking "who fills this?"

### 1. CONTEXT
Holds the growing conversation (user msgs + tool results), so it can be
resent every loop. Exists **because the LLM has no memory**.
- Agent *uses* Context (Agent -> Context), does NOT contain it.
- Kept separate so it can be shared later (e.g. REPL hands one Context
  across many turns).
- Boundary: Context = conversation. NOT tools. (AI once regressed and let
  Context hold tools — that's a bug, tools belong in the Registry.)

### 2. PROMPT BUILDER  (two-way translator at the LLM seam)
Sits between my agent's internal "house" format and each provider's dialect.
- **OUTBOUND** (agent -> LLM): house conversation -> the provider's request shape
- **INBOUND**  (LLM -> agent): provider's messy reply -> house shape = "normalize"
- One translator that knows all 5 provider dialects (not one universal format —
  no universal format exists; providers genuinely disagree on structure).
- "normalize" = the INBOUND job specifically.
- Earns its keep TWICE per loop (once sending, once receiving).

House = my agent's own internal standard format. Inside the agent, everything
is house shape; translation to a provider dialect happens only at the edge.

### 3. API CLIENT
Physically fires the raw HTTP request across the internet to the provider's
REST endpoint, then receives the raw reply.
- **Raw REST, no HTTP library** (locked rule: full access to feature set;
  even official SDKs don't always expose every feature).
- Ugly consequence: to make a secure https call by hand it needs the SSL
  **certificate path**, which differs per OS (Mac/Linux/Windows). Andrew
  **hardcodes** the path for his machine rather than take a library.
- NOTE: cert path != dotenv. dotenv reads the secret API KEY (Config, outer
  ring). Cert path points at the SSL certificate (API Client). Different things.

### 4. REGISTRY
The tool lookup table + dispatcher.
- **REGISTER** = put a tool into the table (`"attack" -> <code>`). Happens ONCE
  at setup.
- **DISPATCH** = look up a name + RUN it. Happens EVERY loop when the LLM
  names a tool. (Dispatch is an ACTION, not an output.)
- Lets the Agent avoid a giant `if tool == ... elsif ...`. Add a tool = just
  register it; Agent code never changes.
- Registry is agnostic to WHAT each tool does, but is still IN THE PATH
  (loop breaks without it).

### Only ONE LLM runs at a time
5 providers available (Anthropic, OpenAI, Gemini, Ollama, Ollama Cloud), but
only the one chosen in settings is contacted. The 5 recipes exist so switching
is a config edit, not a code rewrite. Agent never contacts all five.

### My agent != the coding harness
- Coding harness (Claude Code) = the tool I USE to build my agent.
- My agent (Boukensha) = the thing I'm BUILDING (the MUD bot).
- Both call an LLM, but different purposes. Don't drive the game with the harness.

---

## Who actually plays the MUD (the doing chain)

The Agent never touches the MUD directly. A tool is a THIN relay.

```
LLM: "attack rat"        (brain decides)
  -> Agent dispatches via Registry
    -> attack tool (thin relay)
      -> MUD MANAGER  <- this is who actually plays the MUD
        -> TCP -> MUD server -> "rat is wounded" -> back up the chain
```

MUD Manager = mandatory Ruby component. **Two jobs:**

**Job 1 — owns the persistent TCP connection.** Stays open across every tool
call. If each tool opened its own connection, I'd lose login/session state.

**Job 2 — translates, both directions.** Not a pipe — a translator:

```
OUTBOUND:  tool call {"tool":"attack","input":{"target":"rat"}}
           -> MUD Manager translates to THIS MUD's syntax -> "kill rat\n"
           -> sends over TCP
INBOUND:   MUD replies raw text "You hit the rat. It squeals."
           -> MUD Manager parses it -> returns to tool -> Agent -> Context
```

Why the Manager owns this: different MUDs use different verbs for the same
action (`kill` vs `attack` vs `hit`). If the tool knew the exact verb, that
knowledge would leak into my agent code. Tool knows WHAT (generic: attack the
rat); MUD Manager knows HOW this MUD phrases it and how to parse the reply.

---

## Pattern: translators sit at seams

There are TWO two-way translators, at two different boundaries. Easy to
conflate — they translate different pairs of "languages."

```
LLM <-> [PROMPT BUILDER] <-> Agent <-> Registry <-> tool <-> [MUD MANAGER] <-> MUD server
         house <-> provider-JSON                             tool-call <-> MUD-text
         (talking to the BRAIN)                              (talking to the GAME)
```

Neither knows the other's dialect exists, and neither needs to.

**The pattern:** anywhere two different "languages" meet, a dedicated two-way
translator sits exactly at that seam — never in the middle of the system,
always at the boundary.

---

## The MCP gap (why MCP exists)

```
BEFORE (all Ruby):     tool (Ruby)   --directly calls-->  MudManager (Ruby)   OK
AFTER  (Python agent): tool (Python) --cannot call---->   MudManager (Ruby)   FAILS
```

Python can't import Ruby. Language gap -> need a neutral bridge -> **MCP**
(Model Context Protocol): pass text (JSON) messages instead of calling code.
Text is language-agnostic, so the barrier dissolves.

- HOST = my agent (asks for + calls tools)
- SERVER = the separate program that owns the tools (MUD Manager run as
  `mud-manager --mcp`)

```
BEFORE:  tool --directly calls-->    MudManager
AFTER:   tool --MCP text message-->  MudManager   (works across any language)
```

Banked:
- MCP was NOT in the original plan — forced by the Python-can't-call-Ruby wall.
- Andrew: MCP lessons are a ~2h build, "worth watching, not doing" — copy the
  MUD Manager + standard tool library from his repo instead of building MCP.

---

## LOGGER  (to the side, not in the path)

Records every event (API response, tool_call, tool_result, cost, model,
provider) to a session file for later review. The loop components don't keep
this info themselves.

- Writes `~/.boukensha/sessions/<date>-<session_id>.jsonl`
  (JSON lines = one JSON object per line, one line per event).
- **subscribe / broadcast**: the loop ANNOUNCES events; whoever subscribed
  records them. One event -> many listeners (the .jsonl file AND the live
  screen/TUI). Loop doesn't know or wait on who's listening.
- Same pattern lets the log-visualizer (browser app) read those .jsonl files.

**In the path vs to the side** (the delete test):
```
Delete Registry -> loop BROKEN (can't dispatch tools)   -> IN THE PATH
Delete Logger   -> loop still works, just no records     -> TO THE SIDE
```

Agnostic = "doesn't care about detail X." Registry is agnostic to tool
CONTENT; Logger is agnostic to event MEANING. Being agnostic != being
removable — those are independent axes.

---

## Full inner-ring architecture

```
LLM  (brain: decides "call tool X" or "end_turn")
                     |                        ^
        (outbound)   v                        |  (inbound)
            +--------+------------------------+--------+
            |                  AGENT                   |  loop: 1->2->3->repeat
            +--------+---------------------------------+  + MAX_ITERATIONS
                     | uses each loop:
IN THE PATH ---------+-----------------------------------------------------
                     +- [CONTEXT]         holds conversation (LLM has no memory)
                     +- [PROMPT BUILDER]  TRANSLATOR @ LLM seam, both ways:
                     |                    house <-> provider-JSON
                     +- [API CLIENT]      raw HTTP, hardcoded SSL cert path
                     +- [REGISTRY]        register once, dispatch each loop
                              | dispatch
                              v
                         tool (thin relay)
                              | MCP message
                              v
                     [MUD MANAGER --mcp]  (Ruby, mandatory)
                       TRANSLATOR @ GAME seam, both ways:
                       tool-call <-> MUD text syntax
                       + owns persistent TCP connection
                              | TCP
                              v
                          MUD server
                              | raw text reply
                              v
                       parsed -> back up -> appended to CONTEXT
TO THE SIDE ---------------------------------------------------------------
   [LOGGER] <..... listens to every event (subscribe/broadcast)
                   -> writes .jsonl file
                   -> feeds live screen/TUI```

**The spine, one sentence:** the Agent loops — ask the LLM, run the tool it
names, feed the result back — and every other box is just something one of
those three steps needs.

**The second pattern:** two seams, two two-way translators —
Prompt Builder at the LLM boundary, MUD Manager at the game boundary.

---

## Still to do (next session)
- OUTER ring: Config, Struct Skeleton, Run DSL, REPL, Global Executable, TUI
  (how a human starts + drives the agent).
- Routine tail for this lesson: mini-debrief (journaling-method.md) + tracker tick.