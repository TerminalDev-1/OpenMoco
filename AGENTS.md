# mo.co Python server project

## Terminology
OpenMoco is a private server. Always call the project a private server and the Android application a test client or private-server client. Never use "clone" to describe this project or its client. This user preference applies to all future explanations, code comments, documentation, and release notes.

## Battle stability (resolved 2026-10-14)
Two Codex client hooks broke battle play; both are removed. Do not restore them:
- Encounter cap (5bf784 enemy-vector compaction + 752514 spawn-batch writes)
  crashed on joystick input; it shrank a native actor vector without
  unregistering the omitted actors.
- Forcing the tutorial loot-disabled setting 6c2894 to false (globally or only
  at the 705d98 XP call) froze Mainloop at 100% CPU after warm battle reentry.
  It froze in 3 of 3 runs; v0.6.0 and the bridge without it passed 10 cycles.
Verify stability with repeated leave-battle/portal-reentry cycles plus combat,
not brief movement. The user set the release bar on 2026-10-15: more than 4
clean cycles is a pass (no need to complete 10). Still report any crash seen. Frida Process.enumerateThreads() returns no threads in this
client, and a tgkill signal sampler crashed it: do not reuse those probes.
Never leave a diagnostic or failed probe build installed for manual play, and
never publish one. A caught native abort does not mean the client can continue.
Latest client: v0.12.0-one-connection (pre-release, target 22c48e2, base
cc2d77f9..., kill reports on the game connection, no 9340 bridge; six assets
verified remotely; the tablet runs this exact base),
https://github.com/TerminalDev-1/OpenMoco/releases/tag/v0.12.0-one-connection.
Before it: v0.11.0-battle-jobs (target 6c644f1, base c1a3727b...,
in-battle jobs tracker),
https://github.com/TerminalDev-1/OpenMoco/releases/tag/v0.11.0-battle-jobs.
Before that: v0.10.0-server-xp (target 6ce3a68, base
876b08de...), https://github.com/TerminalDev-1/OpenMoco/releases/tag/v0.10.0-server-xp
(raw kill reports only; server XP via native event 1217); six assets passed
remote size/SHA-256 checks and the tablet runs this exact base. Before it:
v0.9.0-character-editor (target 1c9dc70, base 61c11c9b...). Previous: v0.8.0-xp-bar
(target 5755bbe, base e950a79a...). Seven unchanged splits/parts stay
linked from v0.3.0-apartment. Its Leave Battle SIGSEGV (own-home handler) was a
server encoding bug, fixed in home.py on 2026-10-15 with no client change: the
native reader has no bounds checks, so own-home field counts must be exact.
Verify new own-home fields with a native stream-offset probe (PROJECT_STATUS.md).
The previous fixed client is published as v0.7.0-kill-xp (pre-release, target 2fcc986):
https://github.com/TerminalDev-1/OpenMoco/releases/tag/v0.7.0-kill-xp
Six assets passed remote size/SHA-256 checks; the seven unchanged splits/parts
stay linked from v0.3.0-apartment. The tablet runs this exact base (c57e756f).

