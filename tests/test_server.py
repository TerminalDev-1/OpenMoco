import asyncio
import json
from pathlib import Path
import tempfile
import unittest
from protocol import Frame, FrameDecoder
from server import capture


class ServerTests(unittest.IsolatedAsyncioTestCase):
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
