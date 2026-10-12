from pathlib import Path
import tempfile
import unittest
from accounts import AccountStore


class AccountTests(unittest.TestCase):
    def test_create_and_reconnect_after_reopening(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'accounts.sqlite3'
            store = AccountStore(path)
            created = store.authenticate(0, None)
            self.assertTrue(created.created)
            self.assertNotEqual(created.account_id,0)
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
