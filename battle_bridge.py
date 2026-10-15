"""Server-side battle progress, fed by the private-server client's outcome reports.

Combat itself still runs in the client. The client bridge (loader_diagnostics.js)
reads its native kill/rescue counters and posts cumulative counts here over a
loopback HTTP endpoint on port 9340. The server owns everything after that: it
decides what each report is worth, keeps the totals, and turns them into
tutorial quest progress (progress.py) and the saved XP sent in the home profile.

Reports are trusted local input, not proof of server-authoritative kills. A
battle epoch plus cumulative high-water marks make retries and replayed
prediction events harmless: only the increase over the best previous report
in the same battle is credited.

XP is credited per reported kill, not per collected drop. Enabling the
client's XP drops in the tutorial area froze its game thread after battle
reentry.
"""
import asyncio
from contextlib import suppress
import hmac
import json
import secrets

from progress import KILL_TARGET, RESCUE_TARGET, XP_LEVELS

# characters.csv LootProfile -> loot_profiles.csv XP (Weak 2000, WeakMedium
# 4000, Strong 10000). Native 6a58c8 scales that value and divides by 10000;
# loot XP / 1000 matches the observed ~1.6 collected XP per kill. Daily-budget
# multipliers, level adjustment and randomized rounding are not reproduced.
KILL_XP = {
    10800020: 2, 10800021: 2, 10800026: 2, 10800117: 2, 10800120: 2,  # Weak
    10800138: 4,                                                      # WeakMedium
    10800036: 10, 10800268: 10,                                       # Strong
}
MONSTERS = frozenset(KILL_XP)
CIVILIANS = frozenset(range(10800309, 10800314))  # Human civilians, not Spirits.
REPORTABLE = frozenset(str(character) for character in MONSTERS | CIVILIANS)

MAX_COLLECTED_XP = 60000   # Native per-battle XP budget.
MAX_COUNT = 100000
MAX_BODY = 16384
BRIDGE_PATH = '/openmoco/battle'


def _validate_report(counts, xp):
    """Return clean {character_id_str: count} or raise ValueError."""
    if type(xp) is not int or not 0 <= xp <= MAX_COLLECTED_XP:
        raise ValueError('Invalid cumulative native XP')
    if not isinstance(counts, dict) or len(counts) > len(REPORTABLE):
        raise ValueError('Invalid outcome counts')
    clean = {}
    for key, count in counts.items():
        if str(key) not in REPORTABLE:
            raise ValueError('Unsupported character outcome')
        if type(count) is not int or not 0 <= count <= MAX_COUNT:
            raise ValueError('Invalid cumulative outcome')
        clean[str(key)] = count
    return clean


def _credit(previous, counts):
    """Compare cumulative counts with the battle's best previous report.

    Returns (merged high-water marks, new kills, new rescues, kill XP).
    """
    merged = dict(previous)
    kills = rescues = kill_xp = 0
    for key, count in counts.items():
        delta = max(0, count - previous.get(key, 0))
        merged[key] = max(count, previous.get(key, 0))
        character = int(key)
        if character in MONSTERS:
            kills += delta
            kill_xp += delta * KILL_XP[character]
        else:
            rescues += delta
    return merged, kills, rescues, kill_xp


def _battle_xp(counts):
    """Kill XP credited so far in one battle, from its high-water counts."""
    return sum(count * KILL_XP[int(key)] for key, count in counts.items() if int(key) in MONSTERS)


