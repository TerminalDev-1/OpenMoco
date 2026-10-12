# Project status — 2026-10-12

## Approved next stages: current work
The user approved encrypted transport, local guest accounts, compatible login
replies, and minimum home/profile data. Incoming login encryption is now resolved.
Decoding the 13.5.1 obfuscated peer-public-key table reproduced the saved native
nonce and ciphertext exactly with standard BLAKE2b-24 and PyNaCl NaCl Box.
The previous mismatch came from overlooking native substitution of the peer
public key into the hash input; do not repeat the custom-cipher hypothesis.

A new local key pair is stored only in .local/server-key.json. The clone's
bootstrap validates and re-encodes its native public-key table before connect.
The runner provisions only the public key into clone-private storage. Real
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
The current live research process uses --login and a probe-enabled clone;
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

After the earlier automated verification the clone was force-stopped, PC test listeners were
stopped, and the two test ADB reverse mappings were removed. The cloned app
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
  wire data. The captured clone login has account ID 0, no token, version fields
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
  clone-only base updates; the final installation and cold launch succeeded.
- The current base APK is `build/diagnostic-client/base.apk`, built with
  `python tools/build_diagnostic_client.py --debuggable --local-network`.
- It retains package `com.supercell.moco.localtest`, separate providers,
  allowBackup=false, and the original DEX/native/assets. Added classes3.dex
  contains DiagnosticFactory; Frida Gadget 17.23.3 runs the local bootstrap.
- Native loader package lookups were still hard-coded to com.supercell.moco.
  Redirecting those lookups to the clone fixed the initial JNI_ERR failure.
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
  clone-only base update, local listeners, ADB reverse, and optional launch.
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
The user approved all four stages: encrypted transport, local guest accounts,
compatible login replies, and minimum home/profile data. Their dependencies
are recorded in AGENTS.md under Remaining implementation choices.
Minimum local guest-account persistence, compatible login replies, and the
client's required home/profile state are all still missing. The exact home
message schema has not been reverse-engineered. Continue through these stages
without waiting for another selection or repeat approval.

1. Resolve the login encryption algorithm, nonce construction, and embedded
   server-public-key configuration from native evidence. Standard PyNaCl and
   hashlib comparisons have not matched; do not assume compatible crypto yet.
2. Configure a newly generated local server key pair in the clone, implement
   verified login decryption and the evidenced server reply, and only then
   create/authenticate a separate local-server identity. Never use real credentials.
3. Keep all experiments on local endpoints and preserve the original app.

Do not infer successful reverse engineering from the Python loopback test.
