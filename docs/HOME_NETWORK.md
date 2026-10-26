# Play over your home network (no adb)

By default the test client talks to the server through adb: it connects to its
own port 9339 and `adb reverse` carries that to your PC. You can instead build a
client that connects straight to your PC over Wi-Fi. Then you don't need
wireless debugging or a USB cable to play, and several phones or tablets can
connect to one server at the same time.

Each device logs in with its own local guest account and keeps its own
progress. The players don't see each other yet: shared-world multiplayer isn't
implemented.

## 1. Give your PC a fixed address

The client connects to one IPv4 address that's built into the APK, so your PC
needs to keep it. Open your router's admin page and add a **DHCP reservation**
(also called a static lease or address reservation) for your PC's network
adapter. Wi-Fi and Ethernet adapters each have their own address. Then find
the address:

```powershell
ipconfig
```

Use the **IPv4 Address** of the adapter on your home network, for example
`192.168.1.20`. If the address changes later, rebuild and reinstall the client
(step 2).

## 2. Build a client for that address

You need the build prerequisites from the [README](../README.md) and the server
key from `python tools/create_server_key.py`. Replace `192.168.1.20` with your
PC's address:

```powershell
python tools/build_diagnostic_client.py --debuggable --local-network --server-host 192.168.1.20 --server-key .local/server-key.json
python tools/verify_test_client.py --diagnostic --base-only
```

This builds `build/diagnostic-client/base.apk` with three values built in:

- your PC's address. Only the game connection (port 30000, sent to 9339) goes
  there; other app traffic stays on the device's own loopback, where nothing
  listens.
- your server's public key, so the client doesn't need adb to receive it.
- the server's XP level table.

The build accepts only a private home-network address, never a public internet
one. It's a personal build: don't share or publish it. `tools/package_release.py`
refuses to package a build that has an address or server key built in. Public
releases keep the adb (loopback) default.

Install it once, with the same splits as before (this step still uses adb):

```powershell
adb install-multiple -r -p com.supercell.moco.localtest --no-streaming build/diagnostic-client/base.apk
```

A file left behind by an earlier adb run (`files/local-server-public-key.txt` or
`files/xp-levels.json`) takes priority over the values built into the client.
Both hold the same data, so leaving them in place is harmless.

## 3. Allow port 9339 in Windows Firewall

In an administrator PowerShell:

```powershell
New-NetFirewallRule -DisplayName 'OpenMoco private server (home network)' -Direction Inbound -Action Allow -Protocol TCP -LocalPort 9339 -RemoteAddress LocalSubnet -Profile Any
```

`LocalSubnet` lets in only devices on your own network. Don't forward port 9339
on your router: the server is meant for your home network, not the internet.

## 4. Start the server in home-network mode

```powershell
python tools/run_local_test.py --lan --login --apartment
```

The server listens on `0.0.0.0:9339`, prints your PC's addresses, and closes any
connection that doesn't come from a private, link-local or loopback address.
This mode uses no adb at all. On Windows, the desktop `Run OpenMoco Server.bat`
launcher starts this mode. It refuses to start a second server while port 9339
is in use.

Now open **OpenMoco** (older builds: mo.co Local Test (Local Server)) from the app icon on any device
with the home-network build installed. Wireless debugging can stay off.

## Limits

- Combat still runs on each device; the server credits each device's kill
  reports to that device's own account.
- If two devices share one account (for example, after copying app data), the
  server doesn't coordinate their sessions.
- The adb path still works: `python tools/run_local_test.py --login --apartment`
  with a loopback build.
