import unittest

from scene import apartment_scene, tutorial_scene, monster_tutorial_scene, HOME_SPAWN
from stream import Reader


class SceneTests(unittest.TestCase):
    def test_native_monster_snapshot_and_account_rebinding(self):
        import hashlib
        identity = (128 << 32) | 1
        body = monster_tutorial_scene(identity)
        # Native serializer golden rebound to a synthetic identity, never a
        # private capture identity. Includes the extra character and bit flags.
        self.assertEqual(hashlib.sha256(body).hexdigest(), 'de824bed3661cbe4a620754408e30d56e54f6233a3e16b7e7dda8413bb215356')
        self.assertEqual(len(body), 650)
        for offset in (50, 480):
            self.assertEqual(Reader(body[offset:]).compact(64), identity)
        other = (255 << 32) | 0xffffffff
        changed = monster_tutorial_scene(other)
        self.assertEqual(Reader(changed[50:]).compact(64), other)
        with self.assertRaises(ValueError):
            monster_tutorial_scene(1)

    def test_tutorial_identity_and_native_selection_metadata(self):
        identity = (128 << 32) | 1
        body = tutorial_scene(identity)
        self.assertEqual(len(body), 498)
        self.assertEqual(Reader(body[50:]).compact(64), identity)
        self.assertEqual(Reader(body[329:]).compact(64), identity)
        native_metadata = bytes.fromhex('000000010000000000a652210000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000')
        self.assertEqual(body[-69:-4], native_metadata)
        with self.assertRaises(ValueError):
            tutorial_scene(1)

    def test_account_binding_and_starter_objects(self):
        # Native template identities occur before the player metadata and in it.
        identity = (128 << 32) | 1
        scene = apartment_scene(identity)
        self.assertEqual(len(scene), 521)
        self.assertIn(b'Local Hunter', scene)
        self.assertIn(bytes.fromhex('fb5d268a65c3f9f625886b20e2b934c3'), scene)
        first = Reader(scene[50:])
        self.assertEqual(first.compact(64), identity)
        second = Reader(scene[329:])
        self.assertEqual(second.compact(64), identity)
        self.assertEqual(HOME_SPAWN, (22 * 65536 + 32768, 67 * 65536 + 32768))
        self.assertEqual(len(apartment_scene(identity, portal=False)), 487)

    def test_local_namespace_boundary_and_large_id(self):
        for identity in ((255 << 32) | 0xffffffff, (166 << 32) | 4):
            scene = apartment_scene(identity)
            self.assertIn(b'Local Hunter', scene)
        for identity in (0, 1, 128 << 32, (256 << 32) | 1, -1, 'id'):
            with self.assertRaises(ValueError):
                apartment_scene(identity)
