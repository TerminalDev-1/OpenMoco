# OpenMoco private-server Android client

This mo.co 13.5.1 test build installs as `com.supercell.moco.localtest`, alongside
the official app. It targets ARM64 devices, Android 10 or later, with the
English and xxhdpi resource splits used in the verified tablet configuration.
The local encrypted guest login and keepalives work. The Python server's
`--apartment` mode sends a local player and starter bow at the apartment spawn.
The portal renders and travel into Downtown Chaos is verified. Age-onboarding
categories, reported tutorial steps and the last scene persist. Tap the minimap,
then Leave Battle to return home. The first monster renders and takes damage;
it currently flees quickly. Full quest progression and authoritative gameplay
remain unfinished. The build is debuggable; research probes are disabled.

## Download and assemble

Download the updated base APK, manifest, assembler and checksums from
[v0.6.0-reconnect](https://github.com/TerminalDev-1/OpenMoco/releases/tag/v0.6.0-reconnect).
For a fresh installation, also download the three configuration APKs and four
asset-pack parts from
[v0.3.0-apartment](https://github.com/TerminalDev-1/OpenMoco/releases/tag/v0.3.0-apartment).
These seven files are unchanged and checked by the new manifest. Put all files
in one folder; use the new manifest and assembler. You need the base APK, the three
small configuration APKs, all four numbered asset-pack parts,
`release-manifest.json`, and `assemble_release.py`. `SHA256SUMS.txt` provides
download checksums. The asset pack is split because each GitHub release asset
must be smaller than 2 GiB. The base APK alone is not a complete installation.

From that folder, using Python 3.10 or newer:

```powershell
python assemble_release.py
```

The tool verifies every APK and numbered part against the manifest, joins
the parts into `split_install_time_asset_pack.apk`, and verifies the completed
file. Allow about 4 GB of additional disk space for the assembled APK.

## Install alongside the original app

Enable Android debugging and connect your tablet with ADB. Then run this
single command from the download folder:

```powershell
adb install-multiple -r --no-streaming OpenMoco-13.5.1-localtest.apk split_config.arm64_v8a.apk split_config.en.apk split_config.xxhdpi.apk split_install_time_asset_pack.apk
```

This installs or updates only the local-test package. Never uninstall or clear
the official `com.supercell.moco` app as part of setup. This build uses its own
local data. Do not sign it into your real Supercell account.

## Start the Python server and local routing

Download the OpenMoco repository, connect exactly one authorized Android device,
and run from the repository folder:

```powershell
python -m pip install -r requirements.txt
python tools/create_server_key.py
python tools/run_local_test.py --login --apartment --launch
```

ADB must be on PATH or discoverable through your Android SDK; otherwise add
`--adb` with its executable path. With multiple devices, add `--serial` for
your test tablet. The runner forwards tablet ports 9339 and 9340 to the PC,
starts the game listener and SDK sink, and launches **mo.co Local Test (Local
Server)**. Local routing is installed before game startup. Keep ADB connected
while testing. The runner provisions only your server's public key into the
test client. Keep the private key and `.local/accounts.sqlite3` on your PC; retain
both across runs to preserve local test identities. The server verifies local
credentials and sends the compatible encrypted login reply and starter apartment.
Authenticated age choices and reported tutorial steps persist. Reconnect resumes
the saved scene and unfinished step without replaying completed intro steps.
With the return-home client update, tap the minimap, then **Leave Battle** to
return to the apartment. Quest execution and authoritative combat remain unfinished.
Keep the server process running during manual testing. The local-network client
now preserves the native socket status on reconnect, so bringing it back to the
foreground can complete login without restarting the app. Update to v0.6.0 for
this repair; it uses the same saved local account and matching configuration splits.
The client
suppresses automatic idle closure and keeps its foreground screen awake. Keep
wireless debugging connected: losing ADB forwarding can still cause a connection
error. With duplicate wireless device aliases, select the active one using
`--serial` as with multiple devices.

These login instructions require the v0.2.0-local-login client or a newer build.
The earlier v0.1.0-hello client supports the hello milestone only.

Existing installations can use the base APK as a partial update only when
the four matching release splits are already installed with the same signer.
For that case, run:

```powershell
adb install-multiple -r -p com.supercell.moco.localtest --no-streaming OpenMoco-13.5.1-localtest.apk
```
