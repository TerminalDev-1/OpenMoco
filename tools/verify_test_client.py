"""Verify package isolation, signing, alignment, and preserved APK payloads."""
import hashlib
import argparse
import json
from pathlib import Path
import subprocess
import zipfile

from build_test_client import BUILD_TOOLS, NEW, ROOT, SPLITS


def digest(stream):
    result = hashlib.sha256()
    while block := stream.read(1024 * 1024):
        result.update(block)
    return result.digest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--diagnostic', action='store_true', help='Verify the instrumented base with the preserved offline splits')
    parser.add_argument('--base-only', action='store_true', help='Validate only the changed base APK')
    args = parser.parse_args()
    report = {}
    certificates = set()
    for name in (SPLITS[:1] if args.base_only else SPLITS):
        folder = 'diagnostic-client' if args.diagnostic and name == 'base.apk' else 'offline-client'
        built = ROOT / 'build' / folder / name
        print('Verifying', name, flush=True)
        def command(*args):
            return subprocess.run([str(a) for a in args], check=True, capture_output=True, text=True).stdout
        xml = command(BUILD_TOOLS / 'aapt2.exe', 'dump', 'xmltree', built, '--file', 'AndroidManifest.xml')
        assert f'package="{NEW}"' in xml, name
        if name == 'base.apk':
            if args.diagnostic:
                with zipfile.ZipFile(built) as apk:
                    config = json.loads(apk.read('lib/arm64-v8a/libgadget.config.so'))
                    network = config['interaction']['parameters']['local_network']
                    assert apk.read('lib/arm64-v8a/libgadget.script.so') == (ROOT / 'client' / 'loader_diagnostics.js').read_bytes()
                    assert apk.read('lib/arm64-v8a/libgadget.so') == (ROOT / '.tools' / 'libgadget.so').read_bytes()
                    assert apk.read('classes3.dex') == (ROOT / 'build' / 'diagnostic-client' / 'dex' / 'classes.dex').read_bytes()
                assert ('android.permission.INTERNET' in xml) == network
                assert 'com.supercell.moco.localtest.DiagnosticFactory' in xml
                assert 'mo.co Local Test (' in xml
            else:
                assert 'android.permission.INTERNET' not in xml
                assert 'mo.co Local Test (Offline)' in xml
            assert 'com.supercell.moco.GameApp' in xml
            assert ':allowBackup(0x01010280)=false' in xml
            authorities = [line for line in xml.splitlines() if ':authorities' in line]
            assert len(authorities) == 8
            assert all(NEW + '.' in line for line in authorities)
        signature = command('java', '-jar', BUILD_TOOLS / 'lib' / 'apksigner.jar', 'verify', '--print-certs', built)
        certificate = next(line for line in signature.splitlines() if 'certificate SHA-256 digest:' in line)
        certificates.add(certificate)
        command(BUILD_TOOLS / 'zipalign.exe', '-c', '-P', '16', '4', built)
        checked = 0
        with zipfile.ZipFile(ROOT / 'analysis' / 'apks' / name) as original, zipfile.ZipFile(built) as patched:
            excluded = {'AndroidManifest.xml', 'resources.arsc', 'stamp-cert-sha256'}
            for entry in original.infolist():
                if entry.filename in excluded or entry.filename.startswith('META-INF/'):
                    continue
                with original.open(entry) as src, patched.open(entry.filename) as dst:
                    assert digest(src) == digest(dst), entry.filename
                checked += 1
        report[name] = {'package': NEW, 'verified_payload_entries': checked,
                        'signature_valid': True, 'alignment_valid': True}
        print('PASS:', name, checked, 'unchanged payload entries', flush=True)
    assert len(certificates) == 1, 'All splits must share a signing certificate'
    filename = 'diagnostic-build-verification.json' if args.diagnostic else 'build-verification.json'
    (ROOT / 'analysis' / filename).write_text(json.dumps(report, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
