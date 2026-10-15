import unittest

from naming import decode_name_change, name_change_result


class NamingTests(unittest.TestCase):
    def test_decodes_captured_sign_payload(self):
        # 17582/v0 captured when the hunter-name screen's SIGN was pressed.
        self.assertEqual(decode_name_change(bytes.fromhex('00000002686901')), ('hi', True))

    def test_rejects_trailing_bytes(self):
        with self.assertRaises(ValueError):
            decode_name_change(bytes.fromhex('0000000268690100'))

    def test_success_reply_layout(self):
        # Native 0x75e8a4: boolean (false = success), int code, string name.
        self.assertEqual(name_change_result('hi'), bytes.fromhex('00' '00000000' '00000002' '6869'))

    def test_failure_reply_sets_flag_and_code(self):
        self.assertEqual(name_change_result('hi', failed=True, code=3)[:5], bytes.fromhex('0100000003'))


if __name__ == '__main__':
    unittest.main()


class OwnHomeNameTests(unittest.TestCase):
    def test_unnamed_home_keeps_empty_name_and_clear_flag(self):
        from home import own_home
        body = own_home(1)
        self.assertEqual(body[16:22], bytes.fromhex('00' '00000000' '00'))

    def test_named_home_sets_name_and_flag(self):
        from home import own_home
        body = own_home(1, name='hi')
        self.assertEqual(body[16:24], bytes.fromhex('00' '00000002' '6869' '01'))
        self.assertEqual(body[24:], own_home(1)[22:])

    def test_rejects_invalid_name(self):
        from home import own_home
        with self.assertRaises(ValueError):
            own_home(1, name='')


class SceneNameTests(unittest.TestCase):
    def test_apartment_nameplate_uses_saved_name(self):
        from scene import apartment_scene
        identity = (128 << 32) | 1
        default = apartment_scene(identity)
        named = apartment_scene(identity, name='hi')
        self.assertNotIn(b'Local Hunter', named)
        self.assertIn(b'\x00\x00\x00\x02hi\x00', named)
        self.assertEqual(len(named), len(default) - 10)
        with self.assertRaises(ValueError):
            apartment_scene(identity, name='')
