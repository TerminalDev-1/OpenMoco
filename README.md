# OpenMoco

An experimental local Python server for the supplied mo.co 13.5.1 Android
client. The isolated test client connects, completes an encrypted local guest
login, and exchanges encrypted keepalives and frame acknowledgements. A minimum
home profile initializes onboarding. The minimum apartment scene includes a
local player, character, head cosmetic, and starter bow at the map's spawn.
The apartment portal renders and takes the player into Downtown Chaos.
The user verified travel on the tablet. Tap the minimap, then **Leave Battle**
to return to the apartment. Age choices, reported tutorial steps and the last
scene persist across reconnects, so completed intro steps do not replay.
Downtown Chaos now starts with twelve initialized monsters and six civilians.
The client renders Spirit civilians and simulates movement and combat;
monster attacks reduce civilian health in the verified street encounter.
The initial population refreshes on entry/reconnect and can clear quickly.
Full quest progression, server-authoritative combat, sustained enemy waves
and rewards remain unfinished.

The Git source tree contains research code and build tools. It does not contain
the original APKs, game assets, extracted libraries, private signing keys,
or device captures. Bring your own client input to reproduce the build.

The experimental local-test client and all required splits are available as
[release downloads](https://github.com/TerminalDev-1/OpenMoco/releases/tag/v0.5.0-return-home).
See [installation instructions](docs/INSTALL.md). The return-home release contains
the updated base APK; fresh installations also need the unchanged configuration
splits and asset parts linked from the previous apartment release. The large asset APK is split
into numbered download parts and reassembled with checksum verification.
Other projects' distribution approaches are recorded in
[related projects](docs/RELATED_PROJECTS.md).

Python 3.10+ is required. Capture/hello mode uses the standard library;
local-key login decryption requires `python -m pip install -r requirements.txt`.

## Local-key login decryption (development client)

The development client can use your own server key pair. Generate the private
key locally, build the updated debuggable client, and install/test it:

```powershell
python -m pip install -r requirements.txt
python tools/create_server_key.py
python tools/build_diagnostic_client.py --debuggable --local-network
python tools/verify_test_client.py --diagnostic --base-only
python tools/run_local_test.py --install --login --launch
```

To test the minimum apartment with the normal client, add `--apartment`:

```powershell
python tools/run_local_test.py --login --apartment --launch
```

The server supplies the account-bound scene. No private scene fixture or native
apartment probe is required. The server responds to portal scene requests with a native-derived tutorial
frame. Authenticated age choices and tutorial transitions persist in SQLite.
Reconnect resumes the last supported scene and unfinished tutorial step. Keep
the local account database and server key; quest execution remains unfinished.

The private key stays in ignored `.local/server-key.json`. Only the public key
is provisioned into the test client through ADB. The bootstrap verifies the supplied
13.5.1 key layout and configures the native peer key before connection. Python
has verified and decrypted login on the tablet using this configuration.
The tablet's native login-success handler completed with a separate local ID.
Saved local tokens are accepted on reconnect. The starter home profile and portal destination are implemented.
The published v0.2.0-local-login APK includes this feature with probes disabled.
The older v0.1.0-hello APK supports only the hello milestone.
The optional builder `--server-key` flag can embed a public key as a fallback;
the runtime public-key file takes precedence. The bootstrap reads that file
through [Frida's File API](https://frida.re/docs/javascript-api/#file).

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
the prepared test client routes it to 9339 through ADB reverse. Incoming
TCP bytes and session metadata are saved under `captures/`. Capture-only
mode sends no responses; `--handshake` enables the verified hello response.
Connections close
when the peer disconnects; quiet manual sessions remain open without a cumulative capture cutoff.

For a device on the same LAN, explicitly bind an interface reachable by it:
```powershell
python server.py --host 0.0.0.0 --port 9339
```
Starting server.py alone does not configure tablet forwarding. Use
tools/run_local_test.py with the prepared local-network test client for the
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
`run-as` access to the test client's diagnostic files and is optional for connection
testing. The local-network flag restores INTERNET permission with the
bootstrap's routing enabled. The factory refuses startup if that bootstrap
does not finish.

For the already installed test client and paired tablet, run:
```powershell
python tools/run_local_test.py --install --launch
```
This updates only the test client's base APK, forwards tablet port 9339 to the PC,
starts the game capture listener and a separate SDK sink on port 9340, and
launches the test client. Keep the tablet wirelessly connected. Stop the PC listener
with Ctrl+C. The source game's observed connection port is 30000; the bootstrap
maps that libg.so connection to local test port 9339.

For a fresh test client installation, install the diagnostic base together with
the four offline ARM64/English/xxhdpi/asset splits, all signed by the local
key. Partial installation requires the test client to exist already.

Protocol observations and runtime evidence are documented in PROJECT_STATUS.md.
The framing implementation is in protocol.py. Capture mode sends no responses.
To test the implemented initial hello exchange:
```powershell
python tools/run_local_test.py --handshake --launch
```
The tablet has accepted the 20100 response and sent an encrypted 10101 login
envelope. This verifies the first hello exchange; the subsequent encrypted guest login is also implemented in `--login` mode. Incoming `.bin` and outgoing `.server.bin`
captures and session metadata are saved under `captures/game/`.

Run the protocol and TCP integration checks with:
```powershell
python -m unittest discover -s tests -v
```

For native protocol research only, add `--protocol-diagnostics` when building
the diagnostic client. This enables build-specific memory dumps and probes
that save ephemeral encryption inputs inside the test client's private diagnostic
folder. Normal builds leave them disabled. These private files must stay out
of public releases. The passive ARM64 inspector is
`tools/disassemble_runtime.py`; it uses Capstone from `.tools/python`.
The bootstrap uses the official
[Frida Gadget script interaction](https://frida.re/docs/gadget/) to run locally
without a separate Frida server on the tablet.
# Current login development

`--login` verifies the tablet's encrypted request, creates or validates a
separate guest in `.local/accounts.sqlite3`, and sends its encrypted login reply.
The client accepts it and sends encrypted keepalives. The starter home profile, apartment and portal destination are implemented.
Reconnect tokens are hashed in storage.

For transport research, add `--transport-probe` to `tools/run_local_test.py
--login --launch`. It sends an encrypted empty keepalive; the diagnostic build's
native Box verifier accepted it. This verifies reply encryption, not login.
Research probes must be disabled in published client builds.

The server keeps quiet connections open. The local-network client suppresses its automatic idle-close policy and keeps
the foreground activity screen awake. Physical network or ADB loss can still
interrupt routing. During onboarding the server answers game-clock
18851 with 28851, including the latest received frame-ready 18853 confirmation.
This prevents the client's frame-gap disconnect; it does not supply gameplay.
For socket-close investigation, `--connection-diagnostics` enables passive
native close/shutdown tracing. Normal builds disable it, and release packaging
rejects either connection or protocol research probes.

For local home-data research, inspect the compressed scene table without
changing the APK:

```powershell
python tools/read_client_table.py build/offline-client/split_install_time_asset_pack.apk
```

The decoded CSV is written under ignored `analysis/`. Its `Home` row identifies
`scene/home.json` and one player. This establishes client configuration only;
the server's scene/frame/player payload still needs to be derived.

### Current onboarding research
The test client now reaches age-onboarding and "Let's Go" with an experimental
own-home profile and scene frame. Game-clock replies and frame acknowledgements
are implemented; subsequent onboarding commands and gameplay remain incomplete.
The current manual-testing server runs in the
background; runtime details are in PROJECT_STATUS.md. Keep it running while the
user tests. home.py encodes the validated minimum profile; scene.py supplies the apartment
and tutorial destination. Broader scene serialization remains ongoing work. The known zero-ID starter fixture is encoded with the
authenticated local guest's ID before delivery.

Research-only fixture delivery is available through `--login --home-probe PATH
--profile-probe PATH` on tools/run_local_test.py. Fixture bodies, captures, and
native diagnostics stay in ignored local directories. Normal login behavior
retains its verified baseline. Do not distribute protocol-probe APK builds.

The apartment renders its player, bow and portal, and travel to Downtown Chaos
is verified. The implementation path for animations,
movement, and portal travel is documented in [apartment research](docs/APARTMENT_PROTOCOL.md).
To inspect only the observed commands in a private decrypted session:

```powershell
python tools/inspect_client_turns.py captures/game/SESSION.session.bin
```

This reports tutorial references and command counts. It does not execute
commands or provide movement, portal travel, or gameplay.
