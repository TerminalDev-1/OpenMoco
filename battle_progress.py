"""Server-side battle progress from the client's raw kill reports.

Combat itself still runs in the client (a deterministic rollback simulation,
see docs/BATTLE_PROTOCOL.md; the server would have to run the same simulation
to see kills itself). The client bridge (loader_diagnostics.js) only reads its
native killedEnemies counters and sends the raw cumulative count per
character data ID over the game connection, inside the client's own 18855
message (decode_kill_report). It decides nothing: every XP decision is made
here, for the game session that owns the connection. There is no listener
or token of its own.

For each report the server
- accepts only the monsters and civilians of the battle scene the account is
  in (anything else, e.g. Meat or spirits, is ignored),
- credits only the increase over the battle's best previous report (a battle
  epoch plus cumulative high-water marks make repeated reports and replayed
  prediction events harmless),
- caps the credited kills by the battle's elapsed time (KILL_RATE),
- prices each kill from characters.csv LootProfile -> loot_profiles.csv XP,
- saves XP, kills and rescues (progress.py turns them into quest progress),
- and gives the XP back to the running battle as the game's own XP event
  (battle_events.py, logic event 1217), so the native XP bar fills from
  server XP. The display data the client bridge still writes (job progress
  for the in-battle jobs tracker, the bar's base XP) rides on that event
  (display_trailer).
"""
import json
import secrets
import struct
import time
import zlib

from progress import KILL_TARGET, RESCUE_TARGET, XP_LEVELS, boost_kill_xp, credit_jobs, job_quests

TUTORIAL_AREA = 10900001   # Downtown Chaos
SHRINE_CANYON = 10900006   # W01_OA01

# characters.csv LootProfile -> loot_profiles.csv XP / 1000 (Weak 2000,
# WeakMedium 4000, Strong 10000, BossOpenSmall 88000, BossOpen 176000).
# Native 6a58c8 scales the loot XP and divides by 10000; loot XP / 1000 matches
# the observed ~1.6 collected XP per weak kill. Daily-budget multipliers, level
# adjustment and randomized rounding are not reproduced.
SCENE_KILL_XP = {
    TUTORIAL_AREA: {
        10800020: 2, 10800021: 2, 10800026: 2, 10800117: 2, 10800120: 2,  # Weak
        10800138: 4,                                                      # WeakMedium
        10800036: 10, 10800268: 10,                                       # Strong
    },
    # Monsters of the canyon zones sent by scene.canyon_scene (zones.csv
    # 149..165). Meat (Resource), the protected dragonling and the running
    # spirits are not monsters and earn nothing here.
    SHRINE_CANYON: {
        10800022: 2, 10800027: 2,                     # Weak melee / ranged
        10800038: 10, 10800269: 10,                   # Strong jumper / slammer
        10800449: 88, 10800056: 176, 10800087: 176,   # Zone 165 bosses
    },
}
# Human tutorial civilians (not Spirits) count as rescues in Downtown.
SCENE_RESCUES = {
    TUTORIAL_AREA: frozenset(range(10800309, 10800314)),
    SHRINE_CANYON: frozenset(),
}

KILL_RATE = 4      # Credited kills per second of battle, after the burst.
KILL_BURST = 20
MAX_COUNT = 100000
MAX_ENTRIES = 256
MAX_BODY = 16384
DESYNC_REPORT = 18855        # Client message type that carries the kill report.
REPORT_KIND = 'kills'        # Report JSON: {"openmoco": "kills", "counts": {...}}.
TRAILER_MAGIC = b'OMCO'      # Ends the display trailer appended to 28852.
MAX_TRAILER = 4096


