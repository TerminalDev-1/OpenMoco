import asyncio
import json
from pathlib import Path
import tempfile
import unittest

from accounts import AccountStore
from battle_bridge import BattleBridge


class BattleBridgeTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.store = AccountStore(Path(self.folder.name)/'accounts.sqlite3')
        self.account = self.store.authenticate(0, None)
        self.bridge = BattleBridge(self.store, 'a'*64)
        self.epoch = self.bridge.begin(self.account.account_id, 'one')

    def report(self, counts, xp=0, epoch=None):
        return self.bridge.report(self.account.account_id, epoch or self.epoch, counts, xp)

    def test_retries_rollbacks_and_missing_keys_do_not_repeat_rewards(self):
        self.report({'10800021': 2, '10800309': 1}, 3)
        self.report({'10800021': 2, '10800309': 1}, 3)
        self.report({'10800021': 1}, 1)
        state = self.report({'10800021': 3}, 5)
        self.assertEqual((state['kills'], state['rescues'], state['xp']), (3, 1, 6))
        self.assertFalse(state['tutorial_ready'])

    def test_kill_xp_uses_loot_profiles_and_survives_reopen(self):
        state = self.report({'10800021': 50, '10800309': 3})
        self.assertEqual(state['xp'], 100)  # Weak loot profile: 2 per kill.
        self.assertTrue(state['tutorial_ready'])
        state = self.report({'10800021': 50, '10800138': 1, '10800268': 2, '10800309': 3}, 7)
        self.assertEqual(state['xp'], 124)  # WeakMedium 4, Strong 10; collected XP ignored.
        reopened = AccountStore(self.store.path)
        profile = reopened.authenticate(self.account.account_id, self.account.token).profile
        self.assertEqual(profile['battle_progress']['xp'], 124)
        self.assertEqual(profile['tutorials'], {})  # Readiness does not fake completion.

    def test_epoch_account_and_character_isolation(self):
        other = self.store.authenticate(0, None)
        with self.assertRaises(ValueError):
            self.bridge.report(other.account_id, self.epoch, {'10800021': 1}, 1)
        for counts, xp in [({'10800092': 1}, 0), ({'10800021': True}, 0), ({}, -1), ({}, True)]:
            with self.assertRaises(ValueError):
                self.report(counts, xp)
        newer = self.bridge.begin(self.account.account_id, 'two')
        with self.assertRaises(ValueError):
            self.report({'10800021': 1}, 1)
        self.bridge.end(self.account.account_id, 'one')
        self.assertEqual(self.bridge.state(self.account.account_id)['epoch'], newer)
        self.bridge.end(self.account.account_id, 'two')
        with self.assertRaises(ValueError):
            self.bridge.state(self.account.account_id)

    def test_http_authorization_and_persistence(self):
        async def check():
            listener = await asyncio.start_server(self.bridge.handle, '127.0.0.1', 0)
            try:
                port = listener.sockets[0].getsockname()[1]
                async def send(token):
                    r, w = await asyncio.open_connection('127.0.0.1', port)
                    body = json.dumps(dict(account_id=str(self.account.account_id), epoch=self.epoch,
                                           counts={'10800021': 1}, xp=2)).encode()
                    w.write(f'POST /openmoco/battle HTTP/1.1\r\nAuthorization: Bearer {token}\r\nContent-Length: {len(body)}\r\n\r\n'.encode()+body)
                    await w.drain()
                    result = await r.read()
                    w.close()
                    await w.wait_closed()
                    return result
                self.assertIn(b'403', await send('wrong'))
                self.assertIn(b'200', await send('a'*64))
                self.assertEqual(self.bridge.state(self.account.account_id)['xp'], 2)  # One weak kill.
            finally:
                listener.close()
                await listener.wait_closed()
        asyncio.run(check())
