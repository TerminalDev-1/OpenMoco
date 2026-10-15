import unittest
from stream import Writer

from scene import apartment_scene, tutorial_scene, monster_tutorial_scene, populated_tutorial_scene, encounter_tutorial_scene, HOME_SPAWN
from stream import Reader


class SceneTests(unittest.TestCase):
    def test_progression_snapshot_native_golden_and_account_binding(self):
        import hashlib
        from stream import Writer
        from scene import progression_tutorial_scene
        identity = (128 << 32) | 1
        body = progression_tutorial_scene(identity)
        self.assertEqual(len(body), 4946)
        self.assertEqual(hashlib.sha256(body).hexdigest(), '0dbc514f5e365f7287c11bfdca59922274d39df80a9900f8bfee65c263862b72')
        for offset in (50, 4776):
            self.assertEqual(Reader(body[offset:]).compact(64), identity)
        other = (255 << 32) | 0xffffffff
        changed = progression_tutorial_scene(other)
        self.assertEqual(Reader(changed[50:]).compact(64), other)
        self.assertEqual(changed.count(Writer().compact(other, 64).bytes()), 2)
        for invalid in (0, 1, True, 'local'):
            with self.assertRaises(ValueError):
                progression_tutorial_scene(invalid)
    def test_native_recurring_encounters_and_identity(self):
        import hashlib
        from stream import Writer
        identity = (128 << 32) | 1
        body = encounter_tutorial_scene(identity)
        self.assertEqual(len(body), 4395)
        self.assertEqual(hashlib.sha256(body).hexdigest(), '902ad777eb1bcbcffed49d12747867e210dd86f38471d5585451206c2fa55e14')
        for offset in (50, 4225):
            self.assertEqual(Reader(body[offset:]).compact(64), identity)
        other = (255 << 32) | 0xffffffff
        self.assertEqual(encounter_tutorial_scene(other), body.replace(
            Writer().compact(identity, 64).bytes(), Writer().compact(other, 64).bytes()))
        self.assertIn(tutorial_scene(other)[-69:-4], encounter_tutorial_scene(other))
        with self.assertRaises(ValueError):
            encounter_tutorial_scene(1)

    def test_native_population_snapshot_and_account_rebinding(self):
        import hashlib
        from stream import Writer
        identity = (128 << 32) | 1
        body = populated_tutorial_scene(identity)
        # Full native-encoder golden: twelve enemies and six RunningNpc
        # civilians, with health/gear/faction and initial spawn IDs preserved.
        self.assertEqual(len(body), 3104)
        self.assertEqual(hashlib.sha256(body).hexdigest(), 'a1d45249710edf1c43aaa6b9f6926016d6d13a98b6b048dd59a848558d5007a2')
        for offset in (50, 2934):
            self.assertEqual(Reader(body[offset:]).compact(64), identity)
        other = (255 << 32) | 0xffffffff
        changed = populated_tutorial_scene(other)
        original_identity = Writer().compact(identity, 64).bytes()
        replacement = Writer().compact(other, 64).bytes()
        self.assertEqual(changed, body.replace(original_identity, replacement))
        # The native frame has an additional trailing flag here; the embedded
        # battle-selection configuration itself must still match exactly.
        self.assertIn(tutorial_scene(other)[-69:-4], changed)
        for invalid in (1, 0, True, 'local', (127 << 32) | 1):
            with self.assertRaises(ValueError):
                populated_tutorial_scene(invalid)

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
        # Player metadata level/realLevel follow the linked identity.
        identity_bytes = Writer().compact(identity, 64).bytes()
        for level in (1, 4, 63):
            body = apartment_scene(identity, level=level)
            start = body.rindex(identity_bytes) + len(identity_bytes)
            self.assertEqual(body[start:start + 3], bytes([level, level, 2]))
            self.assertEqual(len(body), len(apartment_scene(identity)))
        with self.assertRaises(ValueError):
            apartment_scene(identity, level=64)
        self.assertEqual(len(apartment_scene(identity, portal=False)), 487)

    def test_local_namespace_boundary_and_large_id(self):
        for identity in ((255 << 32) | 0xffffffff, (166 << 32) | 4):
            scene = apartment_scene(identity)
            self.assertIn(b'Local Hunter', scene)
        for identity in (0, 1, 128 << 32, (256 << 32) | 1, -1, 'id'):
            with self.assertRaises(ValueError):
                apartment_scene(identity)
