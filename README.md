# OpenMoco

An experimental local Python server for the supplied mo.co 13.5.1 Android
client. The isolated test client connects, accepts the initial server hello,
and sends an encrypted login request. Login authentication, the rest of the
encrypted handshake, home data, and gameplay remain unimplemented.

The Git source tree contains research code and build tools. It does not contain
the original APKs, game assets, extracted libraries, private signing keys,
or device captures. Bring your own client input to reproduce the build.

The experimental local-test client and all required splits are being published
as [release downloads](https://github.com/TerminalDev-1/OpenMoco/releases).
See [installation instructions](docs/INSTALL.md). The large asset APK is split
into numbered download parts and reassembled with checksum verification.
Other projects' distribution approaches are recorded in
[related projects](docs/RELATED_PROJECTS.md).

Python 3.10+ is required; no third-party Python dependencies are needed.

## Inspect the supplied package
```powershell
python tools/inspect_package.py
```
The inspector saves a package inventory and native string offsets to
`analysis/package_report.json`, and extracts only the two relevant ARM64
libraries. Original archives are preserved. It does not unpack the large
asset pack. Strings are investigative clues, not verified runtime behavior.

## Run the capture listener
```powershell
python server.py
```
It defaults to `127.0.0.1:9339`. The observed native game TCP port is 30000;
the prepared clone routes it to 9339 through ADB reverse. Incoming
TCP bytes and session metadata are saved under `captures/`. Capture-only
mode sends no responses; `--handshake` enables the verified hello response.
Connections close
after 30 seconds idle or a 4 MiB capture limit.

For a device on the same LAN, explicitly bind an interface reachable by it:
```powershell
python server.py --host 0.0.0.0 --port 9339
```
Starting server.py alone does not configure tablet forwarding. Use
tools/run_local_test.py with the prepared local-network clone for the
verified connection setup. Current evidence is in PROJECT_STATUS.md.

## Separate offline Android test build
```powershell
python tools/build_test_client.py
python tools/verify_test_client.py
```
The builder targets ARM64, English, and xxhdpi splits plus the install-time
asset pack. It requires Android build-tools 35.0.0, platform android-35, and
Java/keytool on PATH. Set `ANDROID_SDK_ROOT` or `ANDROID_HOME` to your SDK,
or put its path in ignored `.local/android-sdk.txt`. ADB is discovered from
PATH or the SDK; the runner also accepts `--adb`. The resulting APKs live under
`build/offline-client/` and share a local signing key in `.local/`.

The package is `com.supercell.moco.localtest`, labeled
`mo.co Local Test (Offline)`. Provider authorities and the app's custom
permission have separate names. Backup is disabled, and INTERNET permission
is removed for initial inspection. It cannot connect to our server in this
offline form. Native game code, DEX, and game assets are preserved; original
archives are never changed. No real Supercell login is part of testing.

The builder does not install or launch apps. The verifier checks package
identity, permissions, provider authorities, split signatures, alignment,
and hashes of preserved payloads. Its report is saved in
`analysis/build-verification.json`.

Binary resource structures follow the
[AOSP ResourceTypes.h definitions](https://android.googlesource.com/platform/frameworks/base/+/refs/heads/main/libs/androidfw/include/androidfw/ResourceTypes.h).

## Working local-server client
The current installed test app uses the diagnostic base, labeled
`mo.co Local Test (Local Server)`. Its added factory loads Frida Gadget and
the local bootstrap before the original game initializes. The bootstrap
fixes a native package-identity lookup and a loader process-classification
check, then routes IP connections to local test ports. The original app and
its private data remain separate. Offsets are specific to this 13.5.1 build.

Build and validate the diagnostic base:
```powershell
python tools/build_diagnostic_client.py --debuggable --local-network
python tools/verify_test_client.py --diagnostic --base-only
```
The build requires the existing Android tools and `.tools/libgadget.so`
(official Frida Gadget 17.23.3 for Android ARM64). The debug flag enables
`run-as` access to the clone's diagnostic files and is optional for connection
testing. The local-network flag restores INTERNET permission with the
bootstrap's routing enabled. The factory refuses startup if that bootstrap
does not finish.

For the already installed clone and paired tablet, run:
```powershell
python tools/run_local_test.py --install --launch
```
This updates only the clone's base APK, forwards tablet port 9339 to the PC,
starts the game capture listener and a separate SDK sink on port 9340, and
launches the clone. Keep the tablet wirelessly connected. Stop the PC listener
with Ctrl+C. The source game's observed connection port is 30000; the bootstrap
maps that libg.so connection to local test port 9339.

For a fresh clone installation, install the diagnostic base together with
the four offline ARM64/English/xxhdpi/asset splits, all signed by the local
key. Partial installation requires the clone to exist already.

Protocol observations and runtime evidence are documented in PROJECT_STATUS.md.
The framing implementation is in protocol.py. Capture mode sends no responses.
To test the implemented initial hello exchange:
```powershell
python tools/run_local_test.py --handshake --launch
```
The tablet has accepted the 20100 response and sent an encrypted 10101 login
envelope. This verifies the first hello exchange; login authentication and a
login reply are still pending. Incoming `.bin` and outgoing `.server.bin`
captures and session metadata are saved under `captures/game/`.

Run the protocol and TCP integration checks with:
```powershell
python -m unittest discover -s tests -v
```

For native protocol research only, add `--protocol-diagnostics` when building
the diagnostic client. This enables build-specific memory dumps and probes
that save ephemeral encryption inputs inside the clone's private diagnostic
folder. Normal builds leave them disabled. These private files must stay out
of public releases. The passive ARM64 inspector is
`tools/disassemble_runtime.py`; it uses Capstone from `.tools/python`.
The bootstrap uses the official
[Frida Gadget script interaction](https://frida.re/docs/gadget/) to run locally
without a separate Frida server on the tablet.
