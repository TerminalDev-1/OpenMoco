"""Local capture listener with an opt-in, client-verified initial hello response."""
import argparse
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import uuid
import secrets
import time
from protocol import Frame, FrameDecoder, decode_client_hello, server_hello


async def capture(reader, writer, output, handshake=False, server_key=None, accounts=None, transport_probe=False, home_probe=None, profile_probe=None, apartment=False):
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
    local_account = None
    clock_started = time.monotonic()
    confirmed_frame = 0
    current_scene = 10900000 if apartment else None
    print(f'Connected: {peer}; capture {session}', flush=True)
    try:
        with (output / (session + '.bin')).open('wb') as stream:
            while True:
                # Manual testing sessions must remain open while the tablet is idle.
                chunk = await reader.read(65536)
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
                                print(f'{session}: encrypted login received; awaiting local verification' if crypto is not None else
                                      f'{session}: encrypted login captured; no local key configured', flush=True)
                                if crypto is not None:
                                    from protocol import decode_login_prefix
                                    plaintext = crypto.decode_login(frame.payload)
                                    login_prefix = decode_login_prefix(plaintext)
                                    (output / (session + '.login.bin')).write_bytes(plaintext)
                                    state = 'login_decrypted'
                                    print(f'{session}: verified and decrypted local-key login: {login_prefix}', flush=True)
                                    if accounts is not None:
                                        from protocol import decode_login_request
                                        request = decode_login_request(plaintext)
                                        account = accounts.authenticate(request.account_id, request.token)
                                        local_account = {'account_id': account.account_id, 'created': account.created}
                                        state = 'local_account_validated'
                                        print(f'{session}: local guest account validated; client login reply still pending', flush=True)
                                    if transport_probe:
                                        # Empty decoder at native 0x8df280; this checks crypto, not login success.
                                        response = Frame(20108, 0, crypto.encode_initial_reply(b''))
                                        encoded = response.encode()
                                        with (output / (session + '.server.bin')).open('ab') as replies:
                                            replies.write(encoded)
                                        writer.write(encoded)
                                        await writer.drain()
                                        sent.append({'message_type': 20108, 'version': 0, 'payload_bytes': len(response.payload)})
                                        state = 'encrypted_transport_probe_sent'
                                        print(f'{session}: sent encrypted empty keepalive transport probe; no login success reply', flush=True)
                                    elif accounts is not None:
                                        from protocol import login_reply
                                        reply = login_reply(account, request.version_fields)
                                        response = Frame(reply.message_type, reply.version, crypto.encode_initial_reply(reply.payload))
                                        encoded = response.encode()
                                        with (output / (session + '.server.bin')).open('ab') as replies:
                                            replies.write(encoded)
                                        writer.write(encoded)
                                        await writer.drain()
                                        sent.append({'message_type': response.message_type, 'version': response.version,
                                                     'payload_bytes': len(response.payload)})
                                        state = 'local_login_reply_sent'
                                        print(f'{session}: sent encrypted local login reply (29125/v1); home data pending', flush=True)
                                        if profile_probe is not None or apartment:
                                            from home import own_home
                                            # Bind the validated starter profile to this local guest.
                                            profile_body = own_home(account.account_id, age_category=account.profile.get('age_category', 0), tutorials=account.profile.get('tutorials', {})) if apartment or profile_probe == own_home(0) else profile_probe
                                            response = Frame(24548, 0, crypto.encode_session(profile_body))
                                            encoded = response.encode()
                                            with (output / (session + '.server.bin')).open('ab') as replies:
                                                replies.write(encoded)
                                            writer.write(encoded)
                                            await writer.drain()
                                            sent.append({'message_type': 24548, 'version': 0, 'payload_bytes': len(response.payload)})
                                            print(f'{session}: sent account-bound starter profile' if apartment else f'{session}: sent native-evidenced own-home probe; client acceptance pending', flush=True)
                                        if home_probe is not None or apartment:
                                            from scene import apartment_scene, monster_tutorial_scene
                                            if apartment:
                                                current_scene = account.profile.get('scene_id', 10900000)
                                                scene_body = monster_tutorial_scene(account.account_id) if current_scene == 10900001 else apartment_scene(account.account_id)
                                            else:
                                                scene_body = home_probe
                                            response = Frame(23491, 0, crypto.encode_session(scene_body))
                                            encoded = response.encode()
                                            with (output / (session + '.server.bin')).open('ab') as replies:
                                                replies.write(encoded)
                                            writer.write(encoded)
                                            await writer.drain()
                                            sent.append({'message_type': 23491, 'version': 0, 'payload_bytes': len(response.payload)})
                                            state = ('tutorial_scene_sent' if current_scene == 10900001 else 'apartment_scene_sent') if apartment else 'home_scene_probe_sent'
                                            print(f'{session}: sent {len(scene_body)}-byte account-bound apartment' if apartment else f'{session}: sent native-evidenced scene-start probe; client acceptance pending', flush=True)
                            elif crypto is not None and crypto.reply_sent:
                                plaintext = crypto.decode_session(frame.payload)
                                record['decrypted_bytes'] = len(plaintext)
                                with (output / (session + '.session.bin')).open('ab') as clear:
                                    clear.write(Frame(frame.message_type, frame.version, plaintext).encode())
                                print(f'{session}: verified session frame {frame.message_type}, {len(plaintext)} decrypted bytes', flush=True)
                                if apartment and frame.message_type == 16543 and frame.version == 0:
                                    from commands import decode_client_turn
                                    try:
                                        turn = decode_client_turn(plaintext)
                                        for command in turn.commands:
                                            if command.account_id not in (0, account.account_id):
                                                continue
                                            if command.command_type == 541:
                                                accounts.record_age_choice(account.account_id, command.fields['age'])
                                                print(f'{session}: persisted local onboarding category', flush=True)
                                            elif command.command_type == 574:
                                                accounts.record_tutorial(account.account_id, command.fields['tutorial'], command.fields['step'])
                                                print(f'{session}: persisted tutorial transition', flush=True)
                                    except ValueError as error:
                                        print(f'{session}: turn unsupported: {error}', flush=True)
                                if apartment and frame.message_type == 13222 and frame.version == 0:
                                    from scene_requests import decode_scene_request
                                    try:
                                        selection = decode_scene_request(plaintext)
                                    except ValueError as error:
                                        print(f'{session}: scene selection unsupported: {error}', flush=True)
                                    else:
                                        if selection.scene_id == 10900001 and current_scene != 10900001:
                                            from scene import monster_tutorial_scene
                                            response = Frame(23491, 0, crypto.encode_session(monster_tutorial_scene(account.account_id)))
                                            encoded = response.encode()
                                            with (output / (session + '.server.bin')).open('ab') as replies:
                                                replies.write(encoded)
                                            writer.write(encoded)
                                            await writer.drain()
                                            sent.append({'message_type': 23491, 'version': 0, 'payload_bytes': len(response.payload)})
                                            current_scene = 10900001
                                            accounts.record_scene(account.account_id, current_scene)
                                            confirmed_frame = 0
                                            state = 'tutorial_scene_sent'
                                            print(f'{session}: sent account-bound TutorialAreaBasic after portal selection', flush=True)
                                if apartment and frame.message_type == 13223 and frame.version == 0:
                                    # Native 0x764214: two flags and optional selection.
                                    # The actual map's Leave Battle button sent 00.
                                    if plaintext != b'\x00':
                                        print(f'{session}: unsupported leave-battle options', flush=True)
                                    elif current_scene != 10900000:
                                        from home import own_home
                                        from scene import apartment_scene
                                        saved = accounts.authenticate(account.account_id, account.token).profile
                                        responses = [
                                            (24548, own_home(account.account_id, age_category=saved.get('age_category', 0), tutorials=saved.get('tutorials', {}))),
                                            (23491, apartment_scene(account.account_id)),
                                        ]
                                        for message_type, body in responses:
                                            response = Frame(message_type, 0, crypto.encode_session(body))
                                            encoded = response.encode()
                                            with (output / (session + '.server.bin')).open('ab') as replies:
                                                replies.write(encoded)
                                            writer.write(encoded)
                                            sent.append({'message_type': message_type, 'version': 0, 'payload_bytes': len(response.payload)})
                                        await writer.drain()
                                        current_scene = 10900000
                                        accounts.record_scene(account.account_id, current_scene)
                                        confirmed_frame = 0
                                        state = 'apartment_scene_sent'
                                        print(f'{session}: returned to account-bound apartment after Leave Battle', flush=True)
                                if frame.message_type == 18853:
                                    from protocol import decode_frame_ready
                                    confirmed_frame = max(confirmed_frame, decode_frame_ready(plaintext))
                                if frame.message_type == 18851:
                                    from protocol import game_clock_reply
                                    response = game_clock_reply(plaintext, int((time.monotonic() - clock_started) * 1000), confirmed_frame)
                                    response = Frame(response.message_type, response.version, crypto.encode_session(response.payload))
                                    encoded = response.encode()
                                    with (output / (session + '.server.bin')).open('ab') as replies:
                                        replies.write(encoded)
                                    writer.write(encoded)
                                    await writer.drain()
                                    sent.append({'message_type': response.message_type, 'version': response.version, 'payload_bytes': len(response.payload)})
                                    # Preserve the verified transport keepalive during game-clock traffic.
                                    keepalive = Frame(20108, 0, crypto.encode_session(b''))
                                    encoded = keepalive.encode()
                                    with (output / (session + '.server.bin')).open('ab') as replies:
                                        replies.write(encoded)
                                    writer.write(encoded)
                                    await writer.drain()
                                    sent.append({'message_type': 20108, 'version': 0, 'payload_bytes': len(keepalive.payload)})
                                if frame.message_type == 10108 and not plaintext:
                                    response = Frame(20108, 0, crypto.encode_session(b''))
                                    encoded = response.encode()
                                    with (output / (session + '.server.bin')).open('ab') as replies:
                                        replies.write(encoded)
                                    writer.write(encoded)
                                    await writer.drain()
                                    sent.append({'message_type': 20108, 'version': 0, 'payload_bytes': len(response.payload)})
                    except ValueError as error:
                        framing_error = str(error)
                        reason = 'protocol_error'
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
                    'local_account': local_account,
                    'note': 'Apartment and portal travel verified; full progression persistence and authoritative gameplay remain incomplete.' if apartment else 'Local login development; home data and gameplay remain unimplemented.' if handshake
                            else 'Raw incoming TCP bytes. No protocol responses were sent.'}
        (output / (session + '.json')).write_text(json.dumps(metadata, indent=2), encoding='utf-8')
        print(f'Closed: {session}; {total} bytes; {reason}', flush=True)


async def run(host, port, output, handshake=False, server_key=None, account_store=None, transport_probe=False, home_probe=None, profile_probe=None, apartment=False):
    output.mkdir(parents=True, exist_ok=True)
    if server_key is not None and account_store is None:
        from accounts import AccountStore
        account_store = AccountStore(Path(__file__).resolve().parent/'.local/accounts.sqlite3')
    server = await asyncio.start_server(lambda r, w: capture(r, w, output, handshake, server_key, account_store, transport_probe, home_probe, profile_probe, apartment), host, port)
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
    parser.add_argument('--apartment', action='store_true', help='Send the minimum local player/apartment state; requires --login')
    parser.add_argument('--server-key', type=Path, default=Path(__file__).resolve().parent/'.local/server-key.json')
    args = parser.parse_args()
    if args.apartment and not args.login:
        parser.error('--apartment requires --login')
    try:
        key = None
        if args.login:
            from transport import load_key
            key = load_key(args.server_key)
        asyncio.run(run(args.host, args.port, args.output, args.handshake or args.login, key, apartment=args.apartment))
    except KeyboardInterrupt:
        pass
