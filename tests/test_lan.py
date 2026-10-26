import asyncio
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from nacl.public import Box, PrivateKey
from nacl.secret import SecretBox

from accounts import AccountStore
from protocol import Frame, FrameDecoder
from server import home_network_peer, start
from transport import LoginTransport

HELLO = (bytes.fromhex('000000010000000f0000000d000000010000000500000028') +
         b'6bb2cf52ebd2f26a4a7c78154daea6ca2dd371a6' + bytes.fromhex('0000000200000002ffffffff'))


class GuestClient:
    """A minimal test client: hello, guest login, then encrypted keepalives."""

    def __init__(self, port, server_key):
        self.port, self.server_key = port, server_key

    async def read_frame(self):
        header = await asyncio.wait_for(self.reader.readexactly(7), 5)
        size = int.from_bytes(header[2:5], 'big')
        return FrameDecoder().feed(header + await self.reader.readexactly(size))[0]

    async def login(self):
        self.reader, self.writer = await asyncio.open_connection('127.0.0.1', self.port)
        self.writer.write(Frame(10100, 0, HELLO).encode())
        challenge = (await self.read_frame()).payload[4:]
        client = PrivateKey.generate()
        box = Box(client, self.server_key.public_key)
        nonce = bytes(range(24))
        body = (0).to_bytes(8, 'big') + (-1).to_bytes(4, 'big', signed=True)
        body += bytes.fromhex('0000000d0000000100000005') + (5).to_bytes(4, 'big') + b'local'
        login_nonce = hashlib.blake2b(bytes(client.public_key) + bytes(self.server_key.public_key), digest_size=24).digest()
        self.writer.write(Frame(10101, 9, bytes(client.public_key) +
                                box.encrypt(challenge + nonce + body, login_nonce).ciphertext).encode())
        reply = await self.read_frame()
        assert (reply.message_type, reply.version) == (29125, 1)
        reply_nonce = hashlib.blake2b(nonce + bytes(client.public_key) + bytes(self.server_key.public_key), digest_size=24).digest()
        plain = box.decrypt(reply.payload, reply_nonce)
        self.receive_nonce, self.cipher = plain[:24], SecretBox(plain[24:56])
        self.send_nonce = nonce
        self.account = int.from_bytes(plain[56:64], 'big')
        for expected in (24548, 23491):  # Own home, then the starting scene.
            frame = await self.read_frame()
            assert frame.message_type == expected
            self.receive_nonce = LoginTransport.advance(self.receive_nonce)
            self.cipher.decrypt(frame.payload, self.receive_nonce)
        return self.account

    async def keepalive(self):
        self.send_nonce = LoginTransport.advance(self.send_nonce)
        self.writer.write(Frame(10108, 0, self.cipher.encrypt(b'', self.send_nonce).ciphertext).encode())
        reply = await self.read_frame()
        self.receive_nonce = LoginTransport.advance(self.receive_nonce)
        return reply.message_type, self.cipher.decrypt(reply.payload, self.receive_nonce)

    def close(self):
        self.writer.close()


@mock.patch('progress.season_seconds_left', lambda now: 86400)
class HomeNetworkTests(unittest.IsolatedAsyncioTestCase):
    async def test_several_devices_play_at_once_with_their_own_guest_accounts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            key = PrivateKey.generate()
            server = await start('127.0.0.1', 0, root / 'captures', True, key,
                                 AccountStore(root / 'accounts.sqlite3'), apartment=True, lan_only=True)
            port = server.sockets[0].getsockname()[1]
            clients = [GuestClient(port, key) for _ in range(3)]
            try:
                # All three log in at the same time and stay connected together.
                accounts = await asyncio.gather(*(client.login() for client in clients))
                self.assertEqual(len(set(accounts)), 3)
                for _ in range(2):
                    replies = await asyncio.gather(*(client.keepalive() for client in reversed(clients)))
                    self.assertEqual(replies, [(20108, b'')] * 3)
                # One device leaving does not end the others' sessions.
                clients[0].close()
                self.assertEqual(await clients[2].keepalive(), (20108, b''))
                self.assertEqual(await clients[1].keepalive(), (20108, b''))
            finally:
                for client in clients:
                    client.close()
                server.close()
                await server.wait_closed()

    def test_home_network_peers(self):
        for address in ('127.0.0.1', '192.168.1.20', '10.0.0.5', '172.16.4.2', '::1',
                        'fe80::1%12', '::ffff:192.168.1.20', 'fd00::5'):
            self.assertTrue(home_network_peer(address), address)
        for address in ('8.8.8.8', '2001:4860:4860::8888', '::ffff:8.8.8.8', 'not an address'):
            self.assertFalse(home_network_peer(address), address)

    async def test_internet_peers_are_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            server = await start('127.0.0.1', 0, Path(directory), lan_only=True)
            port = server.sockets[0].getsockname()[1]
            try:
                with mock.patch('server.home_network_peer', return_value=False):
                    reader, writer = await asyncio.open_connection('127.0.0.1', port)
                    self.assertEqual(await asyncio.wait_for(reader.read(), 5), b'')
                    writer.close()
                self.assertEqual(list(Path(directory).glob('*.json')), [])
            finally:
                server.close()
                await server.wait_closed()


if __name__ == '__main__':
    unittest.main()
