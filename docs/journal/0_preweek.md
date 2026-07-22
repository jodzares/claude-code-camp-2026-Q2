# Preweek Technical Documentation

## Technical Goal
Main tehnical goal would be exploring and estimating effectiveness of two different solutions (architectures) in their playing tbaMUD and achieving results based on goals provided vs cost.

1. Sole Agent wise - EndToEnd driven by coding harness, graded with haiku and sonnet (leveling effort from medium to xhigh effort for both)
2. Coding harness + skill - daviding e2e chain, also scaled from haiku to sonnet (leveling effort from medium to xhigh effort for both)

## Technical Uncertainty
1. Will my manual (human) playing of MUD give me good enough info to evaluate the agents play?
2. I was and still am not sure to which degree effectiveness of coding harness and skill I am influencing with imperfect "prompt". (do I measure only architecture or also measuring quality of my prompt)
3. When the agent explores rooms and wolrds blindly, will its mapping solution be any good - or should I hand it my pre-built algorithm (not maps, but algorithm how it should map)
4. Can long-living , but computation-free session drain tokens, does the coding harness have some protection mechanism, will it recognize it should pause until operation in game is done (for example resting or sleeping for recovery, which is essentially only time consuming)

## Technical Hypotheses
1. I think by watching Andrews different scenarios exploration plus my own manual play will be sufficient to evaluate agent's play, because these two show how competent play looks  (assess, consider, dying and restoring...)
2. I think prompt quality matters but to certain extent only — bad prompt can degrade results heavily, while good and optimized one can improve ~10-20%. The limiting factor is agents own reasoning of goals. So the comparison should mostly measure arhitectures.
3. I think the agent will build a workable map, but not the most efficient one, because:
   - it mainly does blind exploration and brute-force backtracking
   - it will incrementally add new knowledge to its initial algorithm and never redesign it
   
   As the map grows, short-route search and rerouting will get worse over time. A pre-built algorithm should out-perform it.
4. I think code harness will drain tokens, because:
   - it will not be oriented on optimal resource preservation, but rather goal achievement. 
   - it does not have inbuilt constraint to prevent long sessions
   
   Agent will keep sending commands to check statuses causing unnecessary token usage, so doing this sporadically or delegating waiting to external watcher should help significantly reducing toke usage

## Technical Observations
1. Watching Andrews playthroughs and playing along manually gave me valuable insights to build a proper picture of how the game should be played, for example assess before fighting, check the room, manage recovery... That also help me build my frame for for judging the agent runs, and later basically shaped how the skill teaches the agent to play.

2. During test cases with essentially two prompts:

   1. v1 — pure goal oriented
   2. v2 — built with help of claude.ai (initial) plus /skillcreator, then further fine-tuned by me to contain goal decomposition plus instruction to keep checkpoints and update its own knowledge base. 
   ([full skill](../../week0_explore/explore_architecture/02_agent_skills/.claude/skills/play-mud))

   With v1 I noticed repeated deaths and not much learning (same mistakes were repeated), while v2 stayed alive longer, kept recovering and earned 20-30 coins. I also observed it updated its checkpoints and knowledge base, and most importantly one self-made lesson (kill more fidos to level up and earn -> scouted bigger mob -> consider said unsafe -> skipped it -> kept grinding -> then bought dagger). It also proposed multiple players (parallelization), which I declined because it's not in the scope of preweek, so I didn't push the test that far.

   After it kept dying over and over in v1 I added combat rules into the skill (check who else is in the room before fighting, consider the target first and health points) and v2 showed real improvement, but still didn't seem enough for our challenge - I noticed the skill could self-improve, but faster with my own steering and management.

3. The agent's own mapping in v1 runs was poor — it basically logged adjacent
   rooms (room a -> room b).

   This resulted in failures when trying to revisit the room, it couldn't route
   toward a specific one. Also what I noticed, it didn't have enough material to
   conclude why it needs to go to a specific room, for example being thirsty —
   should trigger "where can I find water, is this something I should already
   know from past rooms I visited". So the agent essentially didn't connect need
   to remembered room knowledge.

   Custom mapping solution was built where:
   - every room had its own coordinates
   - room description was stored and every room got a unique identity composed
     of title+desc (hash) just to avoid possible collision if some room names
     repeat.

   This made routing back to visited rooms work, and knowledge like the fountain
   becomes a lookup:
   ```json
   "f453505b": {
     "id": "f453505b",
     "title": "The Bakery",
     "desc": "You are standing inside the small bakery. A sweet scent of danish and fine bread fills the room. [...]",
     "coords": [0, 1, 0],
     "exits": {
       "south": { "to": "e44913d0", "dest_title": "Main Street", "sealed": false }
     },
     "contents": ["The baker looks at you calmly, wiping flour from his face with one hand."],
     "notes": [],
     "visits": 1
   }
   ```
4. During skill runs, in the rest/recovery phase, the agent was waiting for HP
   to climb.

   Rest requires nothing except waiting, yet a full agentic loop fired per
   health check:
   - the agent already used the cheapest command (bare Enter — prompt carries HP)
   - measured from transcript log: SENT timestamps `:52, :52, :54, :54, :56, :56, :58` (1–2 per sec, ~50 peeks per rest, HP 1 -> 5 -> 9)
   - live statusline reading during one such rest: ~3–4k tokens

   Each peek was a full agent turn - the whole context re-sent just to read a
   two digit number.

   I moved the waiting into the daemon `recover` (one call, one answer with a
   reason). Same statusline check on a daemon rest: ~50 tokens (one session each and not in a controlled benchmark but more observatial)

5. Arch 1 (sole agent, no skill) reinvented the wheel every session, basically same never changing
   login flow.
   Tried different models and no substantial improvement; same with scaling
   effort, neither better nor worse.

   Because agentic login was uncontrollable and unreliable, I moved login into
   the skill's script — the model is out of the loop entirely.

   But a better model did prepare a better script.

## Technical Conclusions
1. Manual play and Andrewws walkthrough were enough to judge the agent's runs and ended up even shaping
   how the skill teaches.

2. My ~10–20% guess was wrong, but the real gain came when the prompt stopped being wording and became
   structure, which is how v2 pulled far ahead of v1.
   The "wall" part held, the agents reasoning didnt necessarily improve and what improved was the scaffolding and structure built around it.
   The compariosn did end up measuring different architectures, but only because prompt turned into architecture along the way.  The skill improves fastest with my own steering, not on its own.

3. The agents own map wasnt even workable by long short, it couldnt route back to visited rooms always
   and even woese never connected a need to remember the room knowledge
   Degradation over time never tested, map failed too early, so it stays unconfirmed.
   With prebuild navigation routing back works always and "fountain" becames a lookup. 
   The real gap wasnt only route efficiency, but memory (map had to become agents knowledgebase, not
   only a router)

4. The drain was real - a single rest that required nothing but waiting cost ~3–4k tokens.
   The polling bet hit exactly: the agent even used the cheapest command (bare Enter) to check HP, yet fired a full agentic loop for it every 1–2 seconds, ~50 times per rest. 
   Moving the waiting inside the daemon dropped one rest from ~3–4k tokens to ~50 (statusline readings, one session each — observational, not benchmarked). 
   What H4 missed - the cost was never the commands, it was the full agentic loop behind each one, the whole context resent just to read a two-digit number.

 5. The proof of concept succeeded, skills can play the game, cheaper than the raw harness, but on a borrowed loop, with no
    control to force re-planning and no visibility into actions or cost. Complex goals require a loop I own.



## Key Takeaway
Preweek_0 showed that architecture works, but to move forward I need my own loop (to gain better control and visibility)
