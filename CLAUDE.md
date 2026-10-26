# OpenMoco: notes for Claude

OpenMoco is a mo.co private server written in Python, with a separate test
client (`com.supercell.moco.localtest`). The goal is 100% of the server
behaviour the 13.5.1 client needs. Never call it a clone.

**AGENTS.md is the full project guide** (scope, terminology, safety rules,
verified baseline, release history). Read it, then the newest sections at the
top of PROJECT_STATUS.md, before starting work. This file only adds how the
user wants Claude to work.

## How the user wants the work done
- Don't stop early. Keep going through failures and diagnosis until the
  requested feature works, or until a real blocker needs the user.
- Commit **and push** every verified checkpoint to
  https://github.com/TerminalDev-1/OpenMoco (`main`), including partial ones.
  Label partial work as partial in the commit message and in
  PROJECT_STATUS.md, with its open defects. Don't leave checkpoints local.
- Before every push, check the staged files for private data: keys,
  `.local/`, account databases, captures, APKs, the PC's or tablet's
  home-network address.
- Ask before starting a new session for a task.
- Keep AGENTS.md and PROJECT_STATUS.md current after material changes.

## Practical notes (Windows PC)
- adb: `%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe`. Find the tablet
  with `adb mdns services`; use the `_adb-tls-connect` serial it lists.
- `.local/android-sdk.txt` may point at a missing SDK; set
  `ANDROID_SDK_ROOT=%LOCALAPPDATA%\Android\Sdk` before building.
- Tests: `.venv\Scripts\python.exe -m unittest discover -s tests`.
- Windows PowerShell 5.1 mangles quotes in `git commit -m`; write the message
  to a file and use `git commit -F <file>`.
- Tablet screenshots: `adb shell screencap -p /data/local/tmp/x.png`, then
  `adb pull` (PowerShell `>` corrupts binary output). Delete the file after.
- Before every scripted tap or swipe, check that the test client is the
  foreground app (`dumpsys activity activities`, `topResumedActivity`). If it
  crashed, taps land on the user's home screen and open other apps.
- Native analysis: `tools/disassemble_runtime.py <address>` reads the runtime
  dump in `analysis/runtime/game` (load base in `game-metadata.json`).
- Live probes need an `--apartment-probe` build plus
  `files/apartment-probe.js` (run-as). Keep hooks minimal; never leave a probe
  build installed or publish one. Reinstall the normal build and check its hash.
- The manual server runs hidden in home-network mode; its PID and logs are in
  `.local/user-test-server.json`. Restart it after server changes and
  record the new PID.
