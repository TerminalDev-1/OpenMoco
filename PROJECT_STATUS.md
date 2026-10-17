# Project status — 2026-10-16

## Daily jobs / map missions, server side (2026-10-17, verified on the tablet)
Map missions ("Jobs" in the portal) are native Quests in client-home +0xa0
without a data reference. Findings (quest category filter 0x78eeb4, card job
count 0x78f780, daily goal 0x78fc24, completion 0x78e108):
- +4 is the QuestType (1 = defeat); +8 progress, +c target; +0x40 claimed;
  0x78e108 counts a quest complete when progress >= target and not claimed.
- +0x20 (count +0x28, raw references via 0x83c13c) are the target monsters:
  the card reads "Hunt <first monster's TID>_M" (e.g. Jumpers, Slashers).
- +0x60 is the portal map card slot ID (avatar +0x48 slot) the job belongs
  to; with +0x5c == 0 it is a daily map job (categories 2..4, 25). +0x50 > 0
  marks bounties, +0x48 main quests, +0x88 > 0 the type-36 daily goal
  ("Complete Jobs"), which also reads an avatar +0x88 object of type 0x1195
  (next-job timer +0x24, streak +0x2c) that is not sent yet.
Implementation (progress.py, battle_bridge.py, home.py): three jobs a UTC day
from a server pool for the Shrine Canyon card (Hunt Drogs 30, Jumpers 8,
Slashers 8, Juggler 1), chosen deterministically per account and day, saved
in the profile once progress starts. Server-credited canyon kills advance
them; a completed job is marked claimed and pays JOB_XP_REWARD (100 XP,
PROVISIONAL) once, also sent to the running battle. Jobs start only after
ToHQ (no mixing with tutorial quests).
Tablet (normal client, real account; backup
.local/accounts.before-jobs-20261017.sqlite3): the canyon card shows Hunt
Jumpers 0/8, Hunt Slashers 0/8, Hunt Juggler 0/1 with monster models; one
credited Jumper kill showed 1/8 after Leave Battle. Completion on the tablet
is not seen yet (unit-tested). Gaps: the "Complete Jobs" daily goal and its
streak (header still says DONEZO / Next in 0 s), official job rewards, claim
command handling.
Tablet note: after the tablet's reboot its wireless-debugging port changed;
the runner now uses --serial 192.168.1.91:42235 (adb connect).

## Next: server-side jobs, mission quests and chaos cores (2026-10-16, research notes)
User direction: rewards and future systems stay server side. Findings so far:
- Commands: 583 (decoder 0x687fa8) reports a feature-unlock screen shown
  ("featureunlocks" reference, e.g. 6300009 the MERCH SHOP); 593 (0x6864ac)
  carries one data reference (SocialHub 10900005 in the COOL zone). Both are
  decoded now, so those turns are no longer dropped; neither is persisted yet,
  so the MERCH SHOP unlock popup can show again.
- Correction (user, 2026-10-17): chaos cores are NOT the upgrade cores below;
  they are the monster loot opened after battle ("OPEN CHAOS CORE",
  "monsters have a higher chance to drop Chaos Cores", "Chaos Cores and Chaos
  Kits increase the power of your gear"). Earlier wrong note kept for context:
- Chaos cores are the weapons' UPGRADE CORES (TID_PANDORA_CHAOS_CORE "Upgrade
  Core", resources PowerGem and the Damage/Healing/Cooldown/AttackSpeed gems;
  texts: monsters drop them, "The tougher the monster, the more likely").
  The weapon detail page shows three core slots; the owned-weapon entry
  0x768794 has two raw-int-counted reference lists (+0x08, +0x18), the likely
  equipped cores. The COOL zone's CORES item (HomeItem type 11, chaos-core
  storage) is the storage. To do: the cores inventory schema, server drop
  rolls per credited kill, and equip handling.
- Mission quests: main_quest_step_quests QuestType 1 (185 of 393) is "defeat N
  in location", with optional QuestMonsterCond/QuestEventTypeCond; the server
  already sends such quests for Intro_3 (+0xa0 quests, +0xf0 steps). After
  Tutorial_1 (the real account has claimed up to Tutorial_1_8, 15400016) the
  next line is Shrinecanyon (Manny). Shrinecanyon_6_1's DragonlingProtect is a
  protect event (TID_PROTECT_ARCHEOLOGIST), not a kill, so kill reports alone
  cannot drive every QuestType 1 quest. Other types (13 dungeon, 19, 16 gear,
  9, 15, 20 PvP ...) are not understood yet.
- Jobs (daily jobs, "Complete Jobs / DONEZO" in the portal) are not researched
  yet; their own-home collection is unknown.
- Shop offers: the SHOP screen opens empty; offers are server data
  (client shop_items/billing tables), not researched yet.

## COOL zone (SocialHub 10900005) unlocked as home after ToHQ (2026-10-16, verified on the tablet)
Server-only. scene.cool_zone_scene: the item-free Home frame renamed to
SocialHub 10900005, every home-spawn pair moved to the w00_cool_zone_v2 map's
spawn cell (52,48), plus the map's eight key items. The map objects came from
the client's own decoder (probe .local/coolzone-map-probe.js on
server_scene/w00_cool_zone_v2.map_bin from the install-time asset pack):
skinshop, wardrobe, portal, radio, weaponloadout, teamup, elitehunter,
chaoscorestorage. A second probe (.local/coolzone-scene-probe.js) added them
as HomeItem 2010 (types 3, 1, 2, 4, 5, 9, 8, 11) and saved the client's
re-encode (748 bytes); Python reproduces it byte for byte (identity, name and
level dynamic).
Unlock rule (progress.cool_zone_unlocked): the account has reached the ToHQ
tutorial (15600009), the tutorial that sends the player to SocialHub. Then the
client's flagged home request (13222 SocialHub after Leave Battle or naming)
loads the COOL zone instead of the apartment, and an unflagged SocialHub
selection from the apartment does too. accounts.record_scene accepts it and a
reconnect resumes it.
Tablet (normal client 876b08de, real account copy, then restored to hash
8bf390af): the COOL zone loads with the player in the lounge next to TEAM UP;
the hall has WEAPONS, PORTAL, SHOP and CORES. SHOP shows the MERCH SHOP
feature-unlock popup and then an empty SHOP screen (no offers sent yet).
Soak: 5 warm COOL zone -> portal -> Shrine Canyon -> combat -> Leave Battle
cycles, one process (24321), one connection, server XP sent in 5 of 6
battles. Screenshots .local/cool-*.png, ccz-*-home/battle.png.
Known gaps: shop offers, radio/team-up/elite-hunter/cores screens are not
populated; command 583 (sent on the shop unlock) is not decoded, so that turn
is skipped; the apartment is no longer reachable once the COOL zone is home.

## Apartment weapons rack (2026-10-16, verified on the tablet, partial)
Server-only. The home map has a third key-item marker, pf_keyitem_weaponloadout
at (1331761,4538660). A temporary probe (.local/armoury-probe.js on the never-
published --apartment-probe build) added HomeItem 2010 type 5 (Armoury) with
prefab sc3d/pf_keyitem_weaponloadout there and saved the client's own
re-encoded apartment (576 bytes); scene._ARMOURY_SUFFIX reproduces it byte for
byte (item 201000002, prefab asset fb5d268ade98e5c0...). The normal v0.10.0
client renders the rack labelled WEAPONS, and walking up to it opens the
WEAPONS screen.
Owned weapons (server-only, home.py): the WEAPONS list (refresh 0x4a53e4)
reads client-home +0x78 (decoder 0x768de8, entries 0x768794: battle-kit data
reference, two adjacent booleans +0x28/+0x29, then two raw-int-counted
reference lists +0x08/+0x18). It is the fourth count after the key/value
collection (after +0x48 0x770c74, +0x58 0x7852c4, +0x68 0x777610). The server
now sends SmartBow 6700000 there. Probe build, own-home offset probe: exact
decode (1517/1517). The WEAPONS list shows SPEEDSHOT, and its detail page
opens (Ranged Damage, health 20000, EQUIPPED, MASTERY) with three empty
UPGRADE CORES slots: chaos cores are these weapon upgrade cores (resources
PowerGem "Upgrade Core" and the Damage/Healing/Cooldown/AttackSpeed gems). The
two reference lists of 0x768794 are the likely core slots (not verified).

## Server-decided battle XP via native XP event 1217; Shrine Canyon kills credited (2026-10-16, verified on the tablet)
User decision: keep the deterministic-port research parked; the client reports
only raw kill counts, and the server makes every XP decision and gives the XP
back to the battle with the game's own XP event.

Client (loader_diagnostics.js, normal build 876b08de...):
- posts raw cumulative killedEnemies counts for every character ID (no
  compiled-in allowlist, at most 256 IDs) and no collected XP;
- the collected-XP hook (0x74a0e4) and the battle-XP addition on 0x73a364 are
  gone. 0x73a364 now only applies the server's base XP on Mainloop;
- the bridge now also activates for battles that start with monster zones only
  (2008), not just with monsters (2002). Shrine Canyon starts with zones only,
  so before this the bridge never activated there.
- kept: the XP level table install (needed before XP can be positive), the
  local routing, idle-close and map-control hooks.
Server (battle_bridge.py, battle_events.py, server.py):
- per-scene tables: Downtown monsters/civilians as before; canyon monsters
  10800022/27 (Weak 2), 10800038/269 (Strong 10), bosses 10800449 (88),
  10800056/087 (176), from zones.csv 149..165 -> characters.csv LootProfile ->
  loot_profiles.csv XP / 1000. Meat, the protected dragonling and spirits earn
  nothing. Unknown IDs are ignored, not rejected.
- high-water marks per battle epoch, and credited kills capped at 20 + 4/s of
  battle time (excess is credited later as time allows).
- newly credited XP is queued on the game session and sent at the next
  frame-ready as 28852 with one LogicXpEvent 1217 (battlePlayerId 0, xp) at
  frame ready-2, provided that frame is newer than the last confirmed one.
  Execute 0x74e0cc -> 0x739fc4 adds it to player +0x1a0 inside the
  simulation; the HUD bar, the level badge and the native "+N" counter show it.
Verification (temporary account copy, then restored to
.local/accounts.before-xpevent-20261016.sqlite3, hash 8bf390af...):
- old v0.9.0 client + new server in Downtown: events accepted, no crash; the
  bar counted XP twice (old hook + native), which proved 1217 adds XP natively.