class BattleBridge:
    def __init__(self, accounts, token):
        self.accounts, self.token = accounts, token
        self.active = {}  # account_id -> (game session, battle epoch)
        with accounts.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS battle_reports '
                       '(epoch TEXT PRIMARY KEY, account INTEGER NOT NULL, '
                       'counts TEXT NOT NULL, xp INTEGER NOT NULL)')

    # ----- battle lifetime (called by the game session) --------------------

    def begin(self, account_id, session):
        """Start a new battle epoch when the account enters TutorialAreaBasic."""
        epoch = secrets.token_hex(16)
        self.active[account_id] = (session, epoch)
        with self.accounts.connect() as db:
            db.execute('INSERT INTO battle_reports VALUES (?,?,?,0)', (epoch, account_id, '{}'))
        return epoch

    def end(self, account_id, session):
        if account_id in self.active and self.active[account_id][0] == session:
            del self.active[account_id]

    # ----- requests from the client bridge -------------------------------

    def state(self, account_id):
        """Battle start: epoch, saved totals and the XP display data."""
        if account_id not in self.active:
            raise ValueError('No authenticated battle for this account')
        epoch = self.active[account_id][1]
        with self.accounts.edit_profile(account_id) as profile:
            saved = dict(profile.get('battle_progress', {}))
        with self.accounts.connect() as db:
            row = db.execute('SELECT counts FROM battle_reports WHERE epoch=?', (epoch,)).fetchone()
        battle_xp = _battle_xp(json.loads(row[0])) if row else 0
        return dict(saved, epoch=epoch, **self._xp_display(saved.get('xp', 0), battle_xp))

    @staticmethod
    def _xp_display(total_xp, battle_xp):
        """What the client's XP bar shows: XP before this battle plus XP earned in it."""
        return {'xp_before_battle': total_xp - battle_xp, 'battle_xp': battle_xp,
                'xp_levels': list(XP_LEVELS)}

    def report(self, account_id, epoch, counts, xp):
        """Credit a cumulative report and return the account's saved totals."""
        if account_id not in self.active or self.active[account_id][1] != epoch:
            raise ValueError('Stale or unauthenticated battle')
        counts = _validate_report(counts, xp)
        row_id = account_id & 0xffffffff
        # Profile and high-water marks commit together under one SQLite lock.
        with self.accounts.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT account,counts,xp FROM battle_reports WHERE epoch=?', (epoch,)).fetchone()
            if row is None or row[0] != account_id:
                raise ValueError('Unknown battle epoch')
            merged, kills, rescues, kill_xp = _credit(json.loads(row[1]), counts)
            saved_row = db.execute('SELECT profile FROM accounts WHERE id=?', (row_id,)).fetchone()
            if saved_row is None:
                raise ValueError('Unknown account')
            profile = json.loads(saved_row[0])
            progress = profile.setdefault('battle_progress', {})
            # Client-collected XP stays in battle_reports for comparison only.
            progress['xp'] = progress.get('xp', 0) + kill_xp
            progress['kills'] = progress.get('kills', 0) + kills
            progress['rescues'] = progress.get('rescues', 0) + rescues
            progress['tutorial_ready'] = progress['kills'] >= KILL_TARGET and progress['rescues'] >= RESCUE_TARGET
            db.execute('UPDATE accounts SET profile=? WHERE id=?', (json.dumps(profile), row_id))
            db.execute('UPDATE battle_reports SET counts=?,xp=? WHERE epoch=?',
                       (json.dumps(merged), max(xp, row[2]), epoch))
        if kills or rescues:
            print(f'Battle progress: +{kills} kills, +{rescues} rescues, +{kill_xp} kill XP; '
                  f'tutorial_ready={progress["tutorial_ready"]}', flush=True)
        return dict(progress, epoch=epoch, **self._xp_display(progress['xp'], _battle_xp(merged)))

    # ----- loopback HTTP endpoint -----------------------------------------

    async def _read_request(self, reader):
        """Return (method, path, headers) of a bounded HTTP/1.1 request head."""
        head = await asyncio.wait_for(reader.readuntil(b'\r\n\r\n'), 5)
        if len(head) > 8192:
            raise ValueError('Headers too large')
        lines = head.decode('ascii').split('\r\n')
        method, path, _ = lines[0].split(' ')
        headers = {}
        for line in lines[1:]:
            if ':' in line:
                name, value = line.split(':', 1)
                headers[name.lower()] = value.strip()
        return method, path, headers

    async def handle(self, reader, writer):
        """Bounded loopback HTTP endpoint; unrelated SDK traffic gets closed."""
        status, result = 400, {'error': 'Invalid bridge request'}
        try:
            method, path, headers = await self._read_request(reader)
            if path != BRIDGE_PATH:
                return
            if not hmac.compare_digest(headers.get('authorization', ''), 'Bearer ' + self.token):
                status, result = 403, {'error': 'Invalid local bridge token'}
                return
            length = int(headers.get('content-length', '0'))
            if not 0 < length <= MAX_BODY:
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
            await self._respond(writer, status, result)

    @staticmethod
    async def _respond(writer, status, result):
        with suppress(ConnectionError):
            data = json.dumps(result).encode('ascii')
            writer.write(f'HTTP/1.1 {status} Result\r\nContent-Type: application/json\r\n'
                         f'Content-Length: {len(data)}\r\nConnection: close\r\n\r\n'.encode('ascii') + data)
            await writer.drain()
        writer.close()
        with suppress(ConnectionError):
            await writer.wait_closed()