## Current progression work
The user approved a client-reporting bridge. The user then chose kill-based XP
(2026-10-14) because collected XP needed the freezing 6c2894 override. Python
credits XP per newly reported kill from the native loot profiles: Weak 2,
WeakMedium 4, Strong 10 (loot XP / 1000). This is an approximation: daily-budget
multipliers, level adjustment and randomized rounding are not reproduced, and
counts are trusted client reports. Client-collected XP is recorded per battle
epoch for comparison only. The in-game XP bar is not updated by server XP yet.
Python journals outcomes by authenticated battle epoch with cumulative
high-water marks. Combat remains simulated by the client.
Update 2026-10-15: the user asked for tutorial completion once the tutorial
objectives are earned. The server now sends Intro_3 quests in own-home and,
on Leave Battle with 50 kills and 3 rescues, advances Portal to ClaimQuests.
The native client then finishes the Portal tutorial and starts character
creation (verified on the tablet). Never advance it without the earned
objectives. Editing battle-snapshot bytes makes the client quit; don't retry.
The in-battle XP bar now fills: the bridge installs the server's (provisional)
XP level table and adds server battle XP to the HUD XP getter. The old freeze
was the client's empty level table, not the 6c2894 override itself; keep a
non-empty, all-positive table before any XP can become positive. Read the
latest status section.
The server code was refactored for readability (GameSession class); the user
wants existing logic kept, not rewritten.
Update 2026-10-15 (evening): the character editor lists faces/hairstyles from
server-granted pool-0 vanity items (client-home +0xe0) and command 543 picks
persist in the current build; the bridge writes native XP memory only on
Mainloop for the live battle (verified with 6+7 clean soak cycles). The
apartment badge now shows the saved-XP level (server-only, verified
2026-10-15): own-home sends the avatar +0x40 player-level track and its
client-home +0xe8 XP record, and the apartment snapshot's metadata level is
set from XP. No bridge write is needed at home. Never press READY in the
editor for the user.
Update 2026-10-15 (night): the hunter-name SIGN screen works (verified on the
tablet). The popup only closes through client command 14, which the server
cannot send, so Python saves the name and reloads home like Leave Battle with
the own-home name-set flag. See PROJECT_STATUS.md before changing it.

Update 2026-10-16: the portal works server-side. The season track's +0x28 is
the season's remaining seconds (rolling 28-day local seasons, provisional).
Portal map cards are avatar +0x48 slots; only state 1 (opens <= now < ends)
reacts to presses, and TutorialArea is refused by the start check, so the
card is Shrine Canyon (10900006). Its scene (scene.canyon_scene, verified
2026-10-16) spawns the player at the map's tag-17 marker (63,99) and sends
one native Zone per map monster zone; the client keeps them populated.
Canyon kills are not credited yet (client bridge allowlist). The apartment now
includes a native-encoded wardrobe HomeItem (type 1); its WARDROBE screen
opens. With map slots present the client auto-advances the portal-set
tutorial quests and can reach ToHQ (COOL zone, unserved): see
PROJECT_STATUS.md before changing key 70, portal sets or 591 handling.

Update 2026-10-16 (combat authority research): battles are a deterministic
rollback simulation verified by server frame checksums (28854); the server
never sends hits, health or deaths. Server-decided combat therefore needs a
bit-exact port of the native battle logic matched against client checksums;
the user parked that port. Do not send 28853/28854 or inject other logic
events without reading docs/BATTLE_PROTOCOL.md first.
Update 2026-10-16 (user decision, verified): the client bridge reports only
raw kill counts (any character ID); the server validates them per scene,
caps them by battle time, prices them from the loot tables, saves them and
sends the XP to the battle as native XP event 1217 (28852). Shrine Canyon
kills now earn XP. Keep the XP level table install in the client.
Update 2026-10-16 (user request: rewards stay server side; weapons, shop and
COOL zone): the apartment has the native weapons rack, the WEAPONS screen lists
the server-owned starter bow (client-home +0x78), and the COOL zone (SocialHub)
is served as home once ToHQ is reached, with its shop, portal, wardrobe,
weapons and cores items. Shop offers, jobs, quests and chaos cores are next;
see the newest PROJECT_STATUS.md sections.
Update 2026-10-17 (battle end): Leave Battle in Shrine Canyon gets the
battle-end summary 23200 (battle_end.py); EXIT sends 13223 body 01, which
then goes home. Update 2026-10-18: the user had chaos cores removed ("they
don't exist anymore"); the summary has no drops and shows the equipped look.
Never send the generic reward kinds there: they crash after a battle
(0x4de43c). See PROJECT_STATUS.md.

Update 2026-10-18 (user request: one connection): battle_bridge.py and the
loopback HTTP bridge on port 9340 are gone. The client bridge sends its raw
kill counts on the game connection inside the client's own desync-report
message 18855 (native sender 0x5c3654, zlib JSON {"openmoco":"kills"}); the
game session credits them (battle_progress.py, same rules) and appends the
display data (jobs, base XP, levels) as a trailer to its 28852 XP events,
which the bridge reads at the 0x761770 decoder. Verified on the tablet with
6 canyon entries / 5 warm cycles on one process. Don't reintroduce a second
connection. See PROJECT_STATUS.md.
Update 2026-10-18: the battle-start configuration (0x761c60) is mapped and
filled by the server for Shrine Canyon: XP before the battle and the XP level
table (+0/+8, the in-battle XP bar now fills), the portal slot in the
selection, and today's jobs (+0x20, the in-battle jobs tracker). The bridge
writes the server's job progress into those quests (the tracker's own kill
count reads a frame copy that never sees kills). Map slot +0x38 text titles
the portal card ("SHRINE CANYON"). XP drop orbs: the loot gate is open
outside TutorialAreaBasic; the player's native XP budget (+0x190) is 0, so
its drops are 0 XP. Enabling orbs is a pending user decision.
Update 2026-10-18: the top XP bar shown on the battle-end summary is native
behaviour, not a bug. The bar ([[0xfad818]+0x70]) stays under allow-listed
popup types (0x57fa7c), and the summary's type 0x3f9 is on that list. The user
chose to keep it; don't hide it. See PROJECT_STATUS.md.

