# Project status — 2026-10-13

## Portal rendering and idle-close checkpoint
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
