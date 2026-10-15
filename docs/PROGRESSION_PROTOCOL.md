# Tutorial progression research — 13.5.1

Human civilians and spirits are separate records. RunningNpc 10800092 uses
the Spirit model/event. Human tutorial civilians 10800309..10800313 use
pf_civilian_01..05, the Civilian event and health 1000. The normal encounter
snapshot retains spirits and adds humans; native human spawn zones also
choose the supplied tutorial civilian variants.

## Recurring encounters

The native Zone entity is 2008, resolved from Zone data table type 17. Its
serializer 0x74e4c0 preserves data, timer, spawn count, zone index and four
integer arrays: spawn-point X/Y, previous killed tick and enemies alive.
Native tick 0x74ea90 drives replenishment. Lazy initialization at 0x74ecc0
resolves the map index/count and calls 0x7507c8 to fill the point arrays.

The supplied tutorial map resolves 1700114 to index 9/48 points, 1700133 to
index 8/32 points and 1700134 to index 7/13 points. Zone 1700115 has no matching
points and stays inactive. In the verified two-minute observation, enemy
counts stayed between 25 and 63 and increased 44 times after decreases.
Five enemy types are initially present; recurring non-melee variants are
additional work. Do not replace these spawners with repeated scene-start
responses, which would reset the player and encounter state.

## XP and earned quest advancement

Current Python receives frame-ready acknowledgements and movement/action
traffic. It does not yet execute authoritative combat or award persistent XP.
The supported Leave Battle request 13223/v0 body 00 contains no kill/XP report.
Silence, elapsed time or a number of attack-button presses must not be treated
as proof of a kill or earned reward.

Native reflection 0x7358c8 names these battle-stat fields:

| Offset in the reflected object | Native name |
| --- | --- |
| 0x190 | normalXpAvailableFromEnemies |
| 0x194 | restedXpAvailableFromEnemies |
| 0x198 | gearPityTimer |
| 0x19c | monsterXpGained |
| 0x1a0 | otherXpGained |

The owning object and its live player binding still need to be traced before
using these offsets. They are not confirmed offsets in a Character or Player
entity. Resource data distinguishes XpPoint (Meta, instance 20) from the
XpDropSmall/Big/Huge collectible records (instances 21/22/23). Native resource
entry decoding 0x791cc8 reads a data reference and two integer values. The
own-home avatar now carries saved XP as XpPoint 300020 (value, 0); a tablet
probe confirmed 0x791cc8 decodes it into the avatar's resource list. Its
visible effect is still unverified (the apartment badge stays at level 1).

Own-home layout fixes (2026-10-15, measured with native stream offsets):
client-home +0x130 is object 0x7717b0 with six integers, and the empty avatar
after its resource list is the key/value count (0x779ab4) plus 14 zero bytes.
The earlier encoder wrote one and twenty, which kept the total length but put
the avatar start five bytes early. That only mattered once the avatar held
data: the XP reference was misread as a key/value collection and the decoder
read 16 bytes past the payload, crashing when those heap bytes were not zero.

The supplied Intro_3 quest entries have QuestType 1 and target values 50 and 3.
Both require TutorialAreaBasic; the second also requires Civilian events.
Resolve QuestType 1 and the progress/claim schemas rather than assuming these
values represent XP. Commands 575/576 carry main-quest step references but
remain decoded without execution. Implement persisted, earned quest progress
and reward application before allowing Luna's completion prompt to advance
the tutorial. Existing 574 tutorial persistence must remain intact.

## Implemented: Intro_3 and Portal tutorial completion (2026-10-15)

- Quest collection home+a0 (0x78ecf8): header next-quest-ID plus three ints,
  then Quests (0x78da48). Quest +0 is a unique ID assigned from the header by
  0x78ff08. MainQuestManager home+f0 (0x784638) entries (0x7850fc): step data
  reference, compact, new bit, claimed bit.
- GoToPortal: Intro_3 new, with Intro_3_1 kills/50 and Intro_3_2 rescues/3.
- Leave Battle with both objectives earned: Portal -> ClaimQuests; own-home
  carries Intro_3 claimed and Tutorial_Name_10 unlocked. The client finishes
  the Portal tutorial and starts the Name tutorial (EditCharacter).
- Client commands 575 (step seen) and 576 (step done) carry main_quest_steps
  references. Their names are inferred from observed order; they're persisted
  and replayed on reconnect.

## Implemented: XP bar (2026-10-15)

- XP level table: config [[[0xfadbf8]+8]+0x30], +0 base XP, +8 int vector.
  The client ships no table; an empty one makes level loop 0x788de8 spin
  forever once XP > 0. The battle HUD copies it to +0x1c8 at creation.