Update 2026-10-18 (user request: no adb to play, several connections): the
test client can be built with --server-host <PC home-network IPv4> and then
connects over Wi-Fi; the server's --lan mode binds 0.0.0.0:9339 and refuses
non-home-network peers; each device has its own guest account. Verified on the
tablet with wireless debugging off (6 battles, one process). Home-network
builds contain the user's address and server key: never publish or commit
them, and keep the PC's address out of committed docs. Public releases keep
the loopback/adb default. See docs/HOME_NETWORK.md and PROJECT_STATUS.md.

## Current scene-transition priority
The verified reconnect/background-resume APK is published as v0.6.0-reconnect:
https://github.com/TerminalDev-1/OpenMoco/releases/tag/v0.6.0-reconnect.
Source bed4164; six new asset digests/sizes and seven linked unchanged split/part
dependencies are verified. The current tablet has this normal client installed.
Warm reconnect was also repaired in the client routing hook: preserve native
errno with SystemFunction and callback this.errno for connect/sendto. Android's
nonblocking connect returns EINPROGRESS (115); the previous hook could lose it
and immediately close a zero-byte connection. A same-process foreground resume
now completes saved-account login without restarting the app or server. Verify
actual encrypted login/frame traffic, not only Get-NetTCPConnection. Leave the
manual server running; see latest PROJECT_STATUS.md for logs and current PIDs.
Background resume can stall prediction after the client reports a new frame
but before its next clock poll. Acknowledge every valid current-scene 18853
through 28851, and reset simulation time at loaded notification 13224.
The isolated 13.5.1 client also skips only the prediction-gap timeout at
0x60e7fc after verifying 0x540003ad. Its parent otherwise sets simulation
+0x2944 on resume before acknowledgements arrive, freezing actors even with
idle-close suppressed. Ordinary socket errors/reconnect must remain enabled.
Repair both warm return-home and the frozen/T-posed battle player before further
progression work. Do not claim a scene is playable from a socket or screenshot
alone: verify joystick movement in battle and apartment over repeated travel.
Static scene snapshots start at frame zero; reset the simulation clock on each
scene, ignore old ready reports until empty 13224/v0, and acknowledge the first
new ready frame without waiting for another clock request. Return-home sends
own-home first and waits for the actual flagged 13222 selection 10900005 before
the apartment. This restricted mapping does not implement COOL-zone unlocks.
A one-second delay was inconsistent; omitting own-home crashed. Do not restore
those failed experiments or reset tutorial/account progress to hide this bug.
Read the latest PROJECT_STATUS.md and keep the hidden manual server running.

