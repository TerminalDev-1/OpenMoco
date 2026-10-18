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
        self.assertEqual(len(scene), 586)
        self.assertIn(bytes.fromhex('fb5d268ade98e5c01ea755b7ad5b0c80'), scene)  # Weapons rack prefab.
        self.assertIn(bytes.fromhex('8291d8bf0100b1c8a201a484aa04'), scene)  # Item 201000002 at its marker.
        self.assertEqual(len(apartment_scene(identity, armoury=False)), 553)
        self.assertIn(b'Local Hunter', scene)
        self.assertIn(bytes.fromhex('fb5d268a65c3f9f625886b20e2b934c3'), scene)  # Portal prefab.
        self.assertIn(bytes.fromhex('fb5d268a12b06052d20f1eaf3a4c7f5c'), scene)  # Wardrobe prefab.
        self.assertEqual(len(apartment_scene(identity, wardrobe=False)), 521)
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


class BattleSceneTests(unittest.TestCase):
    def test_shrine_canyon_native_golden_spawn_zones_and_identity(self):
        import hashlib
        from scene import canyon_scene
        identity = (128 << 32) | 1
        body = canyon_scene(identity)
        self.assertEqual(len(body), 829)
        self.assertEqual(hashlib.sha256(body).hexdigest(), '05643ca21d5eeee9ba393ac2cb5b88574be9b640b334ad64bef8c338d50b8b6c')
        self.assertEqual(body[1:9], Writer().compact(10900006).bytes() * 2)
        self.assertEqual(body.count((10900006).to_bytes(8, 'big')), 1)
        self.assertNotIn((10900001).to_bytes(8, 'big'), body)
        for offset in (50, 660):
            self.assertEqual(Reader(body[offset:]).compact(64), identity)
        # Player at the canyon spawn marker, tile (63,99), centered.
        spawn = Writer().compact((63 << 16) | 0x8000).compact((99 << 16) | 0x8000).bytes()
        self.assertEqual(body.count(spawn), 5)
        self.assertNotIn(Writer().compact(3964928).compact(4751360).bytes(), body)
        # Sixteen native Zone entities; each carries its zone data ID twice.
        zones = (1700149, 1700150, 1700151, 1700152, 1700153, 1700154, 1700155, 1700156,
                 1700157, 1700158, 1700159, 1700160, 1700161, 1700162, 1700164, 1700165)
        for zone in zones:
            self.assertEqual(body.count(Writer().compact(zone).bytes()), 2, zone)
        other = (255 << 32) | 0xffffffff
        self.assertEqual(canyon_scene(other).count(Writer().compact(other, 64).bytes()), 2)
        for invalid in (0, 1, True, 'local'):
            with self.assertRaises(ValueError):
                canyon_scene(invalid)

    def test_battle_scene_dispatch(self):
        from scene import battle_scene, canyon_scene, progression_tutorial_scene
        account = (200 << 32) | 4
        self.assertEqual(battle_scene(account, 10900001), progression_tutorial_scene(account))
        self.assertEqual(battle_scene(account, 10900006), canyon_scene(account))
        with self.assertRaises(ValueError):
            battle_scene(account, 10900002)


class CoolZoneTests(unittest.TestCase):
    def test_cool_zone_is_the_renamed_home_with_its_key_items(self):
        from scene import COOL_ZONE_SPAWN, SOCIAL_HUB, cool_zone_scene
        identity = (128 << 32) | 1
        body = cool_zone_scene(identity)
        hub = Writer().compact(SOCIAL_HUB).bytes()
        self.assertEqual(body[1:1 + 2 * len(hub)], hub * 2)
        spawn = Writer().compact(COOL_ZONE_SPAWN[0]).bytes() + Writer().compact(COOL_ZONE_SPAWN[1]).bytes()
        self.assertEqual(body.count(spawn), 5)
        self.assertEqual(body.count(Writer().compact(identity, 64).bytes()), 2)
        self.assertEqual(body.count(bytes.fromhex('d8bf01')), 8)  # Eight HomeItem 2010 IDs.
        named = cool_zone_scene(identity, level=4, name='hi')
        self.assertIn(b'\x00\x00\x00\x02hi', named)
        self.assertEqual(len(named), len(body) - 10)
        with self.assertRaises(ValueError):
            cool_zone_scene(identity, level=64)

    def test_cool_zone_unlocks_with_the_to_hq_tutorial(self):
        from progress import cool_zone_unlocked
        self.assertFalse(cool_zone_unlocked({'tutorials': {'15600007': 0}}))
        self.assertTrue(cool_zone_unlocked({'tutorials': {'15600009': 0}}))
        self.assertFalse(cool_zone_unlocked({}))


class CanyonJobsTests(unittest.TestCase):
    def test_battle_config_carries_jobs_and_map_slot(self):
        from home import Quest
        from scene import canyon_scene
        from stream import Reader
        account = (0x80 << 32) | 5
        plain = canyon_scene(account)
        job = Quest(0, 3, 8, locations=(10800027,), main=False, map_slot=1)
        body = canyon_scene(account, (job,), 1)
        ref = (10900006).to_bytes(8, 'big')
        start = plain.rindex(ref) + 8
        self.assertEqual(body[:start], plain[:start])
        reader = Reader(body[start:])
        self.assertEqual([reader.bit_boolean() for _ in range(3)], [False, False, True])
        self.assertEqual([reader.compact() for _ in range(4)], [1, 0, 0, 0])  # slot, +20, two compacts
        self.assertEqual((reader.compact(), reader.raw(8)), (0, bytes(8)))    # holder list, reference
        self.assertEqual([reader.compact() for _ in range(5)], [1, 0, 0, 0, 1])  # quest header, count
        self.assertEqual([reader.compact() for _ in range(4)], [0, 1, 3, 8])  # ID, type, progress, target
        self.assertTrue(body.endswith(plain[-40:]))

    def test_battle_config_carries_xp_and_level_table(self):
        from scene import canyon_scene
        from stream import Writer
        account = (0x80 << 32) | 5
        plain = canyon_scene(account)
        body = canyon_scene(account, xp=5901, levels=(100, 200))
        start = plain.rindex((10900006).to_bytes(8, 'big')) - 4
        config = Writer().compact(5901).compact(2).compact(100).compact(200).bytes()
        self.assertEqual(body, plain[:start] + config + plain[start + 2:])
        self.assertEqual(canyon_scene(account, xp=5901), plain)   # No table: unchanged.
        with self.assertRaises(ValueError):
            canyon_scene(account, xp=1, levels=(0,))