def decode_kill_report(payload):
    """Return the raw counts of an 18855 kill report, or None for anything else.

    18855 is the client's desync report (sender 0x5c3654, encoder 0x7651fc):
    two byte buffers, each a raw int length (-1 when absent) and its bytes.
    The setters (0x76511c / 0x76518c -> 0x8f6f30) fill a buffer from a native
    string through zlib (0xa18b30: 4-byte little-endian plain length, then a
    zlib stream). The client bridge sends its report as the first buffer and
    no second one. This server never sends frame checksums (28854), so the
    client has no reason to send a real desync report; one would not parse
    as a report and is ignored.
    """
    from stream import Reader
    reader = Reader(payload)
    size = reader.integer()
    if not 4 < size <= MAX_BODY or reader.remaining != size + 4:
        return None
    data = reader.raw(size)
    if reader.integer() != -1:
        return None
    plain_size = int.from_bytes(data[:4], 'little')
    if not 0 < plain_size <= MAX_BODY:
        return None
    try:
        plain = zlib.decompressobj().decompress(data[4:], MAX_BODY + 1)
        report = json.loads(plain.decode('ascii'))
    except (zlib.error, UnicodeError, ValueError):
        return None
    if len(plain) != plain_size or not isinstance(report, dict) or report.get('openmoco') != REPORT_KIND:
        return None
    return report.get('counts')


def display_trailer(display):
    """Bytes appended to a 28852 XP event for the client bridge.

    The native decoder (0x761770) reads only the frame and the events vector;
    the client bridge reads this trailer from the end of the received stream
    (stream +0x18 length, +0x38 data): ASCII JSON, its 4-byte big-endian
    length, then TRAILER_MAGIC.
    """
    data = json.dumps(display, separators=(',', ':')).encode('ascii')
    if len(data) > MAX_TRAILER:
        raise ValueError('Display trailer too large')
    return data + struct.pack('>I', len(data)) + TRAILER_MAGIC


def _validate_report(counts):
    """Return clean {character_id: count} or raise ValueError.

    The client reports every character it has killed; IDs that are not part
    of the battle scene are ignored when credited.
    """
    if not isinstance(counts, dict) or len(counts) > MAX_ENTRIES:
        raise ValueError('Invalid outcome counts')
    clean = {}
    for key, count in counts.items():
        if not isinstance(key, str) or not key.isdigit() or not 0 < int(key) < 1 << 40:
            raise ValueError('Invalid character data ID')
        if type(count) is not int or not 0 <= count <= MAX_COUNT:
            raise ValueError('Invalid cumulative outcome')
        clean[int(key)] = count
    return clean


def _credit(scene, record, counts, elapsed):
    """Credit a report against one battle's record.

    record = {'seen': high-water counts, 'credited': credited counts}, keyed
    by character ID string. Returns (new record, kills, rescues, kill XP,
    {character ID: newly credited count}).
    """
    kill_xp_table, rescuable = SCENE_KILL_XP[scene], SCENE_RESCUES[scene]
    seen = dict(record.get('seen', {}))
    credited = dict(record.get('credited', {}))
    for character, count in counts.items():
        if character in kill_xp_table or character in rescuable:
            key = str(character)
            seen[key] = max(seen.get(key, 0), count)
    budget = KILL_BURST + int(KILL_RATE * max(0.0, elapsed)) - sum(credited.values())
    kills = rescues = kill_xp = 0
    gained = {}
    for key in sorted(seen):
        gain = min(seen[key] - credited.get(key, 0), budget)
        if gain <= 0:
            continue
        budget -= gain
        credited[key] = credited.get(key, 0) + gain
        character = int(key)
        gained[character] = gain
        if character in kill_xp_table:
            kills += gain
            kill_xp += gain * kill_xp_table[character]
        else:
            rescues += gain
    return {'seen': seen, 'credited': credited}, kills, rescues, kill_xp, gained


def _battle_xp(scene, record):
    """Kill XP credited so far in one battle."""
    table = SCENE_KILL_XP[scene]
    return sum(count * table.get(int(key), 0) for key, count in record.get('credited', {}).items())


class Battle:
    """One battle epoch of one authenticated game session."""

    def __init__(self, account_id, scene):
        self.account_id, self.scene = account_id, scene
        self.epoch = secrets.token_hex(16)
        self.started = time.monotonic()


