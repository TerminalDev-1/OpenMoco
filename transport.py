"""Native-evidenced NaCl initial login transport for the 13.5.1 client."""
import hashlib
import hmac
import json
from pathlib import Path
import secrets
from nacl.exceptions import CryptoError
from nacl.public import Box, PrivateKey, PublicKey
from nacl.secret import SecretBox


def load_key(path):
    record = json.loads(Path(path).read_text(encoding='utf-8'))
    key = PrivateKey(bytes.fromhex(record['private_key']))
    if bytes(key.public_key).hex() != record['public_key']:
        raise ValueError('Local server key pair is inconsistent')
    return key


class LoginTransport:
    def __init__(self, server_key, challenge):
        if len(challenge) != 24:
            raise ValueError('Expected 24-byte local challenge')
        self.server_key = server_key
        self.challenge = challenge
        self.client_public = None
        self.client_nonce = None
        self.server_nonce = secrets.token_bytes(24)
        self.session_key = secrets.token_bytes(32)
        self.box = None
        self.reply_sent = False
        self.receive_nonce = None
        self.send_nonce = self.server_nonce

    def decode_login(self, payload):
        if self.box is not None or len(payload) < 32 + 16 + 48:
            raise ValueError('Invalid or duplicate login envelope')
        client_public = payload[:32]
        try:
            box = Box(self.server_key, PublicKey(client_public))
            nonce = hashlib.blake2b(client_public + bytes(self.server_key.public_key), digest_size=24).digest()
            plaintext = box.decrypt(payload[32:], nonce)
        except (CryptoError, ValueError) as error:
            raise ValueError('Login encryption verification failed') from error
        if len(plaintext) < 48 or not hmac.compare_digest(plaintext[:24], self.challenge):
            raise ValueError('Login challenge does not match this connection')
        self.client_public = client_public
        self.client_nonce = plaintext[24:48]
        self.box = box
        return plaintext[48:]

    def encode_initial_reply(self, payload):
        if self.box is None or self.reply_sent:
            raise ValueError('Login must be decoded before a reply')
        nonce = hashlib.blake2b(self.client_nonce + self.client_public + bytes(self.server_key.public_key), digest_size=24).digest()
        result = self.box.encrypt(self.server_nonce + self.session_key + payload, nonce).ciphertext
        self.reply_sent = True
        self.receive_nonce = self.client_nonce
        return result

    @staticmethod
    def advance(nonce):
        # Native 13.5.1 routine 0xfd81f8 adds two, carrying across 24 bytes.
        return ((int.from_bytes(nonce, 'little') + 2) % (1 << 192)).to_bytes(24, 'little')

    def encode_session(self, payload):
        if not self.reply_sent:
            raise ValueError('Initial encrypted reply must precede session traffic')
        self.send_nonce = self.advance(self.send_nonce)
        return SecretBox(self.session_key).encrypt(payload, self.send_nonce).ciphertext

    def decode_session(self, payload):
        if not self.reply_sent:
            raise ValueError('Initial encrypted reply must precede session traffic')
        nonce = self.advance(self.receive_nonce)
        try:
            result = SecretBox(self.session_key).decrypt(payload, nonce)
        except CryptoError as error:
            raise ValueError('Session encryption verification failed') from error
        self.receive_nonce = nonce
        return result
