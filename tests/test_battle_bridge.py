import asyncio
import json
from pathlib import Path
import tempfile
import unittest

from accounts import AccountStore
from battle_bridge import KILL_BURST, KILL_RATE, SHRINE_CANYON, BattleBridge


class BattleBridgeTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.store = AccountStore(Path(self.folder.name)/'accounts.sqlite3')
        self.account = self.store.authenticate(0, None)
        self.bridge = BattleBridge(self.store, 'a'*64)
        self.granted = []
        self.epoch = self.begin('one')

    def begin(self, session, scene=10900001, long_ago=True):
        epoch = self.bridge.begin(self.account.account_id, session, scene, self.granted.append)
        if long_ago:  # Lift the elapsed-time kill cap for bulk reports.
            self.bridge.active[self.account.account_id].started -= 3600
        return epoch

    def report(self, counts, epoch=None):
        return self.bridge.report(self.account.account_id, epoch or self.epoch, counts)

    def test_retries_rollbacks_and_missing_keys_do_not_repeat_rewards(self):
        self.report({'10800021': 2, '10800309': 1})
        self.report({'10800021': 2, '10800309': 1})
        self.report({'10800021': 1})
        state = self.report({'10800021': 3})
        self.assertEqual((state['kills'], state['rescues'], state['xp']), (3, 1, 6))
        self.assertFalse(state['tutorial_ready'])
        self.assertEqual(self.granted, [4, 2])  # Only new XP goes to the battle.

    def test_kill_xp_uses_loot_profiles_and_survives_reopen(self):
        state = self.report({'10800021': 50, '10800309': 3})
        self.assertEqual(state['xp'], 100)  # Weak loot profile: 2 per kill.
        self.assertTrue(state['tutorial_ready'])
        state = self.report({'10800021': 50, '10800138': 1, '10800268': 2, '10800309': 3})
        self.assertEqual(state['xp'], 124)  # WeakMedium 4, Strong 10.
        reopened = AccountStore(self.store.path)
        profile = reopened.authenticate(self.account.account_id, self.account.token).profile
        self.assertEqual(profile['battle_progress']['xp'], 124)
        self.assertEqual(profile['tutorials'], {})  # Readiness does not fake completion.

    def test_raw_reports_are_validated_per_scene(self):
        # Spirits, Meat and canyon monsters earn nothing in Downtown.
        state = self.report({'10800092': 4, '10800212': 2, '10800022': 5, '10800021': 1})
        self.assertEqual((state['kills'], state['xp']), (1, 2))
        canyon = self.begin('two', SHRINE_CANYON)
        state = self.report({'10800022': 3, '10800269': 1, '10800056': 1, '10800212': 9,
                             '10800100': 1, '10800309': 2, '10800021': 4}, canyon)
        # Weak 2, Strong 10, BossOpen 176; Meat, the protected dragonling,
        # civilians and Downtown monsters are ignored in the canyon.
        self.assertEqual((state['kills'], state['rescues'], state['xp']), (6, 0, 2 + 6 + 10 + 176))  # Totals include Downtown's kill.
        self.assertEqual(self.granted, [2, 192])

    def test_kills_are_capped_by_battle_time(self):
        epoch = self.begin('two', long_ago=False)
        state = self.report({'10800021': 500}, epoch)
        self.assertEqual(state['kills'], KILL_BURST)
        self.bridge.active[self.account.account_id].started -= 10
        state = self.report({'10800021': 500}, epoch)
        self.assertEqual(state['kills'], KILL_BURST + 10 * KILL_RATE)

    def test_xp_bar_display_splits_saved_and_battle_xp(self):
        from progress import XP_LEVELS
        self.report({'10800021': 10})  # 20 XP in an earlier battle.
        epoch = self.begin('two')
        state = self.bridge.state(self.account.account_id)
        self.assertEqual((state['xp_before_battle'], state['battle_xp']), (20, 0))
        self.assertEqual(state['xp_levels'], list(XP_LEVELS))
        result = self.report({'10800021': 3, '10800268': 1}, epoch=epoch)
        self.assertEqual((result['xp'], result['xp_before_battle'], result['battle_xp']), (36, 20, 16))
        result = self.report({'10800021': 3, '10800268': 1}, epoch=epoch)
        self.assertEqual(result['battle_xp'], 16)
        self.assertEqual(self.bridge.state(self.account.account_id)['battle_xp'], 16)

    def test_xp_levels_never_stall_the_native_level_loop(self):
        from progress import XP_LEVELS
        self.assertTrue(XP_LEVELS)
        self.assertTrue(all(type(v) is int and v > 0 for v in XP_LEVELS))

    def test_epoch_account_and_report_isolation(self):
        other = self.store.authenticate(0, None)
        with self.assertRaises(ValueError):
            self.bridge.report(other.account_id, self.epoch, {'10800021': 1})
        for counts in [{'10800021': True}, {'10800021': -1}, {'x': 1}, {'-5': 1}, [], {str(i): 1 for i in range(300)}]:
            with self.assertRaises(ValueError):
                self.report(counts)
        with self.assertRaises(ValueError):
            self.bridge.begin(self.account.account_id, 'two', 10900000)
        newer = self.begin('two')
        with self.assertRaises(ValueError):
            self.report({'10800021': 1})
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
                                           counts={'10800021': 1})).encode()
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


