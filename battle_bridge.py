"""Local client-reported combat progress, separate from the native game protocol.

Combat still runs in the private-server client. Reports are trusted local input,
not proof of server-authoritative kills. A battle epoch and cumulative high-water
marks make retries and replayed prediction events harmless.
"""
import asyncio
import hmac
import json
import secrets

MONSTERS = frozenset((10800020, 10800021, 10800026, 10800117, 10800120,
                      10800138, 10800036, 10800268))
CIVILIANS = frozenset(range(10800309, 10800314))
KILL_TARGET, RESCUE_TARGET = 50, 3


class BattleBridge:
    def __init__(self, accounts, token):
        self.accounts, self.token = accounts, token
        self.active = {}
        with accounts.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS battle_reports '
                       '(epoch TEXT PRIMARY KEY, account INTEGER NOT NULL, counts TEXT NOT NULL, xp INTEGER NOT NULL)')

    def begin(self, account_id, session):
        epoch = secrets.token_hex(16)
        self.active[account_id] = (session, epoch)
        with self.accounts.connect() as db:
            db.execute('INSERT INTO battle_reports VALUES (?,?,?,0)', (epoch, account_id, '{}'))
        return epoch

    def end(self, account_id, session):
        if account_id in self.active and self.active[account_id][0] == session:
            del self.active[account_id]

    def state(self, account_id):
        if account_id not in self.active:
            raise ValueError('No authenticated battle for this account')
        with self.accounts.edit_profile(account_id) as profile:
            saved = dict(profile.get('battle_progress', {}))
        return dict(epoch=self.active[account_id][1], **saved)

    def report(self, account_id, epoch, counts, xp):
        if account_id not in self.active or self.active[account_id][1] != epoch:
            raise ValueError('Stale or unauthenticated battle')
        if type(xp) is not int or not 0 <= xp <= 60000:
            raise ValueError('Invalid cumulative native XP')
        if not isinstance(counts, dict) or len(counts) > len(MONSTERS | CIVILIANS):
            raise ValueError('Invalid outcome counts')
        clean = {}
        for key, count in counts.items():
            if str(key) not in {str(i) for i in MONSTERS | CIVILIANS}:
                raise ValueError('Unsupported character outcome')
            if type(count) is not int or not 0 <= count <= 100000:
                raise ValueError('Invalid cumulative outcome')
            clean[str(key)] = count
        # Profile and high-water marks commit together under one SQLite lock.
        with self.accounts.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT account,counts,xp FROM battle_reports WHERE epoch=?', (epoch,)).fetchone()
            if row is None or row[0] != account_id:
                raise ValueError('Unknown battle epoch')
            previous = json.loads(row[1])
            merged = dict(previous)
            kills = rescues = 0
            for key, count in clean.items():
                delta = max(0, count - previous.get(key, 0))
                merged[key] = max(count, previous.get(key, 0))
                if int(key) in MONSTERS:
                    kills += delta
                else:
                    rescues += delta
            saved_row = db.execute('SELECT profile FROM accounts WHERE id=?', (account_id & 0xffffffff,)).fetchone()
            if saved_row is None:
                raise ValueError('Unknown account')
            profile = json.loads(saved_row[0])
            progress = profile.setdefault('battle_progress', {})
            progress['xp'] = progress.get('xp', 0) + max(0, xp - row[2])
            progress['kills'] = progress.get('kills', 0) + kills
            progress['rescues'] = progress.get('rescues', 0) + rescues
            progress['tutorial_ready'] = progress['kills'] >= KILL_TARGET and progress['rescues'] >= RESCUE_TARGET
            db.execute('UPDATE accounts SET profile=? WHERE id=?', (json.dumps(profile), account_id & 0xffffffff))
            db.execute('UPDATE battle_reports SET counts=?,xp=? WHERE epoch=?', (json.dumps(merged), max(xp, row[2]), epoch))
        if kills or rescues or xp > row[2]:
            print(f'Battle progress: +{kills} kills, +{rescues} rescues, +{max(0, xp-row[2])} XP; tutorial_ready={progress["tutorial_ready"]}', flush=True)
        return dict(epoch=epoch, **progress)

    async def handle(self, reader, writer):
        """Bounded loopback HTTP endpoint; unrelated SDK traffic gets closed."""
        status, result = 400, {'error': 'Invalid bridge request'}
        try:
            head = await asyncio.wait_for(reader.readuntil(b'\r\n\r\n'), 5)
            if len(head) > 8192:
                raise ValueError('Headers too large')
            lines = head.decode('ascii').split('\r\n')
            method, path, _ = lines[0].split(' ')
            headers = dict(line.split(':', 1) for line in lines[1:] if ':' in line)
            headers = {k.lower(): v.strip() for k, v in headers.items()}
            if path != '/openmoco/battle':
                return
            if not hmac.compare_digest(headers.get('authorization', ''), 'Bearer ' + self.token):
                status, result = 403, {'error': 'Invalid local bridge token'}
            else:
                length = int(headers.get('content-length', '0'))
                if not 0 < length <= 16384:
                    raise ValueError('Invalid body length')
                body = json.loads(await asyncio.wait_for(reader.readexactly(length), 5))
                account_id = int(body['account_id'])
                if method == 'POST':
                    result = self.report(account_id, body['epoch'], body['counts'], body['xp'])
                elif method == 'GET':
                    result = self.state(account_id)
                else:
                    raise ValueError('Unsupported method')
                status = 200
        except (ValueError, KeyError, TypeError, UnicodeError, asyncio.IncompleteReadError,
                asyncio.LimitOverrunError, asyncio.TimeoutError, ConnectionError):
            pass
        finally:
            try:
                data = json.dumps(result).encode('ascii')
                writer.write(f'HTTP/1.1 {status} Result\r\nContent-Type: application/json\r\nContent-Length: {len(data)}\r\nConnection: close\r\n\r\n'.encode('ascii') + data)
                await writer.drain()
            except ConnectionError:
                pass
            writer.close()
            try:
                await writer.wait_closed()
            except ConnectionError:
                pass
