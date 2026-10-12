"""Inventory the APKM and collect native networking string clues, offline."""
import io
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    package = next(ROOT.glob('*.apkm'))
    output = ROOT / 'analysis'
    output.mkdir(exist_ok=True)
    report = {'package': package.name, 'splits': [], 'native_clues': {}}
    pattern = re.compile(r'(?:https?://|wss?://|supercell|moco|ClientHello|ServerHello|LoginMessage|connect|socket|handshake|encrypt|decrypt|certificate)', re.I)
    with zipfile.ZipFile(package) as bundle:
        report['metadata'] = json.loads(bundle.read('info.json'))
        report['splits'] = [{'name': e.filename, 'size': e.file_size} for e in bundle.infolist()]
        for split in ('base.apk', 'split_config.arm64_v8a.apk'):
            with zipfile.ZipFile(io.BytesIO(bundle.read(split))) as apk:
                report[split] = [{'name': e.filename, 'size': e.file_size} for e in apk.infolist()]
                for name in apk.namelist():
                    if name.endswith(('/libg.so', '/libsupercell_moco.so')):
                        data = apk.read(name)
                        target = output / name
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_bytes(data)
                        clues = []
                        for match in re.finditer(rb'[\x20-\x7e]{6,}', data):
                            value = match.group().decode('ascii')
                            if len(value) < 1500 and pattern.search(value):
                                clues.append({'offset': hex(match.start()), 'text': value})
                        report['native_clues'][name] = clues
    (output / 'package_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    for name, clues in report['native_clues'].items():
        print(name, 'clues:', len(clues))
        for clue in clues[:35]:
            print(clue['offset'], clue['text'])
    print('Saved analysis/package_report.json; strings are clues, not verified runtime behavior.')


if __name__ == '__main__':
    main()
