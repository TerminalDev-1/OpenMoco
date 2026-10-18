"""Start the local game capture server and route the isolated tablet client."""
import argparse
import asyncio
import json
from pathlib import Path
import subprocess
import sys
import zipfile
from android_tools import DEFAULT_ADB

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from server import run

PACKAGE = 'com.supercell.moco.localtest'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adb', type=Path, default=DEFAULT_ADB)
    parser.add_argument('--serial', help='Use a specific authorized tablet if multiple devices are connected')
    parser.add_argument('--install', action='store_true', help='Update only the isolated client base APK')
    parser.add_argument('--launch', action='store_true', help='Launch only the isolated test client')
    parser.add_argument('--handshake', action='store_true', help='Enable the experimental server hello response')
    parser.add_argument('--login', action='store_true', help='Verify and decrypt the local-key login')
    parser.add_argument('--apartment', action='store_true', help='Start the minimum account-bound apartment; requires --login')
    parser.add_argument('--transport-probe', action='store_true', help='Send an encrypted empty keepalive to verify native reply decryption; requires --login')
    parser.add_argument('--home-probe', type=Path, help='Send an evidenced local scene-start body after login, for protocol research')
    parser.add_argument('--profile-probe', type=Path, help='Research own-home body; requires --home-probe')
    parser.add_argument('--server-key', type=Path, default=ROOT/'.local/server-key.json')
    parser.add_argument('--lan', action='store_true', help='Serve clients built with --server-host over the home '
                        'network (0.0.0.0:9339, home-network peers only); no adb or tablet connection is used')
    args = parser.parse_args()
    if args.lan and (args.install or args.launch or args.serial):
        parser.error('--lan uses no adb; install or launch the client separately')
    if args.apartment and (not args.login or args.transport_probe or args.home_probe or args.profile_probe):
        parser.error('--apartment requires --login without research fixtures/probes')
    if args.transport_probe and not args.login:
        parser.error('--transport-probe requires --login')
    if args.home_probe and (not args.login or args.transport_probe):
        parser.error('--home-probe requires --login without --transport-probe')
    if args.profile_probe and not args.home_probe:
        parser.error('--profile-probe requires --home-probe')
    profile_probe = args.profile_probe.read_bytes() if args.profile_probe else None
    if profile_probe is not None and not 0 < len(profile_probe) <= 65536:
        parser.error('Profile-probe body must contain 1..65536 bytes')
    home_probe = args.home_probe.read_bytes() if args.home_probe else None
    if home_probe is not None and not 0 < len(home_probe) <= 65536:
        parser.error('Home-probe body must contain 1..65536 bytes')
    key = None
    if args.login:
        from transport import load_key
        key = load_key(args.server_key)
    if args.lan:
        print('Home-network mode. Clients connect to this PC at:', ', '.join(lan_addresses()) or 'unknown', flush=True)
        serve(args, '0.0.0.0', key, home_probe, profile_probe, lan_only=True)
        return
    if not args.adb.is_file():
        parser.error('adb not found; provide --adb with its installed path')
    serial = args.serial
    if serial is None:
        listing = subprocess.check_output([str(args.adb), 'devices'], text=True)
        devices = [line.rsplit('\t', 1)[0] for line in listing.splitlines()[1:]
                   if '\t' in line and line.rsplit('\t', 1)[1].strip() == 'device']
        if len(devices) != 1:
            parser.error('Exactly one authorized tablet is required, or provide --serial')
        serial = devices[0]
    def adb(*items):
        subprocess.run([str(args.adb), '-s', serial, *items], check=True)
    if args.install:
        base = ROOT / 'build' / 'diagnostic-client' / 'base.apk'
        with zipfile.ZipFile(base) as apk:
            config = json.loads(apk.read('lib/arm64-v8a/libgadget.config.so'))
            if config['interaction']['parameters'].get('local_network') is not True:
                parser.error('Build with --local-network before installing for a server test')
            if key is not None and not config['interaction']['parameters'].get('supports_local_server_key') and config['interaction']['parameters'].get('server_public_key') != bytes(key.public_key).hex():
                parser.error('Build the test client with the matching --server-key before a login test')
            if apk.read('lib/arm64-v8a/libgadget.script.so') != (ROOT / 'client' / 'loader_diagnostics.js').read_bytes():
                parser.error('Client bootstrap changed; rebuild the base APK first')
        adb('install-multiple', '-r', '-p', PACKAGE, '--no-streaming', str(base))
    if key is not None:
        public_file = ROOT/'.local/server-public-key.txt'
        public_file.parent.mkdir(parents=True, exist_ok=True)
        public_file.write_text(bytes(key.public_key).hex()+'\n', encoding='ascii')
        adb('push', str(public_file), '/data/local/tmp/openmoco-server-public-key.txt')
        adb('shell', 'run-as', PACKAGE, 'mkdir', '-p', 'files')
        adb('shell', 'run-as', PACKAGE, 'cp', '/data/local/tmp/openmoco-server-public-key.txt', 'files/local-server-public-key.txt')
    if args.apartment:
        # The old loopback battle bridge's token; kill reports now use the game connection.
        adb('shell', 'run-as', PACKAGE, 'rm', '-f', 'files/battle-bridge-token.txt')
        # The server's XP level table, installed by the client bridge before the
        # battle HUD is built (the client data has no table of its own).
        from progress import XP_LEVELS
        levels_path = ROOT/'.local/xp-levels.json'
        levels_path.write_text(json.dumps(list(XP_LEVELS)), encoding='ascii')
        adb('push', str(levels_path), '/data/local/tmp/openmoco-xp-levels.json')
        adb('shell', 'run-as', PACKAGE, 'cp', '/data/local/tmp/openmoco-xp-levels.json', 'files/xp-levels.json')
    # One connection: the game port. The bootstrap points SDK traffic at the
    # tablet's loopback port 9340, where nothing listens, so it is refused there.
    adb('reverse', 'tcp:9339', 'tcp:9339')
    subprocess.run([str(args.adb), '-s', serial, 'reverse', '--remove', 'tcp:9340'],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    async def launch():
        if key is not None:
            await asyncio.to_thread(adb, 'shell', 'am', 'force-stop', PACKAGE)
        await asyncio.to_thread(adb, 'shell', 'am', 'start', '-W', '-n', PACKAGE + '/com.supercell.moco.GameApp')
    serve(args, '127.0.0.1', key, home_probe, profile_probe, launch if args.launch else None)


def lan_addresses():
    """This PC's IPv4 addresses on private networks (for the client build)."""
    import ipaddress
    import socket
    found = set()
    for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
        address = ipaddress.IPv4Address(info[4][0])
        if address.is_private and not address.is_loopback and not address.is_link_local:
            found.add(str(address))
    return sorted(found)


def serve(args, host, key, home_probe, profile_probe, after_bind=None, lan_only=False):
    async def session():
        listener = asyncio.create_task(run(host, 9339, ROOT / 'captures' / 'game', args.handshake or args.login, key, transport_probe=args.transport_probe, home_probe=home_probe, profile_probe=profile_probe, apartment=args.apartment, lan_only=lan_only))
        # Allow the listener to bind before launching the client.
        await asyncio.sleep(0.1)
        if listener.done():
            await listener
        if after_bind is not None:
            await after_bind()
        await listener
    try:
        asyncio.run(session())
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
