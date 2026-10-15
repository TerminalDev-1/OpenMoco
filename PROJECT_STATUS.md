# Project status — 2026-10-15

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
restarted). It stopped because the tablet was switched to Settings; the
required 10-cycle soak is not complete, so no APK release yet. The soak used a
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