- Bar: 0x57f870 shows HUD+0x178 base XP plus battle XP from 0x73a364
  (player +0x19c + +0x1a0 - baseline). The bridge fills both tables, sets the
  bases and adds server battle XP to 0x73a364's result (display-only callers).
- Server table progress.XP_LEVELS is provisional (200 per level, 29 levels).

## Home level display (2026-10-15)

- The badge/HUD level is level loop 0x788de8 over base XP plus 0x57e768
  (battle getter 0x612758 in game mode 3, unclaimed quest rewards 0x57ed8c,
  0x57ee8c). Base XP is HUD +0x178 and config +0; no native path found
  copies the avatar XpPoint resource there, so it has no visible effect.
- The bridge sets base XP only in battle. The HUD table at +0x1c8 reads
  empty again shortly after being filled (per frame in the apartment), so a
  positive apartment base is unsafe until its owner is traced (freeze rule).
- Traced: HUD +0x198/+0x1c8 are shared pointers that the HUD rebuild
  (0x57e1f4..0x57e600) replaces with a newly built table. In battle (game mode
  3) the table and base come from config 0x49959c. At home (mode 0) they come
  from the profile: track = 0x78d170(avatar +0x40), the first entry whose
  [+0x68]+0 == 1, +0x24 == 0 and +0x28 > 0. Its levels are [+0x68]+0x28
  (count +0x34). Base XP is the client-home +0xe8 record whose ID matches
  track +8 (value +4, lookup 0x7872f8). With no track, the base is 0 and the
  table is empty, hence the level-1 badge. 0x756a30 is the native player-level
  getter over the same pair; 0x7565b8 is the native add-XP routine.
- home.py now sends this pair when saved XP is positive: track
  PLAYER_LEVEL_TRACK (local ID 1, entry 0x78b29c) with the provisional
  XP_LEVELS, and a record 0x788054 (ID, XP). The meaning of track +0x20,
  +0x28, +0x2c and +0xd8 is unknown (+0x28 = 1, +0xd8 = -1, the constructor
  default). A probe build measured an exact decode (own-home ends at
  1245/1245) and a stable home HUD table (29 levels, base 1901, level 4).
- The overhead name badge is a different reader (0x5acee0..0x5acf68). It
  shows the character metadata level (+0x14). Only for the local player, and
  only when 0x57e768() >= 1 (battle XP in a battle), does it run the config
  level loop instead. The apartment therefore needs the level in its scene
  snapshot. Player metadata (visitor 0x73ab98: accountId, teamId,
  battlePlayerId, level, trophyBadgeLevel, collectorLevel, realLevel,
  totalLevel, faction, name) uses a presence bit in the shared boolean byte
  plus a compact value per field. In the apartment suffix, the two bytes after
  the linked identity are level and realLevel. scene.apartment_scene now
  writes progress.level_for_xp(saved XP) there, capped at 63 to stay one byte.
  Battle snapshots are unchanged.

## Character editor and cosmetics (2026-10-15)

- Signup list builder 0x570be4 lists owned vanity items of the chosen slot
  (0x797cf0 over client-home +0xe0; slot 3 face, 2 hair). Entries 0x796ba8:
  raw data reference + count of (int, int) sub-entries 0x797034.
- Current build: client-home +0x88 (0x76b378) -> +0x10 (0x769988): ints
  +0/+4, name, +0x18 dye strings (graphicAsset UUIDs, 0x83c214), +0x40
  cosmetic references, +0x50 entries (0x794b14).
- Command 543 (decoder 0x68732c): cosmetic reference, optional int "slot".
  Handler 0x687128 rejects unowned items and replaces one dye per kind.
- The server grants pool-0 faces/hairstyles/dyes, equips face 2900435 and
  the canBePreset dyes by default, and persists 543 picks as profile `look`.

## COOL zone

The user confirmed this is a separate area, not the wardrobe. Supplied battle
data identifies SocialHub 10900005 with scene/w00_cool_zone_v2.json, CoolZone
music and 14 players. SocialHub_FTUE 10900309 uses home.json with CoolZone
music. The later ToHQ tutorial explicitly selects SocialHub; its steps include
Luna's portal prompt, SocialHubPortalAppear and SocialHubPortalEnter.

The current server supports only the apartment and Downtown Chaos. COOL-zone
travel and the earned unlock are not implemented. Add the correct scene,
player placement, selection metadata and account unlock together after the
required progression is understood. Do not mark tutorials complete or grant
XP just to expose the area.
