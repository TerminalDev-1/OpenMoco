import hashlib
import unittest
from nacl.public import Box, PrivateKey
from transport import LoginTransport


class TransportTests(unittest.TestCase):
    def fixture(self):
        server, client = PrivateKey.generate(), PrivateKey.generate()
        challenge, client_nonce = bytes(range(24)), bytes(range(24,48))
        box = Box(client, server.public_key)
        nonce = hashlib.blake2b(bytes(client.public_key)+bytes(server.public_key), digest_size=24).digest()
        payload = bytes(client.public_key)+box.encrypt(challenge+client_nonce+b'login body', nonce).ciphertext
        return LoginTransport(server, challenge), box, payload, client_nonce, server, client

    def test_verified_login_and_first_reply(self):
        transport, box, payload, nonce, server, client = self.fixture()
        self.assertEqual(transport.decode_login(payload), b'login body')
        reply = transport.encode_initial_reply(b'reply body')
        reply_nonce = hashlib.blake2b(nonce+bytes(client.public_key)+bytes(server.public_key), digest_size=24).digest()
        self.assertEqual(box.decrypt(reply, reply_nonce), transport.server_nonce+transport.session_key+b'reply body')
        with self.assertRaises(ValueError):
            transport.decode_login(payload)

    def test_tampered_ciphertext_is_rejected(self):
        transport, _, payload, _, _, _ = self.fixture()
        with self.assertRaises(ValueError):
            transport.decode_login(payload[:-1]+bytes([payload[-1]^1]))
        self.assertIsNone(transport.box)

    def test_wrong_challenge_is_rejected(self):
        transport, _, payload, _, _, _ = self.fixture()
        transport.challenge = bytes(24)
        with self.assertRaises(ValueError):
            transport.decode_login(payload)

    def test_wrong_server_key_is_rejected(self):
        transport, _, payload, _, _, _ = self.fixture()
        wrong = LoginTransport(PrivateKey.generate(), transport.challenge)
        with self.assertRaises(ValueError):
            wrong.decode_login(payload)
