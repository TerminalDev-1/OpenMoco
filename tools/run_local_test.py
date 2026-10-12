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
    parser.add_argument('--server-key', type=Path, default=ROOT/'.local/server-key.json')
    args = parser.parse_args()
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
    key = None
    if args.login:
        from transport import load_key
        key = load_key(args.server_key)
    if args.install:
        base = ROOT / 'build' / 'diagnostic-client' / 'base.apk'
        with zipfile.ZipFile(base) as apk:
            config = json.loads(apk.read('lib/arm64-v8a/libgadget.config.so'))
            if config['interaction']['parameters'].get('local_network') is not True:
                parser.error('Build with --local-network before installing for a server test')
            if key is not None and not config['interaction']['parameters'].get('supports_local_server_key') and config['interaction']['parameters'].get('server_public_key') != bytes(key.public_key).hex():
                parser.error('Build the clone with the matching --server-key before a login test')
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
    adb('reverse', 'tcp:9339', 'tcp:9339')
    adb('reverse', 'tcp:9340', 'tcp:9340')
    async def session():
        async def sdk_sink(reader, writer):
            try:
                await asyncio.wait_for(reader.read(4096), timeout=5)
            except (asyncio.TimeoutError, ConnectionError):
                pass
            finally:
                writer.close()
                try:
                    await writer.wait_closed()
                except ConnectionError:
                    pass
        sdk = await asyncio.start_server(sdk_sink, '127.0.0.1', 9340)
        listener = asyncio.create_task(run('127.0.0.1', 9339, ROOT / 'captures' / 'game', args.handshake or args.login, key))
        # Allow the listener to bind before launching the client.
        await asyncio.sleep(0.1)
        if listener.done():
            await listener
        if args.launch:
            if key is not None:
                await asyncio.to_thread(adb, 'shell', 'am', 'force-stop', PACKAGE)
            await asyncio.to_thread(adb, 'shell', 'am', 'start', '-W', '-n', PACKAGE + '/com.supercell.moco.GameApp')
        try:
            await listener
        finally:
            sdk.close()
            await sdk.wait_closed()
    try:
        asyncio.run(session())
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
