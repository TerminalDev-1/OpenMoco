import unittest
from stream import Reader, Writer


class StreamTests(unittest.TestCase):
    def test_native_compact_integer_boundaries(self):
        # First byte has six value bits and a separate sign bit.
        vectors = {0: '00', 63: '3f', 64: '8001', -1: '7f', -64: '40',
                   -65: 'ff7e', 900000: 'a0ee6d'}
        for value, encoded in vectors.items():
            wire = bytes.fromhex(encoded)
            self.assertEqual(Writer().compact(value).bytes(), wire)
            self.assertEqual(Reader(wire).compact(), value)
        for bits in (32, 64):
            for value in (-(1 << (bits-1)), (1 << (bits-1))-1):
                self.assertEqual(Reader(Writer().compact(value,bits).bytes()).compact(bits),value)

    def test_boolean_packing_across_intervening_integer_fields(self):
        writer = Writer().boolean(True).boolean(False).boolean(True).compact(64).boolean(True)
        self.assertEqual(writer.bytes(), bytes.fromhex('0d8001'))
        reader = Reader(writer.bytes())
        self.assertEqual([reader.boolean() for _ in range(3)], [True,False,True])
        self.assertEqual(reader.compact(),64)
        self.assertTrue(reader.boolean())
        self.assertEqual(reader.remaining,0)

    def test_malformed_streams_are_rejected(self):
        for wire in (b'',b'\x80',b'\x80'*6,b'\xbf\xff\xff\xff\x7f'):
            with self.assertRaises(ValueError):
                Reader(wire).compact()
        with self.assertRaises(ValueError):
            Reader(bytes.fromhex('fffffffe')).string()
        with self.assertRaises(ValueError):
            Reader(bytes.fromhex('00000004')+b'xx').string()
        with self.assertRaises(ValueError):
            Writer().compact(1 << 31)
