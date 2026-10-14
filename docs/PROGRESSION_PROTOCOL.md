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
entry decoding 0x791cc8 reads a data reference and two integer values; confirm
their semantics before changing the own-home avatar/resource encoder.

The supplied Intro_3 quest entries have QuestType 1 and target values 50 and 3.
Both require TutorialAreaBasic; the second also requires Civilian events.
Resolve QuestType 1 and the progress/claim schemas rather than assuming these
values represent XP. Commands 575/576 carry main-quest step references but
remain decoded without execution. Implement persisted, earned quest progress
and reward application before allowing Luna's completion prompt to advance
the tutorial. Existing 574 tutorial persistence must remain intact.

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
