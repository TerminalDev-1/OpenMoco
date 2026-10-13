"""Prepare verified client APKs as GitHub release assets (never Git blobs).

Run verify_test_client.py --diagnostic before packaging. The large asset APK
is split into 1 GiB parts so each download stays below GitHub's asset limit.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def package(output, part_size=1024**3):
    if not 0 < part_size < 2 * 1024**3:
        raise ValueError('Release parts must be smaller than 2 GiB')
    output.mkdir(parents=True, exist_ok=True)
    base = ROOT / 'build/diagnostic-client/base.apk'
    with zipfile.ZipFile(base) as apk:
        params = json.loads(apk.read('lib/arm64-v8a/libgadget.config.so'))['interaction']['parameters']
        if not params.get('local_network') or params.get('protocol_diagnostics') or params.get('connection_diagnostics') or params.get('apartment_probe'):
            raise ValueError('Publish only a local-network build with research probes disabled')
        if apk.read('lib/arm64-v8a/libgadget.script.so') != (ROOT/'client/loader_diagnostics.js').read_bytes():
            raise ValueError('Rebuild the APK to match the current bootstrap source')
    sources = [(base, 'OpenMoco-13.5.1-localtest.apk')]
    sources += [(ROOT/'build/offline-client'/name, name) for name in [
        'split_config.arm64_v8a.apk', 'split_config.en.apk',
        'split_config.xxhdpi.apk', 'split_install_time_asset_pack.apk']]
    files, downloads = [], []
    for source, name in sources:
        whole = hashlib.sha256()
        entry = {'name': name, 'size': source.stat().st_size}
        if entry['size'] < 2 * 1024**3:
            destination = output / name
            with source.open('rb') as stream, destination.open('wb') as target:
                while block := stream.read(1024*1024):
                    target.write(block)
                    whole.update(block)
            entry['sha256'] = whole.hexdigest()
            downloads.append(entry)
        else:
            entry['parts'] = []
            with source.open('rb') as stream:
                remaining = entry['size']
                index = 1
                while remaining:
                    count = min(part_size, remaining)
                    part = {'name': name + f'.part{index:02}', 'size': count}
                    checksum = hashlib.sha256()
                    with (output / part['name']).open('wb') as target:
                        needed = count
                        while needed:
                            block = stream.read(min(1024*1024, needed))
                            if not block:
                                raise ValueError('Unexpected source EOF')
                            target.write(block)
                            whole.update(block)
                            checksum.update(block)
                            needed -= len(block)
                    part['sha256'] = checksum.hexdigest()
                    entry['parts'].append(part)
                    downloads.append(part)
                    remaining -= count
                    index += 1
                    print('Prepared:', part['name'], flush=True)
            entry['sha256'] = whole.hexdigest()
        files.append(entry)
        print('Prepared:', name, flush=True)
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    manifest = {'package': 'com.supercell.moco.localtest', 'client_version': '13.5.1',
                'source_commit': commit, 'architecture': 'arm64-v8a',
                'protocol_diagnostics': False, 'files': files}
    (output/'release-manifest.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
    shutil.copyfile(ROOT/'tools/assemble_release.py', output/'assemble_release.py')
    shutil.copyfile(ROOT/'docs/INSTALL.md', output/'INSTALL.md')
    lines = [f"{entry['sha256']}  {entry['name']}" for entry in downloads]
    for name in ['release-manifest.json', 'assemble_release.py', 'INSTALL.md']:
        lines.append(hashlib.sha256((output/name).read_bytes()).hexdigest()+'  '+name)
    (output/'SHA256SUMS.txt').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print('Release directory:', output, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'build/releases/v0.1.0-hello')
    args = parser.parse_args()
    package(args.output)
