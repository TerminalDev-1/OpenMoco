from pathlib import Path
import tempfile
import unittest
from accounts import AccountStore


class AccountTests(unittest.TestCase):
    def test_onboarding_is_bound_and_survives_reopen(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'accounts.sqlite3'
            store = AccountStore(path)
            first, other = store.authenticate(0, None), store.authenticate(0, None)
            store.record_age_choice(first.account_id, 15)
            reopened = AccountStore(path)
            self.assertEqual(reopened.authenticate(first.account_id, first.token).profile['age_category'], 3)
            self.assertNotIn('age_category', reopened.authenticate(other.account_id, other.token).profile)
            reopened.record_age_choice(first.account_id, 16)
            self.assertEqual(reopened.authenticate(first.account_id, first.token).profile['age_category'], 2)
            for age in (0, 100, '16'):
                with self.assertRaises(ValueError):
                    reopened.record_age_choice(first.account_id, age)
            with self.assertRaises(ValueError):
                reopened.record_age_choice(1, 16)

    def test_create_and_reconnect_after_reopening(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'accounts.sqlite3'
            store = AccountStore(path)
            created = store.authenticate(0, None)
            self.assertTrue(created.created)
            self.assertNotEqual(created.account_id,0)
            self.assertLessEqual(created.account_id >> 32,255)
            self.assertNotIn(created.token,repr(created))
            reopened = AccountStore(path)
            returning = reopened.authenticate(created.account_id,created.token)
            self.assertFalse(returning.created)
            self.assertEqual(returning.profile,created.profile)
            self.assertEqual(returning.account_id,created.account_id)
            self.assertNotIn(created.token,path.read_bytes().decode('latin1'))

    def test_invalid_credentials_and_foreign_ids(self):
        with tempfile.TemporaryDirectory() as folder:
            store = AccountStore(Path(folder)/'accounts.sqlite3')
            account = store.authenticate(0,None)
            for identity,token in [(0,'unexpected'), (account.account_id,None),
                                   (account.account_id,'wrong'), (1,account.token)]:
                with self.assertRaises(ValueError):
                    store.authenticate(identity,token)

    def test_distinct_guest_ids_and_tokens(self):
        with tempfile.TemporaryDirectory() as folder:
            store=AccountStore(Path(folder)/'accounts.sqlite3')
            first,second=store.authenticate(0,None),store.authenticate(0,None)
            self.assertNotEqual(first.account_id,second.account_id)
            self.assertNotEqual(first.token,second.token)

    def test_migrate_legacy_id_without_losing_token_or_profile(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'accounts.sqlite3'
            store = AccountStore(path)
            account = store.authenticate(0,None)
            with store.connect() as db:
                db.execute('UPDATE settings SET value=? WHERE name=?', ('1073741824','namespace'))
            migrated = AccountStore(path)
            legacy_id = (1073741824 << 32) | (account.account_id & 0xffffffff)
            returning = migrated.authenticate(legacy_id,account.token)
            self.assertLessEqual(returning.account_id >> 32,255)
            self.assertEqual(returning.profile,account.profile)
            self.assertEqual(migrated.authenticate(returning.account_id,account.token).account_id,returning.account_id)
            with self.assertRaises(ValueError):
                migrated.authenticate(legacy_id,'wrong')