## Goal and agreed scope
OpenMoco is a mo.co private server written in Python. The goal is to fully
reimplement mo.co's server in Python, aiming for 100% feature coverage:
accounts, worlds, combat, progression, inventory, multiplayer, and all other
server behavior needed by the Android client. The supplied 13.5.1 client is the
current compatibility target. Connecting it was the first milestone, not the
limit of the project. This is an implementation project, not a research project.
Describe the project this way in documentation, repository metadata, releases,
and conversation. Use plain, approachable wording. Keep incomplete features
clearly marked; 100% is the goal, not a claim about today's implementation.
The user will test the client on an Android tablet with wireless debugging enabled, not an emulator. Dictation initially described this as a phone and debugging disabled; the user corrected both.

## Test-client isolation
- Use `com.supercell.moco.localtest` as the separate Android application/package ID for the private-server client. It has been applied to the five tablet splits; see PROJECT_STATUS.md for installation/runtime status.
- The initial offline test build removes INTERNET permission and disables backup. Restore network permission only after implementing local routing; the offline build cannot connect to the server as-is.
- Install alongside `com.supercell.moco`; never replace, uninstall, clear data for, or modify the user's original mo.co installation.
- The test build must have separate local data, and any login implementation must use a separate local-server identity. Changing the Android package ID alone does not isolate production account progress.
- Do not sign the private-server client into the user's real Supercell account or launch it against production for testing. Establish local routing before running it.
- All APK splits must have consistent package identity and signing; inspect provider authorities and other package-dependent configuration for conflicts before installation.

## First milestone
Inspect the package, identify the client transport and connection configuration, and implement the smallest server needed for an initial connection. Add login and gameplay only after the connection path is understood. Distinguish a socket connection, a valid protocol handshake, authentication, and gameplay; never claim one proves another.

## Verified baseline
Encrypted local login is verified on the tablet using a newly generated local server key pair. The bootstrap decodes/re-encodes this build's obfuscated peer-public-key table; the server uses Curve25519/XSalsa20-Poly1305 NaCl Box with BLAKE2b-24(client public key + server public key). The earlier mismatch was an incomplete interpretation of native inputs, not evidence of a custom cipher. `--login` verifies the challenge, validates local guest credentials, sends 29125/version 1, and handles authenticated SecretBox keepalives. The native success handler completes. The starter home, apartment and portal destination are verified; full gameplay remains unfinished.
- Use `tools/create_server_key.py`; keep private key JSON under ignored `.local/`. The runner provisions only the public key into the debuggable test client and cold-launches it for `--login` tests. Do not publish private keys or decrypted login captures.
- The public v0.2.0-local-login APK supports runtime public-key provisioning and verified local guest login with probes disabled. The older v0.1.0-hello APK predates that feature. Continue publishing verified client updates when needed; diagnostic builds with protocol probes enabled must not be published.

The connection milestone and first hello exchange are achieved. The renamed Android client sends an 83-byte initial message, type 10100, version 0, payload length 76. With `--handshake`, the Python server replies with 20100/version 0 containing a length-prefixed 24-byte random challenge. The tablet accepts it and sends 10101/version 9. This was reproduced across cold launches, including with native protocol probes disabled. Use `--login` for the now-verified encrypted local login and session; home data and gameplay remain unimplemented.
- Use the diagnostic base APK built with `--local-network` alongside the four preserved offline splits. The original app remains installed separately.
- The native game connection was observed on port 30000; the bootstrap routes it to tablet loopback port 9339, forwarded to the PC by ADB reverse.
- The local-network build restores INTERNET permission only together with bootstrap routing. DNS resolves to loopback; IP connect/send operations are redirected to local test ports. SDK traffic is pointed at tablet loopback port 9340, where nothing listens (refused); the runner no longer forwards it.
- DiagnosticFactory refuses startup if the per-process bootstrap completion marker is missing.
- The bootstrap redirects the protection library's hard-coded package lookup to the test package and applies a narrowly scoped loader UID-classification compatibility override. It does not change the kernel UID or the original app's data.
- Native offsets are specific to the supplied 13.5.1 build. Do not reuse them for another version without inspecting it.
- `python tools/run_local_test.py --install --launch` updates only the test client base APK, starts capture/routing, and launches the test client. See README.md for prerequisites.
- Add `--handshake` to enable the verified initial server response. Capture-only mode remains the default. The received login envelope is not proof of authentication.
- Native protocol dumps and encryption-input probes require an explicit diagnostic build flag, `--protocol-diagnostics`. Those files contain private ephemeral test material and stay under ignored local directories. Normal test builds leave these probes disabled.
- The initial native login had account ID 0 and no token. The client now stores local credentials and reconnects to the private local account store. Never use them against production; package identity alone does not isolate an account.
- The user expects persistence through routine failures. Do not end at the first crash with only an investigation summary; continue diagnosis and concrete fixes within the authorized milestone.

