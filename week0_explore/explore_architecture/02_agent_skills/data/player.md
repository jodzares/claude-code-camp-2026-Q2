# Player: Dummy

Level 1 Swordpupil · 23/23 hp · 100/100 mana · 81/84 mv · 40 gold · 528/2000 exp
Location: Ye Olde Water Shoppe `b4b01b94`
Condition: fed · standing · wimpy set to 8 · carrying 2x meat

## Campaign goal
Level up enough to defeat the Massive Minotaur in the Newbie Zone
(CHALLENGES.md). Not close yet — level 1, 528/2000 exp, 1472 to next level.
At ~33 exp/fido, that's 45+ more fido kills for level 2 alone — pure grinding
does not scale to Minotaur-ready. Next priority: scout for **quests** (exp
gain without killing), or find if there's a different zone/mechanic
(progression via practice/skills once unlocked, or a high-level zone already
discovered that the player can't access yet).

## Current tactical checkpoints
- [x] Checked `equipment` — character starts fully armed and armored
- [x] Found 3 distinct Main Streets with different adjacent shops/areas
- [x] Scouted east border (Outside East Gate) — reaches "zone above your
      recommended level" after 2 rooms; forest is out-of-bounds
- [x] Hunted backwards fidos (identical to regular fidos: 33 exp, 10g, meat)
- [x] Mapped Water Shop, Market Square, Temple Square, General Store, Pet Shop
- [ ] Quest system — does one exist? (check `help quest` / explore bulletin boards)
- [ ] Find a viable exp source beyond fido grinding (quests? events? alt zones?)
- [ ] Practice kick — still 0 sessions; gated by level, not time (needs level-up)
- [ ] Locate and scout the Newbie Zone / Massive Minotaur difficulty

## Session ledger: Growth
| Round | exp | gold | notes |
|---|---|---|---|
| before session | 469 | 30 | end of exploration round |
| backwards fido kill | 502 | 40 | +33 exp, +10 gold at Water Shop |
| — | 528 | 40 | (final score after exploration overhead) |

**Net this session:** +59 exp, +10 gold

## Learned
- The game has an **explicit level warning**: "This zone is above your
  recommended level" when you venture too far beyond the East Gate. Not just
  flavor — it's a hard barrier; the forest beyond is inaccessible at level 1.
- **Backwards fidos are identical to regular fidos** in every way: `consider`
  says "perfect match", combat and HP work the same, rewards are 33 exp + 10g
  + meat. A visual novelty, not a progression opportunity.
- **There are at least 3 distinct Main Streets** in Midgaard, each connecting
  to different shops (Weapon Shop, General Store, etc.). The room-hashing
  system correctly identifies them as separate; real duplication, not a bug.
- **Hunger/thirst can be cleared in-town** without needing to return to
  distant fountains: eat from inventory (meat from corpses), or buy water
  cheap (2g for a cup at Water Shop, or use Temple Square fountain free).
  Knowing this helped recover mid-exploration.
- **Movement economy forces route planning.** Started round at 84 mv, ended at
  81 after just 5 moves from the Practice Yard to the East Gate. At this rate,
  inefficient exploration can strand you far from rest with no movement left.

## Friction
- **The exp grind is mathematically unsustainable.** Fidos give 33 exp each;
  level 2 needs 1472 more exp (45+ kills). That's not a progression system,
  it's a tedium timer. For context: at this rate, a Massive Minotaur—a high-end
  Newbie Zone mob—would require level 5-10+ easily. Reaching that via fido
  grinding would take hundreds of kills over hours of real time. Design
  implication: either (1) quests exist and give exp significantly faster,
  (2) there's a tougher-but-still-safe mob zone the player hasn't found, or
  (3) progression bottlenecks hard at level 1 for new players, causing them to
  quit. High-priority finding: scout for quests or alternate exp sources.
- **Backwards fidos look like a progression step but are not.** A new player
  encountering them outside town would read them as "harder mobs, better loot"
  and be disappointed when they're identical to fidos. A room description or
  mob name that hints at danger (e.g. "feral" or "corrupted" instead of just
  walking backwards) would mislead more subtly; pure backwards-walk is so
  visual that the sameness is actually more confusing.
- **Bulletin boards exist but their content is not obvious.** Saw them in
  Swordsmen's Guild Bar and Reading Room, but `read board` was never tried —
  they might hold quest information or news, but there's no `help` hint about
  interacting with boards. A new player might walk past them never knowing
  what they're for.
- **The general store (north of Main Street `4404756a`) is unexplored.**
  Might sell consumables (potions, scrolls), quests, or progression items. No
  shop-door sign or npc named, so it's not obvious which room it is or how to
  access it.
- **The pet shop sounds like a novelty but might sell summons or pets.** If
  pets give exp or help in combat, this could be an undiscovered progression
  path. Not yet explored.
- **The Grunting Boar Inn (east of Temple Square) exists but its purpose is
  unclear.** Inns often offer rest/recovery and `rent` (save character). Its
  proximity to the Temple hints it's a lodging/safe zone, but no NPC desc or
  exits listed yet.
- **No quest board or quest-giver discovered yet.** Bulletin boards exist but
  are not interacted with. If a quest system exists, finding it is a hard blocker
  for faster exp and progression past the fido grind.

## Next session recommendation
**Priority 1: Investigate quest system.** Check `help quest`, read bulletin
boards in guild/tavern, talk to NPCs (innkeeper, shopkeepers, guildmaster).
If quests exist, they are likely the intended progression path and will unlock
faster exp gain.  
**Priority 2: Explore unexplored adjacent rooms** (General Store, Pet Shop,
Grunting Boar Inn, Common Square) to map more of Midgaard and find if there's
a progression gate (high-level zone, locked door, level-gated NPC).  
**Priority 3: If no quests found after 30 minutes of investigation**, grinding
is the only path forward. Pick a safe spot (no guards) and farm fidos until
level 2, then re-assess whether practice/skills unlock or if any new options
become available.