- new client: Downtown and Shrine Canyon kills credited ("+2 kills, +4 kill
  XP" in the canyon); 5 scripted warm Leave Battle -> apartment -> portal ->
  canyon cycles with combat, one process (18807), one connection, XP sent in
  every battle; the native counter showed "+2" for 2 server XP (no doubling).
  Screenshots .local/xpe-*.png, xpc-*-home/battle.png; log
  captures/user-test-server-xpevent-client2.log.
Still client-reported: the kill counts themselves (the server cannot see
kills without running the battle simulation, see the section below). The
apartment-to-battle level badge in the canyon showed 5 once battle XP > 0.
Published as https://github.com/TerminalDev-1/OpenMoco/releases/tag/v0.10.0-server-xp
(six assets, remote size/SHA-256 verified; unchanged splits from v0.3.0).
Manual server: hidden, mode server-xp-events, log
captures/user-test-server-server-xp-events.log, PID in .local/user-test-server.json.

## Server-authoritative combat: research result (2026-10-16, blocked)
Requested: the server, not the client, decides hits, damage, deaths, kills,
rescues and XP, then battle_bridge.py is removed. Research only so far; no
server or client change, nothing sent to the tablet. Full evidence:
docs/BATTLE_PROTOCOL.md.

Finding: a battle is a deterministic rollback simulation. The official server
sends input events (28852/28855), input acknowledgements (28853), confirmed
frames (28851) and checksums of its own simulated frame (28854). It never
sends health, hits, deaths or positions. The client hashes its whole
serialized frame (0x8e56e0: every entity plus the frame random) and compares
it with 28854; a mismatch makes it request frame JSON (18853 frame 0x7fffffff)
and report a desync (18855), after which it ignores server battle events.
Server-injectable logic events (factory 0x7eeaec) are join/leave, add
character, controller input 1214, level up 1215, debug 1216, XP grant 1217,
map event 1218, CSV changes 1219/1220 and player update 1221; none reports a
kill, and each runs inside the shared simulation.

Consequence: Python can only decide combat by porting the native battle
logic bit for bit and matching the client's checksums. A plausible but
different simulation would be ignored (no checksum) or desync the client.
That is a full reverse-engineering port of the 0x6b0000..0x7f0000 logic and
cannot be verified piecewise, because one checksum covers the whole frame.

Status: superseded by the section above (server-decided XP, raw kill
reports, XP event 1217). The deterministic port was started as research
only and parked at the user's request: the frame checksum is a
rotate-left-by-1-and-add hash over every archive field (ChecksumEncoder
vtable 0xecd950), written through the same binary archive (writer vtable
0xecef00) as the wire frames.

## Shrine Canyon battle scene with native recurring zones (2026-10-16, verified on the tablet)
Server-only (scene.py, server.py); no client change. Shrine Canyon W01_OA01
(10900006) no longer reuses the renamed Downtown snapshot. scene.canyon_scene
sends an 829-byte native-encoded frame, and scene.battle_scene picks the
builder for each portal destination.

How it was made (temporary --apartment-probe build 2d9b45b5, never
published; probe script removed, normal v0.9.0 base 61c11c9b reinstalled):
- At 0x5bf784 entry the SceneConfig data (+0x10) and frame map (+0xb8) are
  still null, so the probe read the live map from the HUD frame
  (hud +0x68 -> +0x2878 -> +0xb8). The canyon RogueMap is 145x164 tiles, with
  27 zones in its table (+0xa0, count +0xac) and 34 markers (+0x130, count
  +0x13c). Exactly one marker has tag 17: tile (63,99), the shrine path next to
  the campfire. The other 33 (tag 0) match the client-simulated hunters
  (data 10800000, 14 of them in the live frame, e.g. "Stormy"). The tag
  computed from the 0x1467c9 string "SpawnA" was 19, which matches no marker, so
  that tag lookup is not understood yet.
- The Python body (mob-free TutorialAreaBasic frame renamed to 10900006,
  player position pairs replaced with tile (63,99) centered) went to the
  probe client. It created and registered one native Zone (0x728294 /
  0x728284) per monster/NPC zone of the map: 1700149..1700162, 1700164
  RunningNpc and 1700165 boss. The ten OneTimeChest zones and the easter egg
  were left out. The client's own re-encode is 829 bytes. It kept every
  Python byte and inserted the 16 zones (331 bytes at offset 263); each zone
  carries its data ID twice. scene.py holds it byte for byte, and the identity
  is dynamic at offsets 50/660 (synthetic golden SHA-256 05643ca2...).
- Live observation (analysis/canyon/run2-canyon-live.json, private): zones
  resolve their map points within 5 s (melee 260, ranged 180, ambush 314,
  RunningNpc 100 points, ...). Enemies went 0 -> 160 (10800022, 10800027,
  10800038, 10800269, 10800212, ...), the boss zone started at ~15 s, and
  137..165 enemies stayed alive throughout the 90 s. Zones 1700158 and 1700162
  (frequency 999) stayed inactive. The player stayed at (63.5,99.5), health
  20000, with no knockout on arrival.

Normal client, temporary account copy (all tutorials done, then restored):
apartment -> PORTAL -> EXPEDITION card -> BATTLE loaded the canyon with the
player alive at the shrine path. Monsters were found near the campfire,
bridge and camp. Combat worked (hits of 300/600, a bot hunter helping), and
two level-10 dragonlings knocked out the level-1 player once (normal
difficulty; the in-place respawn worked). Leave Battle returned home. Then
5 scripted warm portal -> canyon -> combat -> Leave Battle cycles: one
process (29326), 6 canyon entries / 6 returns, frame acks still advancing,
~60% CPU, no crash buffer entries. Screenshots .local/canyon-n*.png,
canyon-cycle1..5-*.png.

Known defects / follow-ups:
- Canyon kills earn no server XP. The client bridge's compiled-in allowlist
  (client/loader_diagnostics.js:110) and battle_bridge.KILL_XP only know the
  Downtown monster IDs, so canyon kills are never reported. Fixing it needs
  a new client build (allowlist plus loot-profile XP for the canyon
  characters) and a release; the server must accept the same IDs.
- No initial pack: monsters appear only once zones resolve (~5 s).
- The battle name badge still says "Local Hunter" and level 1 (snapshot
  metadata).
- Chest zones, invasion events (battle_scenes.csv InvasionPortalEvent_W01_OA01)
  and the easter egg are not sent.
Account: real state restored from .local/accounts.before-canyon-20261016b.sqlite3
(hash 55fc7d07..., ToHQ HQDone, saved scene 10900006); the test copy is kept as
.local/accounts.after-canyon-soak.sqlite3. Manual server: hidden, mode
local-shrine-canyon-zones, log captures/user-test-server-canyon.log, PID in
.local/user-test-server.json. The reconnect resumed the canyon (829 bytes).

## Next steps: endless monster spawning and the Shrine Canyon card (2026-10-16)
Status: steps 1-3 below are done for Shrine Canyon (see the section above).
Downtown still has its fixed initial pack plus four tutorial zones.
User request: monsters should keep spawning without end, like the official
game, instead of a scene with a fixed initial pack (about a dozen monsters).

Endless spawning (next implementation step). The client already has the
native mechanism: Zone entities (type 2008, data 1700000 + zones.csv
_instanceId) replenish their monsters in zone tick 0x74ea90. Each zone
resolves its map index and spawn points lazily (0x74ecc0 -> 0x7507c8).
Downtown proved it: four tutorial zones kept 25..63 enemies alive for two
minutes (see "Recurring encounters" in docs/PROGRESSION_PROTOCOL.md). A zone
only spawns if the loaded map lists it, so the Downtown zones do nothing
in Shrine Canyon. Plan:
1. For each battle map, read its zone table (RogueMap +0xa0 data pointers,
   count +0xac, index 0 unused; 0x7be968 searches it) and its spawn markers
   (+0x130 pointers, count +0x13c; marker +8/+0xc tile, +0x10 tag). This can
   be read from the live map with a temporary probe, or decoded offline
   from server_scene/<map>.map_bin in the install-time asset pack.
2. Send a Zone entity for every enemy zone that the map lists, encoded by the
   client's own encoder (probe build, then a Python template). Then the
   client refills the map by itself, everywhere, for as long as the battle
   lasts. Keep the initial pack small; the zones do the rest.
3. Check by observation: live enemy counts must keep recovering after kills
   over several minutes, and repeated Leave Battle/portal cycles (the more
   than 4 clean cycles bar) must stay stable. Kill XP keeps coming from
   the bridge's per-epoch reports.
4. Later: Python-side spawn budgets per zone (NPCCountPercent,
   NPCSpawnFrequencySec, elite chances, invasion events from
   battle_scenes.csv) once combat becomes server-authoritative. Do not
   resend scene-start to "respawn"; that resets the player and the battle.
Shrine Canyon (10900006) was the first map done this way.

Shrine Canyon card says "Continue the recruitment process" (reported by the
user). That text is TID_DUNGEON_SELECTOR_MAP_LOCKED_PORTAL_NOT_ACTIVE. Step
IDs are 14200000 + tutorial_steps.csv _instanceId: the account was at
14200025 WaitForMaps3 (HunterTrack3 finished, action WaitForNextTutorial,
PortalStates INACTIVE), not a claim step. The client had already claimed
the track step and reported main-quest step 15400014 (Tutorial_1_6_35) as
seen and done. It adds the next step (15400015 Tutorial_1_7, tutorial ToHQ)
only when it rebuilds its quests from own-home. At the previous login it
did the same for 15400013. The user relaunched the client, and ToHQ
started with the portal pulsing again. No server change was needed. Live
quest advancement without a relaunch is still missing (the server sends no
quest update after a claim).

Server bug fixed: command 569 (main-quest claim, sent with the client
analytics event claim_quest) was unsupported, so the server dropped the
whole turn, including a 574 PortalSet3 -> Set3 transition. Factory case
0x67e46c, vtable 0xeae2c0, field decoder 0x67c790: base fields, then a
compact count and compact quest indices at +0x28 (observed [0]). commands.py
decodes it. Execution (0x67c7cc) and quest rewards are not implemented.

## Portal season timer, Shrine Canyon map card and apartment wardrobe (2026-10-16)
User report: after the hunter name, the portal listed nothing and showed
"Season ends in 0 s"; the wardrobe was missing. Verified on the tablet
(tablet screenshots .local/portal-*.png, card-*.png, done-*.png, wardrobe-*.png).

Season timer (server-only). The portal header and home HUD take the season
from the first avatar +0x40 track with +0x68 type 1, +0x24 == 0 and +0x28 > 0
(0x4f76e0 -> 0x78d170; the same track as the XP level badge). +0x28 is the
season's remaining seconds; the label is +0x28 minus time since receipt
(0x526c48, factor 0.001). We sent 1, hence "0 s". progress.py now runs
rolling 28-day seasons from 2026-01-05 UTC (provisional; the official
schedule is unknown). Tablet: "Season ends in 23 d 11 h".

Portal map list (server-only). The portal list (0x5132f8) reads three avatar
collections after the tracks, each filtered by home key/value 70 (tutorial
portal set, filter 0x6832f0):
- +0x48 map slots (0x786524, entry 0x785f44, card 0x5150b4): five ints
  (+28 opens-in, +2c ends-in seconds), two empty versioned objects, an empty
  list, an empty path/sha object, map object 0x78636c (raw battle-scene ref,
  six ints: +8 must equal the season track's +68 +4 (0x6832b4), +14 = portal
  set), base 0x779e68 (slot ID, empty list), raw ref, empty list.
- +0x50 = VERSUS cards (entry 0x782890, needs its +38 object); +0x58 = rift
  sets (0x7743c4). Both stay empty.
Card state (0x5150b4): -1/-1 = state 0, which ignores presses (0x516f80);
opens <= now < ends = state 1, which opens the map popup (0x511de0).
The start check 0x682df0 returns 4 when allowed; TutorialArea (10900002)
returns 1 (scene flag +0x170 while the portal has no tabs), so the card is
Shrine Canyon W01_OA01 (10900006), open now, ending with the season.
BATTLE sends 13222 with the third optional object (0x786738: slot ID, +20);
scene_requests decodes it. Python answers with the populated Downtown
snapshot renamed to 10900006 (two compact IDs + the raw selection).
Tablet (temporary account copy with all tutorials finished, then restored):
card "EXPEDITION", popup "HUNTING / DRAGONLING WORLD, Closes in 23 d 10 h",
BATTLE loaded the canyon, the player respawned at the campfire, the
joystick moved them across a bridge, and minimap Leave Battle returned to
the apartment. Own-home decode was exact (1402/1402) with a stream-offset
probe. Known defects: the Downtown monsters are placed by Downtown
coordinates, so they land on the canyon spawn and knocked the player out
once on arrival; the canyon has no native population yet. The battle name
badge says "Local Hunter" (snapshot metadata).

Wardrobe (server-only). HomeItem type enum: 0 Unknown, 1 Wardrobe, 2 Portal,
3 Shop, 4 Radio, 5 Armoury, 6 Computer, 8 EndGame, 9 TeamUp, 11 Storage.
A temporary probe added a native HomeItem 2010 (type 1, prefab
sc3d/pf_keyitem_wardrobe, map marker (1684275,4502323)) to the live
apartment and saved the client's own re-encoded scene; scene.py uses it as
the 553-byte apartment template (identity, level and name stay dynamic; the
Python body matched the native dump byte for byte). Tablet: a purple
wardrobe cabinet renders, its WARDROBE button opens the wardrobe (face,
hair, hat, outfit and mount slots) and the face list works (command 543,
already persisted). Hats/outfits/mounts have no owned items yet.

Tutorial behaviour observed (not changed): with map slots present, the
client auto-completes the portal-set quests (command 591 advances key 70
0 -> 1 -> -1 each session; the server does not persist key 70) and moves
through PortalSet2 -> HunterTrack3 -> ToHQ without playing jobs or the
rift. HunterTrack steps set the portal INACTIVE (0x6458d4 -> 0x6cbe88)
until the weapon sprint reward is claimed, and ToHQ sends the player to
SocialHub (COOL zone), which this server does not serve yet. Real portal
sets (+0x14 set numbers, jobs, TutorialDungeon) and track rewards remain to
be implemented. Command 569 appeared in a turn and is not decoded (the
whole turn is skipped). "Next in 0 s / Complete Jobs" (daily jobs) is not
fixed.

Account: real state restored from .local/accounts.before-events-20261016.sqlite3
(PortalSet2, step 14200027); test copies kept as
.local/accounts.after-events-test*.sqlite3 and accounts.after-portal-maps-soak.sqlite3.
Client: temporary --apartment-probe build (2d9b45b5..., never published) was
used and the normal v0.9.0 base (61c11c9b...) is reinstalled; the probe
script was removed. Manual server: hidden, mode local-portal-maps-wardrobe,
log captures/user-test-server-portal-wardrobe.log, PID in
.local/user-test-server.json.

## Hunter-name SIGN (2026-10-15, verified on the tablet)
The "YOUR HUNTER NAME" screen (tutorial 15600002, step 14200011) works.
SIGN sends 17582/v0: name string + boolean 1 (sender 0x5b28c8 also sets the
popup's waiting flag +0xac, which greys SIGN). Native findings:
- Replies routed to the name popup (popup id 0x10, getter 0x4e492c returns
  its +0x1c8 listener, vtable 0xea5918): 20205 (0x5bec5c, error code 1..6 ->
  listener +0x10, re-enables SIGN) and 28350 (decoder 0x75e8a4: bool, BE int,
  string). 28350 with false calls listener +0x20, an empty function for this
  popup, so it cannot finish the screen on its own.
- The popup closes only through command 14 (execute 0x688cf8): it sets the
  profile name (+0x30) and name-set flag (+0x48), then calls game listener
  slot 0x48 (0x5a0568), which closes popup 0x10. Command 14 is decoded only
  from client turns (16543 decoder 0x774668); its JSON form (27971) reflects
  only base fields and "id", not the name, so the server cannot send it.
- Own-home profile 0x755e34: raw long, optional long, name string (+0x30),
  name-set flag (+0x48), three ints. The tutorial opens the name popup only
  while the flag is false (0x6278c0, 0x646844).
Implementation (naming.py, server.py, accounts.py, home.py, scene.py): accept
17582, save display_name + name_set, reply 28350 {false, 0, name}, then reload
home exactly like Leave Battle (own-home with the name set, then the apartment
after the client's flagged 13222). The apartment nameplate now uses the saved
name (template metadata string). Tablet result: SIGN reloaded the apartment,
Luna's "hunter application approved" chat continued, and a later reconnect
showed no name popup and the nameplate "hi". Remaining: the Downtown Chaos
scene templates still show "Local Hunter"; name validation and the 20205
error codes are not implemented (any 1..60-byte name is accepted).
Account DB backup: .local/accounts.sqlite3.bak-before-name-20261015212700.

## Apartment level badge shows saved XP (server-only)
Work on 2026-10-15 (late evening). No client change; the installed tablet base
is still the published v0.9.0 normal build (61c11c9b...).

Why the badge stayed at 1: there are two readers, and both lacked server data.
- Home HUD: the HUD rebuild (0x57e1f4..0x57e600) replaces the shared-pointer
  tables HUD +0x198/+0x1c8 on every rebuild. That is what emptied the
  bridge-filled table about 1.5 s later. At home it takes base XP and levels
  from the profile: the avatar +0x40 track with +0x68 type 1 (0x78d170), and
  the client-home +0xe8 record with the same ID. We sent neither.
- Overhead name badge (0x5acee0): the character metadata `level` from the
  scene snapshot. Only the local player in a battle with XP gets the config
  loop. Our apartment snapshot said 1.
Fix: home.py sends the player-level track (local ID 1, provisional
XP_LEVELS) and its record (XP) when saved XP > 0. scene.apartment_scene writes
level/realLevel = progress.level_for_xp(XP) (same-length bytes; battle
snapshots untouched). See docs/PROGRESSION_PROTOCOL.md "Home level display"
for the decoders and layouts. Every test module passes.

Verified on the tablet:
- Temporary --apartment-probe build (not published; the normal base was
  reinstalled): own-home decodes to exactly 1245/1245. The client holds track 1
  (type 1, 29 levels) and the record (XP 1901), and the home HUD reads base
  1901, level 4, from a stable 29-entry table. Hooking generic decoders
  (0x779e68, 0x78b29c, 0x78cdd4, 0x78d04c, 0x78723c) crashed startup with
  SIGBUS; keep probes to own-home/client-home/avatar.
- Normal client: the apartment badge shows 4 for 1901 XP (.local/ht-normal-home.png).
  Soak on a temporary GoToPortal copy (kills reset per cycle): first battle
  plus 8 scripted warm Leave Battle -> apartment -> portal -> battle cycles
  with combat. One process, one connection, frames kept growing, no crash or
  freeze. With XP set to 1999, a kill crossed 2000 and the next apartment
  showed 5 (.local/ht-soak-2-home.png).
Real account restored from .local/accounts.before-home-track-soak.sqlite3
(15600002 -> 14200011, saved look, XP 1901); soak copy kept in
.local/accounts.after-home-track-soak.sqlite3. A cold launch reopened the
hunter-name screen. Manual server: hidden, mode local-home-level-track, log
captures/user-test-server-home-level.log, PID in .local/user-test-server.json.
Not done: the real level curve and track ID are unknown (provisional table).
The battle name badge shows the snapshot level 1 until the first credited
kill (battle snapshot not edited, per the AGENTS.md rule).

## Character editor, bridge race fix, home XP and startup-crash findings
Work by a side session on 2026-10-15 (evening). Normal client (all
diagnostic flags false) installed on the tablet: base SHA-256 61c11c9b...,
built with `--debuggable --local-network`; verify_test_client passes (1457
unchanged payload entries). 71 tests pass (run per module; see below).

1. Character editor (EditCharacter 14200010) now lists faces and hairstyles.
   Native evidence: the signup screen's list builder 0x570be4 (tab titles
   at 0x577f74, slot 3 = FACE, 2 = HAIR) counts owned items with 0x797cf0
   over client-home +0xe0. With none it shows
   TID_BUILDS_POPUP_NO_SKIN_CANDIDATES_%i and lists nothing. +0xe0 is the
   vanity-item collection (0x79716c, entry 0x796ba8: raw data reference, then
   a count of two-integer sub-entries 0x797034; "Invalid vanity item data
   found!"). The server now owns the free default set: rAssetCosmetic records
   with pool 0 and enabledForPlayers (26 faces, 32 hairstyles, 19 dyes).
   The headless preview came from an empty current build: build manager
   +0x88 (0x76b378) -> current build +0x10 (0x769988: two ints, name,
   +0x18 dye strings, +0x40 cosmetic refs, +0x50). Equipped cosmetics go in
   +0x40; equipped dyes are graphicAsset UUID strings in +0x18 (0x83c214,
   max 50 chars; 0x769e70 keeps one per kind). Defaults: face 2900435 (the
   head the apartment scene renders) and the canBePreset dyes (mid skin,
   brown eyes, brunette hair). With them the preview has a coloured head.
   Command 543 (factory case 0x67dd28, decoder 0x68732c: base fields, cosmetic
   data reference, optional int "slot"; handler 0x687128 checks ownership
   in +0xe0) is decoded; the server persists each pick as profile `look`
   (face/hair/dye_<kind>, starter items only) and returns it in the current
   build. Verified on the tablet: options appear for both buttons, a face and
   a hairstyle apply, and both survive a cold relaunch. The two icons beside
   the face list did not respond to taps; colour pickers are not verified.
   The editor test picks were made on a temporary copy; the user's real
   account was restored without a saved look, so the choice stays theirs.
   Do not press READY for the user: that finishes their tutorial step.

2. XpPoint (avatar 300020) has no visible effect, and the apartment badge
   shows level 1. Why: the HUD/badge level comes from base XP + 0x57e768
   (battle getter 0x612758 when game mode is 3, unclaimed quest rewards
   0x57ed8c, battle-related 0x57ee8c) through level loop 0x788de8 with the
   config/HUD level tables. Nothing found reads the avatar's resources on
   that path. Base XP is HUD +0x178 / config +0, which only the bridge sets,
   and only in battle. An apartment experiment (bridge fetching saved XP and
   writing HUD +0x178 outside battle) was reverted, not shipped: about 1.5 s
   after the bridge filled the HUD table (+0x1c8), the table read empty
   again, in both the apartment and battle. That matches the earlier ~1200
   per-visit refills, so something re-creates or clears it per frame. A
   positive base with an empty table is the documented Mainloop freeze, so
   it isn't safe until the owner of HUD +0x1c8 is traced. The other
   0x788de8 caller, 0x758090 (from 0x6843e4), uses a per-item table at
   [item+0x68]+0x28 and a home+0x18 -> +0xe8 record keyed by the item's ID.

3. Bridge race fixed (client/loader_diagnostics.js). Server replies
   arriving on the Frida JS thread now only update JS state; the config
   table and base-XP writes run on Mainloop in the 0x73a364 hook, and only
   for the battle that requested them (dropped after Leave Battle or a new
   scene start). Also found and fixed: the 0x57f870 HUD hook never detached
   in the apartment (it waited for a battle-only reply) and refilled the
   HUD table with a fresh native allocation every frame (about 1,200 per
   apartment visit). It now attaches only for battles, fills once per scene,
   and detaches at non-battle scene starts. Verified on the exact installed
   build: 6/6 scripted warm Leave Battle -> apartment -> portal -> battle
   cycles with combat plus the first battle, one process, one connection,
   one HUD table fill per battle, no rejected writes, badge level 4 and kills
   credited. An earlier build of the same logic also passed 7/7. Soaks used
   temporary GoToPortal copies of the account (kills reset per cycle); the
   real state came from .local/accounts.before-bridge-fix.sqlite3 and
   .local/accounts.before-home-xp.sqlite3 (soak copies: .local/accounts.after-
   bridge-soak*.sqlite3).

4. Early-startup SIGSEGV (probe build): not reproduced on the normal
   client. 22 rapid relaunches (10 x force-stop/start with 4 s, 12 x 2.5 s)
   all stayed alive with no Sentry crash envelope. The original crash
   envelopes are gone from the tablet (only session envelopes remain), and
   there are no dropbox tombstones for 2026-10-15. They happened only with
   the --apartment-probe build relaunched in quick succession, before any
   connection. Treat them as a probe-build artifact (unknown cause); recheck
   if they appear on a normal build.

Published: https://github.com/TerminalDev-1/OpenMoco/releases/tag/v0.9.0-character-editor
(pre-release, target 1c9dc70). Six assets (base 61c11c9b..., manifest,
assembler, INSTALL.md, SHA256SUMS.txt, DOWNLOADS.md) matched remote sizes and
SHA-256 digests; the seven v0.3.0-apartment dependencies still match. The
installed tablet base is this release build.

Tests: `python -m unittest discover tests` hangs if a server test fails
inside its async exchange; run modules one by one with a timeout to see the
failure. Manual server: hidden, mode local-starter-look-and-bridge-fix, log
captures/user-test-server-vanity.log, PID in .local/user-test-server.json.

## Leave Battle SIGSEGV fixed: own-home layout bug (server-only fix)
Root cause: two compensating field-count errors in home.py's own-home
encoder. Client-home +0x130 is object 0x7717b0, which reads six compact
integers; we wrote one. The avatar after its resource list is a key/value
count (0x779ab4) plus 14 zero bytes; we wrote twenty. The total length was
unchanged, so the all-zero starter still matched the native sample byte for
byte. But the avatar started five bytes early. Once the avatar carried the
XpPoint resource (added earlier on 2026-10-15), the native avatar decoder
read the XP reference's `04` byte as a 4-entry key/value count. It never
decoded the resource, and it read 16 bytes past the end of the payload.
The native ByteStream readers (vtable 0xecd7d8: +0x110 compact 0x8d7f24,
+0xf0 raw int, +0x120 raw long) have no bounds checks. The over-read
therefore consumed whatever heap bytes followed the buffer: usually zeros
(harmless), once about 6 KB of junk (survived), and in the soak crash a stale
tagged heap pointer. Its bytes `.. a4 b2 44 71 ..` decode as count 560292
(x22 = 0x88ca4 in the envelope), and the next byte 0x71 decodes as type -15.
Factory 0x79b1d0 returned NULL, and 0x756074 dereferenced it. So the crash
was deterministic misparsing plus heap-content-dependent luck, not a
teardown race and not the quest objects.

Evidence: a temporary --apartment-probe build (not published; the normal
v0.8.0 base e950a79a is reinstalled) logged the stream offset (+0x14) and
length (+0x18) at 0x755e34, 0x77e0b8, 0x77c010, 0x78ecf8, 0x784638 and
0x791cc8. Before the fix, the 292-byte payload was decoded to offset 308,
0x791cc8 never ran, and avatar resources=0. The client's own native
re-encode (309 bytes) decoded exactly, and its client-home tail and avatar
matched the corrected layout. After the fix, the same state decodes to
exactly 292, 0x791cc8 runs at 258, and the avatar holds XpPoint = 1901.
The quest and MainQuestManager sections were already exact (85..172).
Payloads without saved XP are byte-identical to before.

Fix: home.py (+0x130 = six integers; avatar remainder = 15 zero bytes, then
the three-integer suffix), plus a regression test that walks the client-home
tail, avatar and suffix in native order. 67 tests pass.

Tablet verification, normal v0.8.0 client (probes off), temporary GoToPortal
copy of the account with kills/rescues reset before every battle: 9 warm
Leave Battle -> apartment -> portal -> battle cycles with combat on one
process and one connection. That includes the first manual cycle and 8
scripted cycles, past the earlier failure at cycle 8. No crash and no freeze;
frame traffic kept growing. The real account state was restored from
.local/accounts.before-crash-probe.sqlite3, and the soak copy is kept in
.local/accounts.after-crashfix-soak.sqlite3. A cold launch resumed in the
character editor as before. Manual server restarted hidden to load the fix:
mode local-own-home-layout-fix, log captures/user-test-server-crashfix.log,
PID in .local/user-test-server.json.

Also seen: two early-startup SIGSEGVs (fault 0x0 on Mainloop, about 1.4 s
after launch, before any network connection) while relaunching the probe build
in quick succession. They are unrelated to own-home (no message received) and
not reproduced on the normal build in this session; the cause is not known.
Not done: the XpPoint resource now really reaches the client, but its visible
effect is unverified (the apartment badge still shows level 1).
Follow-up risk (not the cause here): the client bridge's 2-second
setInterval keeps calling applyXpDisplay (native writes to the XP config)
from the Frida JS thread after Leave Battle, because `battle` is cleared only
on the next scene start.

## In-battle XP bar fills from server XP; root cause of the old XP freeze found
Found with a temporary --apartment-probe build loading pushed scripts
(never published; the normal build replaced it on the tablet).

Root cause of the 2026-10-14 freeze: the client's XP level table is empty. It
is config object [[[0xfadbf8]+8]+0x30] (+0 base XP, +8 int vector {data,
+8 capacity, +c count}); the client data has no level table and the official
server supplies it. Level loop 0x788de8 subtracts table[min(level,count-1)]
while XP stays >= 0. With count 0 it reads index -1 and never ends, so the
first positive battle XP (XP drops under the old 6c2894 override, or any
direct write) spun Mainloop at 100% CPU. Reproduced by writing 300 to
player+0x1a0 (identical spin), then fixed by installing a table first.

Bar mechanics: HUD update 0x57f870 (entered every frame via 0x57f864) shows
base XP HUD+0x178 plus battle XP. In battle, battle XP is 0x73a364(local player
logic+0x2898) = +0x19c + +0x1a0 - baseline(+0x1f0). The HUD keeps its own level
table copy at +0x1c8 (+0x198 shares it), made at HUD creation. Direct writes
to player XP fields are wiped by prediction rollback every frame.

Implementation (client/loader_diagnostics.js bridge + battle_bridge.py):
- The server owns the table: progress.XP_LEVELS, PROVISIONAL (200 per level,
  from XP_LEVEL_1_OFFSET 200, 29 levels from MAX_LEVEL); the real curve is
  unknown. The runner provisions it as files/xp-levels.json; bridge replies
  also carry xp_levels, xp_before_battle and battle_xp (kill XP credited in
  this battle epoch, recomputed from its high-water counts).
- The bridge fills the config table (native operator new 0xe771c0, count written
  last) at scene start, and the HUD copy from a one-shot 0x57f870 hook that
  also writes HUD+0x178 = xp_before_battle, then detaches.
- A 0x73a364 onLeave hook adds battle_xp to the returned value. That value is
  only cached for display (callers 0x612758, 0x60d2a8, 0x60ebf0), so no
  simulation state changes and rollback cannot undo it.
- Signatures for 0x73a364, 0x5c10f4 and 0x57f870 are checked before hooking.

Verified on the tablet: badge shows level 4 for 1,849 XP; the top bar fills to
the level-4 fraction and grows with kills; a test write produced the native
"+300" counter and "LEVEL UP! 2" banner. tools/verify_test_client.py passes
(base 1457 unchanged payload entries). Installed normal base SHA-256 prefix
e950a79ac34d72d5 (probe flags false). Soak, PARTIAL: 5 warm leave-battle ->
apartment -> portal round trips with combat (6 battle checks, all with live
frame traffic, one connection, no freeze; badge reached level 5 and the bar
restarted). It stopped because the tablet was switched to Settings.
Second soak (fresh, foreground-guarded): cycles 1-7 passed (live frames,
one process). On the 8th Leave Battle the client crashed with SIGSEGV right
after the server sent the own-home profile, before the home-scene request.
Sentry native envelope (private .local/crash-xp-soak/native.envelope): libc
0x96b24 <- 0xfd988 <- libg 0xa4e854, 0xa4bd7c, 0xa4bf34, 0x4035a4, 0x7f1b44,
0x403908, 0x7fed7c, 0xa36144, 0xa35f24, 0x756074. 0x756074 is in the own-home
handler (decoder 0x755e34). Resolved later the same day: an own-home layout
bug that the XpPoint resource exposed (see the section above).
The user then set the pass bar at more than 4 clean cycles and asked to
publish, so v0.8.0-xp-bar was released with this crash listed as known:
https://github.com/TerminalDev-1/OpenMoco/releases/tag/v0.8.0-xp-bar
(pre-release, target 5755bbe). The six assets matched remote sizes and SHA-256
digests, and the seven v0.3.0-apartment dependencies are still published and
match. The installed tablet base is this release build. The real account state
was restored after the soak (backup .local/accounts.after-xp-soak2.sqlite3 keeps
the soak copy). The soak used a
temporary copy of the account state (GoToPortal, kills capped below 50); the
real state was restored from .local/accounts.before-xp-soak.sqlite3 with scene
set back to the apartment.
Not done: the real level curve; the apartment badge and home-profile XP were
not checked; the provisional table is an
approximation, like kill-based XP itself.

## Earlier on 2026-10-15

## Server readability refactor; tutorial Portal step completes on the server
Work on 2026-10-15 (Claude), using the wireless tablet (find it with
`adb mdns services`, then `adb connect`; connection details are in ignored
.local/tablet-connection.txt; ADB lives under the SDK path in
.local/android-sdk.txt). Run the server with `.venv` Python: system Python
lacks PyNaCl.

Refactor, no behavior change: server.py's single 300-line `capture()` is now a
`GameSession` class with one handler per stage/message, named message-type and
scene constants, and a `send_session()` helper. `capture()`/`run()` keep their
signatures. The dead `first_scene_ready` flag was removed (it never affected
output). battle_bridge.py was split into validation, crediting and HTTP helpers
with the same API. All 57 original tests passed unchanged after the server
refactor; 64 tests pass now.

Tutorial quest state (home.py, progress.py), verified on the tablet:
- The own-home profile can now carry the Intro_3 main quest. Quest collection
  home+a0 (decoder 0x78ecf8) is four header ints then quests; header +0 is the
  next quest ID, and native append 0x78ff08 copies it into each quest's +0.
  The failed 10-14 trial used ID 0 twice; IDs 0/1 with header 2 load fine.
  Quest 0x78da48 field order is in `home._quest`. MainQuestManager home+f0
  (0x784638/0x7850fc): data ref, compact, new bit, claimed bit.
- During GoToPortal (14200006) the server sends Intro_3 with Intro_3_1
  (kills/50) and Intro_3_2 (Civilian rescues/3). Progress = saved
  battle_progress capped at targets (the tutorial area is the only battle and is
  reached through GoToPortal, so those outcomes were earned during Intro_3).
- Leave Battle with both objectives done: the server sets the Portal tutorial to
  ClaimQuests (14200007) before sending own-home. The client showed Luna's
  "ur hunter application's approved" chat and sent 574 ClaimQuests itself.
  With only a claimed Intro_3 it waited in the tasks popup forever. Sending
  Intro_3 claimed plus Tutorial_Name_10 (15400003) unlocked continued the chat
  ("to make it official ... let's go!"). After "let's go!" the client sent
  575 x4 (15400003, 15400000, 15400001, 15400004), 576 (15400004),
  574 15600001 -> 0 (tutorial finished) and 574 15600002 -> 14200010
  (EditCharacter). The character editor opens headless: no cosmetics yet.
- 575/576 are now persisted as main_quests seen/done and replayed into the
  MainQuestManager list on reconnect (the first five were replayed into the
  account from capture 20261015T152305Z-2a29c68c). Their exact semantics are
  inferred, not proven. A cold relaunch resumed in the character editor
  (.local/claude-r1.png). Account backup before this:
  .local/accounts.before-intro-complete.sqlite3.
- Saved server XP is sent as the avatar XpPoint resource 300020 (resource entry
  0x791cc8: ref + two raw ints). The client accepts it; no visible UI effect yet.

XP bar: NOT done. The empty strip at the top of battle is the battle XP bar
(strings battle_xp, battle_xp_counter, player_xp_hud_bar_new). Its update
0x57f870 sums three XP values onto HUD +0x178 and has no direct/trampoline
callers (vtable). The battle player's XP fields are serialized in the 23491
snapshot by the SCPlayer visitor 0x7358c8 (+190 normal budget, +194, +198,
+19c monsterXpGained, +1a0 otherXpGained). Any edit near the budget in the
4946-byte snapshot (one-byte-longer values or a same-length 00->32 change) made
the client quit silently with no Sentry or logcat crash, consistent with a
snapshot integrity check. Do not retry blind snapshot byte edits. Options:
native-generated snapshots, or the client bridge writing server XP into the
live SCPlayer after each report (needs a new APK).

"Move battles onto the server": the server now owns crediting, totals, quest
progress and tutorial completion. Combat simulation is still the client's.

Manual server: hidden, mode local-intro-completion, log
captures/user-test-server-claude.log; PID in .local/user-test-server.json.

## Earlier status (2026-10-14)

## Battle crash and freeze fixed; XP now credited per kill
Both battle stability problems from the Codex handoff are diagnosed and fixed in
client/loader_diagnostics.js. The fixed normal client (all diagnostic flags
false) is installed on the tablet; no APK release has been published yet.

Joystick crash: Codex's uncommitted encounter-cap hook compacted the native
enemy vector at SceneStart 5bf784 from 18 to 8 entries without unregistering
the other actors, and rewrote Zone +e4 spawn batches at 752514. Several native
SIGSEGV/SIGBUS crashes followed login. The hook is removed, not repaired.

Freeze: the battle bridge forced the tutorial loot-disabled flag 6c2894
(ldrb [x0,#0x2f8]) to false so native XP drops would spawn. Disassembly confirms
705d94 moves the SCPlayer into x22 before the 705d98 call, so Codex's narrowed
override targeted the right call, but it still froze. After warm battle reentry,
the main Mainloop thread spun at 100% CPU (state R, no futex) while the Frida JS
thread stayed alive; server frame traffic stopped and the screen stayed static.
The process did not crash. Bisection on the tablet, each run made of
leave-battle -> apartment -> portal reentry cycles plus about 8 combat rounds:
- bridge with the 6c2894 override: froze in 3 of 3 runs, within 1-5 cycles;
- published v0.6.0 (no bridge): 10 cycles, no freeze;
- bridge without the override: 10 cycles, no freeze.
The exact native loop address is unknown. Frida Process.enumerateThreads()
returns zero threads in this client, and a tgkill/CModule signal sampler
crashed the already frozen process. simpleperf needs security.perf_harden=0,
which was not changed.

XP: the user chose kill-based XP as a workaround. battle_bridge.py credits each
newly reported kill using characters.csv LootProfile and loot_profiles.csv XP:
Weak 2000, WeakMedium 4000, Strong 10000, divided by 1000 (2/4/10). Native
6a58c8 multiplies base XP by runtime factors, divides by 10000 and rounds
randomly; loot XP / 1000 matches the ~1.6 collected XP per kill observed through
the bridge. Daily-budget multipliers (MONSTER_XP_*), level adjustment and random
rounding are not reproduced. Kill counts are trusted client reports. Collected
XP is still recorded in battle_reports for comparison but no longer awarded.
Existing saved XP (collected under the old bridge) was kept. The in-game XP bar
does not show server XP yet. Verified: 57 tests pass, and the server log shows
"+1 kills, +0 rescues, +2 kill XP" from real tablet play. The final normal
build then passed 10 reentry cycles with combat (22:19-22:33 local): no freeze
or crash, and 81 kill-XP reports, including mixed types such as
"+4 kills, +1 rescues, +16 kill XP".

Published as pre-release v0.7.0-kill-xp, targeting 2fcc986:
https://github.com/TerminalDev-1/OpenMoco/releases/tag/v0.7.0-kill-xp. The base APK
(61356239 bytes, SHA-256 c57e756f04a12428a66e4941229d4e1c3041255d7794c3f55ad4015f55ad17fa)
matches the tablet's installed base. All six release assets matched remote
sizes and digests, and the seven v0.3.0-apartment dependencies are still
published. Probes are off; the build is debuggable for key provisioning.
Open review findings (docs/CODE_REVIEW_2026-10-14.md, H2-H6) still apply to
this client: diagnostic dumps/JNI logging run in normal builds, and
package_release.py does not check debuggable state or a clean tree.

Manual server restarted hidden to load the change: see .local/user-test-server.json
(mode local-kill-xp-bridge, log captures/user-test-server-kill-xp.log).

## Priority: restore normal client after diagnostic battle freeze
The user reported battle freezing after movement and asked whether the installed
APK was diagnostic. It was: a temporary --apartment-probe build used for native
quest/profile inspection. The later profile-layout probe caught a native abort;
do not assume the process remains safe after that exception. Broad decoder
hooks also prevented login and were removed. These builds were not published.
The first Python quest-bearing own-home trial crashed before session traffic;
its integration was removed. Saved XP, account and tutorial records were kept.

The verified normal bridge base (build/xp-normal-base.apk) was reinstalled with
protocol_diagnostics, connection_diagnostics and apartment_probe all false.
Capture 20261014T192943Z-66446738 completes saved-account login and encrypted
frame/input traffic. Joystick movement, actor animation and XP collection work
again in .local/freeze-normal-before/after.png. Return-home restored the portal
(.local/freeze-map.png), followed by warm portal reentry and animated combat
(.local/freeze-normal-reentry-moved.png and moved2.png). Further native quest
experiments must not leave a failed diagnostic client installed for the user.
No new APK release has been published during this work.

Native isolated inspection confirmed XpDropSmall data ID 300021, hence the
XpPoint instance 20 is 300020. Intro_3_1/2 runtime quest objects have fields
[0,1,0,50] / [0,1,0,3], Civilian event filter for the latter, and reference
15500000/15500001. Their native encoder samples are recorded privately in
analysis/progress-layout.json; full own-home integration remains unverified.
A standalone native profile encoder probe aborted after decoding: its input
was allocated through Frida Memory.alloc, while stream reset 8d7b2c frees the
previous buffer through native e77200. Use native allocation for owned buffers
before attempting that isolated round trip again; verify this hypothesis.

Current hidden manual launcher/listener: see .local/user-test-server.json;
listener 17512, --login --apartment, logs
captures/user-test-server-quest-layout.log and .stderr.log. Keep it running.


## Active work: collected XP and native tutorial progression
The user approved a private-client outcome bridge first; combat remains client
simulated. Checkpoint 29f84e4 adds a native-derived 4946-byte snapshot with
initialized slime 10800138, jumping dragonling 10800036 and slammer 10800268
alongside five existing monster records, spirits, humans and native zones.
Local metadata level starts at 1; enemy-XP budget 60000 is not earned XP.
Normal probe-free acceptance: capture 20261014T191433Z-24a93363 and
.local/xp-normal.png, showing animated combat.

The loopback 9340 bridge now journals per-battle epoch cumulative counts and
collected XP in SQLite. Native killedEnemies metadata +98 supplies counts;
SCPlayer +19c is read after collectible application 0x74a0e4. Do not award XP
from death calculation 0x705d50 or drop effects. The user corrected this:
XP is collected in battle, and the nearby badge previously climbed to 243/247
while the top bar did not. +190 is available budget; metadata +14 is level.
The supplied tutorial loot gate 0x6c2894 returns config +2f8; the isolated
client enables native XP calculation while the provisioned bridge is active.
Hooks verify 13.5.1 signatures. Bot accounts and Spirit counts are excluded.
Reports are trusted client input, not authoritative Python combat. Actual
normal-client reports reached 41 collected XP, 19 kills and 2 human counts;
duplicate reports awarded zero. Four bridge tests cover retries, rollback,
epoch/account isolation, HTTP auth and reopening the database.

Native quest state, XP avatar/top-bar binding, Luna completion and earned
unlocks remain unfinished. 50 kills/3 human counts record tutorial_ready only,
without marking the native tutorial complete. Continue those state layouts.
Hidden manual launcher/listener 5580/24584, --login --apartment, normal bridge
APK installed. Logs captures/user-test-server-xp.log and .stderr.log; keep it
running. Socket/stream API reference: https://frida.re/docs/javascript-api/.


## Reconnect repair: preserve native socket error status
The server and ADB reverse mappings were running when the user saw Connection
Error. The client opened and immediately closed several zero-byte connections
(including 20261014T162123Z-5c5a21d5), before any 10100 hello. A trial server-first
hello did not run before those immediate closes and was removed.

The local connect/sendto replacement now uses Frida SystemFunction and restores
the captured errno through the callback context. Android nonblocking connect
returns -1/EINPROGRESS (115); losing that status across the JavaScript bridge
can make the client treat an ongoing connection as failed. Only game connect
results are logged; per-packet temporary logging was removed. Reference:
https://frida.re/docs/javascript-api/#systemfunction.

After updating only the isolated base APK, a deliberate server restart plus
background/foreground test reconnected the same tablet process (29978) without
force-stop, reinstall or tapping Try Again. Capture 20261014T162613Z-5b21a027
contains 10100, encrypted 10101, validated saved credentials and continued
authenticated frame traffic. The final normal base passes verification with
1457 unchanged payload entries and all diagnostic probes disabled. The original
mo.co app and both applications' data were preserved.

The longer background test then exposed a prediction stall: an 18851 reply
confirmed the previous ready frame, the resumed client sent a newer 18853, and
stopped polling clocks. Python now acknowledges every ready report through the
existing 28851 layout, without requiring another clock poll. Scene time also
starts at empty 13224 so loading pauses cannot age a fresh snapshot. All 52
tests pass, covering monotonic acknowledgements, loaded boundaries and repeats.
Acknowledgements alone did not prevent the native foreground-resume race:
0x60e7fc compares predicted/confirmed frames and 0x60e868 sets simulation flag
+0x2944 before the server reply is processed. The normal private-server client
now verifies instruction 0x540003ad and changes that one branch to 0x1400001d,
continuing at 0x60e870. This removes the local prediction-gap timeout policy;
ordinary socket errors and reconnect remain intact. Never reuse the offset for
another client version without checking its instruction and behavior.
The final client passed a 42-second background/foreground test: authenticated
frame traffic continued and joystick movement worked in rejoin-gap-before/after.png
(capture 20261014T163727Z-61fe4968). After the usage-limit interruption, the
server was restarted and wireless forwarding restored. The already-displayed
error required one Try Again tap; this is not a claim of automatic retry while
an error dialog remains open. Same-process saved-account login and apartment
movement then worked again in capture 20261014T182109Z-a5d77dbc, screenshots
.local/rejoin-now-before/after.png. Account progress was preserved.
Current hidden server launcher/listener: 24640/12796, --login --apartment, logs
captures/user-test-server-rejoin.log and .stderr.log. Keep it running.
Published v0.6.0-reconnect at
https://github.com/TerminalDev-1/OpenMoco/releases/tag/v0.6.0-reconnect,
targeting bed4164. All six new assets passed remote size/SHA-256 checks; all
seven linked unchanged dependencies from v0.3.0-apartment also matched.
The final normal base is installed on the tablet with probes disabled.
The server remains running and actual authenticated frame traffic continues.

## Project identity and full implementation goal
The user clarified that OpenMoco is a mo.co private server written in Python,
with a goal of 100% server feature coverage. Connection/login milestones are
early steps toward that complete implementation. README.md now introduces
the project in plain language, lists playable features and unfinished work,
and provides run/build instructions without presenting it as a research project.
AGENTS.md records this goal and wording preference for future sessions.
GitHub's repository description uses the same private-server identity.
This documentation change does not alter the running server or installed client.

## Priority repair: warm scene transitions and frozen battle player
The user reported return-home with an overhead camera, absent portal and a
T-posed player that could not move. Reproduced in .local/return-home-broken.png;
the same saved account and apartment snapshot worked on a cold login. Removing
the own-home refresh crashed native code at 0x7562e0 (null x0). Separating the
profile/scene by one second worked twice but failed on the third round trip.
Neither experiment is a complete fix, and neither timing workaround remains.

Return now sends 24548 own-home, then waits for the client's actual flagged
13222 selection (10900005, auxiliary 0/0, references 0/6700000) before sending
the current apartment. This is a constrained return-home mapping, not unlocked
COOL-zone travel. The empty 13224/v0 notification separates old and new scene
frame reports: native constructor 0x7637d0, getter 0x763804, caller 0x60ea10.
Old 18853 reports are ignored until that boundary; the first new ready frame
is immediately acknowledged through the existing 28851 clock layout.

The battle regression also exposed a clock error: static snapshots start at
frame zero, but the previous server used connection elapsed time in later
scenes. First ready frames jumped into thousands, with frozen/T-posed or missing
actors. Reset the simulation clock when sending each fresh scene, retain the
client timestamp echo, and keep acknowledgements monotonic within that scene.
The clock reset, loaded boundary and first-ready acknowledgement are now tested
together. No account/tutorial reset, new APK, or research client hook is needed.

All 52 tests pass, including encrypted return ordering, stale frame rejection,
first-ready acknowledgement without another clock request, and clock reset.
Normal tablet verification uses capture 20261014T155306Z-678df9d5. Screenshots
.local/clock-battle0-after.png, clock-battle1-after.png and clock-battle2-after.png
show animated players moved down the street by joystick; clock-home1/2-after.png
show the restored portal and movement onto the rug. Three successive returns
passed in the same socket session, including a longer battle stay; the third
is clock-home3-before/after.png. Both warm battle entries also passed joystick
movement checks. Authenticated frame traffic continues after returning.
Current hidden launcher/listener:
21528/22284; logs captures/user-test-server-scene-clock.log and .stderr.log.
Leave this server running; read .local/user-test-server.json for its current PID.

XP, earned quests/Luna and COOL-zone progression remain the next gameplay work
after reliable scene transitions. The earlier encounter and progression notes
below remain relevant; their process IDs are historical.

## Active checkpoint: human civilians, spirits and recurring encounters
The user corrected the earlier terminology: 10800092 is a Spirit. Keep the
six spirits; human civilians use 10800309..10800313, pf_civilian_01..05,
Civilian event type and native health 1000. The normal client screenshot
.local/encounter-normal-0.png shows both Helpless Civilian and Spirit models
with a Bug enemy nearby. The new initial snapshot has fifteen enemies across
five records: 10800020/21/26 and 10800117/120 (tutorial/melee/ranged dragonlings,
melee/ranged beetles), plus the spirits and five human civilians.

Python now sends the native-derived 4395-byte encounter frame on entry and
reconnect. It contains four native spawner entities (type 2008), Zone data
1700114/115/133/134. Native factory 0x728294 and registration 0x728284 suffice;
zone tick 0x74ea90 initializes map indices/counts/point arrays through
0x74ec60 and 0x7507c8. Melee zone finds index 9 with 48 points; RunningNpc
human zone index 8 with 32 points; ProtectNpc human zone index 7 with 13.
Ranged zone 115 has no matching points in this map and stays inactive. Initial
ranged enemies/beetles remain included; recurring beetle/ranged zones are not
yet configured. A 120-second native observation stayed at 25..63 enemies,
with 44 increases after decreases, verifying replenishment rather than a
one-time pack. No scene reset or client respawn patch is used.

The attempted extra mixed zones needed map context before scene-start setup;
the probe hit a null-context access violation, caught and logged. That failed
extension is not included. Evidence stays private in analysis/variety-live.json.
Dynamic identities are at offsets 50/4225; synthetic golden SHA-256:
902ad777eb1bcbcffed49d12747867e210dd86f38471d5585451206c2fa55e14.
52 tests and normal APK verification pass. The normal Python-fed reconnect is
capture 20261014T150551Z-329a5abb; authenticated traffic continues. Current
hidden launcher/listener: 18680/12952, ports 9339/9340, --login --apartment;
logs captures/user-test-server-encounters.log and .stderr.log. Leave it running.
The installed normal client has research probes disabled.

Remaining requested work: real XP and persisted main-quest progress, Luna's
earned completion prompt, and COOL-zone access. The first Intro_3 quest records
have QuestType 1 targets 50 and 3; the latter requires Civilian events. Resolve
the native quest semantics before presenting these as an XP threshold. The
user confirmed COOL zone is a separate area, not wardrobe. Battle data identifies
SocialHub 10900005 (scene/w00_cool_zone_v2.json) and SocialHub_FTUE 10900309
(home.json with CoolZone music); tutorial ToHQ later selects the social hub.
Do not fake XP, completed quests or tutorial state to expose that area.

## Active checkpoint: multiple monsters and civilians
All previous intended source/docs were committed and pushed: local and remote
main matched 047d427 with a clean working tree before this work began. Private
captures/accounts/keys, generated research and APK build outputs remain ignored;
the verified APK is distributed through releases rather than Git history.

Python now sends a 3104-byte native-derived populated tutorial frame on both
portal entry and saved-scene reconnect. It contains twelve enemies (one
10800020 tutorial dragonling and eleven 10800021 regular small dragonlings)
and six RunningNpc civilians (10800092), in addition to the local player.
Native helper 0x63be18 initializes gear, health/base health, initial spawn IDs,
faction and registration. The native caller 0x63c8ac selects faction 1 for
CharacterType >16 and faction 0 otherwise; do not guess these affiliations.
Regular enemies start with health/base 1890 and civilians with 5000. Live
client difficulty scales nearby enemy health. Two account references stay
dynamic at offsets 50/2934; the synthetic golden SHA-256 is
a1d45249710edf1c43aaa6b9f6926016d6d13a98b6b048dd59a848558d5007a2.
The old single-monster fixture remains available for regression/research.

Native encoding and Python account rebinding pass all 51 tests. The normal
client accepted this Python scene in capture 20261014T141636Z-1213cc51 and
continued authenticated traffic. Read-only HUD observation after another
Python reconnect confirms twelve enemy and six civilian entities, movement,
enemy health changes and decreasing enemy counts during client simulation.
That first 3308-byte placement was checkpointed as 231f016. Several actors
were behind the camp truck/buildings. Joystick observation established that
moving down the screen decreases world Y; the first placement used the wrong
side of the camp. The final groups are on the open street: enemies at X
57.5..63.5, Y 57.5..70.5; civilians at X 58.5/62.5, Y 59.5..68.5. Native
placement helper 0x6dfea0 resets the position/state before recalculation and
base-health copy. The resulting frame is 3104 bytes.

The hands-off street test verified monsters damaging civilians: health fell
from 5000 to 4040, 3080, 2120 and 200 before civilians disappeared. Native
recruits also fight enemies. Private evidence: analysis/street-population-live.json.
The normal probe-free client accepted the final Python frame in capture
20261014T142722Z-88c51c2e, and screenshots .local/street-normal-0.png through
-5.png show Spirit civilians, their dialogue and the recruits. All 51 tests
passed after the final placement. This is an initial encounter population,
refreshed on scene entry/reconnect. Encounters can clear quickly; continuous
respawning, saved kills/rescues and Python-authoritative rewards remain future
work. Do not claim those features from the client simulation.

Current hidden server launcher/listener: 13468/21764, ports 9339/9340,
`--login --apartment`, logs captures/user-test-server-street.log and
captures/user-test-server-street.stderr.log. Leave it running. The installed
normal client has all research probes disabled; keep the local account/progress
database intact. This is server-only behavior and works with the existing
v0.5.0-return-home client release.

## Published return-home APK checkpoint
[v0.5.0-return-home](https://github.com/TerminalDev-1/OpenMoco/releases/tag/v0.5.0-return-home)
is public as a prerelease, targeting source checkpoint 4d603a8. All six new
remote assets have matching names, sizes and SHA-256 digests. The seven unchanged
configuration/asset-part dependencies from v0.3.0-apartment also passed their
remote size/digest checks and are explicitly linked in DOWNLOADS.md. The normal
APK has local routing enabled and protocol, connection and apartment research
probes disabled. Its installed tablet base digest matches the release build;
all five splits remain installed. All 50 tests and normal base verification pass.
The listener remains on ports 9339/9340 with authenticated 18851/18853 traffic
continuing in capture 20261014T140329Z-e3efa881, beyond the old timeout interval.

Completed requested milestones: native return-home access and travel, saving
reported tutorial progress and last scene, and an initial visible damageable
monster. Remaining monster work: diagnose its fleeing behavior, add sustained
encounters/waves and Python-authoritative damage/death/rewards. Quest execution
and inventory progression are also unfinished. Preserve the verified initial
snapshot while testing improvements; do not fabricate completed tutorials.

## Latest verified checkpoint: saved progress and return home
The normal client now opens its minimap and exposes the native Leave Battle
button. Its observed authenticated request is 13223/v0 with body `00` (decoder
0x764214: two flags and optional selection). Python sends the latest saved
24548 profile followed by the account-bound 23491 apartment, resets the frame
confirmation, and persists scene 10900000. Repeated requests in home are ignored;
unsupported options are logged without closing the session. Encrypted integration
tests cover return, duplicate requests, nonces and subsequent portal re-entry.
Real tablet capture `20261014T132054Z-89f86471` and screenshot
`.local/returned-home.png` verify the apartment return without replaying the intro.

The native battlehud constructor normally hides its map hit target for tutorial
scenes. A signature-checked local-network bootstrap hook changes only the return
value of 0x6c2884 when called from 0x499b0c (return address 0x499b10). Other calls
and tutorial completion are unchanged. Tap the minimap, then Leave Battle.
Normal installed client has all research probes disabled. All 50 tests passed;
updated normal base APK identity/signature/alignment/preserved entries passed.

On October 14 the user explicitly verified one visible monster and a successful
hit that damaged it. They reported that it then ran away too quickly. Python now
supplies a native-derived 650-byte tutorial snapshot containing
DragonlingWeakMeleeTutorial, character data 10800020, health/base health 624 and
the five native default gear entries. Position (3964928,4882432) is two tiles
south of the player spawn. The client scales its live health to 437 in the
observed scene. Two account fields remain dynamically bound at offsets 50/480.
The earlier 629-byte snapshot omitted gear/base health and produced live health
1/max health 0. This checkpoint corrects initialization; it does not implement
Python-authoritative enemy AI, damage, death, waves, loot or rewards.
Native factory 0x728294, placement 0x6dfea0 and frame add 0x728284 generated the
fixture. Gear helpers 0x696d20/0x6f1148/0x6f0ec8, recalculation 0x6f18a0 and
base-health copy 0x703c60 complete initialization. Wrong research data IDs
initially returned null; correct table IDs use type * 100000 plus instance,
not * 1000000. Failed probes stay private.

A research-only substitution of DragonlingWeakMeleeSmall (10800021) produced
a 650-byte native snapshot, five gear entries and health/base health 1890.
It loaded, but improved chase/attack behavior was not verified; the normal
checkpoint retains the user-verified tutorial monster. Its Tutorial_1 event
may explain fleeing, but that remains a hypothesis. Broad scene observers
caused unrelated startup faults and were removed. The normal base was rebuilt,
verified and installed with all research flags disabled. A plain base install
was rejected for missing splits; the documented partial install-multiple update
succeeded without clearing test data or touching the original app.
The normal reconnect capture 20261014T140329Z-e3efa881 continues authenticated
18851/18853/18854 traffic. All 50 tests passed after the final snapshot change.

Current hidden server launcher/listener: 4532/18484, ports 9339/9340, mode
`--login --apartment`, logs `captures/user-test-server-near-monster.log` and
`captures/user-test-server-near-monster.stderr.log`.
Keep this server running. The previous listener IDs below are historical.

## Previous checkpoint: Downtown Chaos portal travel
Progress-saving implementation checkpoint: authenticated 574 tutorial transitions
now persist in SQLite by local account, alongside the last supported scene. New
accounts initialize empty tutorial state; reconnect sends native home +0x118
entries and resumes Downtown Chaos when that was the last selected scene. The
native collection/entry encoders 0x7966e8/0x7969a0 write tutorial then step as
raw 64-bit references. Completed tutorials use step zero and resist stale replay.
Targeted account/profile/encrypted reconnect tests passed. Tablet verification
now confirms a direct Downtown Chaos reconnect and return home at GoToPortal,
without the age screen, intro video or earlier phone/weapon sequence. The native
re-encoded 196-byte restored profile matches Python byte for byte. Unfinished
tutorials resume their saved step; do not pretend quests/combat were completed.
The user's previous eight authenticated transitions were recovered into the
existing account with tools/recover_local_progress.py; a private SQLite backup
was retained. No invented completion or account reset was used.
The user clarified that Downtown Chaos has no return-home button beside its map.
Investigate HUD visibility and the native return path before claiming it works.
Monster spawning/combat is now requested; the server still supplies no enemies.
The listener has been replaced with the tested return-home server described above.

On October 14 the user explicitly confirmed: “I'm in downtown chaos. The portal
is verified.” Normal-client screenshots and authenticated captures independently
verify travel from the apartment to TutorialAreaBasic (scene 10900001), displayed
as Downtown Chaos. The destination shows the local player, bow and recruits;
movement inputs continue afterward. Evidence remains private in
`.local/portal-corrected-destination.png`, `.local/portal-reconnected.png` and
captures `20261013T222744Z-4ba2ca50` / `20261014T082434Z-dc190141`.

The server decodes authenticated 13222/v0 requests and sends encrypted 23491/v0
with the 498-byte account-bound tutorial frame, deduplicating repeated requests.
Its complete payload matches native encoding. The previous destination crash
required a populated battle-start selection: 65 bytes replace the empty 54-byte
metadata. In the 487-byte template, use `body[:-58] + metadata + body[-4:]`.
The portal apartment remains 521 bytes. Full authoritative combat/collision,
return travel, and tutorial/quest persistence remain future work; native movement
and recruits do not prove those server systems exist.

Verification: all 47 unit/integration tests passed after the corrected boundary;
encrypted scene requests, account binding, response nonces and repeated-request
deduplication are covered. The five APK splits passed signing/package/alignment
and preserved-entry checks. Current installed normal APK has protocol,
connection and apartment research probes disabled. Age category persistence,
native automatic-idle suppression and foreground screen-awake fixes are included.

The manual server remains running: hidden launcher PID 25732, listener PID 11844,
ports 9339/9340, `--login --apartment`. Logs are
`captures/user-test-server-portal-corrected.log` and `.stderr.log`; runtime record
is `.local/user-test-server.json`. Do not stop it while the user tests. Wireless
ADB forwarding was restored after the physical debugging connection disappeared;
explicit `--serial` selects an active alias when multiple aliases appear. Real
network/ADB loss remains possible; the idle fix does not prevent it.

The user requested publishing the updated APK, README and all source checkpoints.
Published public prerelease:
https://github.com/TerminalDev-1/OpenMoco/releases/tag/v0.4.0-portal
Source checkpoint a43b54e is pushed to main. All six new release assets were
verified against GitHub's uploaded state, sizes and SHA256 digests before
publication; the release is confirmed public. The updated normal base APK is
included with manifest, assembler, installation instructions, dependency links
and checksums. Seven unchanged configuration/asset-part dependencies remain
public on v0.3.0-apartment and their remote sizes/digests match the new manifest.
Fresh installation needs those dependencies; matching existing installations
can update only the base. Neither archives, private keys nor device captures
were added to Git. Ports 9339/9340 remain listening under PID 11844, with actual
authenticated 18851/18853 traffic after publication.

## Historical investigation notes (superseded by the checkpoint above)
The process IDs, research flags, crashes and pending milestones below describe
earlier sessions, not the current manual-testing server or verified destination.

## Portal rendering and idle-close checkpoint
Foreground screen-idle fix: DiagnosticFactory registers test-app lifecycle
callbacks to set FLAG_KEEP_SCREEN_ON on created/resumed activities. Android
dumpsys window confirms GameApp is mHoldScreenWindow after startup. This avoids
the tablet's automatic screen sleep while the test app is foreground; it does
not change device-wide sleep settings or prevent explicit locking/backgrounding.
The APK builder now sends all freshly compiled DiagnosticFactory classes to D8,
including the callback class. An initial build omitted the anonymous class and
failed with ClassNotFoundException; corrected packaging and real startup passed.
Current installed client has all three research flags false.

The destination crash is now localized: libg+0x486150 dereferenced the empty
battle-start configuration's selection at +18 -> +0. Real native crash records
are in cache/sentry/.../outbox with extensionless names, not just *.envelope.
Broad stage hooks and Process.setExceptionHandler introduced unrelated faults;
they were removed, and experimental signal-capture code was saved under .local.
Native 0x766160/0x76622c + 0x77a46c/0x77a54c yields a 65-byte battle-start
body with the TutorialAreaBasic selection. Python's replacement of the 54-byte
empty metadata matches native full-message encoding byte for byte. The resulting
498-byte tutorial response is being tested on the normal client; do not claim
travel complete until the actual destination renders. The hidden server is now
launcher/listener 4816/9632, logs captures/user-test-server-portal-selection.log
and .stderr.log, same ports and --login --apartment. LEAVE RUNNING.

Onboarding reconnect improvement: server executes authenticated 541 age commands
and stores only the native home key-7 category (2 at/above default threshold 16,
3 below), preserving local identity isolation. It delivers that raw key/value
entry on reconnect. Previously submitted choices were recovered from local
authenticated captures for the existing test account, with a local DB backup;
the tablet bypassed SetAge and proceeded to the intro/apartment. No age was
invented or entered on behalf of the user, and raw ages are not stored in profile.
Account isolation/reopen tests and encrypted command-to-reconnect verification
pass. Other tutorial/quest state remains unpersisted.
Current hidden launcher/listener 19888/22980, same ports, logs
captures/user-test-server-portal-profile.log and .stderr.log. LEAVE RUNNING.

Python apartment delivery now includes the native HomeItem 2010 portal (type 2),
prefab sc3d/pf_keyitem_portal, at (1500774,4561305). The 521-byte scene retains
both authenticated local identity bindings. With all research probes disabled,
the tablet visibly rendered the portal and its effects (.local/python-portal-normal.png)
and requested destination 10900001, showing "Entering DOWNTOWN CHAOS".
13222/v0 decoding matches all 74 previously captured selection messages.
The initial native-derived destination frame crashes during initialization;
travel, tutorial persistence, and combat are unfinished. Do not call this a
completed portal travel implementation. client/portal_probe.js records the
fixture-generation method and is research-only.

Local-network bootstrap now checks the 13.5.1 instruction signature and replaces
the specific automatic idle-close method at 0x7fe3d8. Its state 9 produces the
"Connection Idle" dialog. Genuine transport/error paths remain active. On tablet
process 7342, explicit invocation on the connected client held state 8 -> 8 at
22:46:01 BST; encrypted frame/clock traffic continued afterward. Evidence:
files/diagnostics/idle-policy-verification.json and captures/user-test-server-portal-travel.log.
All 44 Python tests pass, including a real 31-second silent socket test. A long
inactive tablet run and final probe-free APK verification remain to be completed.
The already published v0.3.0-apartment APK does not contain this idle patch.

Current hidden manual server launcher/listener: 26588/23036, ports 9339/9340,
--login --apartment, logs captures/user-test-server-portal-travel.log and .stderr.log.
It remains running. Current installed APK has apartment/connection research
flags enabled for fault diagnosis; disable and verify them before release.
The original mo.co installation/data and production accounts remain untouched.
Next: diagnose destination initialization, verify portal travel on the normal
client, publish verified checkpoints/client update, leave the server running.

## Verified checkpoint: Python apartment spawning, normal client
Apartment plan step 1 is complete: the Python server supplies a local Player
2009 and linked character, head cosmetic 2900435, SmartBow 6700000, and the
map-derived spawn (tile 22,67, centered in 16.16 units). The normal test client
visibly renders Local Hunter inside the apartment. Screenshot:
.local/apartment-python-ready.png. Session 20261013T205421Z-45484d90 continues
authenticated frame/clock traffic. The user confirms apartment operation and
working client audio; the portal itself is still absent. Do not list audio as
a defect. Portal rendering/travel, authoritative movement, and tutorial/quest
persistence remain unfinished. The broader plan is not complete.

Use `python tools/run_local_test.py --login --apartment --launch`.
scene.py is a constrained native-derived starter template with both compact
account identity fields dynamically bound to the authenticated local guest.
It requires no private scene fixture or client probe. It is not yet a general
scene serializer. The current profile has no progression persistence, so
onboarding can repeat after reconnecting.

Important serialization correction: re-encoding a previously decoded native
message without resetting its stream appended bytes to the old empty scene.
The 599-byte experiment sent from Python therefore rendered an empty apartment.
Resetting the stream via 0x8d7b2c before native encoding produces a standalone
487-byte body. The Python output matches that native body byte for byte. Both
identity fields are re-bound per account; encrypted new-account and reconnect
tests verify profile/scene delivery and subsequent nonce ordering.

All 41 tests pass with the corrected standalone scene, including encrypted
new-account and reconnect delivery. Full APK
verification passed all five matching splits: 1457 base and 40015 split payload
entries unchanged, consistent signing/alignment/package isolation. The installed
release candidate has protocol_diagnostics, connection_diagnostics, and
apartment_probe all false. Original mo.co data/package remain untouched.

ADB's daemon stalled during the server transition; restarting only that daemon
restored the already-paired wireless device. The failed runner was replaced.
Current hidden background launcher/listener: 16972/24564, ports 9339/9340,
mode --login --apartment, logs captures/user-test-server-apartment-live.log
and .stderr.log. .local/user-test-server.json records these details. LEAVE ON.

The apartment release is public:
https://github.com/TerminalDev-1/OpenMoco/releases/tag/v0.3.0-apartment.
Source checkpoint 6f0b117; controller checkpoint 7420bf9. All 12 remote asset
names, sizes, and SHA-256 digests matched the prepared files before publication.
Five-split verification and local reassembly passed. Assets include the normal
probe-free base, three matching configuration APKs, four asset-pack parts,
manifest, checksums, reassembly tool, and corrected installation instructions.
GitHub's tag lookup API returned 404 for the draft; verification instead used
the authenticated release listing and release ID before making it public.
Private keys, account/device data, captures, extracted research assets, and
original archives remain excluded. The user confirms client audio is fine.

Next implementation work: execute and persist evidenced tutorial/quest commands,
then implement authoritative movement/collision and the missing key-item portal.
Keep the current normal apartment test and background server available.

## Controller input decoder checkpoint
movement.py decodes authenticated 18854/v0 using the native decoder chain
0x76536c -> 0x71ca2c -> 0x7e5898. Two raw frame/sequence integers precede
a compact controller field and packed stick header. Mode 2 carries compact
x/y; other present modes carry a signed angular byte. The signed header
stores strength as (header+128)>>3. Native angular fixed-point conversion
and authoritative execution remain unfinished. All 2,797 captured inputs
decode with zero trailing bytes; observed strength/mode are both zero.
All 39 tests pass in the existing .venv (global Python lacks PyNaCl).
This is a decoder checkpoint, not verified player movement; continue the plan.

Map research now decodes the bundled home.map_bin with the native asset
factory 0x65ab3c and reader 0x866e00, without attaching a hook to that reader.
Hooking it caused SIGBUS and was removed; the manual server stayed running.
Asset +30 points to RogueMap (vtable 0xec0838, fields 0x7bd02c). It is 50x90.
Map +50..+90 hold parallel object-tag/x/y/rotation/scale vectors, not entity
pointer vectors. Runtime spawn-marker collection +130 is empty immediately
after decoding and requires processing. Raw local map/captures remain ignored.

## Partial checkpoint: head cosmetic and bow rendered
The loaded asset database assets/assets.scdb is SQLite. Its meta/asset tables
map cosmetic global IDs to original JSON definitions. cos_head_male_05 is
2900435, slot 3, enabledForPlayers=true. Applying this loaded data record with
native 0x6f2624 after character construction fixes the missing head. The tablet
now visibly renders a complete Local Hunter and SmartBow, still outside the
apartment at default coordinates. .local/apartment-head-cosmetic.png records
this partial result (with the tablet's screenshot-preview overlay). The native
scene body grows from 541 to 545 bytes. Placement, Python delivery, movement,
and portal travel remain unfinished; this is another partial checkpoint.

## Partial checkpoint: visible native player/character
The user now explicitly accepts verified partial rendering as a checkpoint;
partial checkpoints do not complete a plan step or justify ending the work.
Step 1 remains in progress. The full apartment plan is authorized, including
necessary isolated client test builds/relaunches; keep the server available.

The apartment research probe constructs Player 2009 and a linked Character
through native 0x7ac630, initializes local guest metadata and SmartBow, and
serializes a 541-byte scene. The tablet visibly renders Local Hunter with a
level/health bar, torso and legs. It is at default position (0,0), outside the
apartment, with missing head/appearance; movement and portal travel are not
verified. Screenshot: .local/apartment-graph-current.png. Research session
20261013T163351Z-c3132ea2 remains alive with authenticated clock/frame traffic.
This is a client-side native construction probe, not Python server spawning.

Important corrections: Frame +b0 needs a runtime scene object initialized by
0x7affa0, not the serialized SceneConfig. Substituting SceneConfig caused its
frame pointer to be treated as a callback interface, destroying the frame and
clearing +a8/+b0/+c0/+c8/+d8. The default RuntimeScene's +28 callback interface
is initialized by 0x7a27dc. Player initialization 0x735214 needs the frame's
context (+c8); metadata is +1e8. Both current/original battle-kit pointers are
at metadata +1c0/+1c8. Spawn flag 0 queues objects in pending vectors and
produces a 226-byte scene without serializing the player; flag 1 inserts them
into active vectors and produces the 541-byte body containing Local Hunter.

The research build uses --apartment-probe, disabled by default and blocked
from release packaging. client/apartment_probe.js is provisioned only into
the test package's files/apartment-probe.js, then read by the guarded bootstrap.
Native-generated bodies, account-bound state, snapshots and captures remain
ignored. The server runner/listener are unchanged (7904/10464). Next: derive
the home spawn marker and appearance from the supplied map/profile, reproduce
the scene in Python, verify with the probe disabled, then proceed through
tutorial persistence, movement, portal travel, and animation/reconnect checks.

## Current apartment/cutscene investigation
Screenshot .local/apartment-current.png shows Luna's 'THAT BOW! THAT PORTAL!'
prompt and the apartment/joystick, but no visible character, bow, or portal.
The background session remains connected. A controlled joystick drag produced
no movement packet in this empty scene; no restart or reinstallation was used.

Local tutorial tables explain the intro movie, phone animation, portal and
weapon animations, controls guide, and forced TutorialAreaBasic destination.
Actual 16543 commands report Initial steps 0..3 and completion, then Portal
steps 4..6. commands.py now decodes all eight observed command layouts with
persistent presence bits across commands. tools/inspect_client_turns.py decoded
all 210 turns at verification, with zero unsupported commands and zero trailing
bytes. It does not print credentials, age values, or account IDs. The parser
does not execute or persist game commands or change the running server.

Native research found Player type 2009, Character 2001/2002, shared replicated
position fields, player metadata/character links, and movement event 1214.
18852/28852 carry structured event vectors; there is no captured movement event
yet. See docs/APARTMENT_PROTOCOL.md for exact evidence and remaining unknowns.
All 36 tests pass, including five new command-layout regression tests.
Next: establish object-manager allocation/reference encoding, insert a properly
linked local player/character in Frame 1200, then verify visible spawning. Only
after that implement captured movement, collision, weapon/portal interaction,
destination scene, and persisted tutorial state. Do not invent these layouts.

Long-session follow-up: the native client later displayed a separate
'Connection Idle' policy dialog and closed session af493a2a after its long
inactive run. The listener remained PID 10464. In-process retry made two
zero-byte connections; force-stopping and relaunching only the test package
restored encrypted guest login and frame traffic (session
20261013T160917Z-9f786e4e, tablet PID 31500), without restarting the server,
clearing data, or reinstalling. Native AFK policy and warm reconnect are still
unknowns; the earlier repair addresses the 35-second frame-gap disconnect,
not every possible client-side idle policy. Preserve this distinction.

## Active repair: persistent onboarding connection
The previous approximately 35-second disconnection was initiated by the tablet,
not by the running listener. Connection-only close/shutdown tracing located the
native caller at 0x60e860: current frame exceeds confirmed frame plus the
configured tolerance (0x60e7ec..0x60e7fc, native log 'Connection lost %d > %d').
The server's separate 30-second read timeout and 4 MiB cumulative capture cutoff
have also been removed. Individual frame size validation remains enforced.

18853/v0 carries one raw signed frame integer plus two adjacent boolean flags
(decoder 0x765728). The server records the maximum authenticated received frame.
18851/v0 carries raw 64-bit client clock plus a compact auxiliary (0x765860).
28851/v0 replies with echoed clock, server elapsed milliseconds, raw confirmed
frame, compact -1 and compact 0 (decoder 0x763028). Handler 0x5c3320 queues
event 3 with this raw integer; event dispatch 0x5c2c34 calls 0x610d78 to advance
confirmed frame monotonically. The existing encrypted transport keepalive is
also sent during clock traffic. A guessed 28853 four-integer reply crashed the
client and was discarded; that message remains unimplemented.

The known zero-ID starter profile fixture is now regenerated as
own_home(authenticated_account_id). Guest IDs and reconnect tokens remain
isolated from production. Frame acknowledgements support the onboarding
experiment; authoritative state, subsequent commands, and gameplay are pending.

All 31 tests pass, including 31 seconds of socket silence beyond the old cutoff,
encrypted clock/frame acknowledgements with out-of-order frames, nonce ordering,
and correct authenticated profile IDs. The temporary connection diagnostic
build was replaced with a verified normal local-network build: 1457 unchanged
payload entries, connection/protocol probes both disabled. Release packaging
rejects either probe flag. No production application or data was modified.

Actual tablet verification: initial repaired session 20261013T154705Z-358bc7bc
continued beyond the old disconnect boundary. After replacing the diagnostic
APK, normal-build session 20261013T154816Z-af493a2a remained established for
over two minutes with continuous authenticated 18851/18853 traffic; PID 30390
remained alive. At 15:50:30 UTC the client displayed Luna's onboarding dialogue
('a bow? what portal?') with no connection error. No UI input was automated.
This demonstrates sustained onboarding connectivity, not complete gameplay.

Current hidden background runner: launcher PID 7904, listener PID 10464 on
9339 and 9340. Started with tools/run_local_test.py --login --home-probe
.local/home-scene-probe-body.bin --profile-probe .local/own-home-probe-body.bin
--launch, using the canonical installed ADB. Logs:
captures/user-test-server-frame-ack.log and matching .stderr.log.
.local/user-test-server.json contains current launcher details. LEAVE RUNNING.

This section supersedes historical timeout/integration notes below.

## Latest checkpoint: onboarding/profile initialization
home.py implements a named Python encoder for 24548/v0 own-home data. Its
zero-ID encoding matches the corrected native-based 156-byte research profile
byte for byte; identity placement and invalid-input tests also pass. All 27
tests pass. Integration of this encoder with the authenticated account is still
pending; the current research server serves a zero-ID fixture within the
isolated test package/local session. Real Supercell accounts remain untouched.

Native own-home decoder: 0x786fdc -> 0x755e34, client-home 0x77e0b8, avatar
0x77c010. Required empty conditional collections are at client-home +e0, +120,
+18, +20, +28, +30; omitting them caused native UI null dereferences. The
selected collection reference must be BattleKit SmartBow 6700000, whose native
+108 link is ArcherWeapon. Attempts with StartingWeapon 11300000, ArcherWeapon
11301483, and metadata record 7500000 were wrong for this field. A direct native
lookup proved both registries resolve these IDs identically; the earlier theory
that a separate profile-data registry needed populating was incorrect.

The native stream has two boolean modes: persistent packed flags (0x8d7160 /
0x8d724c) and adjacent booleans, reset by scalar fields (0x8d7034 / 0x8d711c).
stream.py now supports both. Trace nesting must suppress primitive subcalls;
the previously labelled standalone float word was a string-length field.

Adding an evidenced OpenWorld handler 1240 to the native frame fixed the frame
copy crash, but the home profile was still necessary before scene startup.
Protocol probes affected one protected-code crash report; probe-free tests gave
useful native null-dereference sites. The installed client has probes disabled.
Ignored native crash envelopes were preserved by a bounded run-as shell watcher.
No private captures, keys, or asset tables are included in the checkpoint.

With the corrected profile and scene fixture, capture
20261013T151038Z-ccb391ad reached the age-onboarding UI and remained alive,
sending authenticated 18851/18853 events. The user completed onboarding and
confirmed the "Let's Go" screen. This is UI initialization, not playable home
or gameplay. 10110 is a device/GPU telemetry report, not a confirmed error.
The next concrete work is to decode and implement the evidenced scene-clock/
onboarding messages (18851/18852/18853 and supported server 28851/28852/28853),
then integrate persistent account/home state and add the required player frame.
Preserve the running manual test server during that investigation.

## Active home investigation (supersedes historical next steps below)
Terminology checkpoint c9e04f5 was pushed. OpenMoco is a private server; the
Android application is the test client. Both public releases' INSTALL.md assets
and SHA256SUMS.txt were updated and their remote digests verified; APKs were
unchanged. The v0.1 release body also uses the corrected terminology.

stream.py implements bounded native compact signed 32/64-bit integers and
packed booleans. Boolean bits remain packed across intervening integer/string
fields. Native methods: 0x8d7f24, 0x8d8464, 0x8d724c. All 23 tests pass.

Native scene-start message 23491/v0 uses SceneConfig 1003 and Frame 1200.
The typed Home data reference is 10900000 (class 109), verified through the
client's loaded data registry; 900000 is a metadata override and caused a
required-type mismatch. Correcting both scene references allows all scene-start
handler stages to complete. Captures 20261012T202324Z-8c708e15 and
20261012T202832Z-4673525a confirm decoding/handler completion and authenticated
10177 (two strings plus a compact integer); its semantics remain unknown.
This does not establish a usable home screen: the client subsequently crashes.

The recovered private native crash envelope locates the null dereference at
libg+0x725714: Frame copying requires the non-null handler at primary+0xd8.
The default frame lacks it. Removing concurrent fixture-generation probes did
not fix that crash. Structured registry dispatch is 0x8f07c0; its three child
factories are 0x6b5648, 0x7eeaec, 0x83d234. Unbounded type sampling encountered
an invalid constructor path and was removed; use statically supported types.
Type 1240 is an evidenced OpenWorld handler candidate, not yet a verified Home
handler. The experimental --home-probe path is opt-in; normal --login retains
the working baseline. Research APKs with probes enabled must not be published.

The prior background manual-test runner PID 13576 was stopped for research;
its .local/user-test-server.json metadata is stale until the runner is restored.
Wireless ADB occasionally stalled during APK installation. Restarting only the
verified adb fork-server daemon and retrying recovered the paired tablet.
No original-app data or test credentials were cleared. Private native samples,
crash envelopes, screenshots, and captures remain in ignored analysis/.local.

Next: supply the evidenced compatible frame handler, verify its required player
and account state, implement a Python encoder, and observe an actual usable home
on the tablet. Then restore the probe-free client and manual testing server.

## Updated APK release: published and verified
https://github.com/TerminalDev-1/OpenMoco/releases/tag/v0.2.0-local-login is a
public prerelease built from source commit 6467451. Its 12 assets include the
probe-free base APK, all four matching splits (the asset pack in four parts),
manifest, reassembler, installation instructions, and checksums. Every remote
asset name, size, upload status, and SHA-256 matched its local counterpart before
publication. Reassembly verified the completed large APK. Full five-split
verification passed, preserving 1457 base and 39950 asset-pack payload entries.
The current server/test client still lack home data and gameplay.
The first release-create attempt rejected an abbreviated target SHA (HTTP 422);
retrying with the full commit SHA succeeded. No duplicate release was created.

Completed source checkpoints this session: b8485d6 (incoming crypto), 8fefb16
(reply crypto/guest store), db70918 (native login/session), 6467451 (probe-free
release preparation), and a9be3fb (CSV reader/home research). All were pushed.
Native guest login, saved-token reconnect, and encrypted keepalives are verified.
The remaining approved stage is minimum home/frame/player data; it is not
implemented or proven. Start with SceneConfig type 1003, frame type 1200, and
the 23491 scene-start message/handler described below, preserving the working
login baseline. Error replies and broader gameplay also remain future work.

## Current manual testing server
The server is running in a hidden background process with file-backed logs,
so it is independent of the foreground tool session. Launcher PID 21720;
listener PID 24368, verified on ports 9339 and 9340. Private runtime metadata:
.local/user-test-server.json. Logs: captures/user-test-server.log and
captures/user-test-server.stderr.log. Mode: login-home-onboarding, using the
ignored native scene fixture and the corrected 156-byte profile fixture.
Capture 20261013T151353Z-85fa64b4 verifies the tablet's authenticated login,
profile/scene replies, and subsequent client events. The user confirms reaching
"Let's Go" after age-onboarding. The client subsequently closes its connection;
the listener remains active. Required scene/onboarding responses are not yet
implemented, so "Let's Go" can stall or show a connection error. Do not equate
listener availability with a completed game session. Do not stop this server
or reinstall/cold-launch the test client while the user is testing.


## Current milestone: native login acceptance and encrypted session
Further home research identified the SceneConfig type getter at 0x7b17bc
(1003) and its field serializer at 0x7b0aa4. Fields include data, battleTime,
initialFrame, initialFrameEvents, initialFrameChecksum, mapChecksum,
frameChecksums, chronosModifiers, chronosCsvChanges, and serializedFrames.
The correct wire representation and minimum frame/player contents are still
unknown. Avoid treating a structurally empty object as a valid home.

tools/read_client_table.py now decodes this build's compressed CSV assets:
five LZMA property bytes, four-byte little-endian plain length, compressed data.
It limits archive entries, declared output, and decoder memory to 64 MiB.
The supplied battle_scenes.csv decoded to 188182 bytes. Its Home row names
scene/home.json, SceneType Home, and PlayerCount 1; no numeric scene ID has yet
been established. The decoded table stays under ignored analysis/.
The original installation's version and first-install/update timestamps were
rechecked after the latest test client installation and matched the earlier snapshot.

Home investigation continued after the login checkpoint: message 23491 carries
a typed `sceneConfig` (type parameter 1003), optional nested structures, and
snapshot bytes; message 23492 is decompressed and decoded as 23491 by the game
handler. The scene-start handler is 0x5bf784. Required non-null nested data is
consumed there. This is a next investigation target, not a verified minimal home
schema. No trial home payload was sent. The post-login observer list was empty;
the actual message consumer was traced through 0x7feda4 -> 0x80b62c -> 0x5be224.
Native serializers expose keys such as `sceneConfig`, `players`, and `events`;
standalone strings are not proof of a valid home payload. Read-only scratch
analyses and the tablet loading-screen image remain under ignored analysis/.

Type 29125/version 1 is now verified as the login-success reply. Its native
decoder (0x835d6c), encoder (0x8359f4), router admission, and handler (0x80d2e8)
were inspected. The real tablet completed that handler on capture
20261012T193151Z-b62a94ce and repeatedly sent authenticated empty 10108/v0
SecretBox keepalives. Python decrypted them and returned encrypted 20108/v0.
A second cold launch, 20261012T193301Z-596ef655, reproduced the exchange.
Twenty tests pass, including a complete socket-level synthetic guest login,
encrypted reply, keepalive, and token reconnect.

Initial replies reached the success handler but crashed with a null SCString
assignment at 0x816148. Investigation traced this to player-tag conversion
0x8f81e8: an ID high word >255 returns null. The first SQLite namespace was too
large. It now allocates a persisted namespace from 128..255, preserves the
old namespace as a token-validated migration alias, and returns the same local
profile/token with the corrected ID. No test client data or original app was cleared.
The client still supplied the old research ID on the second launch; the alias
remains necessary. Successful replies use a compatible high word and preserve
the existing local account's low word.
This namespace is a compatibility choice, not a claim of globally reserved IDs.
Isolation rests on the separate package, local routing, private local store,
and never using these credentials against production.

A native default encoder sample (110 bytes, zero IDs/null tokens) verifies the
reply field order. The server uses real local IDs/tokens, the observed client
version fields, zero/null defaults for unknown fields, and present empty
configuration strings in the suffix. A truncated-prefix experiment was not
sufficient to prove a complete valid reply. A Process exception-handler probe
was tried briefly; it captured unrelated/intercepted faults and was removed.
The useful probe was a narrowly scoped null-SCString assignment hook.

The normal --login server now sends this reply and supports encrypted keepalives.
The home/profile message schema is the remaining approved stage, under active
inspection. A usable home screen and gameplay have not been verified. Updated
probe-free APK publication remains due after stabilizing the client build.

## Latest verified checkpoint: reply encryption and local guest storage
The tablet accepted a NaCl Box encrypted server reply in capture
20261012T191859Z-f2be5847. The native Box-open wrapper at libg+0xa36d1c
reported status 0 for the 72-byte ciphertext. The diagnostic reply is an empty
20108/version-0 keepalive, not a login-success reply. Do not equate this with
the client reaching its home screen. Use --login --transport-probe to reproduce.
Native session-cipher inspection establishes SecretBox and little-endian
24-byte nonce increments of two before each operation. Session methods have
authentication, replay, ordering, and carry tests; session traffic is not yet
verified against the tablet.

accounts.py implements persistent SQLite guest identities, a distinct positive
32-bit ID namespace, random reconnect tokens stored as hashes, and a minimal
local profile. The live server created a guest from the tablet's decrypted
zero-ID/null-token login. It has not sent those credentials to the client yet;
repeat fresh launches therefore create additional guests. Accounts remain in
ignored .local/accounts.sqlite3. Eighteen tests pass, including persistence,
invalid tokens, foreign IDs, and crypto tampering. The first account tests
exposed unclosed SQLite connections on Windows; explicit closing fixed this.

Full factory sampling found 216 supported types across the uint16 range.
Type 29125/version 1 is a strong login-success candidate: it is admitted by
the pre-login router beside LoginFailed and its decoder reads two account IDs,
strings, and version fields. Its layout and handling still need live verification.
20104 and 24101 are not supported. Ignored evidence:
analysis/runtime/message-factory-all.json and analysis/login-ok-decode.txt.

Checkpoint b8485d6 was accidentally pushed after the APK verifier rejected a
stale embedded diagnostic script: the PowerShell command continued despite
the failed native exit code. This was disclosed, the APK rebuilt, and the
matching source/build verified before installing. Subsequent builds passed
1457 unchanged payload-entry checks and produced the live observations above.
Keep checks and commit/push in separate inspected calls.

The current research listener is the foreground --login --transport-probe
runner, replacing stale background PID metadata. Research probes remain enabled
only in the local development APK; do not publish this diagnostic build.
Next: verify 29125's account/token fields and client handler, then derive the
actual home/profile schema and publish a probe-free updated client release.

## Approved next stages: current work
The user approved encrypted transport, local guest accounts, compatible login
replies, and minimum home/profile data. Incoming login encryption is now resolved.
Decoding the 13.5.1 obfuscated peer-public-key table reproduced the saved native
nonce and ciphertext exactly with standard BLAKE2b-24 and PyNaCl NaCl Box.
The previous mismatch came from overlooking native substitution of the peer
public key into the hash input; do not repeat the custom-cipher hypothesis.

A new local key pair is stored only in .local/server-key.json. The test client's
bootstrap validates and re-encodes its native public-key table before connect.
The runner provisions only the public key into test-client-private storage. Real
tablet captures 20261012T185708Z-5b1b9b41, 20261012T185957Z-1a170e34, and
20261012T190616Z-59829e05 all decrypted successfully: account ID 0, no token,
version fields [13,1,5]. Thirteen tests passed, including wrong-key, tampering,
challenge verification, and initial reply crypto round-trip. Native inspection
also establishes first-reply nonce BLAKE2b-24(client nonce + client public key
+ server public key), with server nonce (24 bytes) and session key (32 bytes)
preceding the reply body. That reply still needs live client verification.

The actual native message factory was observed at method 0x7590dc. Its runtime
samples show that 20104 and 24101 are unsupported by this client; do not assume
generic Supercell login/home message IDs. Further inspection is continuing.
Diagnostic samples are under analysis/runtime/, excluded from Git.
The current live research process uses --login and a probe-enabled test client;
the earlier background server was replaced for this work. The public
v0.1.0-hello release remains the earlier probe-free hello build. Local accounts,
the server login-success reply, and minimum home data are still in progress.

## Active user testing session
At the user's request, the handshake-mode server was started in a background
Python process, listening on PC loopback ports 9339 and 9340.
The paired tablet's ADB reverse mappings are enabled and the isolated client
was launched. Logs: captures/user-test-server.log and
captures/user-test-server.stderr.log; process details:
.local/user-test-server.json. These are runtime facts to recheck before
reusing or stopping the process. Leave this session running for the user.
This mode captures the encrypted login request but cannot authenticate yet.
The manual-test launch produced captures/game/20261012T181258Z-b6b32b3e.*:
10100 received, 20100 sent, and encrypted 10101 received. Its socket closed
after the idle timeout; the listener process remains running as last checked.

## Verified result
The isolated Android client connects to the Python server. Two cold-launch
tests captured an 83-byte initial message from the native game library.
The second test used the new incremental decoder and produced type 10100,
version 0, and 76 payload bytes. The 7-byte header is consistent with
big-endian uint16 type, uint24 length, and uint16 version.

The first hello exchange is now implemented and verified. In `--handshake`
mode the server sends 20100/version 0, payload length 28: a big-endian
four-byte length followed by a fresh 24-byte challenge. The tablet accepts
it and sends 10101/version 9 with 1,775 encrypted payload bytes. This was
reproduced on multiple cold launches, including the final normal build with
protocol probes disabled (captures/game/20261012T180051Z-176bfeee.bin).
The state is `encrypted_login_received`; full encrypted handshake,
authentication, a login reply, and gameplay remain unimplemented.

After the earlier automated verification the test client was force-stopped, PC test listeners were
stopped, and the two test ADB reverse mappings were removed. The test client
remains installed. The original app's version and installation/update
timestamps match the pre-test snapshot (analysis/original-install-final.txt).
The wireless tablet remains paired; no re-pairing is required to continue.
The later user-requested testing session is active as described above.

## Publication intent — recorded 2026-10-12
Update: the user now requests a public GitHub repository and a pushed
checkpoint after every successfully verified change. They are choosing the
repository name and selected `OpenMoco`. The public source repository is now
https://github.com/TerminalDev-1/OpenMoco, default branch main, remote origin.
Initial checkpoint: 7ad283e (verified hello exchange and isolated client tooling).
GitHub visibility and the remote commit were checked after the push. Six tests
passed and the diagnostic base verification preserved 1457 original payload
entries. The initial public tree contained only 17 source/documentation files; APKs,
archives, captures, extracted libraries, and private keys were excluded.
Android tooling discovery now uses SDK environment variables or ignored local
configuration, and device identifiers were removed from public documentation.
AGENTS.md records the checkpoint rule and
public-content exclusions.

The user subsequently explicitly requested APK publication. AGENTS.md now
requires a public verified client release with the matching splits and install
instructions. Release v0.1.0-hello is public at
https://github.com/TerminalDev-1/OpenMoco/releases/tag/v0.1.0-hello:
the 61 MB diagnostic base,
three configuration splits, and the 3.77 GB asset-pack APK split into four
1 GiB-or-smaller parts. tools/package_release.py prepares the assets and
SHA-256 manifest; tools/assemble_release.py validates downloads and reassembles
the asset APK. All 12 release assets uploaded successfully, and GitHub's
SHA-256 digests and sizes matched every local download file before the draft
was published as a pre-release. The full asset APK was reassembled locally
and its hash verified. All five APKs passed package/signature/alignment and
original-payload checks, including 39950 asset-pack entries. Nine automated
tests passed. Release source checkpoint: eda431c.
All five APKs use the isolated package and one signer. Native
protocol probes are disabled. This remains a hello/login-capture prototype,
without authentication or gameplay. Original archives, private signing keys,
device/account records, and raw captures are excluded from releases.
Comparable projects and their external client links are recorded in
docs/RELATED_PROJECTS.md; no distribution policy is inferred from those examples.

## Current implementation
- `--handshake` is opt-in in server.py and tools/run_local_test.py. Incoming
  and outgoing wire bytes are saved separately; metadata records sent frames,
  decoded hello fields, protocol errors, and session state. Unexpected initial
  messages are rejected without a server reply. No login-success response is sent.
- protocol.py now serializes frames and decodes the observed client hello.
  Its separate plaintext login-prefix inspector must not be applied to encrypted
  wire data. The captured test client login has account ID 0, no token, version fields
  [13, 1, 5], the same 40-character fingerprint, and 1,611 remaining opaque bytes.
- The diagnostic builder has optional `--protocol-diagnostics` for loaded game
  dumps and native encryption-input probes. The final installed baseline omits
  this flag. tools/disassemble_runtime.py follows ARM64 branches and annotates
  this build's native trampoline lookup using saved runtime tables.
- Six automated checks passed: fragmented/combined frames, malformed hello and
  login prefixes, frame bounds, real TCP hello/login-envelope capture, and
  rejecting a login that skips hello. Native encryption is still unresolved;
  the captured inputs have not matched a standard Python crypto implementation.
- Wireless streamed base updates stalled during research. Restarting the PC ADB
  daemon restored the existing pairing. The runner now uses --no-streaming for
  test-client-only base updates; the final installation and cold launch succeeded.
- The current base APK is `build/diagnostic-client/base.apk`, built with
  `python tools/build_diagnostic_client.py --debuggable --local-network`.
- It retains package `com.supercell.moco.localtest`, separate providers,
  allowBackup=false, and the original DEX/native/assets. Added classes3.dex
  contains DiagnosticFactory; Frida Gadget 17.23.3 runs the local bootstrap.
- Native loader package lookups were still hard-coded to com.supercell.moco.
  Redirecting those lookups to the test client fixed the initial JNI_ERR failure.
- The next native startup check reported code 0x16. A narrowly scoped getuid
  override at the loader classification call site (return address 0x2231bc)
  selects its isolated-process compatibility path. The real Android UID
  remains separate from the original app's UID.
- The no-INTERNET build subsequently failed in NativeHTTPConnection with an
  uncaught SecurityException and later in the native main loop. The current
  build restores network permission with loopback routing installed before
  the original component factory initializes. A per-process completion
  marker makes bootstrap failure stop startup.
- Observed native game connection: libg.so, original TCP port 30000, routed
  to tablet 127.0.0.1:9339 and forwarded to the PC via ADB reverse. Other IP
  connections are routed to local SDK port 9340; DNS inputs become loopback.
- `tools/run_local_test.py` automates the existing paired tablet, partial
  test-client-only base update, local listeners, ADB reverse, and optional launch.
  Its parser handles the spaces in the tablet's mDNS serial.
- server.py saves raw bytes and frame metadata; protocol.py handles TCP
  fragmentation and combined frames. Six fragmentation patterns and partial
  headers were checked against the real captured message.
- The changed diagnostic base passed package/provider/signature/alignment
  checks and preserved hashes of 1,457 original payload entries. The other
  four splits were already verified, including all 39,950 asset-pack entries.

## Evidence
- Verified hello/login exchange without protocol probes:
  captures/game/20261012T180051Z-176bfeee.bin, .server.bin, and .json
- Earlier reproduced exchanges: captures/game/20261012T174140Z-d8a1fe9f.bin
  and captures/game/20261012T174247Z-69ad84cc.bin
- Detailed handshake research and remaining crypto questions:
  analysis/handshake-research.md; plaintext prefix summary:
  analysis/login-prefix-summary.json
- First raw game packet: captures/game/20261012T170533Z-22f90ec6.bin
- Reproduced decoded packet: captures/game/20261012T172050Z-ae42232f.bin
- Native route log: analysis/local-connection-evidence.txt
- Diagnostic APK validation: analysis/diagnostic-build-verification.json
- Earlier failure/fix logs: analysis/package-lookup-fix-log.txt and
  analysis/loader-compatibility-log.txt
- Decrypted loader segments and selected check code: analysis/runtime/

## Approaches already investigated
Ordinary hooks in protected native code triggered failures/restarts; the
function checks its own instructions. Hardware breakpoints could not attach
on this tablet. Stalker tracing left the loader waiting and was removed.
Neither approach is part of the working baseline. An ADB host stall during
repeat testing was resolved by restarting our PC ADB server; the existing
wireless pairing reconnected automatically without a new pairing code.

## Confirmed scope
Connect the original mo.co Android client to a local Python server first,
then build out the protocol and eventually gameplay. The user will use an
Android tablet with wireless debugging enabled for testing (corrected from
earlier dictation).

## Isolation requirement
The experimental Android package ID will be `com.supercell.moco.localtest`,
installed alongside the original `com.supercell.moco`. This ID has now
been applied to all five rebuilt tablet splits. Preserve the original app
and its data.
Use a separate local-server identity when login is implemented; package
renaming alone does not isolate production account progress.

## Wireless device connection
ADB subsequently confirmed an authorized wireless connection to the user's
tablet. Device identifiers are kept in ignored local evidence. No new pairing was
needed. The earlier empty device list was a snapshot, not proof that the
tablet required pairing. Recheck `adb devices -l` before requesting pairing.

## Findings
- The supplied APKM metadata identifies `com.supercell.moco`, version 13.5.1,
  version code 13000501, ARM64 and ARMv7, Android API 29 minimum.
- Archive.zip holds another copy of the APKM; it was not extracted.
- The APKM includes base.apk, architecture/resource splits, and a large
  install-time asset pack. The inspector skips the asset pack.
- ARM64 libraries include libg.so and libsupercell_moco.so, plus Flutter,
  Supercell ID, audio, and supporting libraries.
- Selected ARM64 libraries were extracted to analysis/lib/arm64-v8a/.
- ASCII string scanning found socket/connect strings in libg.so but no clear
  game endpoint, ClientHello, ServerHello, or LoginMessage string in either
  inspected library. This does not establish how the client connects.
- Full inventory and matched offsets: analysis/package_report.json.
- Python and Android platform-tools/build-tools are available. The tablet
  connection was verified after locating adb; see Wireless device connection.
- An ELF section inspection found sample entropy approximately 8.0 bits/byte
  in libsupercell_moco.so's .text section. This suggests packed/encrypted code,
  but does not identify the protection scheme or network implementation.

## Implementation and verification
- All five offline splits were installed successfully over wireless ADB.
  Android assigned a separate UID and data directory
  `/data/user/0/com.supercell.moco.localtest`.
  Original version and installation/update timestamps were unchanged.
- The first offline launch failed before gameplay: libsupercell_moco.so's
  JNI_OnLoad returned JNI_ERR. PID-filtered evidence is saved in
  analysis/offline-startup-log.txt and analysis/offline-crash-log.txt.
  The log also reports `Bad JNI version passed to GetEnv: -1`.
  The precise cause is not yet established; do not call it a confirmed
  signature check, package-name check, or server failure.
- Static disassembly located JNI_OnLoad at virtual/file address 0x6942e8,
  size 216 bytes. It dispatches through an indirect function pointer and
  has a null-pointer path returning -1. The actual runtime pointer value
  and reason for failed initialization are not established. Evidence:
  analysis/jni-onload-disassembly.txt. Capstone 5.0.9 and pyelftools 0.33
  are installed locally under .tools/python for further inspection.
- The test package was force-stopped after the offline startup test. No
  original-app data was cleared, original app was not replaced, and no
  production account login or production network experiment was performed.
- Static smali inspection established that ixhhs.l.c() loads supercell_moco;
  ixhhs.D.a(int) is native and resolves protected strings. The startup path
  reaches this loader via CoreComponentFactory before application creation.
  Evidence summary: analysis/startup-findings.md.
- tools/build_test_client.py patches compiled manifests and resource-table
  package names without recompiling DEX, native code, or assets. Outputs have
  separate package/provider/custom-permission names and a local signing key.
- The offline build has no INTERNET permission, allowBackup=false, and label
  mo.co Local Test (Offline). Network access must be deliberately restored
  only once local routing has been established.
- tools/verify_test_client.py validated all five splits: package identity,
  base manifest isolation, identical signer, 16 KiB native library alignment,
  and preserved payload hashes, including 39,950 entries in the asset pack.
- Python ZIP writing initially introduced ZIP64 above 2 GiB, incompatible
  with zipalign. The builder uses the classic ZIP 4 GiB offset limit for
  this asset split (~3.8 GB); rebuilding and alignment then succeeded.
- Apktool 3.0.3 was downloaded from its official GitHub release into .tools
  for manifest inspection. Full base resource decoding showed unresolved
  split resources; that decoded output is not used to build the test client.
- tools/inspect_package.py performs reproducible offline inventory and a
  targeted native string scan; ran successfully on the supplied APKM.
- The initial server.py was a raw TCP capture listener with per-session binary
  and JSON output. Framing and the first hello response were subsequently added;
  see Current implementation for the current behavior.
- A loopback smoke test sent 26 bytes, verified exact saved bytes and byte
  count, and verified peer close. Test captures were temporary.
- Port 9339 began as provisional. The native game port was subsequently
  observed as 30000 and is routed to local test listener 9339.
- The Android client has now connected twice; see Verified result. No login
  or gameplay is implemented.

## Next steps
Encrypted login, guest persistence, compatible success replies, reconnects, and
session keepalives are complete. Continue the approved minimum home/profile
stage using the active investigation at the top of this file. Historical
observations above describe earlier milestones, not current blockers.
