import unittest
from home import PLAYER_LEVEL_TRACK, own_home
from progress import XP_LEVELS


class HomeTests(unittest.TestCase):
    def test_tutorial_references_follow_native_collection_order(self):
        # Home encoder 0x77ddd8 -> 0x7966e8 -> 0x7969a0: tutorial then step.
        empty = own_home(1)
        saved = own_home(1, tutorials={'15600001': 14200006, '15600000': 0})
        first = (15600000).to_bytes(8, 'big') + bytes(8)
        second = (15600001).to_bytes(8, 'big') + (14200006).to_bytes(8, 'big')
        position = saved.index(first)
        self.assertEqual(saved[position-1], 2)
        self.assertEqual(saved[position:position+32], first + second)
        self.assertEqual(saved[:position-1] + b'\0' + saved[position+32:], empty)
        with self.assertRaises(ValueError):
            own_home(1, tutorials={'15600000': 14200006})

    def test_native_onboarding_setting_position(self):
        from stream import Reader
        for category in (2, 3):
            body = own_home(1, age_category=category)
            reader = Reader(body[42:])
            self.assertEqual([reader.compact() for _ in range(3)], [0, 0, 0])
            self.assertEqual(reader.compact(), 1)
            self.assertEqual((reader.integer(), reader.integer()), (7, category))
            self.assertEqual(len(body), len(own_home(1)) + 8)

    def test_native_starter_profile_sample(self):
        # Native encoder sample, with all required empty conditional collections
        # present and the evidenced SmartBow selection. No account secrets.
        expected = bytes.fromhex("0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000663be000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000010001000100010001000001000000000000000000000000000000000000000000000000000000")
        self.assertEqual(own_home(0, weapons=()), expected)

    def test_owned_weapons_fill_client_home_78(self):
        # Entries 0x768794 after the +48/+58/+68 counts; verified on the tablet
        # with an exact native decode (stream offset probe) and the WEAPONS list.
        sample = own_home(0, weapons=())
        body = own_home(0)
        entry = (1).to_bytes(1, 'big') + (6700000).to_bytes(8, 'big') + bytes(1) + bytes(8)
        self.assertEqual(len(body), len(sample) + len(entry) - 1)
        self.assertIn(entry, body)

    def test_avatar_resource_follows_native_client_home_tail(self):
        # Native field order after the tutorial collection: client-home
        # 0x77e0b8, avatar 0x77c010, own-home suffix 0x755e34. A tablet probe
        # measured the old encoding: the avatar began 5 bytes early, so the
        # decoder misread the XP reference as a 4-entry key/value collection and
        # read 16 bytes past the 292-byte payload (the Leave Battle SIGSEGV).
        from stream import Reader
        tutorials = {'15600000': 0, '15600001': 14200006}
        body = own_home(1, tutorials=tutorials, xp=1901)
        last = (15600001).to_bytes(8, 'big') + (14200006).to_bytes(8, 'big')
        reader = Reader(body[body.index(last) + len(last):])
        self.assertEqual(reader.raw(16), bytes(16))  # Two raw data references.
        self.assertEqual([reader.compact() for _ in range(3)], [0, 0, 0])
        self.assertEqual((reader.string(), reader.string()), ('', ''))
        self.assertEqual(reader.compact(), 0)  # 0x765d90.
        for _ in range(5):  # Conditional +e0, +120, +18, +20, +28.
            self.assertEqual((reader.bit_boolean(), reader.compact()), (True, 0))
        self.assertEqual(reader.compact(), 0)  # +128 object 0x781f14.
        self.assertEqual((reader.bit_boolean(), reader.compact()), (True, 0))  # +30.
        self.assertEqual([reader.compact() for _ in range(6)], [0] * 6)  # +130 0x7717b0.
        # Avatar: +0, then the resource collection holding XpPoint.
        self.assertEqual((reader.compact(), reader.compact()), (0, 1))
        self.assertEqual(int.from_bytes(reader.raw(8), 'big'), 300020)
        self.assertEqual((reader.integer(), reader.integer()), (1901, 0))
        self.assertEqual([reader.compact() for _ in range(3)], [0] * 3)
        # +40 tracks: one player-level track (0x78b29c) for the home XP badge.
        self.assertEqual(reader.compact(), 1)
        self.assertEqual([reader.compact() for _ in range(5)], [0, 0, 1, 0, -1])
        self.assertEqual(reader.raw(1), bytes(1))  # Six absent optional fields.
        self.assertEqual([reader.compact() for _ in range(5)], [0] * 5)
        self.assertEqual([reader.compact() for _ in range(3)], [1, 0, 0])  # +68 type 1.
        self.assertEqual(reader.raw(8), bytes(8))
        self.assertEqual([reader.compact() for _ in range(2)], [0, 0])
        self.assertEqual(reader.raw(8), bytes(8))
        self.assertEqual([reader.compact() for _ in range(reader.compact())], list(XP_LEVELS))
        self.assertEqual(reader.raw(8), bytes(8))
        self.assertEqual([reader.compact() for _ in range(7)], [0] * 7)
        self.assertEqual((reader.compact(), reader.compact()), (PLAYER_LEVEL_TRACK, 0))
        self.assertEqual([reader.compact() for _ in range(11)], [0] * 11)
        self.assertEqual([reader.compact() for _ in range(3)], [0, 0, 0])  # Suffix.
        self.assertEqual(reader.remaining, 0)

    def test_saved_xp_is_the_player_level_track_record(self):
        # Client-home +e8 (0x78723c) follows the +a0 quest collection; its
        # record 0x788054 keyed by the track ID holds the XP the home HUD reads.
        from stream import Reader
        kit = (6700000).to_bytes(8, 'big')
        for xp, expected in ((0, []), (1901, [PLAYER_LEVEL_TRACK, 1901, 0])):
            body = own_home(1, xp=xp)
            reader = Reader(body[body.rindex(kit) + 8:])
            reader.compact(), reader.compact(), reader.compact(), reader.bit_boolean()
            reader.compact(), reader.compact()
            self.assertEqual([reader.compact() for _ in range(5)], [0] * 5)  # Empty +a0.
            count = reader.compact()
            self.assertEqual(count, 1 if xp else 0)
            if xp:
                self.assertEqual([reader.compact() for _ in range(3)], expected)
                self.assertFalse(reader.bit_boolean())
                self.assertEqual([reader.compact() for _ in range(2)], [0, 0])
                self.assertFalse(reader.bit_boolean())
                self.assertEqual([reader.compact() for _ in range(7)], [0] * 7)
            self.assertEqual(reader.compact(), 0)  # +f0 main quests.

    def test_vanity_items_fill_client_home_e0(self):
        # 0x79716c: count, then entries 0x796ba8 (raw data reference and a
        # compact sub-entry count). The rest of the profile is unchanged.
        from home import STARTER_FACES, STARTER_HAIRSTYLES, STARTER_VANITY
        from stream import Reader
        self.assertEqual((len(STARTER_FACES), len(STARTER_HAIRSTYLES)), (26, 32))
        tutorials = {'15600000': 0, '15600001': 14200006}
        plain = own_home(1, tutorials=tutorials, xp=1901)
        body = own_home(1, tutorials=tutorials, xp=1901, vanity=(2900435, 2900441))
        last = (15600001).to_bytes(8, 'big') + (14200006).to_bytes(8, 'big')
        start = body.index(last) + len(last)
        reader = Reader(body[start:])
        reader.raw(16)
        [reader.compact() for _ in range(3)]
        reader.string(), reader.string()
        reader.compact()
        self.assertEqual((reader.bit_boolean(), reader.compact()), (True, 2))
        for item in (2900435, 2900441):
            self.assertEqual((int.from_bytes(reader.raw(8), 'big'), reader.compact()), (item, 0))
        self.assertEqual(len(body), len(plain) + 2 * 9)
        self.assertEqual(len(own_home(1, vanity=STARTER_VANITY)), len(own_home(1)) + 77 * 9 + 1)  # 77 needs a two-byte count.
        with self.assertRaises(ValueError):
            own_home(1, vanity=(0,))

    def test_equipped_look_fills_current_build_cosmetics(self):
        # Build manager 0x76b378 -> current build 0x769988: two integers, the
        # name, +0x18 dye strings, then +0x40 equipped cosmetic references.
        from home import STARTER_DYES, STARTER_VANITY, equipped_look
        from stream import Reader
        default = equipped_look(None)
        self.assertEqual(default, (2900417, 2900426, 2900422, 2900435))
        chosen = equipped_look({'3': 2900439, '2': 2900443, 'dye_eye': 2900420})
        self.assertEqual(chosen, (2900417, 2900426, 2900420, 2900439, 2900443))
        self.assertEqual(equipped_look({'2': 2900439, 'dye_eye': 2900417}), default)  # Wrong keys.
        body = own_home(1, vanity=STARTER_VANITY, look=chosen)
        index = body.index((2900439).to_bytes(8, 'big') + (2900443).to_bytes(8, 'big'))
        self.assertEqual(body[index - 1], 2)  # +0x40 count.
        dyes = [STARTER_DYES[item][1] for item in chosen[:3]]
        encoded = b''.join(len(d).to_bytes(4, 'big') + d.encode() for d in dyes)
        self.assertEqual(body[index - 1 - len(encoded) - 1:index - 1], bytes([3]) + encoded)
        self.assertEqual(body[index - 1 - len(encoded) - 5:index - 1 - len(encoded) - 1], bytes(4))  # Name ''.
        with self.assertRaises(ValueError):
            own_home(1, look=(2900439,))  # Not owned.

    def test_local_identity_is_in_both_home_id_fields(self):
        identity = (166 << 32) | 4
        encoded = own_home(identity)
        self.assertEqual(int.from_bytes(encoded[8:16], 'big'), identity)
        # The native outer defaults occupy 34 bytes before the client-home ID.
        self.assertEqual(int.from_bytes(encoded[34:42], 'big'), identity)

    def test_invalid_identity_and_unverified_kit_are_rejected(self):
        for identity in (-1, 1 << 64, 'account'):
            with self.assertRaises(ValueError):
                own_home(identity)
        with self.assertRaises(ValueError):
            own_home(1, 11300000)