## Documentation and completed work
- This file preserves the agreed scope, ongoing instructions, verified baseline, and publication intent. PROJECT_STATUS.md records detailed findings, failures, fixes, validation results, evidence paths, and next steps. README.md documents reproducible build and run commands. Read all three when resuming work.
- Completed work includes package inspection; building and validating five independently signed, renamed tablet splits; installing the test client alongside the original; diagnosing native loader and no-INTERNET startup failures; adding the guarded local-network bootstrap; automating tablet routing and launch; and implementing the Python capture server and incremental frame decoder.
- The connection was verified on two cold launches, with the second capture decoded. Original payload hashes, package/provider configuration, signing, alignment, and the original installation's version/timestamps were checked. Test listeners and reverse mappings were stopped afterward; the test client remains installed.
- Keep both this summary and PROJECT_STATUS.md current after material changes. Record unsuccessful approaches and remaining unknowns in PROJECT_STATUS.md so future sessions do not repeat them.
- The user requested a running server for manual testing. Leave that session running unless asked to stop it; recheck process details and logs listed in PROJECT_STATUS.md. A session idle timeout closes that socket, not the listener.

## Remaining implementation choices
Current verified progress: type 29125/version 1 is accepted by the tablet's
native login-success handler with a separate local account and token. It
completes the handler and exchanges authenticated SecretBox keepalives.
Reconnect-token validation is verified on real cold launches. Home data and
gameplay remain absent; this is not a working home screen. The native player-tag
conversion requires the ID high word <=255. Use a persisted local namespace in
128..255; SQLite profiles and tokens belong only to this server. Older development
IDs are migrated with token-validated aliases, without clearing test client data.
See PROJECT_STATUS.md for failures and verification evidence.
The user has now approved all four next stages: encrypted transport, local guest accounts, compatible login replies, and minimum home/profile data. Work through their dependencies without requesting the same approval again:
1. Encrypted transport is verified: local keys, incoming login, initial reply, and session keepalives.
2. Minimal guest storage is implemented: separate local account ID, random reconnect token stored as a hash, local profile, and returning-token validation. No real Supercell identity is used.
3. Compatible success reply, reconnects, and encrypted keepalives are verified. Error-response layouts remain additional future work.
4. Minimal home/profile data: inspect what the client requires after login and serialize the smallest valid starter state. Scene-start 23491/v0, SceneConfig 1003, Frame 1200, and typed Home reference 10900000 are evidenced. The frame handler and player/profile contents remain under investigation; do not invent them.
5. Gameplay, progression, inventory changes, and multiplayer follow after the login/home path works. Their exact server schemas remain to be investigated.
Continue with minimum home data. Preserve the working login/session baseline while investigating the scene/player schema; do not claim a usable home until the tablet actually loads it.

## GitHub checkpoints and APK releases
- The user chose `OpenMoco`. The public source repository is https://github.com/TerminalDev-1/OpenMoco, with default branch `main` and local remote `origin` configured. Use this repository for future checkpoints.
- Commit and push a checkpoint after each successfully verified change. Use descriptive commit messages, include updated documentation, and report the checkpoint. Do not push failed or unverified work as a successful checkpoint.
- Verified partial results also count as checkpoints. The user explicitly
  includes partially rendered players, plants, buildings, and scenes with
  incomplete or black areas. Commit and push these useful intermediate results
  once the observed behavior is verified, label them as partial, and document
  defects and remaining work. A partial checkpoint does not mean a whole plan
  step is complete and is not a reason to end the turn. Continue implementation
  after pushing it; mark each full step complete only after its required checks.
