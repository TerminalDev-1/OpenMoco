"""Persistent local guest identities, independent of Supercell accounts."""
from dataclasses import dataclass, field
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import hmac
import json
from pathlib import Path
import secrets
import sqlite3


@dataclass(frozen=True)
class LocalAccount:
    account_id: int
    token: str = field(repr=False)
    profile: dict
    created: bool


class AccountStore:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS settings (name TEXT PRIMARY KEY, value TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS accounts (id INTEGER PRIMARY KEY AUTOINCREMENT, token_hash TEXT NOT NULL, profile TEXT NOT NULL, created_at TEXT NOT NULL)')
            # Native player-tag conversion 0x8f81e8 rejects a high ID word >255.
            db.execute('INSERT OR IGNORE INTO settings VALUES (?, ?)', ('namespace', str(128 | secrets.randbits(7))))
            self.namespace = int(db.execute('SELECT value FROM settings WHERE name=?', ('namespace',)).fetchone()[0])
            if self.namespace > 255:
                db.execute('INSERT OR IGNORE INTO settings VALUES (?, ?)', ('legacy_namespace', str(self.namespace)))
                self.namespace = 128 | secrets.randbits(7)
                db.execute('UPDATE settings SET value=? WHERE name=?', (str(self.namespace), 'namespace'))
            previous = db.execute('SELECT value FROM settings WHERE name=?', ('legacy_namespace',)).fetchone()
            self.legacy_namespace = int(previous[0]) if previous else None

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path)
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def token_hash(token):
        return hashlib.sha256(token.encode('utf-8')).hexdigest()

    def authenticate(self, account_id, token):
        if account_id == 0:
            if token:
                raise ValueError('A new local guest cannot supply an existing account token')
            token = secrets.token_urlsafe(32)
            profile = {'display_name': 'Local Hunter', 'tutorials': {}, 'scene_id': 10900000}
            with self.connect() as db:
                cursor = db.execute('INSERT INTO accounts (token_hash,profile,created_at) VALUES (?,?,?)',
                    (self.token_hash(token), json.dumps(profile), datetime.now(timezone.utc).isoformat()))
                low_id = cursor.lastrowid
                if low_id > 0xffffffff:
                    raise ValueError('Local account ID range exhausted')
            return LocalAccount((self.namespace << 32) | low_id, token, profile, True)
        if not isinstance(account_id, int) or account_id < 0 or account_id >> 32 not in (self.namespace, self.legacy_namespace) or not token:
            raise ValueError('Unknown local account or missing reconnect token')
        with self.connect() as db:
            row = db.execute('SELECT token_hash,profile FROM accounts WHERE id=?', (account_id & 0xffffffff,)).fetchone()
        if row is None or not hmac.compare_digest(row[0], self.token_hash(token)):
            raise ValueError('Local reconnect token is invalid')
        return LocalAccount((self.namespace << 32) | (account_id & 0xffffffff), token, json.loads(row[1]), False)

    def record_age_choice(self, account_id, age):
        """Persist only native key-7 category from an authenticated 541 command.

        0x684da0 accepts 1..99; 0x684e00..10 yields 3 below the default
        threshold 16, otherwise 2. The raw age is not retained.
        """
        if not isinstance(account_id, int) or account_id >> 32 != self.namespace:
            raise ValueError('Unknown local account namespace')
        if not isinstance(age, int) or not 1 <= age <= 99:
            raise ValueError('Invalid onboarding age choice')
        with self.connect() as db:
            row = db.execute('SELECT profile FROM accounts WHERE id=?', (account_id & 0xffffffff,)).fetchone()
            if row is None:
                raise ValueError('Unknown local account')
            profile = json.loads(row[0])
            profile['age_category'] = 3 if age < 16 else 2
            db.execute('UPDATE accounts SET profile=? WHERE id=?', (json.dumps(profile), account_id & 0xffffffff))

    def record_cosmetic(self, account_id, cosmetic):
        """Persist an equipped starter face or hairstyle from command 543.

        The native handler 0x687128 rejects cosmetics missing from the
        client-home vanity items, so only the server's starter items are kept.
        """
        from home import cosmetic_slot
        slot = cosmetic_slot(cosmetic)
        with self.edit_profile(account_id) as profile:
            profile.setdefault('look', {})[str(slot)] = cosmetic
        return slot

    def record_display_name(self, account_id, name):
        """Persist the hunter name accepted from 17582."""
        with self.edit_profile(account_id) as profile:
            profile['display_name'] = name
            profile['name_set'] = True

    def record_tutorial(self, account_id, tutorial, step):
        from progress import validate_tutorial
        validate_tutorial(tutorial, step)
        with self.edit_profile(account_id) as profile:
            progress = profile.setdefault('tutorials', {})
            key = str(tutorial)
            # A replayed earlier turn must not undo a completed tutorial.
            if key not in progress or progress[key] != 0:
                progress[key] = step

    def record_main_quest(self, account_id, command_type, step):
        """Persist an authenticated 575 (step seen) or 576 (step completed) command."""
        from progress import record_main_quest
        with self.edit_profile(account_id) as profile:
            record_main_quest(profile, command_type, step)

    def claim_quests(self, account_id, quest_ids, now):
        """Persist an authenticated 569 claim. Only the daily goal is handled
        here; returns the XP granted (0 when the goal was not claimed)."""
        from progress import claim_daily_goal, daily_goal_quest_id
        with self.edit_profile(account_id) as profile:
            goal = daily_goal_quest_id(profile, now, account_id)
            if goal is None or goal not in quest_ids:
                return 0
            return claim_daily_goal(profile, now, account_id)

    def complete_intro_quest(self, account_id):
        """Advance the Portal tutorial if Intro_3 was earned. Returns True if advanced."""
        from progress import complete_intro_quest
        with self.edit_profile(account_id) as profile:
            return complete_intro_quest(profile)

    def record_scene(self, account_id, scene_id):
        if scene_id not in (10900000, 10900001, 10900005, 10900006):
            raise ValueError('Unsupported local scene')
        with self.edit_profile(account_id) as profile:
            profile['scene_id'] = scene_id

    @contextmanager
    def edit_profile(self, account_id):
        if type(account_id) is not int or account_id >> 32 != self.namespace:
            raise ValueError('Unknown local account namespace')
        with self.connect() as db:
            # Serialize read/modify/write across simultaneous guest sessions.
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT profile FROM accounts WHERE id=?', (account_id & 0xffffffff,)).fetchone()
            if row is None:
                raise ValueError('Unknown local account')
            profile = json.loads(row[0])
            yield profile
            db.execute('UPDATE accounts SET profile=? WHERE id=?', (json.dumps(profile), account_id & 0xffffffff))
