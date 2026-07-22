---
name: play-mud
description: Play tbaMUD as a real player would - log in over telnet, explore and map the world room by room, fight, rest, shop, train, and pursue goals - while recording player state, a world map, and the friction a real player would hit. Use this skill whenever the user wants to play, explore, map, or test a MUD; asks the agent to reach a location, kill something, earn gold, level up, or find a guild in a MUD; wants a player-journey report on where a MUD confuses, blocks, bores, or overpowers players; or mentions tbaMUD, CircleMUD, DikuMUD, Midgaard, or a MUD on localhost:4000 - even if they do not say the word "skill" or name these scripts.
tools: Bash, Read, Write, Edit, Glob, Grep/mode
---

# Playing tbaMUD

You are playing a MUD the way a curious, careful human player would: you look
around, you take notes, you learn the streets, you avoid fights you would lose,
and you build toward a goal one checkpoint at a time.

Two things make this different from just typing commands at a socket:

1. **You are keeping a map.** Every room you see gets recorded, so that later
   you can find your way back without wandering.
2. **You are the instrument, not just the player.** The point is not only to
   win — it is to notice where a real player would get lost, stuck, bored, or
   crushed, and to write that down. A goal achieved with no observations
   recorded is a half-finished job.

## Players

Our main player: dummy / helloworld
Our secondary player: smarty / goodbyemoon

## The campaign goal

The standing objective, from `week0_explore/CHALLENGES.md`, is: **level up
enough to defeat the Massive Minotaur in the Newbie Zone.** Everything else —
a dagger, a few fidos' worth of gold, practicing kick — is bootstrapping
toward that, not the point in itself. Keep it visible in `data/player.md` as
the top-level goal, with the current tactical checkpoint chain underneath it.

**Do not plan the whole arc from level 1 to the Minotaur up front.** Its
room, its difficulty, and what level or gear it actually takes are unknowns
until scouted. Re-assess at the start of every session, and again at every
checkpoint: given current level/HP/gold and what's nearby, what's the next
reachable step? That might be more of the same grinding spot, or it might be
time to scout a tougher (but still `consider`-safe) area now that you've
outgrown the last one. A goal chain is still useful (see Goals and
checkpoints below) — just keep it short and revise it often instead of
writing a 20-step plan today for a fight you haven't scouted yet.

## Start the session

`scripts/` lives in this skill's directory, while `data/` is written under
whatever directory you are working in — so use the skill's path for the
scripts and let the state files land with the user's project:

```bash
python3 scripts/mud.py start
```

This opens one telnet session and logs in (defaults: `localhost:4000`,
`dummy`/`helloworld`; override with `--host --port --name --password` or the
`MUD_HOST/MUD_PORT/MUD_NAME/MUD_PASSWORD` environment variables). A background
process holds the socket so it survives between your commands — without it,
each shell call would be a new connection and a new login.

Then send commands:

```bash
python3 scripts/mud.py send "look"
python3 scripts/mud.py send ""          # bare newline: cheap vitals check
python3 scripts/mud.py stop             # captures final score, quits the character, closes the session
```

The `stop` command automatically runs `score` before closing, so you always
get your final state in stderr — check it before relying on what you think
you have.

The daemon loads this script once, when it starts. **If you edit anything
under `scripts/`, the running session keeps using the old code** — `stop` and
`start` again, or you will spend a long time debugging a fix that is not
actually loaded.

Every reply ends with the prompt `23H 100M 84V >`, so **your hit points, mana,
and movement arrive with every single command**. You almost never need `score`
just to check health — watch the prompt.

If a reply contains an `[while you were deciding]` block, that is the world
acting on its own: someone arrived, a fight landed a round, hunger set in.
Read it. It is often more important than the reply you asked for.

## The loop

Work in small cycles. Each cycle:

1. **Observe** — send a command, read the reply *and* any async block.
2. **Record** — pipe room output through `nav.py` so the map stays true.
3. **Decide** — check the next checkpoint in `data/player.md`.
4. **Act** — one intention at a time; verify it landed before assuming it did.
5. **Note friction** — if anything surprised you, write it down.

Keep the cycle honest. The most common way an agent breaks a MUD run is
assuming a command worked. Movement fails, doors close, mobs interrupt.
Read the reply.

## Mapping

