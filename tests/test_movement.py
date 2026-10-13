import unittest

from movement import decode_controller_input, Stick
from stream import Writer


class ControllerInputTests(unittest.TestCase):
    def test_captured_angular_stick_and_release(self):
        moving = decode_controller_input(bytes.fromhex('000004ef000001de008150'))
        self.assertEqual((moving.frame, moving.sequence, moving.controller), (1263, 478, 0))
        self.assertEqual(moving.stick, Stick(0, 0, angle=80))
        released = decode_controller_input(bytes.fromhex('000004f1000001e70080'))
        self.assertEqual(released.stick, Stick(0, 0))

    def test_explicit_coordinates_and_multibyte_controller(self):
        body = Writer().integer(20).integer(30).compact(200).raw(b'\x7b').compact(-16384).compact(8192).bytes()
        value = decode_controller_input(body)
        self.assertEqual(value.controller, 200)
        self.assertEqual(value.stick, Stick(31, 2, x=-16384, y=8192))

    def test_invalid_boundaries(self):
        body = bytes.fromhex('000004ef000001de008150')
        for size in range(len(body)):
            with self.subTest(size=size), self.assertRaises(ValueError):
                decode_controller_input(body[:size])
        with self.assertRaises(ValueError):
            decode_controller_input(body + b'\x00')
        with self.assertRaises(ValueError):
            decode_controller_input(Writer().integer(-1).integer(0).compact(0).raw(b'\x80').bytes())
