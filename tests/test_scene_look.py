import hashlib
import unittest

import scene
from home import STARTER_DYES, equipped_look
from stream import Writer

IDENTITY = (128 << 32) | 1
MARKER = scene.LOOK_MARKER_SKINS + (2900419, 2900424, 2900433)


def uuid_bytes(cosmetic):
    return bytes.fromhex(STARTER_DYES[cosmetic][1].replace('-', ''))


def skins(*items):
    writer = Writer().compact(len(items))
    for item in items:
        writer.compact(item)
    return writer.bytes()


class SceneLookTests(unittest.TestCase):
    def builders(self, look):
        return {'apartment': scene.apartment_scene(IDENTITY, look=look),
                'cool zone': scene.cool_zone_scene(IDENTITY, look=look),
                'downtown': scene.progression_tutorial_scene(IDENTITY, look=look),
                'canyon': scene.canyon_scene(IDENTITY, look=look)}

    def test_marker_look_matches_the_client_re_encodes(self):
        # The client's own re-encodes (look probe, 2026-10-18), rebound to
        # the synthetic identity.
        golden = {'apartment': (751, '8abddd94c216483109b55bd681963b96b7d0790b3de7b5f99ddf4acfe4d83bc3'),
                  'cool zone': (914, '00b435bc31be9c5a9606765e4c935cb9164761e22d339a07a3e509fd4411e60b'),
                  'downtown': (5111, '07e4d3cf634cc718ff31419832f4763c2fc243deeccbd448731fc628f41feccd'),
                  'canyon': (995, 'c41c53df48ae344dc1e20996507e9dd1a81858920a09738af2521196ee618f32')}
        for name, body in self.builders(MARKER).items():
            self.assertEqual((len(body), hashlib.sha256(body).hexdigest()), golden[name], name)
            self.assertEqual(body.count(Writer().compact(IDENTITY, 64).bytes()), 2, name)

    def test_saved_look_replaces_every_marker(self):
        look = equipped_look({'3': 2901580, '2': 2901621, 'dye_skin': 2900415,
                              'dye_eye': 2900420, 'dye_hair': 2900425})
        marked = self.builders(MARKER)
        for name, body in self.builders(look).items():
            self.assertEqual(len(body), len(marked[name]), name)
            # Character skins, metadata skinData and originalSkinData.
            self.assertEqual(body.count(skins(2901580, 2901621)), 3, name)
            self.assertEqual(body.count(skins(*scene.LOOK_MARKER_SKINS)), 0, name)
            for dye in (2900415, 2900420, 2900425):
                self.assertEqual(body.count(uuid_bytes(dye)), 3, name)
            for marker in scene.LOOK_MARKER_DYES.values():
                self.assertNotIn(bytes.fromhex(marker.replace('-', '')), body)

    def test_default_look_without_hairstyle_drops_only_skin_bytes(self):
        look = equipped_look(None)  # The template face and the preset dyes, no hairstyle.
        hair = len(Writer().compact(scene.LOOK_MARKER_SKINS[1]).bytes())
        marked = self.builders(MARKER)
        for name, body in self.builders(look).items():
            self.assertEqual(len(body), len(marked[name]) - 3 * hair, name)
            self.assertEqual(body.count(skins(2900435)), 3, name)

    def test_templates_without_a_look_are_unchanged(self):
        self.assertEqual(len(scene.apartment_scene(IDENTITY)), 586)
        self.assertEqual(len(scene.cool_zone_scene(IDENTITY)), 748)
        self.assertEqual(len(scene.canyon_scene(IDENTITY)), 829)

    def test_home_levels_and_name_around_the_moved_bit_byte(self):
        body = scene.apartment_scene(IDENTITY, level=9, name='hi', look=MARKER)
        identity = Writer().compact(IDENTITY, 64).bytes()
        start = body.rindex(identity) + len(identity)
        # level, the shared boolean byte, realLevel, then the name string.
        self.assertEqual(body[start:start + 9], bytes([9, 0x12, 9]) + (2).to_bytes(4, 'big') + b'hi')
        cool = scene.cool_zone_scene(IDENTITY, level=9, name='hi', look=MARKER)
        start = cool.rindex(identity) + len(identity)
        self.assertEqual(cool[start:start + 3], bytes([9, 0x12, 9]))

    def test_canyon_keeps_jobs_and_xp_with_a_look(self):
        from home import Quest
        from progress import XP_LEVELS
        jobs = [Quest(0, 3, 30, quest_type=1, main=False, map_slot=7)]
        plain = scene.canyon_scene(IDENTITY, jobs, 7, 500, XP_LEVELS)
        looked = scene.canyon_scene(IDENTITY, jobs, 7, 500, XP_LEVELS, look=MARKER)
        tail = len(plain) - 829 + 60
        # The same battle-start tail, then one extra shared boolean byte.
        self.assertEqual(looked[-tail - 1:-1], plain[-tail:])
        self.assertEqual(looked[-1:], b'\0')
        self.assertEqual(scene.battle_scene(IDENTITY, scene.SHRINE_CANYON, jobs, 7, 500, XP_LEVELS, look=MARKER),
                         looked)
        self.assertEqual(scene.battle_scene(IDENTITY, 10900001, look=MARKER),
                         scene.progression_tutorial_scene(IDENTITY, look=MARKER))

    def test_invalid_looks_are_refused(self):
        for look in ((2900434, 2900435, 2900415, 2900420, 2900425),    # two faces
                     (2900434, 2900415, 2900420),                      # no hair dye
                     (2900434, 2900415, 2900416, 2900420, 2900425),    # two skin dyes
                     (2900434, 123, 2900415, 2900420, 2900425)):       # not a starter item
            with self.assertRaises(ValueError):
                scene.apartment_scene(IDENTITY, look=look)
        with self.assertRaises(ValueError):
            scene.apartment_scene(IDENTITY, wardrobe=False, look=MARKER)


if __name__ == '__main__':
    unittest.main()
