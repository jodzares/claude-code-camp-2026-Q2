# Week1 Technical Documentation

## Technical Goal
A hand-built baseline agent (Python, 12 steps, on main) that can log into
and act in the MUD via a loop I control, giving me the visibility/logging
an off-the-shelf loop wouldn't.

## Technical Uncertainty
1. I'm uncertain whether I can understand the 12 steps deeply enough to
   assemble them into one working agent — the risk being that even the
   pieces I get through won't cohere into a loop that actually drives the
   MUD.
2. I'm uncertain my understanding of each step is trustworthy, since I
   can't read Ruby myself and rely entirely on Claude's interpretation —
   if that explanation is off, I build on a wrong mental model.
3. I'm uncertain the port-once-at-the-end approach will hold — that a
   single end-of-week Ruby→Python pass won't break in ways I can't trace,
   having skipped incremental building.

## Technical Hypotheses
1. I think I'll end the week with a partially-working agent, because the
   steps depend on each other — an early misunderstood step silently
   breaks later ones — and some are unfamiliar enough that I'll implement
   them wrong without noticing; so the agent should get partway through
   the loop but fail at a specific step, and the break should trace back
   to an earlier step I misunderstood rather than the one where it visibly
   fails. [U1]
2. I think relying on Claude to interpret Ruby will hold for the simple
   steps but break on the complex ones, because on simple steps I can
   sanity-check the explanation against my own intuition while on complex
   ones I have no independent footing to tell a good interpretation from a
   subtly wrong one; so on at least one complex step I should accept an
   explanation that's subtly wrong and only discover it when the build
   misbehaves, not while learning it. [U2]
3. I think the one-pass port will mostly work but throw a cluster of bugs
   I can't immediately trace, because porting everything before testing
   anything means many small translation errors surface together and I
   can't isolate which step caused which failure; so the first run of the
   ported Python agent should fail with multiple simultaneous errors, and
   debugging should cost me more time than the porting itself did. [U3]

## Technical Observations
<!-- Fill during/after the build. Formula: RAN → SAW → CHANGED → (INSIGHT).
     Facts only, no verdicts. Incidents + numbers beat generalities.
     Watch the H1-vs-H3 diagnostic: where an untraceable bug's ROOT sits
     (upstream logic step = H1 / port seam = H3). -->

## Technical Conclusions
<!-- Journal Time. Per-claim rulings → DELTA → [Hx/Ox] tag. -->

## Key Takeaway
<!-- One sentence. -->