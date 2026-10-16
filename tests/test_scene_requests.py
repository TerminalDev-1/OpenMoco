import unittest

from scene_requests import decode_scene_request
from stream import Writer


class SceneRequestTests(unittest.TestCase):
    def test_captured_tutorial_request(self):
        body = bytes.fromhex('000000000000a65221000000000000000000000000000000000000000000')
        request = decode_scene_request(body)
        self.assertEqual(request.scene_id, 10900001)
        self.assertEqual(request.auxiliary, (0, 0))
        self.assertEqual((request.data_reference_a, request.data_reference_b), (0, 0))
        self.assertFalse(request.flag)
        self.assertFalse(request.final_flag)

    def test_initial_request_with_selected_kit(self):
        writer = Writer().bit_boolean(True).raw((10900005).to_bytes(8, 'big'))
        for _ in range(3):
            writer.bit_boolean(False)
        body = writer.compact(0).compact(0).raw(bytes(8)).raw((6700000).to_bytes(8, 'big')).compact(0).bit_boolean(False).bytes()
        request = decode_scene_request(body)
        self.assertTrue(request.flag)
        self.assertEqual(request.data_reference_b, 6700000)

    def test_truncated_and_unimplemented_requests(self):
        body = bytes.fromhex('000000000000a65221000000000000000000000000000000000000000000')
        for size in range(len(body)):
            with self.subTest(size=size), self.assertRaises(ValueError):
                decode_scene_request(body[:size])
        for changed in (body+b'\x00', body[:9]+b'\x01'+body[10:], body[:28]+b'\x01'+body[29:]):
            with self.assertRaises(ValueError):
                decode_scene_request(changed)


class MapSlotRequestTests(unittest.TestCase):
    def test_portal_map_card_battle_request(self):
        # Captured BATTLE press on the Shrine Canyon card (slot 1), 2026-10-16.
        from scene_requests import decode_scene_request
        request = decode_scene_request(bytes.fromhex(
            '000000000000a652260401000000000000000000000000000000000000000000'))
        self.assertFalse(request.flag)
        self.assertEqual(request.scene_id, 10900006)
        self.assertEqual(request.map_slot, (1, 0))
        self.assertEqual(request.auxiliary, (0, 0))
