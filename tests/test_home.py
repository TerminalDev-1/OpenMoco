import unittest
from home import own_home


class HomeTests(unittest.TestCase):
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
