import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from assemble_release import assemble


class ReleaseTests(unittest.TestCase):
    def fixture(self, root):
        parts = []
        for index, data in enumerate([b'first', b'second', b'last'], 1):
            name = f'asset.apk.part{index:02}'
            (root/name).write_bytes(data)
            parts.append({'name': name, 'size': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
        content = b'firstsecondlast'
        entry = {'name': 'asset.apk', 'size': len(content),
                 'sha256': hashlib.sha256(content).hexdigest(), 'parts': parts}
        manifest = {'package': 'com.supercell.moco.localtest', 'files': [entry]}
        (root/'release-manifest.json').write_text(json.dumps(manifest))
        return content

    def test_verified_reassembly_and_repeat(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            content = self.fixture(root)
            assemble(root)
            self.assertEqual((root/'asset.apk').read_bytes(), content)
            assemble(root)

    def test_corrupt_part_is_rejected_before_writing(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.fixture(root)
            (root/'asset.apk.part02').write_bytes(b'broken')
            with self.assertRaises(ValueError):
                assemble(root)
            self.assertFalse((root/'asset.apk').exists())

    def test_paths_cannot_escape_download_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.fixture(root)
            path = root/'release-manifest.json'
            manifest = json.loads(path.read_text())
            manifest['files'][0]['name'] = '../outside.apk'
            path.write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):
                assemble(root)
