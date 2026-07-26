# Preweek Technical Documentation

## Technical Goal
Main technical goal would be exploring and estimating effectiveness of two different solutions (architectures) in their playing tbaMUD and achieving results based on goals provided vs cost.

1. Sole Agent wise - EndToEnd driven by coding harness, tested with haiku and sonnet (leveling effort from medium to xhigh effort for both)
2. Coding harness + skill - dividing e2e chain, also scaled from haiku to sonnet (leveling effort from medium to xhigh effort for both)

## Technical Uncertainty
1. Will my manual (human) playing of MUD give me good enough info to evaluate the agent's play?
2. I was and still am not sure to which degree effectiveness of coding harness and skill I am influencing with imperfect "prompt". (do I measure only architecture or also measuring quality of my prompt)
3. When the agent explores rooms and worlds blindly, will its mapping solution be any good - or should I hand it my pre-built algorithm (not maps, but algorithm how it should map)
4. Can long-living but computation-free session drain tokens, does the coding harness have some protection mechanism, will it recognize it should pause until operation in game is done (for example resting or sleeping for recovery, which is essentially only time consuming)
5. During parallel playing of sub agents, who will be updating player.md (memory of the player)? Will we indeed have true parallelism or sequential play?

## Technical Hypotheses
1. I think watching Andrew's different scenario exploration plus my own manual play will be sufficient to evaluate agent's play, because these two show how competent play looks (assess, consider, dying and restoring...)
2. I think prompt quality matters but to certain extent only — bad prompt can degrade results heavily, while good and optimized one can improve ~10-20%. The limiting factor is agent's own reasoning of goals. So the comparison should mostly measure architectures.
3. I think the agent will build a workable map, but not the most efficient one, because:
   - it mainly does blind exploration and brute-force backtracking
   - it will incrementally add new knowledge to its initial algorithm and never redesign it

   As the map grows, short-route search and rerouting will get worse over time. A pre-built algorithm should out-perform it.
4. I think code harness will drain tokens, because:
   - it will not be oriented on optimal resource preservation, but rather goal achievement
   - it does not have inbuilt constraint to prevent long sessions

   Agent will keep sending commands to check statuses causing unnecessary token usage, so doing this sporadically or delegating waiting to external watcher should significantly reduce token usage.
5. I think both players will write and they will overwrite each other, because they have different goals and different findings as they progress the game, which will as a consequence pollute the memory.
   I think it won't work at the start, because we have one socket and this will cause the agents to collide on it, so they can't truly run in parallel.

## Technical Observations
1. Watching Andrew's playthroughs and playing along manually gave me valuable insights to build a proper picture of how the game should be played, for example assess before fighting, check the room, manage recovery... That also helped me build my frame for judging the agent runs, and later basically shaped how the skill teaches the agent to play.

2. During test cases with essentially two prompts:

   1. v1 — pure goal oriented
   2. v2 — built with help of claude.ai (initial) plus /skillcreator, then further fine-tuned by me to contain goal decomposition plus instruction to keep checkpoints and update its own knowledge base.
   ([full skill](../../week0_explore/explore_architecture/02_agent_skills/.claude/skills/play-mud))

   With v1 I noticed repeated deaths and not much learning (same mistakes were repeated), while v2 stayed alive longer, kept recovering and earned 20-30 coins. I also observed it updated its checkpoints and knowledge base, and most importantly one self-made lesson (kill more fidos to level up and earn -> scouted bigger mob -> consider said unsafe -> skipped it -> kept grinding -> then bought dagger). It also proposed multiple players (parallelization), which I declined because it's not in the scope of preweek, so I didn't push the test that far.

   After it kept dying over and over in v1 I added combat rules into the skill (check who else is in the room before fighting, consider the target first and health points) and v2 showed real improvement, but still didn't seem enough for our challenge — I noticed the skill could self-improve, but faster with my own steering and management — though on the harness loop I had no way to force it to re-plan.

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

   Each peek was a full agent turn — the whole context re-sent just to read a
   two-digit number.

   I moved the waiting into the daemon `recover` (one call, one answer with a
   reason). Same statusline check on a daemon rest: ~50 tokens (one session each and not in a controlled benchmark but more observational).

