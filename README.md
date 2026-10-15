# OpenMoco

OpenMoco is a mo.co private server written in Python. The goal is a complete
Python implementation of mo.co's server: accounts, worlds, combat, progression,
inventory, multiplayer, and everything needed to play the game.

We're building toward 100% feature coverage. It isn't complete yet, but you can
already log in, explore the apartment, use the portal, and fight in Downtown Chaos.
The current client version is **13.5.1**.

## What works now

- Local guest accounts with their own IDs and saved login tokens.
- Saved age choices, tutorial steps, and the last visited scene.
- A playable apartment with a starter bow and working portal.
- Travel to Downtown Chaos and back through **Map → Leave Battle**.
- Movement and player animation across repeated scene changes.
- Eight monster records, spirits, human civilians, and recurring native spawns.
- Kill/rescue counts and kill-based XP saved by the server, reported by a local
  client bridge.
- The first tutorial quest (defeat 50 monsters, rescue 3 civilians) tracked on
  the server. Once you've done both, **Leave Battle** finishes the Portal
  tutorial: Luna congratulates you and the client moves on to character creation.
- Connections stay open while you take a break.
- The client reconnects when you return to the app with the server available.

Still to do: filling the in-battle XP bar, character creation (the editor opens
but has no head/cosmetic data yet), rewards, inventory, COOL-zone access,
multiplayer, and combat controlled by the Python server. Combat currently runs in
the Android client from the scenes supplied by the server. The client bridge
reports native kill/rescue counts. The server decides what they're worth, saves
them, and turns them into quest progress and saved XP.

## Get the client

Download the private-server client from
[GitHub Releases](https://github.com/TerminalDev-1/OpenMoco/releases/tag/v0.6.0-reconnect).
Follow the [installation guide](docs/INSTALL.md) to assemble and install all the
required APK splits. A fresh install also needs the unchanged splits and asset
parts linked from the apartment release.

The client installs as `com.supercell.moco.localtest`, alongside the official
mo.co app. It uses separate app data and a separate local-server account.

## Run the server

You need Python 3.10+, Android platform-tools (ADB), and an Android device
connected to your PC through USB or paired wireless debugging.

From the repository folder:

```powershell
python -m pip install -r requirements.txt
python tools/create_server_key.py
python tools/run_local_test.py --login --apartment --launch
```

The runner starts the Python server, sets up ADB forwarding, gives the client
your server's public key, and launches the app. Keep the server and ADB connection
running while you play. If several devices are connected, add `--serial DEVICE_ID`.
If ADB isn't on PATH, add `--adb PATH_TO_ADB`.

Your accounts are saved in `.local/accounts.sqlite3`, and the server key is in
`.local/server-key.json`. Keep these files between runs to retain your progress
and server identity. Private keys and account files stay out of Git.

Use the v0.6.0 client for the reconnect fix. Existing installations can update
just the base APK with the matching splits already installed; see the guide.

## Build the Android client

To build it yourself, provide the original mo.co 13.5.1 APKM. You'll also need
Android build-tools 35.0.0, platform android-35, Java/keytool, and Frida Gadget
17.23.3 for Android ARM64 at `.tools/libgadget.so`.

```powershell
python tools/build_test_client.py
python tools/verify_test_client.py
python tools/build_diagnostic_client.py --debuggable --local-network
python tools/verify_test_client.py --diagnostic --base-only
```

See the [installation guide](docs/INSTALL.md) for installing the base and its
matching splits. For an existing installation with locally built matching splits:

```powershell
python tools/run_local_test.py --install --login --apartment --launch
```

The repository contains the Python server, client build tools, and implementation
notes. APK downloads live in releases. Original archives, extracted game files,
private keys, accounts, and device captures aren't stored in the source tree.
Diagnostic probes are disabled in published clients.

## Development

We commit and push checkpoints as changes are verified. Partial features are
tracked openly, with what's working and what still needs finishing.

Run the tests:

```powershell
python -m unittest discover -s tests -v
```

[Project status](PROJECT_STATUS.md) tracks completed work and next steps.
[Apartment and scene notes](docs/APARTMENT_PROTOCOL.md) and
[progression notes](docs/PROGRESSION_PROTOCOL.md) explain the implementation.
[AGENTS.md](AGENTS.md) keeps the project goals and working rules in one place.
