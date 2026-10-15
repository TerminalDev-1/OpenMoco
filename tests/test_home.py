import unittest
from home import own_home


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
        self.assertEqual(own_home(0), expected)

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
        self.assertEqual([reader.compact() for _ in range(15)], [0] * 15)
        self.assertEqual([reader.compact() for _ in range(3)], [0, 0, 0])  # Suffix.
        self.assertEqual(reader.remaining, 0)

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