class BattleProgress:
    """Credits the kill reports of the game sessions' battles."""

    def __init__(self, accounts):
        self.accounts = accounts
        with accounts.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS battle_reports '
                       '(epoch TEXT PRIMARY KEY, account INTEGER NOT NULL, '
                       'counts TEXT NOT NULL, xp INTEGER NOT NULL)')

    def begin(self, account_id, scene=TUTORIAL_AREA):
        """Start a new battle epoch when the session enters a battle scene."""
        if scene not in SCENE_KILL_XP:
            raise ValueError('Unsupported battle scene')
        battle = Battle(account_id, scene)
        with self.accounts.connect() as db:
            db.execute('INSERT INTO battle_reports VALUES (?,?,?,0)', (battle.epoch, account_id, '{}'))
        return battle

    def state(self, battle):
        """Saved totals and the XP display data of a running battle."""
        with self.accounts.edit_profile(battle.account_id) as profile:
            saved = dict(profile.get('battle_progress', {}))
            jobs = self._job_progress(battle, profile)
        with self.accounts.connect() as db:
            row = db.execute('SELECT counts FROM battle_reports WHERE epoch=?', (battle.epoch,)).fetchone()
        battle_xp = _battle_xp(battle.scene, json.loads(row[0])) if row else 0
        return dict(saved, epoch=battle.epoch, jobs=jobs, **self._xp_display(saved.get('xp', 0), battle_xp))

    @staticmethod
    def _job_progress(battle, profile):
        """Today's job progress, in the order the battle's quest list has them
        (scene._with_battle_jobs). The client bridge shows it on the in-battle
        jobs tracker; the tracker's own kill counting reads a frame copy that
        never sees kills here."""
        if battle.scene != SHRINE_CANYON:
            return []
        return [min(quest.progress, quest.target) for quest in job_quests(profile, time.time(), battle.account_id)]

    @staticmethod
    def _xp_display(total_xp, battle_xp):
        """XP before this battle (the bar's base), server XP granted in it, and the levels."""
        return {'xp_before_battle': total_xp - battle_xp, 'battle_xp': battle_xp,
                'xp_levels': list(XP_LEVELS)}

    def report(self, battle, counts):
        """Credit a cumulative raw kill report.

        Returns (the account's saved totals with the XP display data, the
        newly credited XP for the running battle).
        """
        counts = _validate_report(counts)
        account_id, epoch = battle.account_id, battle.epoch
        elapsed = time.monotonic() - battle.started
        row_id = account_id & 0xffffffff
        # Profile and high-water marks commit together under one SQLite lock.
        with self.accounts.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT account,counts FROM battle_reports WHERE epoch=?', (epoch,)).fetchone()
            if row is None or row[0] != account_id:
                raise ValueError('Unknown battle epoch')
            record, kills, rescues, kill_xp, gained = _credit(battle.scene, json.loads(row[1]), counts, elapsed)
            saved_row = db.execute('SELECT profile FROM accounts WHERE id=?', (row_id,)).fetchone()
            if saved_row is None:
                raise ValueError('Unknown account')
            profile = json.loads(saved_row[0])
            progress = profile.setdefault('battle_progress', {})
            # Daily jobs are Shrine Canyon map missions; completing one pays its reward.
            job_xp = credit_jobs(profile, gained, time.time(), account_id) if battle.scene == SHRINE_CANYON else 0
            kill_xp = boost_kill_xp(profile, kill_xp, time.time())  # Boosted chaos energy.
            progress['xp'] = progress.get('xp', 0) + kill_xp + job_xp
            progress['kills'] = progress.get('kills', 0) + kills
            progress['rescues'] = progress.get('rescues', 0) + rescues
            progress['tutorial_ready'] = progress['kills'] >= KILL_TARGET and progress['rescues'] >= RESCUE_TARGET
            db.execute('UPDATE accounts SET profile=? WHERE id=?', (json.dumps(profile), row_id))
            db.execute('UPDATE battle_reports SET counts=?,xp=? WHERE epoch=?',
                       (json.dumps(record), _battle_xp(battle.scene, record), epoch))
        if kills or rescues:
            print(f'Battle progress: +{kills} kills, +{rescues} rescues, +{kill_xp} kill XP; '
                  f'tutorial_ready={progress["tutorial_ready"]}', flush=True)
        if job_xp:
            print(f'Daily job completed: +{job_xp} XP', flush=True)
        result = dict(progress, epoch=epoch, jobs=self._job_progress(battle, profile),
                      **self._xp_display(progress['xp'], _battle_xp(battle.scene, record)))
        return result, kill_xp + job_xp
