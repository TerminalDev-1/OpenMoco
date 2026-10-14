import asyncio
import json
from pathlib import Path
import tempfile
import unittest
import hashlib
from nacl.public import Box, PrivateKey
from nacl.secret import SecretBox
from accounts import AccountStore
from transport import LoginTransport
from protocol import Frame, FrameDecoder
from server import capture
from home import own_home
from scene import apartment_scene, encounter_tutorial_scene as tutorial_scene


class ServerTests(unittest.IsolatedAsyncioTestCase):
    async def test_encrypted_guest_reply_reconnect_and_keepalive(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = AccountStore(root/'accounts.sqlite3')
            key = PrivateKey.generate()
            async def exchange(identity, token):
                output = root/str(identity)
                output.mkdir(exist_ok=True)
                finished = asyncio.get_running_loop().create_future()
                async def connected(reader, writer):
                    try:
                        await capture(reader, writer, output, True, key, store, apartment=True)
                        finished.set_result(None)
                    except Exception as error:
                        finished.set_exception(error)
                listener = await asyncio.start_server(connected, '127.0.0.1', 0)
                try:
                    reader, writer = await asyncio.open_connection('127.0.0.1', listener.sockets[0].getsockname()[1])
                    async def read_frame():
                        header = await asyncio.wait_for(reader.readexactly(7), 2)
                        return FrameDecoder().feed(header+await reader.readexactly(int.from_bytes(header[2:5], 'big')))[0]
                    def string(value):
                        return (-1).to_bytes(4,'big',signed=True) if value is None else len(value.encode()).to_bytes(4,'big')+value.encode()
                    hello = bytes.fromhex('000000010000000f0000000d000000010000000500000028')
                    hello += b'6bb2cf52ebd2f26a4a7c78154daea6ca2dd371a6' + bytes.fromhex('0000000200000002ffffffff')
                    writer.write(Frame(10100,0,hello).encode())
                    challenge = (await read_frame()).payload[4:]
                    client = PrivateKey.generate()
                    box = Box(client,key.public_key)
                    nonce = bytes(range(24))
                    body = identity.to_bytes(8,'big') + string(token) + bytes.fromhex('0000000d0000000100000005') + string('local')
                    login_nonce = hashlib.blake2b(bytes(client.public_key)+bytes(key.public_key),digest_size=24).digest()
                    writer.write(Frame(10101,9,bytes(client.public_key)+box.encrypt(challenge+nonce+body,login_nonce).ciphertext).encode())
                    reply = await read_frame()
                    self.assertEqual((reply.message_type,reply.version),(29125,1))
                    reply_nonce = hashlib.blake2b(nonce+bytes(client.public_key)+bytes(key.public_key),digest_size=24).digest()
                    plain = box.decrypt(reply.payload,reply_nonce)
                    server_nonce,session_key,payload = plain[:24],plain[24:56],plain[56:]
                    new_id = int.from_bytes(payload[:8],'big')
                    token_size = int.from_bytes(payload[16:20],'big')
                    new_token = payload[20:20+token_size].decode()
                    cipher = SecretBox(session_key)
                    profile = await read_frame()
                    self.assertEqual(profile.message_type, 24548)
                    server_nonce = LoginTransport.advance(server_nonce)
                    profile_body = cipher.decrypt(profile.payload, server_nonce)
                    progress = {'15600000': 0, '15600001': 14200006} if identity else {}
                    self.assertEqual(profile_body, own_home(new_id, age_category=2 if identity else 0, tutorials=progress))
                    scene = await read_frame()
                    self.assertEqual((scene.message_type, scene.version), (23491, 0))
                    server_nonce = LoginTransport.advance(server_nonce)
                    self.assertEqual(cipher.decrypt(scene.payload, server_nonce), tutorial_scene(new_id) if identity else apartment_scene(new_id))
                    writer.write(Frame(10108,0,cipher.encrypt(b'',LoginTransport.advance(nonce)).ciphertext).encode())
                    keepalive = await read_frame()
                    self.assertEqual(keepalive.message_type,20108)
                    self.assertEqual(cipher.decrypt(keepalive.payload,LoginTransport.advance(server_nonce)),b'')
                    send_nonce = LoginTransport.advance(nonce)
                    receive_nonce = LoginTransport.advance(server_nonce)
                    if not identity:
                        from stream import Writer
                        choice = Writer().compact(0).raw(bytes(8)).compact(1).integer(541)
                        choice.boolean(False).boolean(False).boolean(False).integer(16)
                        send_nonce = LoginTransport.advance(send_nonce)
                        writer.write(Frame(16543, 0, cipher.encrypt(choice.bytes(), send_nonce).ciphertext).encode())
                        for tutorial, step in [(15600000, 0), (15600001, 14200006)]:
                            command = Writer().compact(0).raw(bytes(8)).compact(1).integer(574)
                            command.boolean(False).boolean(False).boolean(False).compact(tutorial, 64).compact(step, 64)
                            send_nonce = LoginTransport.advance(send_nonce)
                            writer.write(Frame(16543, 0, cipher.encrypt(command.bytes(), send_nonce).ciphertext).encode())
                    for client_frame in (1234, 1200):
                        send_nonce = LoginTransport.advance(send_nonce)
                        frame_ready = client_frame.to_bytes(4, 'big') + b'\x00'
                        writer.write(Frame(18853, 0, cipher.encrypt(frame_ready, send_nonce).ciphertext).encode())
                        send_nonce = LoginTransport.advance(send_nonce)
                        request_clock = bytes.fromhex('00000000000014b47f')
                        writer.write(Frame(18851, 0, cipher.encrypt(request_clock, send_nonce).ciphertext).encode())
                        await writer.drain()
                        clock_reply = await read_frame()
                        self.assertEqual(clock_reply.message_type, 28851)
                        receive_nonce = LoginTransport.advance(receive_nonce)
                        clock_body = cipher.decrypt(clock_reply.payload, receive_nonce)
                        self.assertEqual(clock_body[:8], request_clock[:8])
                        self.assertEqual(int.from_bytes(clock_body[16:20], 'big'), 1234)
                        transport_keepalive = await read_frame()
                        self.assertEqual(transport_keepalive.message_type, 20108)
                        receive_nonce = LoginTransport.advance(receive_nonce)
                        self.assertEqual(cipher.decrypt(transport_keepalive.payload, receive_nonce), b'')
                    selection = bytes.fromhex('000000000000a65221000000000000000000000000000000000000000000')
                    if not identity:
                        send_nonce = LoginTransport.advance(send_nonce)
                        writer.write(Frame(13222, 0, cipher.encrypt(selection, send_nonce).ciphertext).encode())
                        await writer.drain()
                        destination = await read_frame()
                        self.assertEqual((destination.message_type, destination.version), (23491, 0))
                        receive_nonce = LoginTransport.advance(receive_nonce)
                        self.assertEqual(cipher.decrypt(destination.payload, receive_nonce), tutorial_scene(new_id))
                    # Repeated selections must not insert a second scene into
                    # the encrypted stream or disrupt the following keepalive.
                    send_nonce = LoginTransport.advance(send_nonce)
                    writer.write(Frame(13222, 0, cipher.encrypt(selection, send_nonce).ciphertext).encode())
                    send_nonce = LoginTransport.advance(send_nonce)
                    writer.write(Frame(10108, 0, cipher.encrypt(b'', send_nonce).ciphertext).encode())
                    await writer.drain()
                    keepalive = await read_frame()
                    self.assertEqual(keepalive.message_type, 20108)
                    receive_nonce = LoginTransport.advance(receive_nonce)
                    self.assertEqual(cipher.decrypt(keepalive.payload, receive_nonce), b'')
                    send_nonce = LoginTransport.advance(send_nonce)
                    writer.write(Frame(13223, 0, cipher.encrypt(b'\x00', send_nonce).ciphertext).encode())
                    await writer.drain()
                    returned_profile, returned_scene = await read_frame(), await read_frame()
                    self.assertEqual(returned_profile.message_type, 24548)
                    receive_nonce = LoginTransport.advance(receive_nonce)
                    self.assertEqual(cipher.decrypt(returned_profile.payload, receive_nonce), own_home(new_id, age_category=2, tutorials={'15600000': 0, '15600001': 14200006}))
                    self.assertEqual(returned_scene.message_type, 23491)
                    receive_nonce = LoginTransport.advance(receive_nonce)
                    self.assertEqual(cipher.decrypt(returned_scene.payload, receive_nonce), apartment_scene(new_id))
                    self.assertEqual(store.authenticate(new_id, new_token).profile['scene_id'], 10900000)
                    # A duplicate leave and unsupported options cannot alter
                    # the encrypted response order or disconnect the session.
                    for options in (b'\x00', b'\x04'):
                        send_nonce = LoginTransport.advance(send_nonce)
                        writer.write(Frame(13223, 0, cipher.encrypt(options, send_nonce).ciphertext).encode())
                    send_nonce = LoginTransport.advance(send_nonce)
                    writer.write(Frame(10108, 0, cipher.encrypt(b'', send_nonce).ciphertext).encode())
                    await writer.drain()
                    keepalive = await read_frame()
                    self.assertEqual(keepalive.message_type, 20108)
                    receive_nonce = LoginTransport.advance(receive_nonce)
                    self.assertEqual(cipher.decrypt(keepalive.payload, receive_nonce), b'')
                    # End in the tutorial to exercise saved-scene restoration
                    # during the next authenticated reconnect.
                    send_nonce = LoginTransport.advance(send_nonce)
                    writer.write(Frame(13222, 0, cipher.encrypt(selection, send_nonce).ciphertext).encode())
                    await writer.drain()
                    destination = await read_frame()
                    receive_nonce = LoginTransport.advance(receive_nonce)
                    self.assertEqual(cipher.decrypt(destination.payload, receive_nonce), tutorial_scene(new_id))
                    writer.close()
                    await writer.wait_closed()
                    await asyncio.wait_for(finished,2)
                    metadata = json.loads(next(output.glob('*.json')).read_text())
                    self.assertNotIn(new_token,json.dumps(metadata))
                    self.assertEqual(metadata['frames'][-1]['decrypted_bytes'], len(selection))
                    self.assertEqual(metadata['state'], 'tutorial_scene_sent')
                    return new_id,new_token,metadata['local_account']['created']
                finally:
                    listener.close()
                    await listener.wait_closed()
            identity,token,created = await exchange(0,None)
            self.assertTrue(created)
            self.assertEqual(await exchange(identity,token),(identity,token,False))

    async def exchange(self, frames):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            finished = asyncio.get_running_loop().create_future()
            async def connected(reader, writer):
                try:
                    await capture(reader, writer, output, handshake=True)
                    finished.set_result(None)
                except Exception as error:
                    finished.set_exception(error)
            listener = await asyncio.start_server(connected, '127.0.0.1', 0)
            port = listener.sockets[0].getsockname()[1]
            try:
                reader, writer = await asyncio.open_connection('127.0.0.1', port)
                writer.write(frames[0].encode())
                await writer.drain()
                header = await asyncio.wait_for(reader.read(7), 2)
                if header:
                    self.assertEqual(len(header), 7)
                    payload = await asyncio.wait_for(reader.readexactly(int.from_bytes(header[2:5], 'big')), 2)
                    response = FrameDecoder().feed(header + payload)[0]
                    for frame in frames[1:]:
                        writer.write(frame.encode())
                    await writer.drain()
                else:
                    response = None
                writer.close()
                await writer.wait_closed()
                await asyncio.wait_for(finished, 2)
                metadata = json.loads(next(output.glob('*.json')).read_text())
                raw = next(p for p in output.glob('*.bin') if '.server.' not in p.name).read_bytes()
                return response, metadata, raw
            finally:
                listener.close()
                await listener.wait_closed()

    async def test_hello_then_login_capture(self):
        hello = bytes.fromhex('000000010000000f0000000d000000010000000500000028')
        hello += b'6bb2cf52ebd2f26a4a7c78154daea6ca2dd371a6' + bytes.fromhex('0000000200000002ffffffff')
        frames = [Frame(10100,0,hello), Frame(10101,9,bytes(range(48)))]
        response, metadata, raw = await self.exchange(frames)
        self.assertEqual((response.message_type, response.version), (20100,0))
        self.assertEqual(response.payload[:4], (24).to_bytes(4,'big'))
        self.assertEqual(len(response.payload), 28)
        self.assertEqual(metadata['state'], 'encrypted_login_received')
        self.assertIsNone(metadata['framing_error'])
        self.assertEqual(raw, b''.join(frame.encode() for frame in frames))

    async def test_login_cannot_skip_hello(self):
        response, metadata, _ = await self.exchange([Frame(10101,9,bytes(48))])
        self.assertIsNone(response)
        self.assertEqual(metadata['close_reason'], 'protocol_error')
        self.assertEqual(metadata['sent_frames'], [])

    async def test_quiet_socket_survives_the_original_idle_cutoff(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            finished = asyncio.get_running_loop().create_future()
            async def connected(reader, writer):
                await capture(reader, writer, output)
                finished.set_result(None)
            listener = await asyncio.start_server(connected, '127.0.0.1', 0)
            reader, writer = await asyncio.open_connection('127.0.0.1', listener.sockets[0].getsockname()[1])
            try:
                await asyncio.sleep(31)
                self.assertFalse(finished.done(), 'Server closed a quiet manual-testing socket')
                wire = Frame(10108, 0, b'').encode()
                writer.write(wire)
                await writer.drain()
                writer.close()
                await writer.wait_closed()
                await asyncio.wait_for(finished, 2)
                self.assertEqual(next(output.glob('*.bin')).read_bytes(), wire)
                record = json.loads(next(output.glob('*.json')).read_text())
                self.assertEqual(record['close_reason'], 'peer_closed')
            finally:
                writer.close()
                listener.close()
                await listener.wait_closed()
