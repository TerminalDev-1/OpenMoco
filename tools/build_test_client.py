"""Create separately signed, OFFLINE APK splits without rebuilding game assets.

Binary structures follow AOSP ResourceTypes.h. Original archives are read-only.
The offline build deliberately lacks INTERNET permission. It is not yet a
client for the Python server.
"""
import argparse
import json
from pathlib import Path
import shutil
import struct
import subprocess
import zipfile
from android_tools import BUILD_TOOLS

# Android APK tools require classic ZIP. Python otherwise inserts ZIP64 at
# 2 GiB, even though classic ZIP offsets support the supplied ~3.8 GB pack.
zipfile.ZIP64_LIMIT = 0xffffffff

ROOT = Path(__file__).resolve().parents[1]
OLD = 'com.supercell.moco'
NEW = OLD + '.localtest'
SPLITS = ['base.apk', 'split_config.arm64_v8a.apk', 'split_config.en.apk',
          'split_config.xxhdpi.apk', 'split_install_time_asset_pack.apk']


def u32(data, offset):
    return struct.unpack_from('<I', data, offset)[0]


def chunks(data, start):
    while start < len(data):
        kind, header, size = struct.unpack_from('<HHI', data, start)
        if size < header or start + size > len(data):
            raise ValueError('Invalid resource chunk')
        yield kind, bytearray(data[start:start + size])
        start += size


def length(data, pos, utf8):
    if utf8:
        n = data[pos]
        return (((n & 127) << 8) | data[pos + 1], pos + 2) if n & 128 else (n, pos + 1)
    n = struct.unpack_from('<H', data, pos)[0]
    return (((n & 32767) << 16) | struct.unpack_from('<H', data, pos + 2)[0], pos + 4) if n & 32768 else (n, pos + 2)


def encode_length(n, utf8):
    if utf8:
        return bytes([128 | (n >> 8), n & 255]) if n > 127 else bytes([n])
    return struct.pack('<HH', 32768 | (n >> 16), n & 65535) if n > 32767 else struct.pack('<H', n)


def read_pool(data):
    count, styles, flags, start, style_start = struct.unpack_from('<IIIII', data, 8)
    if styles or style_start:
        raise ValueError('Styled XML string pool unsupported')
    header = struct.unpack_from('<H', data, 2)[0]
    utf8 = bool(flags & 256)
    strings = []
    for i in range(count):
        pos = start + u32(data, header + i * 4)
        n, pos = length(data, pos, utf8)
        if utf8:
            n, pos = length(data, pos, True)
        strings.append(bytes(data[pos:pos + n * (1 if utf8 else 2)]).decode('utf-8' if utf8 else 'utf-16le'))
    return strings, utf8


def write_pool(strings, utf8):
    offsets, payload = [], bytearray()
    for value in strings:
        offsets.append(len(payload))
        encoded = value.encode('utf-8' if utf8 else 'utf-16le')
        chars = len(value.encode('utf-16le')) // 2
        payload.extend(encode_length(chars, utf8))
        if utf8:
            payload.extend(encode_length(len(encoded), True))
        payload.extend(encoded + (b'\0' if utf8 else b'\0\0'))
    payload.extend(b'\0' * (-len(payload) % 4))
    start = 28 + 4 * len(strings)
    return struct.pack('<HHIIIIII', 1, 28, start + len(payload), len(strings), 0,
                       256 if utf8 else 0, start, 0) + struct.pack('<' + 'I' * len(offsets), *offsets) + payload


def patch_manifest(data, base):
    parts = list(chunks(data, 8))
    pool_index = next(i for i, (kind, _) in enumerate(parts) if kind == 1)
    strings, utf8 = read_pool(parts[pool_index][1])
    replacements = {OLD: NEW}
    for kind, chunk in parts:
        if kind != 0x102:
            continue
        tag = strings[u32(chunk, 20)]
        attr_start, attr_size, count = struct.unpack_from('<HHH', chunk, 24)
        for i in range(count):
            pos = 16 + attr_start + i * attr_size
            name = strings[u32(chunk, pos + 4)]
            if chunk[pos + 15] != 3:
                continue
            value = strings[u32(chunk, pos + 16)]
            if (name == 'authorities' or (tag in ('permission', 'uses-permission') and name == 'name')) and value.startswith(OLD + '.'):
                replacements[value] = NEW + value[len(OLD):]
    changed = [replacements.get(s, s) for s in strings]
    label_index = len(changed)
    if base:
        changed.append('mo.co Local Test (Offline)')
    output = []
    skip_end = False
    removed_internet = False
    for i, (kind, chunk) in enumerate(parts):
        if i == pool_index:
            output.append(write_pool(changed, utf8))
            continue
        if kind == 0x103 and skip_end:
            if strings[u32(chunk, 20)] != 'uses-permission':
                raise ValueError('Unexpected permission structure')
            skip_end = False
            continue
        if kind == 0x102:
            tag = strings[u32(chunk, 20)]
            attr_start, attr_size, count = struct.unpack_from('<HHH', chunk, 24)
            attrs = {strings[u32(chunk, 16 + attr_start + j * attr_size + 4)]: 16 + attr_start + j * attr_size for j in range(count)}
            if base and tag == 'uses-permission' and 'name' in attrs:
                pos = attrs['name']
                if chunk[pos + 15] == 3 and strings[u32(chunk, pos + 16)] == 'android.permission.INTERNET':
                    skip_end = True
                    removed_internet = True
                    continue
            if base and tag == 'application':
                if 'label' not in attrs or 'allowBackup' not in attrs:
                    raise ValueError('Required application attributes missing')
                pos = attrs['label']
                struct.pack_into('<I', chunk, pos + 8, label_index)
                chunk[pos + 15] = 3
                struct.pack_into('<I', chunk, pos + 16, label_index)
                pos = attrs['allowBackup']
                struct.pack_into('<I', chunk, pos + 8, 0xffffffff)
                chunk[pos + 15] = 0x12
                struct.pack_into('<I', chunk, pos + 16, 0)
        output.append(chunk)
    if base and not removed_internet:
        raise ValueError('INTERNET permission not found; offline build aborted')
    body = b''.join(output)
    return struct.pack('<HHI', 3, 8, 8 + len(body)) + body, replacements