class PortalTests(unittest.TestCase):
    def _avatar_after_tracks(self, body):
        """Reader positioned after the avatar's +40 tracks (one level track)."""
        from stream import Reader
        levels = b''.join(__import__('stream').Writer().compact(xp).bytes() for xp in XP_LEVELS)
        index = body.index(levels) + len(levels)
        reader = Reader(body[index:])
        reader.raw(8)
        self.assertEqual([reader.compact() for _ in range(7)], [0] * 7)
        self.assertEqual((reader.compact(), reader.compact()), (PLAYER_LEVEL_TRACK, 0))
        return reader

    def test_season_seconds_are_the_level_track_end(self):
        from progress import SEASON_SECONDS, SEASON_START, season_seconds_left
        self.assertEqual(season_seconds_left(SEASON_START), SEASON_SECONDS)
        self.assertEqual(season_seconds_left(SEASON_START + SEASON_SECONDS - 1), 1)
        body = own_home(1, xp=1901, season_seconds=86400)
        self.assertEqual(len(body), len(own_home(1, xp=1901)) + 2)
        self.assertIn(__import__('stream').Writer().compact(86400).bytes(), body)
        with self.assertRaises(ValueError):
            own_home(1, xp=1901, season_seconds=0)

    def test_map_slot_follows_native_entry_0x785f44(self):
        from home import PORTAL_WORLDS, SHRINE_CANYON
        reader = self._avatar_after_tracks(own_home(1, xp=1901, worlds=PORTAL_WORLDS, season_seconds=86400))
        self.assertEqual(reader.compact(), 1)          # +48 map slots.
        self.assertEqual([reader.compact() for _ in range(5)], [0, 0, 0, 86400, 0])  # Active until season end.
        # Six absent versioned fields: two share the track's boolean byte
        # (native reader 0x8d724c keeps its bit position across fields).
        self.assertEqual(reader.raw(1), bytes(1))
        self.assertEqual(reader.compact(), 0)          # +48 list.
        # path/sha object: its three booleans finish that byte's eight.
        self.assertEqual(int.from_bytes(reader.raw(8), 'big'), SHRINE_CANYON)
        self.assertEqual([reader.compact() for _ in range(6)], [0] * 6)
        self.assertEqual((reader.compact(), reader.compact()), (1, 0))  # Slot ID.
        self.assertEqual(reader.raw(8), bytes(8))
        self.assertEqual(reader.compact(), 0)
        self.assertEqual([reader.compact() for _ in range(10 + 3)], [0] * 13)
        self.assertEqual(reader.remaining, 0)
        with self.assertRaises(ValueError):
            own_home(1, worlds=(10900002,))

    def test_no_worlds_keeps_the_previous_layout(self):
        self.assertEqual(own_home(1, xp=1901, worlds=()), own_home(1, xp=1901))
