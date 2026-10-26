import struct
import unittest

from home import DAILY_GOAL_EVENT_TYPE, DailyGoalEvent, Quest, Writer, _daily_goal_event, own_home
from progress import (DAILY_GOAL_EVENT, DAILY_GOAL_TARGET, DAILY_GOAL_XP, DAY_SECONDS, STREAK_MULTIPLIER,
                      STREAK_THRESHOLD, claim_daily_goal, daily_goal_events, daily_goal_marker, daily_goal_quest_id,
                      daily_goal_quests, daily_jobs, refresh_seconds, streak_record)
from stream import Reader

NOW = 1792000000  # A fixed UTC time, mid-day.


def cool_zone_profile():
    return {'tutorials': {'15600009': 0}, 'battle_progress': {'xp': 1000}}


def finish_jobs(profile, now, count=DAILY_GOAL_TARGET):
    jobs = daily_jobs(profile, now, 7)
    for job in jobs[:count]:
        job['done'] = True
    profile['jobs'] = {'day': int(now) // DAY_SECONDS, 'list': jobs}


class DailyGoalRuleTests(unittest.TestCase):
    def test_goal_follows_todays_finished_jobs(self):
        profile = cool_zone_profile()
        (goal,) = daily_goal_quests(profile, NOW, 7)
        # +88 must equal avatar +0 (daily_goal_marker), or the client drops the goal.
        self.assertEqual((goal.quest_type, goal.job, goal.progress, goal.target, goal.main),
                         (36, NOW // DAY_SECONDS, 0, DAILY_GOAL_TARGET, False))
        self.assertEqual(daily_goal_marker(profile, NOW), goal.job)
        self.assertEqual(daily_goal_marker({'tutorials': {}}, NOW), 0)
        self.assertEqual(goal.rewards, ((2, DAILY_GOAL_XP),))
        finish_jobs(profile, NOW, 2)
        self.assertEqual(daily_goal_quests(profile, NOW, 7)[0].progress, 2)

    def test_claim_needs_every_job_and_pays_once(self):
        profile = cool_zone_profile()
        finish_jobs(profile, NOW, DAILY_GOAL_TARGET - 1)
        self.assertEqual(claim_daily_goal(profile, NOW, 7), 0)
        finish_jobs(profile, NOW)
        self.assertEqual(claim_daily_goal(profile, NOW, 7), DAILY_GOAL_XP)
        self.assertEqual(profile['battle_progress']['xp'], 1000 + DAILY_GOAL_XP)
        self.assertEqual(claim_daily_goal(profile, NOW, 7), 0)  # Once a day.
        self.assertEqual(daily_goal_quests(profile, NOW, 7), ())  # Claimed: left out until tomorrow.
        self.assertIsNone(daily_goal_quest_id(profile, NOW, 7))
        self.assertEqual(len(daily_goal_quests(profile, NOW + DAY_SECONDS, 7)), 1)

    def test_streak_grows_daily_doubles_and_ends_after_a_missed_day(self):
        profile = cool_zone_profile()
        rewards = []
        for day in range(STREAK_THRESHOLD + 1):
            now = NOW + day * DAY_SECONDS
            finish_jobs(profile, now)
            rewards.append(claim_daily_goal(profile, now, 7))
        # Doubled once the streak has reached the threshold before the claim.
        self.assertEqual(rewards, [DAILY_GOAL_XP] * STREAK_THRESHOLD + [DAILY_GOAL_XP * STREAK_MULTIPLIER])
        last = NOW + STREAK_THRESHOLD * DAY_SECONDS
        start, end, total, event, claimed, unused = streak_record(profile, last)
        self.assertEqual((end - start, total, event), (STREAK_THRESHOLD + 1, STREAK_THRESHOLD + 1, DAILY_GOAL_EVENT))
        self.assertEqual(streak_record(profile, last + DAY_SECONDS)[1] - streak_record(profile, last + DAY_SECONDS)[0],
                         STREAK_THRESHOLD + 1)  # Still alive the next day, before its claim.
        missed = last + 2 * DAY_SECONDS
        self.assertEqual(streak_record(profile, missed)[:2], (0, 0))  # A missed day ends it.
        self.assertEqual(daily_goal_quests(profile, missed, 7)[0].rewards, ((2, DAILY_GOAL_XP),))
        finish_jobs(profile, missed)
        self.assertEqual(claim_daily_goal(profile, missed, 7), DAILY_GOAL_XP)
        self.assertEqual(profile['daily_goal']['streak'], 1)

    def test_nothing_before_the_cool_zone(self):
        profile = {'tutorials': {'15600001': 14200006}}
        self.assertEqual(daily_goal_quests(profile, NOW), ())
        self.assertEqual(daily_goal_events(profile), ())
        self.assertEqual(streak_record(profile, NOW), (0,) * 6)
        self.assertEqual(claim_daily_goal(profile, NOW), 0)

    def test_goal_id_follows_the_jobs(self):
        self.assertEqual(daily_goal_quest_id(cool_zone_profile(), NOW, 7), 3)

    def test_unstamped_elapsed_matches_the_client_clock_formula(self):
        from progress import unstamped_elapsed
        # At 12:51:56 on 2026-10-26 the observed countdown error was about 6 h 31 m.
        self.assertEqual(unstamped_elapsed(1793019116096 * 10**6) // 60, 6 * 60 + 31)
        self.assertEqual(unstamped_elapsed((1 << 48) + 5 * 10**9), 5)  # 48-bit wrap.

    def test_refresh_counts_down_to_the_next_utc_day(self):
        self.assertEqual(refresh_seconds(DAY_SECONDS * 5), DAY_SECONDS)
        self.assertEqual(refresh_seconds(DAY_SECONDS * 5 + 60), DAY_SECONDS - 60)


class DailyGoalEncodingTests(unittest.TestCase):
    def test_event_follows_native_decoder_0x76c588(self):
        writer = Writer()
        _daily_goal_event(writer, DailyGoalEvent(1, 0, 0x7fffffff, 3, 300, 7, 2))
        reader = Reader(writer.bytes())
        self.assertTrue(reader.boolean())
        self.assertEqual(reader.compact(), DAILY_GOAL_EVENT_TYPE)
        fields = []
        for _ in range(11):
            self.assertTrue(reader.boolean())
            fields.append(reader.compact())
        self.assertEqual(fields, [1, 0, 0, 0, 0x7fffffff, 3, 300, 7, 2, 0, 0])
        self.assertEqual([reader.compact() for _ in range(3)], [0, 0, 0])
        self.assertEqual(reader.remaining, 0)

    def test_events_are_avatar_88_and_keep_the_rest(self):
        event = DailyGoalEvent(1, 0, 0x7fffffff, 3, 300, 7, 2)
        plain, with_event = own_home(1), own_home(1, events=(event,))
        writer = Writer()
        _daily_goal_event(writer, event)
        self.assertEqual(len(with_event) - len(plain), len(writer.bytes()))
        # The avatar tail: +60, +68, +98, then the +a8/+b8 counts and suffix.
        self.assertEqual(with_event[-8:], plain[-8:])

    def test_reward_entry_and_header_fields(self):
        goal = Quest(0, 2, 3, quest_type=36, main=False, job=1, rewards=((2, 300),))
        plain = own_home(1, jobs=(Quest(0, 2, 3, quest_type=36, main=False, job=1),))
        body = own_home(1, jobs=(goal,))
        self.assertEqual(len(body) - len(plain), 2 + 2 * 1 - 1 + 32 + 7)  # type, amount(2), refs, ints
        self.assertIn(bytes([2]) + bytes([0x80 | (300 & 63), 300 >> 6]) + bytes(32), body)

    def test_goal_marker_is_the_first_avatar_integer(self):
        plain, marked = own_home(1), own_home(1, goal_marker=20752)
        marker = Writer().compact(20752).bytes()
        # An empty avatar plus the own-home suffix is 20 one-byte fields; the marker is the first.
        self.assertEqual(marked, plain[:-20] + marker + plain[-19:])

    def test_refresh_and_streak_fill_client_home(self):
        body = own_home(1, refresh_seconds=3600, streak=(20000, 20003, 5, 1, 0, 0))
        reader = Reader(body)
        reader.raw(16)
        reader.bit_boolean()
        reader.string()
        reader.bit_boolean()
        [reader.integer() for _ in range(3)]
        self.assertEqual(struct.unpack('>Q', reader.raw(8))[0], 1)
        self.assertEqual([reader.compact(), reader.compact(), reader.compact()], [0, 3600, 0])
        streak = Writer()
        for value in (20000, 20003, 5, 1, 0, 0):
            streak.compact(value)
        self.assertIn(streak.bytes(), body)
        self.assertEqual(len(body) - len(own_home(1)), (2 - 1) + len(streak.bytes()) - 6)
        with self.assertRaises(ValueError):
            own_home(1, streak=(1, 2))


class ClaimCommandTests(unittest.TestCase):
    def test_587_and_603_have_only_the_base_fields(self):
        from commands import decode_client_turn
        writer = Writer().compact(5).raw(bytes(8)).compact(2)
        for command_type in (587, 603):
            writer.integer(command_type)
            for _ in range(3):
                writer.boolean(False)
        turn = decode_client_turn(writer.bytes())
        self.assertEqual([c.command_type for c in turn.commands], [587, 603])

    def test_claim_through_the_account_store(self):
        import tempfile
        from pathlib import Path
        from accounts import AccountStore
        with tempfile.TemporaryDirectory() as directory:
            store = AccountStore(Path(directory) / 'accounts.sqlite3')
            account = store.authenticate(0, None)  # A new local guest.
            with store.edit_profile(account.account_id) as profile:
                profile.update(cool_zone_profile())
                finish_jobs(profile, NOW)
            goal = daily_goal_quest_id(store.authenticate(account.account_id, account.token).profile,
                                       NOW, account.account_id)
            self.assertEqual(store.claim_quests(account.account_id, (goal + 1,), NOW), 0)
            self.assertEqual(store.claim_quests(account.account_id, (goal,), NOW), DAILY_GOAL_XP)
            saved = store.authenticate(account.account_id, account.token).profile
            self.assertEqual(saved['daily_goal']['streak'], 1)
            self.assertEqual(store.claim_quests(account.account_id, (goal,), NOW), 0)


if __name__ == '__main__':
    unittest.main()
