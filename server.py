"""OpenMoco private server: local game listener for the 13.5.1 test client.

Each TCP connection is one `GameSession`. A session moves through these stages:

1. Hello: the client sends 10100; we reply 20100 with a random challenge.
2. Login: the client sends encrypted 10101; we verify it with the local server
   key, validate the local guest account and reply 29125.
3. Session: every later frame is SecretBox-encrypted. In apartment mode we send
   the player's own home (24548) and the saved scene (23491), then react to
   tutorial commands, scene travel, leave-battle requests and the game clock.

Without --handshake the listener only records raw bytes. Every connection
writes a capture (<session>.bin, .server.bin, .session.bin and .json) under the
output directory; captures stay in ignored local folders.
"""
import argparse
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import secrets
import time
import uuid

from protocol import Frame, FrameDecoder, decode_client_hello, server_hello

# Client -> server message types.
CLIENT_HELLO = 10100
CLIENT_LOGIN = 10101
CLIENT_KEEPALIVE = 10108
SCENE_SELECTION = 13222      # Portal destination or flagged home request.
LEAVE_BATTLE = 13223         # Minimap "Leave Battle"; body 00 is supported.
SCENE_LOADED = 13224         # Empty body: the new scene finished loading.
CLIENT_TURN = 16543          # Batched commands (541 age, 574 tutorial, 575/576 main quests).
GAME_CLOCK_REQUEST = 18851
FRAME_READY = 18853

# Server -> client message types.
SERVER_HELLO = 20100
SERVER_KEEPALIVE = 20108
SCENE_START = 23491
OWN_HOME = 24548
GAME_CLOCK_REPLY = 28851     # Encoded by protocol.game_clock_reply.

# Client turn command types (see commands.py).
AGE_CHOICE_COMMAND = 541
EQUIP_COSMETIC_COMMAND = 543
TUTORIAL_COMMAND = 574
MAIN_QUEST_SEEN_COMMAND = 575
MAIN_QUEST_DONE_COMMAND = 576

# Scene data references supported by this server.
APARTMENT = 10900000         # Home
TUTORIAL_AREA = 10900001     # TutorialAreaBasic, "Downtown Chaos"
SOCIAL_HUB = 10900005        # Selection the client sends when returning home


def _new_session_id():
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    return stamp + '-' + uuid.uuid4().hex[:8]