- Before the initial public push and every later checkpoint, inspect the staged contents for the existing exclusions: private signing keys, device/account information, raw captures, extracted proprietary inputs, original archives, and generated builds. Stage intended source/documentation explicitly.
- The user explicitly instructed us to publish the private-server Android APK publicly and record this requirement. Publish the verified local-test client as GitHub Release assets, including its required matching splits, checksums, and installation instructions. This supersedes the earlier future-possibility wording; no repeat confirmation is needed for this authorized publication.
- The first APK pre-release is public: https://github.com/TerminalDev-1/OpenMoco/releases/tag/v0.1.0-hello. It contains the base APK, three configuration APKs, four asset-pack parts, and four verification/instruction files. All 12 GitHub asset SHA-256 digests matched the local files before publication.
- The updated local-login pre-release is public: https://github.com/TerminalDev-1/OpenMoco/releases/tag/v0.2.0-local-login. Source commit 6467451; 12 remote asset names/sizes/digests verified, full split verification and reassembly passed, and probe-free tablet login/keepalives reproduced. Home data and gameplay remain incomplete.
- The apartment pre-release is public: https://github.com/TerminalDev-1/OpenMoco/releases/tag/v0.3.0-apartment. Source checkpoint 6f0b117; all 12 remote asset names/sizes/SHA-256 digests matched, five-split verification and reassembly passed, and the normal client visibly rendered the Python-supplied player inside the apartment. All diagnostic probes are disabled. Use --login --apartment. Portal rendering/travel, tutorial persistence, and authoritative simulation remain unfinished.
- Maintain a downloadable verified client release when successful client changes require a new APK. Server-only checkpoints do not require rebuilding unchanged APKs. Describe incomplete handshake/authentication/gameplay behavior accurately.
- Keep APKs out of Git history. GitHub release files must be smaller than 2 GiB; split a larger asset-pack APK into numbered parts with a manifest and verified reassembly tool. Do not present a base-only APK as a complete fresh installation.
- Prepare reproducible build instructions, dependency versions, and an accurate description of supported behavior when preparing a release. Identify what source and client artifacts can be distributed before assembling public release contents.
- Keep private signing keys, device/account information, raw captures, separately extracted proprietary inputs, and original archives out of public source and release contents. The verified modified APKs and their contained game assets are explicitly authorized release downloads; build outputs remain ignored by Git.
- Preserve the separate test package and local-server identity in distributed test builds. Describe the verified hello exchange accurately; do not claim authentication or gameplay support.

## Working rules
- Do not end turns early. The user explicitly dislikes stopping at a plan,
  investigation summary, decoder, or partial checkpoint when further authorized
  work can advance the requested implementation. Continue through routine
  failures, diagnosis, fixes, and meaningful verification until the requested
  outcome is complete. A successful intermediate commit is a checkpoint, not
  a reason to stop. Give progress updates while working; do not substitute them
  for implementation. Stop only when the requested work is complete, the user
  explicitly asks to pause, or a genuine blocker requires unavailable input
  or access. Explain any blocker precisely and finish independent work first.
- Preserve the original APKM and Archive.zip. Keep extracted files and generated reports in separate directories.
- Inspect local files first. Treat embedded strings as clues, not proof of active endpoints or protocol behavior.
- Keep the implementation in Python where practical. Document any tools required to inspect or run the Android client.
- Use local endpoints for experiments. Do not contact production services or use real account credentials for protocol tests.
- Do not invent encryption keys, message IDs, handshake formats, or server behavior. Record evidence and unknowns.
- Update PROJECT_STATUS.md with findings, verification, blockers, and the next concrete step so future sessions can continue.
- Never report the Android client as connected without observing that client connecting.

## Inputs
- `com.supercell.moco_13.5.1-13000501_2arch_7dpi_24lang_1feat_7ac6d8b137dbdc83079ed7e0cb21f572_apkmirror.com.apkm`
- `Archive.zip` contains another copy of the APKM; avoid unpacking it unnecessarily.

