"""Add autonomous, offline loader diagnostics to the isolated base APK."""
import json
import argparse
import ipaddress
from pathlib import Path
import struct
import subprocess
import sys
import zipfile

from build_test_client import BUILD_TOOLS, ROOT, read_pool, write_pool, chunks, u32


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--debuggable', action='store_true', help='Enable run-as for retrieving private runtime dumps')
    parser.add_argument('--local-network', action='store_true', help='Restore INTERNET with bootstrap-enforced loopback routing')
    parser.add_argument('--connection-diagnostics', action='store_true', help='Trace test-client game socket closure without protocol probes')
    parser.add_argument('--apartment-probe', action='store_true', help='Research native player/character construction in the isolated scene')
    parser.add_argument('--protocol-diagnostics', action='store_true', help='Capture build-specific native protocol inputs in test-client-private storage')
    parser.add_argument('--server-key', type=Path, help='Local server key JSON; embeds only its public key')
    parser.add_argument('--server-host', help="The PC's home-network IPv4 address; the client then connects "
                        'there over Wi-Fi instead of through adb reverse (personal builds only, never published)')
    args = parser.parse_args()
    if args.server_host is not None:
        try:
            address = ipaddress.IPv4Address(args.server_host)
        except ValueError:
            parser.error('--server-host must be an IPv4 address such as 192.168.1.20')
        if not args.local_network or not address.is_private or address.is_loopback or address.is_link_local:
            parser.error('--server-host requires --local-network and a private home-network address')
    server_public_key = None
    if args.server_key:
        server_public_key = json.loads(args.server_key.read_text(encoding='utf-8'))['public_key']
        if len(bytes.fromhex(server_public_key)) != 32 or not args.local_network:
            parser.error('--server-key requires a 32-byte public key and --local-network')
    build = ROOT / 'build' / 'diagnostic-client'
    build.mkdir(parents=True, exist_ok=True)
    classes = build / 'classes'
    classes.mkdir(exist_ok=True)
    dex = build / 'dex'
    dex.mkdir(exist_ok=True)
    android = BUILD_TOOLS.parents[1] / 'platforms' / 'android-35' / 'android.jar'
    def run(*args):
        subprocess.run([str(a) for a in args], check=True)
    factory_classes = classes / 'com' / 'supercell' / 'moco' / 'localtest'
    for generated in factory_classes.glob('DiagnosticFactory*.class'):
        generated.unlink()
    run('javac', '--release', '8', '-cp', android, '-d', classes, ROOT / 'client' / 'DiagnosticFactory.java')
    run('java', '-cp', BUILD_TOOLS / 'lib' / 'd8.jar', 'com.android.tools.r8.D8',
        '--lib', android, '--min-api', '29', '--output', dex,
        *sorted(factory_classes.glob('DiagnosticFactory*.class')))
    source = ROOT / 'build' / 'offline-client' / 'base.apk'
    unsigned = build / 'base.unsigned.apk'
    aligned = build / 'base.aligned.apk'
    signed = build / 'base.apk'
    with zipfile.ZipFile(source) as src, zipfile.ZipFile(unsigned, 'w') as dst:
        for entry in src.infolist():
            if entry.filename == 'stamp-cert-sha256' or (entry.filename.startswith('META-INF/') and entry.filename.upper().endswith(('.MF', '.SF', '.RSA', '.DSA', '.EC'))):
                continue
            data = src.read(entry)
            if entry.filename == 'AndroidManifest.xml':
                parts = list(chunks(data, 8))
                pool_index = next(i for i, (kind, _) in enumerate(parts) if kind == 1)
                strings, utf8 = read_pool(parts[pool_index][1])
                debug_index = len(strings)
                strings.append('debuggable')
                map_index = next(i for i, (kind, _) in enumerate(parts) if kind == 0x180)
                resource_map = parts[map_index][1]
                ids = list(struct.unpack('<' + 'I' * ((len(resource_map) - 8) // 4), resource_map[8:]))
                ids += [0] * (len(strings) - len(ids))
                ids[debug_index] = 0x0101000f
                parts[map_index] = (0x180, struct.pack('<HHI', 0x180, 8, 8 + 4 * len(ids)) + struct.pack('<' + 'I' * len(ids), *ids))
                for i, (kind, part) in enumerate(parts):
                    if kind == 1:
                        old = 'androidx.core.app.CoreComponentFactory'
                        assert strings.count(old) == 1
                        strings[strings.index(old)] = 'com.supercell.moco.localtest.DiagnosticFactory'
                        if args.local_network:
                            strings[strings.index('mo.co Local Test (Offline)')] = 'OpenMoco'
                        parts[i] = (kind, write_pool(strings, utf8))
                    elif kind == 0x102 and strings[u32(part, 20)] == 'application':
                        start, attr_size, count = struct.unpack_from('<HHH', part, 24)
                        assert attr_size == 20
                        assert struct.unpack_from('<HHH', part, 30) == (0, 0, 0)
                        attrs = [part[16 + start + j * 20:16 + start + (j + 1) * 20] for j in range(count)]
                        assert not any(strings[u32(a, 4)] == 'debuggable' for a in attrs)
                        attrs.append(struct.pack('<IIIHBBI', strings.index('http://schemas.android.com/apk/res/android'),
                            debug_index, 0xffffffff, 8, 0, 0x12, 0xffffffff if args.debuggable else 0))
                        attrs.sort(key=lambda a: ids[u32(a, 4)])
                        part = part[:16 + start] + b''.join(attrs)
                        struct.pack_into('<I', part, 4, len(part))
                        struct.pack_into('<H', part, 28, len(attrs))
                        parts[i] = (kind, part)
                if args.local_network:
                    ns = strings.index('http://schemas.android.com/apk/res/android')
                    tag = strings.index('uses-permission')
                    value = strings.index('android.permission.INTERNET')
                    start = struct.pack('<HHIII', 0x102, 16, 56, 0, 0xffffffff)
                    start += struct.pack('<IIHHHHHH', 0xffffffff, tag, 20, 20, 1, 0, 0, 0)
                    start += struct.pack('<IIIHBBI', ns, strings.index('name'), value, 8, 0, 3, value)
                    end = struct.pack('<HHIIIII', 0x103, 16, 24, 0, 0xffffffff, 0xffffffff, tag)
                    application = next(i for i, (kind, part) in enumerate(parts) if kind == 0x102 and strings[u32(part, 20)] == 'application')
                    parts[application:application] = [(0x102, start), (0x103, end)]
                body = b''.join(part for _, part in parts)
                data = struct.pack('<HHI', 3, 8, 8 + len(body)) + body
            dst.writestr(entry, data)
        dst.write(dex / 'classes.dex', 'classes3.dex', compress_type=zipfile.ZIP_STORED)
        dst.write(ROOT / '.tools' / 'libgadget.so', 'lib/arm64-v8a/libgadget.so', compress_type=zipfile.ZIP_STORED)
        config = {'interaction': {'type': 'script', 'path': 'libgadget.script.so',
            'parameters': {'local_network': args.local_network, 'protocol_diagnostics': args.protocol_diagnostics, 'connection_diagnostics': args.connection_diagnostics, 'apartment_probe': args.apartment_probe,
                           'supports_local_server_key': True,
                           'game_port': 9339, 'sdk_port': 9340}}, 'runtime': 'qjs'}
        if server_public_key:
            config['interaction']['parameters']['server_public_key'] = server_public_key
        if args.server_host is not None:
            config['interaction']['parameters']['server_host'] = args.server_host
        if args.local_network:
            # Baked in so the client needs no adb provisioning; XP events carry it too.
            sys.path.insert(0, str(ROOT))
            from progress import XP_LEVELS
            config['interaction']['parameters']['xp_levels'] = list(XP_LEVELS)
        dst.writestr('lib/arm64-v8a/libgadget.config.so', json.dumps(config), compress_type=zipfile.ZIP_STORED)
        dst.write(ROOT / 'client' / 'loader_diagnostics.js', 'lib/arm64-v8a/libgadget.script.so', compress_type=zipfile.ZIP_STORED)
    run(BUILD_TOOLS / 'zipalign.exe', '-f', '-P', '16', '4', unsigned, aligned)
    run('java', '-jar', BUILD_TOOLS / 'lib' / 'apksigner.jar', 'sign', '--ks', ROOT / '.local' / 'test-client.p12',
        '--ks-key-alias', 'localtest', '--ks-pass', 'pass:moco-local-development', '--out', signed, aligned)
    run('java', '-jar', BUILD_TOOLS / 'lib' / 'apksigner.jar', 'verify', signed)
    print('Diagnostic base APK:', signed)


if __name__ == '__main__':
    main()
