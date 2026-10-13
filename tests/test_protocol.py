import unittest
from protocol import Frame, FrameDecoder, decode_client_hello, decode_login_prefix, server_hello


class ProtocolTests(unittest.TestCase):
    def test_observed_hello(self):
        payload = bytes.fromhex('000000010000000f0000000d000000010000000500000028')
        payload += b'6bb2cf52ebd2f26a4a7c78154daea6ca2dd371a6'
        payload += bytes.fromhex('0000000200000002ffffffff')
        self.assertEqual(decode_client_hello(payload)['initial_integers'], [1,15,13,1,5])
        for length in range(len(payload)):
            with self.assertRaises(ValueError):
                decode_client_hello(payload[:length])

    def test_fragmented_exchange(self):
        expected = [server_hello(bytes(range(24))), Frame(10101, 9, b'opaque login')]
        wire = b''.join(frame.encode() for frame in expected)
        for size in [1,2,7,13,len(wire)]:
            decoder, actual = FrameDecoder(), []
            for offset in range(0, len(wire), size):
                actual.extend(decoder.feed(wire[offset:offset+size]))
            self.assertEqual(actual, expected)
            self.assertEqual(decoder.pending, b'')

    def test_frame_limits(self):
        with self.assertRaises(ValueError):
            Frame(65536, 0, b'').encode()
        with self.assertRaises(ValueError):
            FrameDecoder(max_payload=1).feed(Frame(10100,0,b'xx').encode())
        with self.assertRaises(ValueError):
            server_hello(b'')

    def test_plaintext_login_prefix(self):
        payload = bytes.fromhex('0000000000000000ffffffff0000000d000000010000000500000028')
        payload += b'6bb2cf52ebd2f26a4a7c78154daea6ca2dd371a6' + b'opaque'
        result = decode_login_prefix(payload)
        self.assertEqual(result['account_id'], 0)
        self.assertFalse(result['token_present'])
        self.assertEqual(result['version_fields'], [13,1,5])
        self.assertEqual(result['remaining_bytes'], 6)
        for length in range(len(payload)-6):
            with self.assertRaises(ValueError):
                decode_login_prefix(payload[:length])


class GameClockTests(unittest.TestCase):
    def test_native_clock_layout_echoes_client_timestamp(self):
        from protocol import game_clock_reply
        from stream import Reader
        response = game_clock_reply(bytes.fromhex('00000000000014b47f'), 5320, 1234)
        self.assertEqual((response.message_type, response.version), (28851, 0))
        reader = Reader(response.payload)
        self.assertEqual(int.from_bytes(reader.raw(8), 'big'), 5300)
        self.assertEqual(int.from_bytes(reader.raw(8), 'big'), 5320)
        self.assertEqual(reader.integer(), 1234)
        self.assertEqual(reader.compact(), -1)
        self.assertEqual(reader.compact(), 0)
        self.assertEqual(reader.remaining, 0)

    def test_invalid_clock_frames_rejected(self):
        from protocol import game_clock_reply
        for payload in (b'', bytes(8), bytes(10)):
            with self.assertRaises(ValueError):
                game_clock_reply(payload, 0)

    def test_frame_ready_flags_and_bounds(self):
        from protocol import decode_frame_ready
        for flags in range(4):
            self.assertEqual(decode_frame_ready(bytes.fromhex('00000123') + bytes([flags])), 291)
        for payload in (b'', bytes(4), bytes(6), bytes.fromhex('ffffffff00'), bytes.fromhex('0000000104')):
            with self.assertRaises(ValueError):
                decode_frame_ready(payload)


if __name__ == '__main__':
    unittest.main()