5. Arch 1 (sole agent, no skill) reinvented the wheel every session — the same deterministic, never-changing login flow, re-solved every time.

   Tried different models and no substantial improvement; same with scaling
   effort, neither better nor worse.

   Because agentic login was uncontrollable and unreliable, I moved login into
   the skill's script — the model is out of the loop entirely.

   But a better model did prepare a better script.

6. When I ran it, player.md (player memory) wasn't touched — neither agent wrote anything, since writing was left entirely to the agent's own decision — so it remained unresolved in that architecture for the time being.

   The agents "traded" one socket, each taking its own turn (so not truly parallel). The real collision point was the shared state directory, not the socket itself — after giving each player its own state directory, a hand test with two daemons ran two live sessions at once.

   With the Agent SDK we couldn't even log in — the agent interpreted the credentials in the md file as personas instead of accounts/logins, so it fell through to the script's silent default name. Passing --name fixed it, once identity became a supplied parameter instead of an agent guess.

   Adding a loop that prints a line every time the agent runs a command (→ running: look) gave me the visibility to follow what's going on — a direct answer to Andrew's "no way of tracking what the agent does" limitation.

   I also tried n8n as a candidate architecture: its Python code node is sandboxed and can't open sockets, so mud.py had to run outside n8n and bridge in.

## Technical Conclusions
1. Manual play and Andrew's walkthrough were enough to judge the agent's runs and ended up even shaping how the skill teaches. [H1/O1]

2. My ~10–20% guess was wrong — the real gain came when the prompt stopped being wording and became structure, which is how v2 pulled far ahead of v1.
   The "wall" part held — the agent's reasoning didn't necessarily improve, and what improved was the scaffolding and structure built around it.
   The comparison did end up measuring different architectures, but only because prompt turned into architecture along the way. The skill improves fastest with my own steering, not on its own. [H2/O2]

3. The agent's own map wasn't even workable, not by a long shot — it couldn't route back to visited rooms always and even worse never connected a need to remembered room knowledge.
   Degradation over time never tested, map failed too early, so it stays unconfirmed.
   With pre-built navigation routing back works always and "fountain" becomes a lookup.
   The real gap wasn't only route efficiency, but memory (map had to become agent's knowledge base, not only a router). [H3/O3]

4. The drain was real — a single rest that required nothing but waiting cost ~3–4k tokens.
   The polling bet hit exactly: the agent even used the cheapest command (bare Enter) to check HP, yet fired a full agentic loop for it every 1–2 seconds, ~50 times per rest.
   Moving the waiting inside the daemon dropped one rest from ~3–4k tokens to ~50 (statusline readings, one session each — observational, not benchmarked).
   What H4 missed — the cost was never the commands, it was the full agentic loop behind each one, the whole context re-sent just to read a two-digit number. [H4/O4]

5. Bet (a) was wrong — nothing was written at all, not overwritten. What to save was left to the agent's decision, so the real lesson is that memory-saving must be a built-in step of the program, not agent discretion.

   Bet (b) was right about the collision — but the cause was the shared state directory, not the socket I blamed, and the fix was lighter than "won't work" implied: giving each player its own state directory was enough to run truly in parallel. [H5/O6]

   Anything with one correct value — identity, memory — must be a supplied parameter, not left to the agent's decision, as both the failed login and the unwritten memory showed.

   n8n bridging makes it a middleman, not the end-to-end architecture we're after.

6. The proof of concept succeeded — skills can play the game, cheaper than the raw harness, but on a borrowed loop, with no control to force re-planning and only the visibility I later built into the SDK loop. Complex goals require a loop I own. [O2/O4/O6]

## Key Takeaway
Preweek showed that the skill architecture works, but to move forward I need my own loop (to gain better control and visibility).