class GameSession:
    """State and message handlers for one client connection."""

    def __init__(self, reader, writer, output, handshake=False, server_key=None,
                 accounts=None, transport_probe=False, home_probe=None,
                 profile_probe=None, apartment=False, battle_bridge=None):
        self.reader, self.writer, self.output = reader, writer, output
        self.handshake = handshake
        self.server_key = server_key
        self.accounts = accounts
        self.transport_probe = transport_probe
        self.home_probe = home_probe
        self.profile_probe = profile_probe
        self.apartment = apartment
        self.battle_bridge = battle_bridge

        self.session = _new_session_id()
        self.peer = writer.get_extra_info('peername')
        self.decoder = FrameDecoder()
        self.total = 0
        self.frames = []          # Metadata for every received frame.
        self.sent = []            # Metadata for every sent frame.
        self.framing_error = None
        self.reason = 'peer_closed'
        self.state = 'awaiting_client_hello' if handshake else 'capture_only'

        # Login results.
        self.hello = None
        self.crypto = None
        self.login_prefix = None
        self.account = None
        self.local_account = None

        # Scene and simulation clock. A new scene starts at frame zero.
        self.current_scene = APARTMENT if apartment else None
        self.clock_started = time.monotonic()
        self.confirmed_frame = 0
        self.awaiting_scene_loaded = False
        self.pending_home_scene = False
        self.last_clock_request = None

    # ----- logging and capture files -------------------------------------

    def log(self, message):
        print(f'{self.session}: {message}', flush=True)

    def _path(self, suffix):
        return self.output / (self.session + suffix)

    def _record_sent(self, frame):
        encoded = frame.encode()
        with self._path('.server.bin').open('ab') as replies:
            replies.write(encoded)
        self.writer.write(encoded)
        self.sent.append({'message_type': frame.message_type, 'version': frame.version,
                          'payload_bytes': len(frame.payload)})

    async def send_plain(self, frame):
        self._record_sent(frame)
        await self.writer.drain()

    async def send_session(self, message_type, body, version=0):
        """Encrypt `body` with the session key and send it."""
        await self.send_plain(Frame(message_type, version, self.crypto.encode_session(body)))

    # ----- connection loop ------------------------------------------------

    async def run(self):
        print(f'Connected: {self.peer}; capture {self.session}', flush=True)
        try:
            with self._path('.bin').open('wb') as stream:
                while True:
                    # Manual testing sessions must remain open while the tablet is idle.
                    chunk = await self.reader.read(65536)
                    if not chunk:
                        break
                    stream.write(chunk)
                    stream.flush()
                    self.total += len(chunk)
                    self.log(f'received {len(chunk)} bytes ({self.total} total)')
                    if self.framing_error is None and not await self._feed(chunk):
                        break
        except (ConnectionError, OSError) as error:
            self.reason = str(error)
        finally:
            await self._close()

    async def _feed(self, chunk):
        """Decode and handle complete frames. Returns False on a protocol error."""
        try:
            for frame in self.decoder.feed(chunk):
                record = {'message_type': frame.message_type, 'version': frame.version,
                          'payload_bytes': len(frame.payload)}
                self.frames.append(record)
                self.log(f'frame {record}')
                await self._dispatch(frame, record)
        except ValueError as error:
            self.framing_error = str(error)
            self.reason = 'protocol_error'
            return False
        return True

    async def _dispatch(self, frame, record):
        if self.handshake and self.state == 'awaiting_client_hello':
            await self.on_client_hello(frame)
        elif self.handshake and self.state == 'hello_sent':
            await self.on_login(frame, record)
        elif self.crypto is not None and self.crypto.reply_sent:
            await self.on_session_frame(frame, record)

    async def _close(self):
        if self.battle_bridge is not None and self.local_account is not None:
            self.battle_bridge.end(self.local_account['account_id'], self.session)
        self.writer.close()
        try:
            await self.writer.wait_closed()
        except ConnectionError:
            pass
        if self.apartment:
            note = ('Apartment and portal travel verified; full progression persistence '
                    'and authoritative gameplay remain incomplete.')
        elif self.handshake:
            note = 'Local login development; home data and gameplay remain unimplemented.'
        else:
            note = 'Raw incoming TCP bytes. No protocol responses were sent.'
        metadata = {'peer': self.peer, 'bytes': self.total, 'close_reason': self.reason,
                    'frames': self.frames, 'framing_error': self.framing_error,
                    'incomplete_frame_bytes': len(self.decoder.pending),
                    'sent_frames': self.sent, 'state': self.state, 'client_hello': self.hello,
                    'login_prefix': self.login_prefix,
                    'local_account': self.local_account,
                    'note': note}
        self._path('.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
        print(f'Closed: {self.session}; {self.total} bytes; {self.reason}', flush=True)

    # ----- stage 1: hello -------------------------------------------------

    async def on_client_hello(self, frame):
        if frame.message_type != CLIENT_HELLO or frame.version != 0:
            raise ValueError('Expected version-0 client hello (10100)')
        self.hello = decode_client_hello(frame.payload)
        challenge = secrets.token_bytes(24)
        if self.server_key is not None:
            from transport import LoginTransport
            self.crypto = LoginTransport(self.server_key, challenge)
        await self.send_plain(server_hello(challenge))
        self.state = 'hello_sent'
        self.log('sent server hello; awaiting next client frame')

    # ----- stage 2: encrypted login ---------------------------------------

    async def on_login(self, frame, record):
        if frame.message_type != CLIENT_LOGIN or frame.version != 9 or len(frame.payload) < 48:
            raise ValueError('Expected encrypted 10101 version-9 login envelope')
        record['client_public_key_bytes'] = 32
        self.state = 'encrypted_login_received'
        if self.crypto is None:
            self.log('encrypted login captured; no local key configured')
            return
        self.log('encrypted login received; awaiting local verification')

        from protocol import decode_login_prefix, decode_login_request
        plaintext = self.crypto.decode_login(frame.payload)
        self.login_prefix = decode_login_prefix(plaintext)
        self._path('.login.bin').write_bytes(plaintext)
        self.state = 'login_decrypted'
        self.log(f'verified and decrypted local-key login: {self.login_prefix}')

        request = None
        if self.accounts is not None:
            request = decode_login_request(plaintext)
            self.account = self.accounts.authenticate(request.account_id, request.token)
            self.local_account = {'account_id': self.account.account_id,
                                  'created': self.account.created}
            self.state = 'local_account_validated'
            self.log('local guest account validated; client login reply still pending')

        if self.transport_probe:
            # Empty decoder at native 0x8df280; this checks crypto, not login success.
            await self.send_plain(Frame(SERVER_KEEPALIVE, 0, self.crypto.encode_initial_reply(b'')))
            self.state = 'encrypted_transport_probe_sent'
            self.log('sent encrypted empty keepalive transport probe; no login success reply')
        elif self.accounts is not None:
            await self._send_login_reply(request)
            if self.profile_probe is not None or self.apartment:
                await self._send_initial_home()
            if self.home_probe is not None or self.apartment:
                await self._send_initial_scene()

    async def _send_login_reply(self, request):
        from protocol import login_reply
        reply = login_reply(self.account, request.version_fields)
        await self.send_plain(Frame(reply.message_type, reply.version,
                                    self.crypto.encode_initial_reply(reply.payload)))
        self.state = 'local_login_reply_sent'
        self.log('sent encrypted local login reply (29125/v1); home data pending')

    def _own_home_body(self, profile):
        from home import STARTER_VANITY, equipped_look, own_home
        from progress import intro_main_steps
        return own_home(self.account.account_id, vanity=STARTER_VANITY,
                        look=equipped_look(profile.get('look')),
                        age_category=profile.get('age_category', 0),
                        tutorials=profile.get('tutorials', {}),
                        main_steps=intro_main_steps(profile),
                        xp=profile.get('battle_progress', {}).get('xp', 0))

    async def _send_initial_home(self):
        from home import own_home
        # Bind the validated starter profile to this local guest.
        if self.apartment or self.profile_probe == own_home(0):
            body = self._own_home_body(self.account.profile)
        else:
            body = self.profile_probe
        await self.send_session(OWN_HOME, body)
        if self.apartment:
            self.log('sent account-bound starter profile')
        else:
            self.log('sent native-evidenced own-home probe; client acceptance pending')

    async def _send_initial_scene(self):
        from scene import apartment_scene, progression_tutorial_scene
        account_id = self.account.account_id
        if self.apartment:
            # Resume the scene saved by the previous session.
            self.current_scene = self.account.profile.get('scene_id', APARTMENT)
            if self.current_scene == TUTORIAL_AREA:
                body = progression_tutorial_scene(account_id)
            else:
                body = apartment_scene(account_id)
        else:
            body = self.home_probe
        if self.battle_bridge is not None and self.current_scene == TUTORIAL_AREA:
            self.battle_bridge.begin(account_id, self.session)
        await self.send_session(SCENE_START, body)
        if not self.apartment:
            self.state = 'home_scene_probe_sent'
            self.log('sent native-evidenced scene-start probe; client acceptance pending')
            return
        self.state = 'tutorial_scene_sent' if self.current_scene == TUTORIAL_AREA else 'apartment_scene_sent'
        self.log(f'sent {len(body)}-byte account-bound apartment')

    # ----- stage 3: encrypted session -------------------------------------

    async def on_session_frame(self, frame, record):
        plaintext = self.crypto.decode_session(frame.payload)
        record['decrypted_bytes'] = len(plaintext)
        with self._path('.session.bin').open('ab') as clear:
            clear.write(Frame(frame.message_type, frame.version, plaintext).encode())
        self.log(f'verified session frame {frame.message_type}, {len(plaintext)} decrypted bytes')

        if self.apartment and frame.version == 0:
            if frame.message_type == CLIENT_TURN:
                self.on_client_turn(plaintext)
            elif frame.message_type == SCENE_SELECTION:
                await self.on_scene_selection(plaintext)
            elif frame.message_type == LEAVE_BATTLE:
                await self.on_leave_battle(plaintext)

        # Clock and keepalive handling applies in every logged-in mode.
        scene_ready = False
        if frame.message_type == SCENE_LOADED and frame.version == 0 and not plaintext:
            self.on_scene_loaded()
        if frame.message_type == FRAME_READY:
            scene_ready = self.on_frame_ready(plaintext)
        if frame.message_type == GAME_CLOCK_REQUEST:
            self.last_clock_request = plaintext
        if frame.message_type == GAME_CLOCK_REQUEST or (scene_ready and self.last_clock_request is not None):
            await self._send_clock_reply()
        if frame.message_type == CLIENT_KEEPALIVE and not plaintext:
            await self.send_session(SERVER_KEEPALIVE, b'')

    def on_client_turn(self, plaintext):
        """Persist the supported commands from an authenticated client turn."""
        from commands import decode_client_turn
        account_id = self.account.account_id
        try:
            turn = decode_client_turn(plaintext)
            for command in turn.commands:
                if command.account_id not in (0, account_id):
                    continue
                if command.command_type == AGE_CHOICE_COMMAND:
                    self.accounts.record_age_choice(account_id, command.fields['age'])
                    self.log('persisted local onboarding category')
                elif command.command_type == EQUIP_COSMETIC_COMMAND:
                    slot = self.accounts.record_cosmetic(account_id, command.fields['cosmetic'])
                    self.log(f'persisted equipped cosmetic {slot}')
                elif command.command_type == TUTORIAL_COMMAND:
                    self.accounts.record_tutorial(account_id, command.fields['tutorial'], command.fields['step'])
                    self.log('persisted tutorial transition')
                elif command.command_type in (MAIN_QUEST_SEEN_COMMAND, MAIN_QUEST_DONE_COMMAND):
                    self.accounts.record_main_quest(account_id, command.command_type, command.fields['step'])
                    self.log(f'persisted main-quest step {command.command_type}')
        except ValueError as error:
            self.log(f'turn unsupported: {error}')

    async def on_scene_selection(self, plaintext):
        from scene_requests import decode_scene_request
        try:
            selection = decode_scene_request(plaintext)
        except ValueError as error:
            self.log(f'scene selection unsupported: {error}')
            return
        if self.pending_home_scene and selection.flag and selection.scene_id == SOCIAL_HUB:
            await self._enter_apartment()
        if selection.scene_id == TUTORIAL_AREA and self.current_scene != TUTORIAL_AREA:
            await self._enter_tutorial_area()

    async def _enter_apartment(self):
        """Second half of return-home: the client asked for its home scene."""
        from scene import apartment_scene
        account_id = self.account.account_id
        await self.send_session(SCENE_START, apartment_scene(account_id))
        self.pending_home_scene = False
        self.current_scene = APARTMENT
        if self.battle_bridge is not None:
            self.battle_bridge.end(account_id, self.session)
        self.accounts.record_scene(account_id, self.current_scene)
        self._reset_scene_clock()
        self.state = 'apartment_scene_sent'
        self.log('returned to apartment after client home-scene request')

    async def _enter_tutorial_area(self):
        """Portal travel from the apartment into Downtown Chaos."""
        from scene import progression_tutorial_scene
        account_id = self.account.account_id
        if self.battle_bridge is not None:
            self.battle_bridge.begin(account_id, self.session)
        await self.send_session(SCENE_START, progression_tutorial_scene(account_id))
        self.current_scene = TUTORIAL_AREA
        self.accounts.record_scene(account_id, self.current_scene)
        self._reset_scene_clock()
        self.state = 'tutorial_scene_sent'
        self.log('sent account-bound TutorialAreaBasic after portal selection')

    async def on_leave_battle(self, plaintext):
        """First half of return-home: send own-home, then wait for the client.

        Native 0x764214 reads two flags and an optional selection; the actual
        map's Leave Battle button sent 00. OwnHome prompts the client's
        asynchronous exit, after which it sends a flagged SocialHub selection.
        We wait for that request instead of racing teardown with a scene.
        """
        if plaintext != b'\x00':
            self.log('unsupported leave-battle options')
            return
        if self.current_scene == APARTMENT or self.pending_home_scene:
            return
        account_id = self.account.account_id
        if self.accounts.complete_intro_quest(account_id):
            self.log('Intro_3 earned: Portal tutorial advanced to ClaimQuests')
        saved = self.accounts.authenticate(account_id, self.account.token).profile
        await self.send_session(OWN_HOME, self._own_home_body(saved))
        self.pending_home_scene = True
        self.state = 'awaiting_home_scene_request'
        self.log('sent home profile; awaiting client home-scene request')

    # ----- simulation clock -----------------------------------------------

    def _reset_scene_clock(self):
        """A fresh scene snapshot starts at frame zero, not at the TCP age."""
        self.confirmed_frame = 0
        self.awaiting_scene_loaded = True
        self.clock_started = time.monotonic()

    def on_scene_loaded(self):
        # Old-scene clock/ready messages precede this boundary. Loading can
        # pause while the app is backgrounded, so time starts here.
        self.confirmed_frame = 0
        self.clock_started = time.monotonic()
        self.awaiting_scene_loaded = False

    def on_frame_ready(self, plaintext):
        """Track the client's ready frame. Returns True if it must be acknowledged.

        Old-scene ready reports can still arrive after travel; acknowledging
        them would advance the new simulation by thousands of frames and freeze
        its actors, so they are ignored until the scene-loaded boundary. After
        that, every report is confirmed immediately: the client can exhaust its
        prediction window (on first load or after resume) before it polls the
        clock again.
        """
        from protocol import decode_frame_ready
        ready_frame = decode_frame_ready(plaintext)
        if self.awaiting_scene_loaded:
            return False
        self.confirmed_frame = max(self.confirmed_frame, ready_frame)
        return True

    async def _send_clock_reply(self):
        from protocol import game_clock_reply
        elapsed_ms = int((time.monotonic() - self.clock_started) * 1000)
        reply = game_clock_reply(self.last_clock_request, elapsed_ms, self.confirmed_frame)
        await self.send_session(reply.message_type, reply.payload, reply.version)
        # Preserve the verified transport keepalive during game-clock traffic.
        await self.send_session(SERVER_KEEPALIVE, b'')


async def capture(reader, writer, output, handshake=False, server_key=None, accounts=None,
                  transport_probe=False, home_probe=None, profile_probe=None, apartment=False,
                  battle_bridge=None):
    """Serve one client connection (kept as a function for callers and tests)."""
    session = GameSession(reader, writer, output, handshake, server_key, accounts,
                          transport_probe, home_probe, profile_probe, apartment, battle_bridge)
    await session.run()


async def run(host, port, output, handshake=False, server_key=None, account_store=None,
              transport_probe=False, home_probe=None, profile_probe=None, apartment=False,
              battle_bridge=None):
    output.mkdir(parents=True, exist_ok=True)
    if server_key is not None and account_store is None:
        from accounts import AccountStore
        account_store = AccountStore(Path(__file__).resolve().parent / '.local/accounts.sqlite3')

    async def connected(reader, writer):
        await capture(reader, writer, output, handshake, server_key, account_store,
                      transport_probe, home_probe, profile_probe, apartment, battle_bridge)

    server = await asyncio.start_server(connected, host, port)
    mode = 'experimental hello' if handshake else 'capture'
    print(f'Local listener: {host}:{port}; mode={mode}', flush=True)
    async with server:
        await server.serve_forever()


def main():
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=9339,
                        help='Local capture port; the observed game port 30000 is redirected here')
    parser.add_argument('--output', type=Path, default=root / 'captures')
    parser.add_argument('--handshake', action='store_true',
                        help='Send the evidenced 20100 hello; capture the next client message')
    parser.add_argument('--login', action='store_true',
                        help='Verify and decrypt login using a local server key')
    parser.add_argument('--apartment', action='store_true',
                        help='Send the minimum local player/apartment state; requires --login')
    parser.add_argument('--server-key', type=Path, default=root / '.local/server-key.json')
    args = parser.parse_args()
    if args.apartment and not args.login:
        parser.error('--apartment requires --login')
    key = None
    if args.login:
        from transport import load_key
        key = load_key(args.server_key)
    try:
        asyncio.run(run(args.host, args.port, args.output, args.handshake or args.login, key,
                        apartment=args.apartment))
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
