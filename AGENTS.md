# mo.co Python server project

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
The connection milestone and first hello exchange are achieved. The renamed Android client sends an 83-byte initial message, type 10100, version 0, payload length 76. With `--handshake`, the Python server replies with 20100/version 0 containing a length-prefixed 24-byte random challenge. The tablet accepts it and sends 10101/version 9 with 1,775 encrypted payload bytes. This was reproduced across cold launches, including with native protocol probes disabled. Full encrypted handshake, authentication, a login reply, and gameplay remain unimplemented.
- Use the diagnostic base APK built with `--local-network` alongside the four preserved offline splits. The original app remains installed separately.
- The native game connection was observed on port 30000; the bootstrap routes it to tablet loopback port 9339, forwarded to the PC by ADB reverse.
- The local-network build restores INTERNET permission only together with bootstrap routing. DNS resolves to loopback; IP connect/send operations are redirected to local test ports. SDK traffic uses local port 9340.
- DiagnosticFactory refuses startup if the per-process bootstrap completion marker is missing.
- The bootstrap redirects the protection library's hard-coded package lookup to the test package and applies a narrowly scoped loader UID-classification compatibility override. It does not change the kernel UID or the original app's data.
- Native offsets are specific to the supplied 13.5.1 build. Do not reuse them for another version without inspecting it.
- `python tools/run_local_test.py --install --launch` updates only the clone base APK, starts capture/routing, and launches the clone. See README.md for prerequisites.
- Add `--handshake` to enable the verified initial server response. Capture-only mode remains the default. The received login envelope is not proof of authentication.
- Native protocol dumps and encryption-input probes require an explicit diagnostic build flag, `--protocol-diagnostics`. Those files contain private ephemeral test material and stay under ignored local directories. Normal test builds leave these probes disabled.
- Native plaintext login inspection observed account ID 0 and no token. Continue to require a separate local-server identity when implementing authentication; no local account has been authenticated or assigned yet.
- The user expects persistence through routine failures. Do not end at the first crash with only an investigation summary; continue diagnosis and concrete fixes within the authorized milestone.

## Documentation and completed work
- This file preserves the agreed scope, ongoing instructions, verified baseline, and publication intent. PROJECT_STATUS.md records detailed findings, failures, fixes, validation results, evidence paths, and next steps. README.md documents reproducible build and run commands. Read all three when resuming work.
- Completed work includes package inspection; building and validating five independently signed, renamed tablet splits; installing the clone alongside the original; diagnosing native loader and no-INTERNET startup failures; adding the guarded local-network bootstrap; automating tablet routing and launch; and implementing the Python capture server and incremental frame decoder.
- The connection was verified on two cold launches, with the second capture decoded. Original payload hashes, package/provider configuration, signing, alignment, and the original installation's version/timestamps were checked. Test listeners and reverse mappings were stopped afterward; the clone remains installed.
- Keep both this summary and PROJECT_STATUS.md current after material changes. Record unsuccessful approaches and remaining unknowns in PROJECT_STATUS.md so future sessions do not repeat them.
- The user requested a running server for manual testing. Leave that session running unless asked to stop it; recheck process details and logs listed in PROJECT_STATUS.md. A session idle timeout closes that socket, not the listener.

## Remaining implementation choices
The user wants to choose the next implementation area. Explain dependencies before starting another area:
1. Complete encrypted transport: resolve native crypto, configure local server keys, decode login, and encrypt replies. This currently blocks a successful wire-level login.
2. Minimal local guest accounts: assign a separate account ID and random reconnect token, store the profile locally, and validate returning tokens. No real Supercell identity is needed for this milestone.
3. Compatible login reply and session handling: derive the success/error layouts from the client, support reconnects, and inspect required keepalive behavior.
4. Minimal home/profile data: inspect what the client requires after login and serialize the smallest valid starter state. The message ID and exact schema are not yet established; do not invent them.
5. Gameplay, progression, inventory changes, and multiplayer follow after the login/home path works. Their exact server schemas remain to be investigated.
Recommend encrypted transport first, then guest accounts and the login reply, then minimum home data. Account storage can be developed independently, but cannot make the current client authenticate until transport and reply compatibility are resolved.

## Possible GitHub and APK publication
- The user explicitly wants a public GitHub repository so they can view the code and checkpoints. They chose the exact name `OpenMoco`. Use the authenticated GitHub account for repository creation.
- Once the repository is created and its remote configured, commit and push a checkpoint after each successfully verified change. Use descriptive commit messages, include updated documentation, and report the checkpoint. Do not push failed or unverified work as a successful checkpoint.
- Before the initial public push and every later checkpoint, inspect the staged contents for the existing exclusions: private signing keys, device/account information, raw captures, extracted proprietary inputs, original archives, and generated builds. Stage intended source/documentation explicitly.
- The user wants the possibility of publishing a GitHub repository and the experimental Android APK documented. A future release may publish the repository together with the test-client APK, including any required split APKs and installation instructions.
- Public repository creation and source checkpoints are authorized under the chosen name `OpenMoco`. Publishing APK release assets remains a future possibility, not part of the repository-creation request. See PROJECT_STATUS.md for actual publication status.
- Prepare reproducible build instructions, dependency versions, and an accurate description of supported behavior when preparing a release. Identify what source and client artifacts can be distributed before assembling public release contents.
- Keep private signing keys, device/account information, raw captures, extracted proprietary inputs, and original archives out of public repository contents. Generated APKs are currently ignored by Git; any intended APK release must be prepared explicitly.
- Preserve the separate test package and local-server identity in distributed test builds. Describe the verified hello exchange accurately; do not claim authentication or gameplay support.

## Working rules
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
