import json
from pathlib import Path
import struct
import tempfile
import unittest
import zlib

from accounts import AccountStore
from battle_progress import (KILL_BURST, KILL_RATE, SHRINE_CANYON, TRAILER_MAGIC, BattleProgress,
                             decode_kill_report, display_trailer)


def kill_report(counts, kind='kills'):
    """An 18855 body as the client bridge sends it through 0x5c3654."""
    plain = json.dumps({'openmoco': kind, 'counts': counts}).encode('ascii')
    data = len(plain).to_bytes(4, 'little') + zlib.compress(plain)
    return struct.pack('>i', len(data)) + data + struct.pack('>i', -1)


class BattleProgressTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.store = AccountStore(Path(self.folder.name)/'accounts.sqlite3')
        self.account = self.store.authenticate(0, None)
        self.progress = BattleProgress(self.store)
        self.granted = []
        self.battle = self.begin()

    def begin(self, scene=10900001, long_ago=True):
        battle = self.progress.begin(self.account.account_id, scene)
        if long_ago:  # Lift the elapsed-time kill cap for bulk reports.
            battle.started -= 3600
        return battle

    def report(self, counts, battle=None):
        state, xp = self.progress.report(battle or self.battle, counts)
        if xp:
            self.granted.append(xp)
        return state

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
        canyon = self.begin(SHRINE_CANYON)
        state = self.report({'10800022': 3, '10800269': 1, '10800056': 1, '10800212': 9,
                             '10800100': 1, '10800309': 2, '10800021': 4}, canyon)
        # Weak 2, Strong 10, BossOpen 176; Meat, the protected dragonling,
        # civilians and Downtown monsters are ignored in the canyon.
        self.assertEqual((state['kills'], state['rescues'], state['xp']), (6, 0, 2 + 6 + 10 + 176))  # Totals include Downtown's kill.
        self.assertEqual(self.granted, [2, 192])

    def test_kills_are_capped_by_battle_time(self):
        battle = self.begin(long_ago=False)
        state = self.report({'10800021': 500}, battle)
        self.assertEqual(state['kills'], KILL_BURST)
        battle.started -= 10
        state = self.report({'10800021': 500}, battle)
        self.assertEqual(state['kills'], KILL_BURST + 10 * KILL_RATE)

    def test_xp_bar_display_splits_saved_and_battle_xp(self):
        from progress import XP_LEVELS
        self.report({'10800021': 10})  # 20 XP in an earlier battle.
        battle = self.begin()
        state = self.progress.state(battle)
        self.assertEqual((state['xp_before_battle'], state['battle_xp']), (20, 0))
        self.assertEqual(state['xp_levels'], list(XP_LEVELS))
        result = self.report({'10800021': 3, '10800268': 1}, battle)
        self.assertEqual((result['xp'], result['xp_before_battle'], result['battle_xp']), (36, 20, 16))
        result = self.report({'10800021': 3, '10800268': 1}, battle)
        self.assertEqual(result['battle_xp'], 16)
        self.assertEqual(self.progress.state(battle)['battle_xp'], 16)

    def test_xp_levels_never_stall_the_native_level_loop(self):
        from progress import XP_LEVELS
        self.assertTrue(XP_LEVELS)
        self.assertTrue(all(type(v) is int and v > 0 for v in XP_LEVELS))

    def test_battles_are_isolated_and_reports_validated(self):
        other = self.store.authenticate(0, None)
        foreign = self.progress.begin(other.account_id)
        foreign.epoch = self.battle.epoch      # Another account cannot use this epoch.
        with self.assertRaises(ValueError):
            self.progress.report(foreign, {'10800021': 1})
        for counts in [{'10800021': True}, {'10800021': -1}, {'x': 1}, {'-5': 1}, [], {str(i): 1 for i in range(300)}]:
            with self.assertRaises(ValueError):
                self.report(counts)
        with self.assertRaises(ValueError):
            self.progress.begin(self.account.account_id, 10900000)
        older = self.battle
        newer = self.begin()
        self.report({'10800021': 1}, older)    # Each epoch keeps its own marks.
        self.assertEqual(self.report({'10800021': 1}, newer)['kills'], 2)

    def test_kill_report_decoding(self):
        self.assertEqual(decode_kill_report(kill_report({'10800021': 3})), {'10800021': 3})
        plain = json.dumps({'openmoco': 'kills', 'counts': {}}).encode()
        data = len(plain).to_bytes(4, 'little') + zlib.compress(plain)
        bad_size = (len(plain) + 1).to_bytes(4, 'little') + zlib.compress(plain)
        for payload in [kill_report({}, kind='desync'), b'', struct.pack('>i', -1) * 2,
                        struct.pack('>i', len(data)) + data + struct.pack('>i', 3) + b'abc',
                        struct.pack('>i', len(bad_size)) + bad_size + struct.pack('>i', -1),
                        struct.pack('>i', 9) + b'\x05\0\0\0notzl' + struct.pack('>i', -1)]:
            try:
                self.assertIsNone(decode_kill_report(payload))
            except ValueError:
                pass   # A truncated stream is rejected by the reader.

    def test_display_trailer_ends_with_length_and_magic(self):
        trailer = display_trailer({'jobs': [1, 2], 'xp_before_battle': 5, 'xp_levels': [200]})
        self.assertTrue(trailer.endswith(TRAILER_MAGIC))
        size = struct.unpack('>I', trailer[-8:-4])[0]
        self.assertEqual(json.loads(trailer[-8 - size:-8]), {'jobs': [1, 2], 'xp_before_battle': 5, 'xp_levels': [200]})
        with self.assertRaises(ValueError):
            display_trailer({'jobs': list(range(5000))})


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
    async def test_kill_reports_on_the_game_connection_credit_the_session_battle(self):
        from battle_events import xp_event
        from server import BATTLE_EVENTS, SHRINE_CANYON, XP_EVENT_LAG, GameSession
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        store = AccountStore(Path(folder.name)/'accounts.sqlite3')

        class Writer:
            def get_extra_info(self, name):
                return None
        session = GameSession(None, Writer(), Path(folder.name), accounts=store, apartment=True)
        session.account = store.authenticate(0, None)
        sent = []
        async def send_session(message_type, body, version=0):
            sent.append((message_type, body))
        session.send_session = send_session
        session.on_kill_report(kill_report({'10800022': 2}))   # Not in a battle: ignored.
        self.assertEqual(session.pending_battle_xp, 0)
        session.current_scene = SHRINE_CANYON
        session._begin_battle(SHRINE_CANYON)
        session.on_kill_report(kill_report({'10800022': 2, '10800212': 4}))
        session.on_kill_report(kill_report({'10800022': 2}))   # Repeats earn nothing.
        self.assertEqual(session.pending_battle_xp, 4)          # Two weak kills, Meat ignored.
        session.on_kill_report(b'not a report')
        session.confirmed_frame = 40
        await session._send_battle_xp(0)
        message_type, body = sent[0]
        self.assertEqual(message_type, BATTLE_EVENTS)
        event = xp_event(40 - XP_EVENT_LAG, 4)
        self.assertTrue(body.startswith(event) and body.endswith(TRAILER_MAGIC))
        display = json.loads(body[len(event):-8])
        self.assertEqual(display['xp_before_battle'], 0)
        self.assertEqual(display['jobs'], [])                   # Jobs start after ToHQ.
        saved = store.authenticate(session.account.account_id, session.account.token).profile
        self.assertEqual(saved['battle_progress']['kills'], 2)


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
    def test_summary_layout_with_look_and_no_drops(self):
        import struct
        from battle_end import battle_end
        from home import STARTER_DYES, equipped_look
        from stream import Reader
        look = equipped_look(None)
        body = battle_end(10900006, account_id=0x80000001, name='hi', look=look)
        reader = Reader(body)
        self.assertEqual([reader.compact() for _ in range(4)], [0, 0, 0, 0])
        self.assertEqual(reader.compact(), 1)                        # one player
        self.assertEqual(struct.unpack('>Q', reader.raw(8))[0], 0x80000001)
        for item in look:   # Dye strings and the face reference are in the look.
            if item in STARTER_DYES:
                self.assertIn(STARTER_DYES[item][1].encode(), body)
            else:
                self.assertIn(struct.pack('>Q', item), body)
        # Scene object, empty drops, compact +0xd8, seven absent objects, ''.
        self.assertTrue(body.endswith(struct.pack(">Q", 10900006) + bytes(10)))
        plain = battle_end(10900006, account_id=0x80000001, name='hi')
        self.assertEqual(len(body) - len(plain),
                         sum(len(STARTER_DYES[i][1]) + 4 if i in STARTER_DYES else 8 for i in look))


class BattleJobProgressTests(unittest.TestCase):
    def test_canyon_replies_carry_job_progress_in_quest_order(self):
        import time
        from progress import job_quests
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        store = AccountStore(Path(folder.name)/'accounts.sqlite3')
        account = store.authenticate(0, None)
        with store.edit_profile(account.account_id) as profile:
            profile['tutorials'] = {'15600009': 0}   # COOL zone reached: jobs active.
        progress = BattleProgress(store)
        battle = progress.begin(account.account_id, SHRINE_CANYON)
        battle.started -= 3600
        self.assertEqual(progress.state(battle)['jobs'], [0, 0, 0])
        with store.edit_profile(account.account_id) as profile:
            quests = job_quests(profile, time.time(), account.account_id)
        monster = quests[0].locations[0]
        reply, _ = progress.report(battle, {str(monster): 2})
        self.assertEqual(reply['jobs'][0], 2)
        battle = progress.begin(account.account_id, 10900001)   # Downtown: no jobs.
        self.assertEqual(progress.state(battle)['jobs'], [])
