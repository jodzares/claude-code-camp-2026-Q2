# Model Intelligence (with AI/ML Expert Rola Dali)

Week 1 · guest: Rola Dali (ML expert) · format: Andrew asks, Rola reasons.
My personal learning notes — not the graded documentation.

## The one takeaway

Don't build your product around a *model*. Build it around a *loop you
control*, and treat the model as a swappable part you plug in. Models are
short-lived and change under you; your loop is the thing you own.

("Around the model" = your loop is the structure and the model is a part
you call through one doorway — NOT your loop wrapping the vendor's box.)

## Spine: Model ≠ System

The whole lesson hangs on splitting two things I used to lump together:

- **Model** = the LLM itself. Just weights and math — Rola's phrase is a
  "mathematical abstraction." Not hardware, not an agent. Just the
  processing part.
- **System** = everything wrapped *around* the model: Loop, Prompt,
  Routing. That wrapper is what turns a bare model into something like
  Claude Code.

Claude Code is NOT a model. It's an agentic *system* with a model inside.

## The split that matters: vendor-side vs user-side

Slide 1 draws a dashed line down the middle. Left = vendor, right = me.
The trap: **"Loop" and "Prompt" show up on BOTH sides** — same words,
different owners, opposite visibility.

```
┌─────────── VENDOR-SIDE (black box) ───────────┐   ┌── USER-SIDE (glass box) ──┐
│                                               │   │                           │
│  ┌─────────────┐   ┌───────────────────┐      │   │   ┌───────────────────┐   │
│  │   Model     │   │      System       │      │   │   │    YOUR loop      │   │
│  │  the LLM:   │   │  (their wrapper)  │      │   │   │  (you build+own)  │   │
│  │ weights,mth │   │  ┌─────────────┐  │      │   │   │  ┌─────────────┐  │   │
│  │ swappable   │   │  │   Loop      │  │      │   │   │  │   Loop      │  │   │
│  │  "car"      │   │  ├─────────────┤  │      │   │   │  ├─────────────┤  │   │
│  └─────────────┘   │  │   Prompt    │  │      │   │   │  │   Prompt    │  │   │
│                    │  ├─────────────┤  │      │   │   │  ├─────────────┤  │   │
│                    │  │   Routing   │  │      │   │   │  │ memory,logs │  │   │
│                    │  └─────────────┘  │      │   │   │  └─────────────┘  │   │
│                    └───────────────────┘      │   │   └───────────────────┘   │
│                                               │   │                           │
│  Model + System = both invisible to you       │   │  Payoff: observability    │
│                                               │   │  + control; swap model    │
│                                               │   │  by config, not rewrite   │
└───────────────────────────────────────────────┘   └───────────────────────────┘
```

- **Vendor-side** = Model + System. Not just uncontrollable — **invisible
  AND uncontrollable**. I can't see in and can't change it.
- **User-side** = my own Loop + Prompt (+ memory, logs). A glass box I own.

### How the two sides connect (one doorway)

My loop does NOT wrap or reach into their box. It sits **beside** it and
**calls in** through a single doorway — the REST API endpoint.

```
   VENDOR-SIDE                         USER-SIDE
   ┌────────┐   ┌──────────┐           ┌──────────┐
   │ Model  │←──│  System  │←───────────│ MY loop  │
   └────────┘   │ (theirs) │  raw REST  │ (mine)   │
                └──────────┘   call     └──────────┘
```

The interface, in full: my user-side agent sends a prompt via **raw REST
API** to the **managed model** on the vendor side, and gets text back.
That's it. I address the **model** — NOT their agent. Whether a loop even
sits behind that door I stay **agnostic** about (can't see it, don't
address it). "Agnostic" = I deliberately don't commit to what's inside.

## Payoff of building my own loop

One word: **observability** (Rola pairs it with **control**). A glass box
instead of a black box — when something breaks, it breaks somewhere I can
open. That's the technical certainty Andrew is chasing: not "I don't know
why it doesn't work."

## The knot I got stuck on: "but I'm still not independent"

My objection while watching: even with my own loop, I still call the
vendor's endpoint, so there's still a black box in front of the model —
so how am I independent?

Resolution is a **fork into two worlds**:

- **Managed model** (Claude/Opus via API): my loop + THEIR black box in
  front of the raw model. Convenient, better out-of-the-box intelligence,
  but rug-pull risk — they can change routing/thinking/prompt-augmenting
  under me. I "roll with it and keep updating."
- **Open/local model** (e.g. Gemma 4 via Ollama): raw weights, nothing in
  front. Rola: "you're independent of the world." But I own the hardware,
  the cost, and I'm frozen at a snapshot.

**What resolves the knot:** observability applies to MY HALF regardless of
which world I pick. Even calling a managed model, I still see and control
my loop, my prompt building, my memory, my logs. And building my own loop
is what makes the open-model world *possible* — if I baked everything into
their agent, I could never swap.

**What we actually build:** own loop + managed models via **raw REST**
(World A). Andrew's instinct is local ("nothing thinking in front of it"),
but that's an aspiration, not the path.

## Connect to my architecture (Iterations carry-over)

Rola's "models are replaceable" is the architectural *justification* for
the Prompt Builder holding **5 provider recipes**. Because the recipes
live in the Prompt Builder, I swap the model by editing config — not by
rewriting code. Only one provider runs at a time; five are available, one
is chosen. That's "the model is a swappable car" made concrete.

## Second thread: the thinking toggle = "two separate cars"

Andrew's real question to Rola: if I turn thinking ON, can I read how the
model reasons, then turn it OFF to save money but keep that knowledge?

**No.** Thinking ON and thinking OFF are not the same model going
faster/slower — they take **different processing paths**. So:

- You canNOT infer OFF-mode reasoning from what ON shows you. Treat them
  as **two separate cars / two separate models**.
- Worse: the reasoning shown when thinking is ON may be a **manufactured
  account of how it *could* have reasoned**, not the model's actual hidden
  reasoning. ("Schrödinger's AI" — observing changes it.)
- We can't know what's happening underneath: more tokens? a looser model
  config? a system in front? routing to a different model? Rola: probably
  looser config + more agentic-loop autonomy, but "we take their word."

Why the toggle exists at all: reasoning costs more (output tokens ~3× input)
and adds latency. Unnecessary for simple tasks (CSS tweaks, quick answers).

## For our MUD use case

- Judging model A vs B = a **benchmark I run continuously**, because
  managed models drift under me. Not "pick the cheapest."
- Managed models hit end-of-life fast — Rola sees client systems go stale
  within ~6 months. Plan for the swap, don't marry a version.
- The whole point of the bootcamp architecture (own loop, own memory, own
  logs) is exactly the glass-box control Rola argues for.