"""Local capture listener with an opt-in, client-verified initial hello response."""
import argparse
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import uuid
import secrets
from protocol import FrameDecoder, decode_client_hello, server_hello


async def capture(reader, writer, output, handshake=False, server_key=None):
    session = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]
    peer = writer.get_extra_info('peername')
    total = 0
    decoder = FrameDecoder()
    frames = []
    framing_error = None
    reason = 'peer_closed'
    sent = []
    state = 'awaiting_client_hello' if handshake else 'capture_only'
    hello = None
    crypto = None
    login_prefix = None
    print(f'Connected: {peer}; capture {session}', flush=True)
    try:
        with (output / (session + '.bin')).open('wb') as stream:
            while True:
                try:
                    chunk = await asyncio.wait_for(reader.read(65536), timeout=30)
                except asyncio.TimeoutError:
                    reason = 'idle_timeout'
                    break
                if not chunk:
                    break
                stream.write(chunk)
                stream.flush()
                total += len(chunk)
                print(f'{session}: received {len(chunk)} bytes ({total} total)', flush=True)
                if framing_error is None:
                    try:
                        for frame in decoder.feed(chunk):
                            record = {'message_type': frame.message_type, 'version': frame.version,
                                      'payload_bytes': len(frame.payload)}
                            frames.append(record)
                            print(f'{session}: frame {record}', flush=True)
                            if handshake and state == 'awaiting_client_hello':
                                if frame.message_type != 10100 or frame.version != 0:
                                    raise ValueError('Expected version-0 client hello (10100)')
                                hello = decode_client_hello(frame.payload)
                                challenge = secrets.token_bytes(24)
                                if server_key is not None:
                                    from transport import LoginTransport
                                    crypto = LoginTransport(server_key, challenge)
                                response = server_hello(challenge)
                                encoded = response.encode()
                                (output / (session + '.server.bin')).write_bytes(encoded)
                                writer.write(encoded)
                                await writer.drain()
                                sent.append({'message_type': response.message_type, 'version': 0,
                                             'payload_bytes': len(response.payload)})
                                state = 'hello_sent'
                                print(f'{session}: sent server hello; awaiting next client frame', flush=True)
                            elif handshake and state == 'hello_sent':
                                if frame.message_type != 10101 or frame.version != 9 or len(frame.payload) < 48:
                                    raise ValueError('Expected encrypted 10101 version-9 login envelope')
                                record['client_public_key_bytes'] = 32
                                state = 'encrypted_login_received'
                                print(f'{session}: encrypted login received; authentication is not implemented', flush=True)
                                if crypto is not None:
                                    from protocol import decode_login_prefix
                                    plaintext = crypto.decode_login(frame.payload)
                                    login_prefix = decode_login_prefix(plaintext)
                                    (output / (session + '.login.bin')).write_bytes(plaintext)
                                    state = 'login_decrypted'
                                    print(f'{session}: verified and decrypted local-key login: {login_prefix}', flush=True)
                    except ValueError as error:
                        framing_error = str(error)
                        reason = 'protocol_error'
                        break
                if total >= 4 * 1024 * 1024:
                    reason = 'capture_limit'
                    break
    except (ConnectionError, OSError) as error:
        reason = str(error)
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except ConnectionError:
            pass
        metadata = {'peer': peer, 'bytes': total, 'close_reason': reason,
                    'frames': frames, 'framing_error': framing_error,
                    'incomplete_frame_bytes': len(decoder.pending),
                    'sent_frames': sent, 'state': state, 'client_hello': hello,
                    'login_prefix': login_prefix,
                    'note': 'Experimental server hello only; no authentication or gameplay.' if handshake
                            else 'Raw incoming TCP bytes. No protocol responses were sent.'}
        (output / (session + '.json')).write_text(json.dumps(metadata, indent=2), encoding='utf-8')
        print(f'Closed: {session}; {total} bytes; {reason}', flush=True)


async def run(host, port, output, handshake=False, server_key=None):
    output.mkdir(parents=True, exist_ok=True)
    server = await asyncio.start_server(lambda r, w: capture(r, w, output, handshake, server_key), host, port)
    print(f'Local listener: {host}:{port}; mode={"experimental hello" if handshake else "capture"}', flush=True)
    async with server:
        await server.serve_forever()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=9339, help='Local capture port; the observed game port 30000 is redirected here')
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parent / 'captures')
    parser.add_argument('--handshake', action='store_true', help='Send the evidenced 20100 hello; capture the next client message')
    parser.add_argument('--login', action='store_true', help='Verify and decrypt login using a local server key')
    parser.add_argument('--server-key', type=Path, default=Path(__file__).resolve().parent/'.local/server-key.json')
    args = parser.parse_args()
    try:
        key = None
        if args.login:
            from transport import load_key
            key = load_key(args.server_key)
        asyncio.run(run(args.host, args.port, args.output, args.handshake or args.login, key))
    except KeyboardInterrupt:
        pass