Never hand-maintain the map in your head or in prose. Pipe the raw output to
`nav.py` and it parses, hashes, links, and coordinates for you:

```bash
python3 scripts/mud.py send "look"  > /tmp/o.txt
python3 scripts/nav.py look --file /tmp/o.txt        # record where you stand

python3 scripts/mud.py send "exits" > /tmp/o.txt
python3 scripts/nav.py exits --file /tmp/o.txt       # learn neighbour names

python3 scripts/mud.py send "north" > /tmp/o.txt
python3 scripts/nav.py move --dir north --file /tmp/o.txt   # record the move
```

Run `nav.py move` for **every** movement, including ones that fail. A refusal
("Alas, you cannot go that way...") is information — it records a wall, and
`nav.py` marks it so you never plan through it again.

Three things about this world are worth understanding, because they are what
make naive mapping fall apart:

**Room titles are not unique.** Midgaard's main street is several different
rooms all titled `Main Street`. So `nav.py` identifies a room by the hash of
its title *and description*, which genuinely differ. This is why you must feed
it the full room output, not just the title — with only the title it cannot
tell one Main Street from the next.

**`exits` names neighbours without walking.** tbaMUD answers `exits` with
`north - The Weapon Shop`, so one cheap command tells you what is adjacent.
Use it on arrival in a new room: it turns blind exploration into informed
choice, and it lets you head toward "The Temple Of Midgaard" before you have
ever set foot there. `nav.py exits` stores these as signposts.

**The map is not a grid.** Coordinates are dead-reckoned from your moves and
kept only as an attribute, never as identity. When a room turns up at
coordinates other than where it was first mapped, the world folds there;
`nav.py` records it as a seam. Seams are not bugs to fix — they are exactly the
kind of thing that disorients a real player, so mention them in your report.

## Navigating

Once rooms are mapped, do not retrace routes by memory. Ask for one:

```bash
python3 scripts/nav.py route --to "The Temple Of Midgaard"
# {"ok": true, "steps": 4, "path": ["north", "north", "east", "north"]}
```

Walk the path one room at a time, recording each move. If a title is ambiguous
(several rooms share it), `route` refuses and lists the candidate ids rather
than guessing — pass the id you meant.

**When a move on a planned route fails**, the door has closed since you mapped
it. Do three things, in this order:

```bash
python3 scripts/nav.py seal --dir north       # 1. forget that link
python3 scripts/nav.py route --to "<goal>"    # 2. re-plan FROM WHERE YOU ARE
```

You stay put, the stale link is gone, and the fresh route starts from your
actual position — which is why it is automatically the best way around, not a
patch on the old plan. There is no separate detour logic; it is the same
mechanism. Doors can reopen, so links are sealed rather than deleted; if you
find it open later, `nav.py unseal --dir north`.

If `route` says unreachable, the map simply does not connect yet. Go explore:

```bash
python3 scripts/nav.py frontier    # nearest room with unexplored exits, and the path to it
```

`frontier` is your exploration engine. It returns the closest unmapped
opportunity and how to reach it, with signposts where known — so exploring is
a decision, not a random walk.

## Goals and checkpoints

A goal is a chain of small, verifiable checkpoints. "Get a better weapon" is
not actionable; the chain is. Write the chain into `data/player.md` before you
start, then work it, marking each one as you clear it:

```
Goal: buy a better weapon
  1. find a shop that sells weapons        <- explore / signposts
  2. learn its price                        <- `list` in the shop
  3. have that much gold                    <- kill things, loot corpses
  4. return to the shop                     <- nav.py route
  5. buy it, wield it, confirm with `equipment`
```

The loop that funds most early goals is: **fight something safe → loot it →
rest until recovered → repeat**. Each part has a rule worth respecting:

- **Before any fight, check who else is in the room.** `look` first. Guards,
  knights, aggressive NPCs — they *wander* and join any fight mid-round.
  A fido that hits for 2 becomes a death sentence when a guard arrives.
  Only fight if the room's contents are harmless or already dead.
- **Then, `consider <target>`.** It tells you whether you would win against
  that one mob. At level 1 with ~23 hit points, guessing wrong ends the run.
  Target names come from the room description — `consider fido`, not
  `consider a beastly fido`, and it must be in the room with you.
