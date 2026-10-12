"""Verify OpenMoco release downloads and reassemble the large asset APK."""
import argparse
import hashlib
import json
from pathlib import Path


def child(directory, name):
    if not isinstance(name, str) or Path(name).name != name or name in ('', '.', '..'):
        raise ValueError('Release filenames must be simple filenames')
    return directory / name


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as source:
        while block := source.read(1024 * 1024):
            result.update(block)
    return result.hexdigest()


def verify(path, entry):
    if not path.is_file() or path.stat().st_size != entry['size'] or digest(path) != entry['sha256']:
        raise ValueError(f'Missing or corrupt release file: {path.name}')


def assemble(directory):
    directory = directory.resolve()
    manifest = json.loads((directory / 'release-manifest.json').read_text(encoding='utf-8'))
    if manifest['package'] != 'com.supercell.moco.localtest':
        raise ValueError('Expected the isolated OpenMoco client package')
    paths = []
    # Check all downloads before writing the reconstructed APK.
    for entry in manifest['files']:
        path = child(directory, entry['name'])
        if 'parts' not in entry:
            verify(path, entry)
        else:
            for part in entry['parts']:
                verify(child(directory, part['name']), part)
    for entry in manifest['files']:
        path = child(directory, entry['name'])
        if 'parts' in entry:
            if path.exists():
                verify(path, entry)
            else:
                temporary = child(directory, entry['name'] + '.assembling')
                with temporary.open('xb') as target:
                    for part in entry['parts']:
                        with child(directory, part['name']).open('rb') as source:
                            while block := source.read(1024 * 1024):
                                target.write(block)
                verify(temporary, entry)
                temporary.rename(path)
        paths.append(path)
        print(f'Verified: {path.name}', flush=True)
    return paths


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, default=Path.cwd())
    args = parser.parse_args()
    assemble(args.directory)
    print('All five client APKs are ready. Follow INSTALL.md for adb install-multiple.')
