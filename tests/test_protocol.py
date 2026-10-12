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


if __name__ == '__main__':
    unittest.main()
