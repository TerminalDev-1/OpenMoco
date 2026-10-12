# OpenMoco v0.2.0-local-login

The isolated mo.co 13.5.1 test client now accepts a local server public key,
completes an encrypted guest login with the Python backend, and exchanges
encrypted keepalives. Local identities and token hashes persist in SQLite.
The original game installation and production account are separate.

Home/player state remains under reverse engineering. The client stays on its
loading screen; this release does not provide gameplay or a usable home screen.

The verified client build has protocol probes disabled. No private server key,
signing key, raw capture, or device configuration is included in the release.
The base APK and all four matching splits are required for a fresh installation.
Download every release asset into one folder, run `python assemble_release.py`,
and follow INSTALL.md. The large asset-pack APK is distributed as four verified
parts; retain enough disk space to reassemble it.

Existing v0.1.0-hello installs can update only the base APK, since the four
configuration/asset splits and signer are unchanged. Install alongside the
official app as `com.supercell.moco.localtest` and use your own local server keys.
