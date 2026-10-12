"""Native-evidenced NaCl initial login transport for the 13.5.1 client."""
import hashlib
import hmac
import json
from pathlib import Path
import secrets
from nacl.exceptions import CryptoError
from nacl.public import Box, PrivateKey, PublicKey


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
        if self.box is None:
            raise ValueError('Login must be decoded before a reply')
        nonce = hashlib.blake2b(self.client_nonce + self.client_public + bytes(self.server_key.public_key), digest_size=24).digest()
        return self.box.encrypt(self.server_nonce + self.session_key + payload, nonce).ciphertext