class BattleEventTests(unittest.TestCase):
    def test_xp_event_layout(self):
        from battle_events import xp_event
        from stream import Reader
        payload = xp_event(1234, 300)
        reader = Reader(payload)
        self.assertEqual(reader.integer(), 1234)
        self.assertEqual(reader.compact(), 1)                     # events count
        self.assertTrue(reader.boolean())                         # event present
        self.assertEqual(reader.compact(), 1217)                  # LogicXpEvent
        self.assertFalse(reader.boolean())                        # battlePlayerId 0
        self.assertTrue(reader.boolean())
        self.assertEqual(reader.compact(), 300)                   # xp
        self.assertFalse(reader.boolean())                        # questSpeciality 0
        self.assertFalse(reader.boolean())                        # dropCoins
        self.assertEqual(reader.remaining, 0)
        self.assertEqual(payload, bytes.fromhex('000004d2' '01' '05' '8113' 'ac04'))

    def test_xp_event_rejects_bad_values(self):
        from battle_events import xp_event
        for frame, xp in [(0, 1), (-1, 1), (1, 0), (1, -3), (1, True), (1 << 31, 1)]:
            with self.assertRaises(ValueError):
                xp_event(frame, xp)


class SessionXpTests(unittest.IsolatedAsyncioTestCase):
    async def test_queued_xp_goes_to_a_recent_unconfirmed_frame(self):
        from battle_events import xp_event
        from server import BATTLE_EVENTS, SHRINE_CANYON, XP_EVENT_LAG, GameSession

        class Writer:
            def get_extra_info(self, name):
                return None
        session = GameSession(None, Writer(), Path(tempfile.gettempdir()))
        sent = []
        async def send_session(message_type, body, version=0):
            sent.append((message_type, body))
        session.send_session = send_session
        session.current_scene = SHRINE_CANYON
        session.queue_battle_xp(4)
        session.queue_battle_xp(10)
        session.confirmed_frame = 101
        await session._send_battle_xp(100)          # Target 99 is already confirmed.
        self.assertEqual(sent, [])
        session.confirmed_frame = 140
        await session._send_battle_xp(101)
        self.assertEqual(sent, [(BATTLE_EVENTS, xp_event(140 - XP_EVENT_LAG, 14))])
        await session._send_battle_xp(140)          # Nothing left to send.
        self.assertEqual(len(sent), 1)
        session.queue_battle_xp(2)
        session._reset_scene_clock()                # A new scene drops the old battle's XP.
        session.confirmed_frame = 50
        await session._send_battle_xp(0)
        self.assertEqual(len(sent), 1)


if __name__ == '__main__':
    unittest.main()


class BattleEndTests(unittest.TestCase):
    def test_summary_layout_with_gem_drops(self):
        import struct
        from battle_end import GEAR_DROP, Drop, battle_end
        from stream import Reader
        body = battle_end(10900006, (Drop(GEAR_DROP, 11301977, 2),), account_id=0x80000001, name='hi')
        reader = Reader(body)
        self.assertEqual([reader.compact() for _ in range(4)], [0, 0, 0, 0])
        self.assertEqual(reader.compact(), 1)                        # one player
        self.assertEqual(struct.unpack('>Q', reader.raw(8))[0], 0x80000001)
        # The drop entry closes the body before compact +0xd8, the seven
        # absent objects and the empty string.
        tail = bytes([0x0c]) + struct.pack('>Q', 11301977) + bytes([2, 0, 0])
        self.assertIn(tail, body)
        self.assertTrue(body.endswith(bytes(4)))

    def test_canyon_kills_roll_pending_cores(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        store = AccountStore(Path(folder.name)/'accounts.sqlite3')
        account = store.authenticate(0, None)
        bridge = BattleBridge(store, 'a'*64)
        epoch = bridge.begin(account.account_id, 'one', SHRINE_CANYON)
        bridge.active[account.account_id].started -= 3600
        bridge.report(account.account_id, epoch, {'10800056': 2})   # Bosses always drop a core.
        with store.edit_profile(account.account_id) as profile:
            self.assertEqual(len(profile['pending_cores']), 2)
