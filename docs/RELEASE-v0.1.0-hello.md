# OpenMoco 13.5.1 — initial hello test client

Experimental Android client for the OpenMoco Python server. Package:
`com.supercell.moco.localtest`, ARM64, English/xxhdpi splits, Android 10+.
It installs alongside the official mo.co app with separate local data.

**Verified:** local TCP connection, initial server hello accepted, encrypted
login request received. **Not implemented:** login authentication, complete
encrypted handshake, home data, gameplay. This is a pre-release research build.
The client is debuggable; native protocol probes are disabled.

## Download and install

Download all 12 release assets into one folder. The base APK is
`OpenMoco-13.5.1-localtest.apk`. It requires three configuration APKs and the
asset-pack APK. The asset pack is supplied as four numbered `.partNN` files
because it exceeds GitHub's per-file size limit.

Run `python assemble_release.py` in that download folder. The tool verifies
the manifest hashes and assembles `split_install_time_asset_pack.apk`.
Follow `INSTALL.md` to install all five APKs together and route the tablet
to the local Python server with ADB reverse.

`SHA256SUMS.txt` lists download hashes, and `release-manifest.json` records
the source checkpoint and completed APK hashes. No private signing key,
account data, device capture, or original APKM archive is included.

For the server, clone https://github.com/TerminalDev-1/OpenMoco and run:

```powershell
python tools/run_local_test.py --handshake --launch
```

The official app and its data must remain separate; use only the local-test
client for these experiments. A successful login is not expected in this build.
