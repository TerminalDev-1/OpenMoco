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
            profile = {'display_name': 'Local Hunter'}
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