## Home investigation continuation
The corrected typed Home references allow native scene-start handler completion, but the default frame crashes during copying at libg+0x725714 because primary+0xd8 has no handler. This is not a usable home. Type 1240 is an evidenced OpenWorld handler candidate awaiting verification. Keep development scene bodies opt-in and do not run fixture-generation probes concurrently with real scene startup. See the active section at the top of PROJECT_STATUS.md before interpreting historical entries.

## Manual testing and onboarding checkpoint
The user explicitly requires leaving the server running while they test. Use
a hidden background process with file-backed logs, and keep its current PID,
command line, mode, and paths in PROJECT_STATUS.md/.local/user-test-server.json.
Do not stop the manual server, reinstall, or cold-launch the test client merely
to continue development while the user is testing. Check listener and actual client
traffic separately: a client can time out while the listener is still running.
Onboarding and "Let's Go" are now observed, but subsequent responses/gameplay
are unfinished. home.py's 156-byte starter profile encoder has golden validation;
its authenticated-account integration now binds the known starter fixture to
the validated local guest ID. Current development fixtures are
isolated local data. See the latest status section before historical findings.

## Persistent test connections
The manual server must not close a session after 30 seconds of silence or
4 MiB of cumulative capture. Keep individual frame length validation.
The observed approximately 35-second disconnect came from the native client:
its current game frame exceeded the last server-confirmed frame limit
(0x60e7ec..0x60e860). Reply to game-clock 18851/v0 with 28851/v0 and advance
its raw confirmation integer from authenticated frame-ready 18853/v0.
Native evidence: 0x5c3320 queues event 3; 0x5c2c34 -> 0x610d78 updates
the confirmed frame monotonically. This acknowledges receipt for the current
onboarding experiment; it does not implement authoritative gameplay.
Do not guess a 28853 payload: the discarded four-integer candidate crashed.
Connection tracing is diagnostic-only (`--connection-diagnostics`), disabled
by default, and blocked from release packaging alongside protocol probes.
Verify real tablet traffic beyond the previous disconnect interval before
claiming the problem fixed. Leave the hidden background listener running.