def patch_resources(data):
    data = bytearray(data)
    offset = struct.unpack_from('<H', data, 2)[0]
    while offset < len(data):
        kind, header, size = struct.unpack_from('<HHI', data, offset)
        if size < header or offset + size > len(data):
            raise ValueError('Invalid table chunk')
        if kind == 0x200:
            name = bytes(data[offset + 12:offset + 268]).decode('utf-16le').split('\0')[0]
            if name == OLD:
                data[offset + 12:offset + 268] = NEW.encode('utf-16le').ljust(256, b'\0')
        offset += size
    return data


def run(*args):
    subprocess.run([str(a) for a in args], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--small-only', action='store_true', help='Skip the large asset pack for initial validation')
    args = parser.parse_args()
    output = ROOT / 'build' / 'offline-client'
    output.mkdir(parents=True, exist_ok=True)
    key = ROOT / '.local' / 'test-client.p12'
    key.parent.mkdir(exist_ok=True)
    # This public development password only protects a local test signing key.
    password = 'moco-local-development'
    if not key.exists():
        run('keytool', '-genkeypair', '-keystore', key, '-storetype', 'PKCS12', '-storepass', password,
            '-alias', 'localtest', '-keyalg', 'RSA', '-keysize', '2048', '-validity', '3650',
            '-dname', 'CN=mo.co Local Test')
    selected = SPLITS[:-1] if args.small_only else SPLITS
    evidence = {}
    with zipfile.ZipFile(next(ROOT.glob('*.apkm'))) as bundle:
        for name in selected:
            source = ROOT / 'analysis' / 'apks' / name
            source.parent.mkdir(parents=True, exist_ok=True)
            if not source.exists():
                print('Extracting', name, flush=True)
                with bundle.open(name) as src, source.open('wb') as dst:
                    shutil.copyfileobj(src, dst, 1024 * 1024)
            unsigned = output / (name + '.unsigned')
            aligned = output / (name + '.aligned')
            signed = output / name
            if signed.exists():
                print('Already built:', name, flush=True)
                continue
            print('Patching', name, flush=True)
            with zipfile.ZipFile(source) as src, zipfile.ZipFile(unsigned, 'w', allowZip64=True) as dst:
                for entry in src.infolist():
                    if entry.filename.startswith('META-INF/') and entry.filename.upper().endswith(('.MF', '.SF', '.RSA', '.DSA', '.EC')):
                        continue
                    if entry.filename == 'AndroidManifest.xml':
                        patched, changes = patch_manifest(src.read(entry), name == 'base.apk')
                        evidence[name] = changes
                        dst.writestr(entry, patched)
                    elif entry.filename == 'resources.arsc':
                        dst.writestr(entry, patch_resources(src.read(entry)))
                    else:
                        with src.open(entry) as input_stream, dst.open(entry, 'w', force_zip64=entry.file_size > 2**31) as output_stream:
                            shutil.copyfileobj(input_stream, output_stream, 1024 * 1024)
            run(BUILD_TOOLS / 'zipalign.exe', '-P', '16', '4', unsigned, aligned)
            run('java', '-jar', BUILD_TOOLS / 'lib' / 'apksigner.jar', 'sign', '--ks', key,
                '--ks-key-alias', 'localtest', '--ks-pass', 'pass:' + password, '--out', signed, aligned)
            run('java', '-jar', BUILD_TOOLS / 'lib' / 'apksigner.jar', 'verify', signed)
            unsigned.unlink()
            aligned.unlink()
    report = output / 'build-report.json'
    previous = json.loads(report.read_text()) if report.exists() else {}
    previous.update(evidence)
    report.write_text(json.dumps(previous, indent=2), encoding='utf-8')
    print('Built OFFLINE client splits; no installation or launch performed.', flush=True)


if __name__ == '__main__':
    main()
