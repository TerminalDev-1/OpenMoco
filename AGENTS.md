# mo.co Python server project

## Terminology
OpenMoco is a private server. Always call the project a private server and the Android application a test client or private-server client. Never use "clone" to describe this project or its client. This user preference applies to all future explanations, code comments, documentation, and release notes.

## Goal and agreed scope
The user wants to reverse-engineer the supplied mo.co 13.5.1 Android client and implement a local Python server. They confirmed that the first milestone is connecting the original Android client to that server. A standalone Python game is not the current objective.
The user will test the client on an Android tablet with wireless debugging enabled, not an emulator. Dictation initially described this as a phone and debugging disabled; the user corrected both.

## Test-client isolation
- Use `com.supercell.moco.localtest` as the separate Android application/package ID for the experimental client. It has been applied to the five tablet splits; see PROJECT_STATUS.md for installation/runtime status.
- The initial offline test build removes INTERNET permission and disables backup. Restore network permission only after implementing local routing; the offline build cannot connect to the server as-is.
- Install alongside `com.supercell.moco`; never replace, uninstall, clear data for, or modify the user's original mo.co installation.
- The test build must have separate local data, and any login implementation must use a separate local-server identity. Changing the Android package ID alone does not isolate production account progress.
- Do not sign the experimental client into the user's real Supercell account or launch it against production for testing. Establish local routing before running it.
- All APK splits must have consistent package identity and signing; inspect provider authorities and other package-dependent configuration for conflicts before installation.

## First milestone
Inspect the package, identify the client transport and connection configuration, and implement the smallest server needed for an initial connection. Add login and gameplay only after the connection path is understood. Distinguish a socket connection, a valid protocol handshake, authentication, and gameplay; never claim one proves another.

## Verified baseline
Encrypted local login is verified on the tablet using a newly generated local server key pair. The bootstrap decodes/re-encodes this build's obfuscated peer-public-key table; the server uses Curve25519/XSalsa20-Poly1305 NaCl Box with BLAKE2b-24(client public key + server public key). The earlier mismatch was an incomplete interpretation of native inputs, not evidence of a custom cipher. `--login` verifies the challenge, validates local guest credentials, sends 29125/version 1, and handles authenticated SecretBox keepalives. The native success handler completes. Home state and gameplay are still pending.
- Use `tools/create_server_key.py`; keep private key JSON under ignored `.local/`. The runner provisions only the public key into the debuggable test client and cold-launches it for `--login` tests. Do not publish private keys or decrypted login captures.
- The public v0.2.0-local-login APK supports runtime public-key provisioning and verified local guest login with probes disabled. The older v0.1.0-hello APK predates that feature. Continue publishing verified client updates when needed; research builds with protocol probes enabled must not be published.

The connection milestone and first hello exchange are achieved. The renamed Android client sends an 83-byte initial message, type 10100, version 0, payload length 76. With `--handshake`, the Python server replies with 20100/version 0 containing a length-prefixed 24-byte random challenge. The tablet accepts it and sends 10101/version 9. This was reproduced across cold launches, including with native protocol probes disabled. Use `--login` for the now-verified encrypted local login and session; home data and gameplay remain unimplemented.
- Use the diagnostic base APK built with `--local-network` alongside the four preserved offline splits. The original app remains installed separately.
- The native game connection was observed on port 30000; the bootstrap routes it to tablet loopback port 9339, forwarded to the PC by ADB reverse.
- The local-network build restores INTERNET permission only together with bootstrap routing. DNS resolves to loopback; IP connect/send operations are redirected to local test ports. SDK traffic uses local port 9340.
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
128..255; SQLite profiles and tokens belong only to this server. Older research
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
- The user explicitly instructed us to publish the experimental Android APK publicly and record this requirement. Publish the verified local-test client as GitHub Release assets, including its required matching splits, checksums, and installation instructions. This supersedes the earlier future-possibility wording; no repeat confirmation is needed for this authorized publication.
- The first APK pre-release is public: https://github.com/TerminalDev-1/OpenMoco/releases/tag/v0.1.0-hello. It contains the base APK, three configuration APKs, four asset-pack parts, and four verification/instruction files. All 12 GitHub asset SHA-256 digests matched the local files before publication.
- The updated local-login pre-release is public: https://github.com/TerminalDev-1/OpenMoco/releases/tag/v0.2.0-local-login. Source commit 6467451; 12 remote asset names/sizes/digests verified, full split verification and reassembly passed, and probe-free tablet login/keepalives reproduced. Home data and gameplay remain incomplete.
- The apartment pre-release is public: https://github.com/TerminalDev-1/OpenMoco/releases/tag/v0.3.0-apartment. Source checkpoint 6f0b117; all 12 remote asset names/sizes/SHA-256 digests matched, five-split verification and reassembly passed, and the normal client visibly rendered the Python-supplied player inside the apartment. All research probes are disabled. Use --login --apartment. Portal rendering/travel, tutorial persistence, and authoritative simulation remain unfinished.
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
The corrected typed Home references allow native scene-start handler completion, but the default frame crashes during copying at libg+0x725714 because primary+0xd8 has no handler. This is not a usable home. Type 1240 is an evidenced OpenWorld handler candidate awaiting verification. Keep experimental scene bodies opt-in and do not run fixture-generation probes concurrently with real scene startup. See the active section at the top of PROJECT_STATUS.md before interpreting historical entries.

## Manual testing and onboarding checkpoint
The user explicitly requires leaving the server running while they test. Use
a hidden background process with file-backed logs, and keep its current PID,
command line, mode, and paths in PROJECT_STATUS.md/.local/user-test-server.json.
Do not stop the manual server, reinstall, or cold-launch the test client merely
to continue research while the user is testing. Check listener and actual client
traffic separately: a client can time out while the listener is still running.
Onboarding and "Let's Go" are now observed, but subsequent responses/gameplay
are unfinished. home.py's 156-byte starter profile encoder has golden validation;
its authenticated-account integration now binds the known starter fixture to
the validated local guest ID. Current research fixtures are
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
Connection tracing is research-only (`--connection-diagnostics`), disabled
by default, and blocked from release packaging alongside protocol probes.
Verify real tablet traffic beyond the previous disconnect interval before
claiming the problem fixed. Leave the hidden background listener running.

## Apartment continuation
Latest portal checkpoint: Python now sends the native-derived 521-byte apartment
with HomeItem 2010, type Portal (2), prefab sc3d/pf_keyitem_portal at the map's
portal marker. A normal client visibly rendered it and requested destination
10900001 via 13222/v0. Destination initialization is still under investigation;
the first tutorial frame crashes, so do not claim travel or combat complete.
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

The user confirmed that the apartment and client audio work, while the portal
itself is missing (the apartment opening/backdrop renders). Do not list audio
as a defect. They requested publishing this apartment checkpoint and its APK.
Continue recording incomplete portal rendering/travel, tutorial persistence,
and authoritative simulation accurately. Use `--login --apartment` for the
normal client/server path; inspect the latest PROJECT_STATUS.md verification.

The user requested a tablet screenshot and investigation of the remaining
animations, cutscenes, portal interaction, and apartment movement. The current
apartment renders but has no visible player, bow, or portal. Client tutorial
commands reach GoToPortal; do not confuse dialogue progress with a playable
scene. Read docs/APARTMENT_PROTOCOL.md for the verified sequence, command
layouts, native player/character schemas, and ordered implementation work.
commands.py is a decoder only; it does not execute or persist commands.
Preserve the working background session while researching. The next concrete
implementation milestone is a correctly linked local player and character in
the scene frame, verified visibly on the tablet before movement or portal work.