- **Attack with `kill <target>`.** Combat runs in rounds on its own; keep
  reading, because rounds land in the async block.
- **Set `toggle wimpy <hp>`** (say a third of your max) and the MUD auto-flees
  for you when a fight turns. Note the `toggle` — bare `wimpy 8` answers
  `Huh!?!` and sets nothing, which is easy to type and easier to miss.
  Confirm you get `Okay, you'll wimp out if you drop below N hit points.`
  **Do not trust wimpy to save you.** It flees, and a stunned character
  cannot flee — so any hit hard enough to stun also disables it. It covers
  slow attrition, not burst damage. `flee` is the manual version.
- **Loot with `get all corpse`** — the reward is in the corpse, not the kill.
- **Recover with one command, not a polling loop:**

  ```bash
  python3 scripts/mud.py recover              # sleep until back to full
  python3 scripts/mud.py recover --to 18      # or to a specific hp
  ```

  It sleeps (faster regen than rest; falls back to `rest` if the room
  refuses), waits *inside the daemon*, and wakes and stands when done. One
  call, one answer — polling this from outside costs a full round trip per
  sample to learn a single number.

  Read the `reason` it returns, it is the whole point:
  - `reached` — you are at target.
  - `stalled` — hp stopped climbing for over two minutes. You are hungry or
    thirsty; eat and drink, waiting longer will not help.
  - `interrupted` — your hp *dropped*, so something is attacking you while
    you sleep. It woke you and bailed. Deal with it now.
  - `timeout` — hit the time limit still climbing; just call it again.

  Regeneration lands on a game tick (roughly every 60–90s), not
  continuously, so hp climbing in visible steps with flat gaps is normal and
  not a stall. Recovering is a good moment to update `data/player.md`.

**Hunger and thirst throttle regeneration.** If the world keeps telling you
`You are hungry` / `You are thirsty` and your hit points crawl, that is why —
eat and drink before you conclude that resting is broken. This is a classic
place real players get quietly stuck, so if it costs you time, record it.

Other progression worth exploring, in rough order of payoff: find your guild
and `practice` your skills; check `help <topic>` for anything unfamiliar; keep
an eye out for shops, banks, and trainers; `rent` at an inn before quitting or
you will wake up back at the temple altar.

## The two state files

**`data/world.md`** is generated — never hand-edit it. Regenerate whenever the
map has meaningfully changed, and at the end of every session:

```bash
python3 scripts/nav.py render
```

Room-specific discoveries belong on the room, so they survive into the render:

```bash
python3 scripts/nav.py note --text "smith sells a long sword, 120 gold - too expensive at level 1"
```

**`data/player.md`** is yours to write and keep current. Rewrite it each cycle
rather than appending, so it reflects *now*:

```markdown
# Player: Dummy

Level 1 Swordpupil · 23/23 hp · 100 mana · 84 mv · 0 gold · 183/2000 exp
Location: Main Street `4d2290b5`
Condition: hungry, thirsty

## Goal
Buy a better weapon.

## Checkpoints
- [x] Found the weapon shop (north of Main Street)
- [ ] Learn prices        <- next
- [ ] Earn 120 gold
- [ ] Buy and wield

## Learned
- Guild of Swordsmen is south of Main Street; practice here.
- Fidos are weak enough to fight at level 1.

## Friction
- `consider` needs the mob's keyword, not its full description. Took 3 tries.
```

The `Friction` section is the actual product. Keep it concrete.

## What to report

You are answering: *where would a real player struggle?* Watch for and write
down:

- **Confusion** — unclear directions, unhelpful help, a command that did not
  do what its name implies, a room whose exits contradict its description.
- **Blocked** — needing gold/level/an item you cannot get yet; a closed door
  with no hint; a fight you cannot win and cannot avoid.
- **Bored** — long stretches of walking or resting with nothing happening;
  grinding the same weak mob for gold.
- **Overpowered** — winning with no effort or risk, which is its own failure.

Anchor each observation to where it happened and what it cost — "spent 6
minutes and 4 deaths learning that the fido near the gate hits harder than
`consider` implied" is useful. "Combat is confusing" is not.

Close the session with `mud.py stop`, and leave `data/player.md` and
`data/world.md` in a state someone could read cold and understand the run.
`data/transcript.log` holds the full raw exchange if you need evidence.