## Apartment continuation
Terminology correction: RunningNpc 10800092 is a Spirit model, not a human
civilian. Preserve those spirits. Human tutorial civilians are 10800309..313
with pf_civilian_01..05, Civilian event type and health 1000. The user requested
varied recurring monsters, then earned progression/Luna's home prompt and the
COOL zone. Python now sends the encounter scene with spirits, human civilians,
five initial enemy types and native recurring zones. XP, main-quest execution,
Luna's completion prompt and COOL-zone access are still under investigation.
The user confirmed COOL zone is a separate area, not the wardrobe. Supplied
battle data identifies SocialHub 10900005 with w00_cool_zone_v2.json and
SocialHub_FTUE 10900309 with home.json. Do not fabricate completion to unlock it.
See docs/PROGRESSION_PROTOCOL.md for the native spawner schema, XP-field names
with unresolved owning-object binding, quest targets and COOL-zone route.
These implementation findings do not mean persistent XP or earned unlocks work.
Current continuation: the user requested abundant initialized monsters and
the civilians they attack after verifying all prior changes were committed.
Python's populated tutorial scene now has twelve enemies and six RunningNpc
civilians, with native gear/base health/factions and dynamic account binding.
51 tests and actual Python-scene decoding pass. Street placement is corrected;
hands-off native observation verifies civilian health decreasing under monster
attacks, and normal-client screenshots show Spirit civilians. This is an initial
population refreshed on entry/reconnect; continuous respawns, saved kills/rescues
and rewards remain unfinished. Read the latest PROJECT_STATUS.md. Keep
the old single-monster fixture as a regression baseline. Do not describe native
client simulation as Python-authoritative combat or persistent kill rewards.
The return-home APK checkpoint is published at
https://github.com/TerminalDev-1/OpenMoco/releases/tag/v0.5.0-return-home,
targeting 4d603a8. Six new assets and seven linked unchanged dependencies passed
remote digest/size checks. The installed normal base matches the release build;
all diagnostic probes are disabled. Keep the current manual server running.
Current requested work: implement the missing return-home HUD/path, monster
gameplay in Downtown Chaos, and persistent progress so reconnects do not replay
the intro/tutorial. Python now persists authenticated 574 tutorial transitions
and the last supported scene, restores home +0x118 raw reference pairs, and
resumes the saved scene. Tests pass; inspect latest status for tablet verification.
Normal-client reconnect now resumes saved scene/step without the completed intro.
Return home is verified through minimap -> Leave Battle, observed 13223/v0 body
00. Python responds with saved own-home plus apartment and saves scene 10900000.
The local-network map hook changes only the tutorial map-hide UI call site;
never mark tutorial completion just to expose controls. The user has now verified
that the first monster renders and can take damage, but flees quickly. The
650-byte initial snapshot includes native default gear and base health, with
two dynamically bound account references. Full server-authoritative combat,
enemy waves and rewards remain unfinished. The first regular-dragonling probe
did not verify improved behavior. Subsequent populated-street work now includes
eleven regular dragonlings and verifies monster damage against civilians; use
the latest populated scene rather than treating that first probe as the final state.
Use tools/recover_local_progress.py only with matching private local login/session
captures and an existing validated account; keep its SQLite backup private.
Do not mark an unfinished tutorial complete just to hide a UI problem.
Latest portal checkpoint: Python now sends the native-derived 521-byte apartment
with HomeItem 2010, type Portal (2), prefab sc3d/pf_keyitem_portal at the map's
portal marker. A normal client visibly rendered it and requested destination
10900001 via 13222/v0. Portal travel is verified: the normal client accepted
Python's 498-byte tutorial scene and entered Downtown Chaos on October 14, 2026.
The user explicitly confirmed the destination, and screenshots show the player,
bow, recruits and movement. Battle-start metadata must include the destination
selection; replace the apartment template's final 58 bytes, preserving its final
four bytes. Full authoritative combat and progression remain unfinished.
The local-network client suppresses only native auto-idle close 0x7fe3d8 after
checking this build's instruction signature. Forced invocation kept state 8 -> 8
and authenticated traffic continued. Real network loss is not suppressed.
Read the latest PROJECT_STATUS.md before the historical apartment notes below.
Authenticated 541 commands now persist only the native onboarding category in
the local profile and return home key 7 on reconnect. Native category is 3 below
default threshold 16, otherwise 2 (0x684e00..10). Do not reverse those categories
or invent the user's choice. Other tutorial/quest commands remain unpersisted.
The test client keeps its foreground activity's screen awake through lifecycle
callbacks. Keep all compiled DiagnosticFactory classes in the generated DEX.
Screen-off launches can show blackness with no game connection until the tablet
wakes/unlocks; inspect dumpsys power and focused window before changing protocol.
Native Sentry crash events may use extensionless filenames in cache/.../outbox.
Process.setExceptionHandler and broad hooks caused unrelated faults in this build;
prefer saved native crash records and narrowly scoped, verified probes.

The user confirmed that the apartment, client audio and portal travel work.
Do not list audio as a defect. They requested publishing the portal checkpoint
and its APK. Continue recording incomplete tutorial/quest persistence and
authoritative simulation accurately. Use `--login --apartment` for the
normal client/server path; inspect the latest PROJECT_STATUS.md verification.

The user requested a tablet screenshot and investigation of the remaining
animations, cutscenes, portal interaction, and apartment movement. The current
apartment now renders its player, bow and portal. Client tutorial
commands reach GoToPortal; do not confuse dialogue progress with a playable
scene. Read docs/APARTMENT_PROTOCOL.md for the verified sequence, command
layouts, native player/character schemas, and ordered implementation work.
commands.py decodes commands; the server persists authenticated age choice 541
and tutorial transition 574. Quest execution and inventory remain unfinished.
Preserve the working background session during development. The next concrete
implementation milestones for player placement and portal travel are verified.
Further gameplay work follows the latest PROJECT_STATUS.md rather than these
historical implementation notes. Publish requested APK checkpoints as GitHub releases.
