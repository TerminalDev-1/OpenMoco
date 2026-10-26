"""13.5.1 tutorial references evidenced by the supplied client tables.

574 updates client-home +0x118: pairs of raw tutorial/step data references.
Native 0x686754 and 0x7969a0 store a null step when a tutorial finishes.

Intro_3 is the main-quest step for the Portal tutorial's GoToPortal step
(tutorial_steps.csv MainQuestStep). Its quests (main_quest_step_quests.csv)
are Intro_3_1, defeat 50 monsters in TutorialAreaBasic, and Intro_3_2, rescue
3 civilians there. The server counts these from client-reported battle
outcomes (battle_progress.py) and sends the progress in the own-home profile.
"""
TUTORIAL_STEPS = {
    15600000: range(14200000, 14200004),
    15600001: range(14200004, 14200009),
    15600002: range(14200009, 14200014),
    15600003: range(14200014, 14200018),
    15600004: range(14200018, 14200022),
    15600005: range(14200022, 14200026),
    15600006: range(14200026, 14200027),
    15600007: range(14200027, 14200028),
    15600008: range(14200028, 14200029),
    15600009: range(14200029, 14200033),
    15600010: range(14200033, 14200034),
}

PORTAL_TUTORIAL = 15600001
GO_TO_PORTAL = 14200006      # Luna: "now go through it!"; MainQuestStep Intro_3.
CLAIM_QUESTS = 14200007      # Action ClaimMainQuests, back home.

INTRO_3 = 15400002           # main_quest_steps instance 2.
INTRO_3_KILLS = 15500000     # Intro_3_1: QuestType 1, target 50.
INTRO_3_RESCUES = 15500001   # Intro_3_2: QuestType 1, target 3, Civilian events.
TUTORIAL_NAME_10 = 15400003  # Next main-quest step, unlocked when Intro_3 is claimed.
MAIN_QUEST_STEPS = range(15400000, 15400100)  # main_quest_steps.csv data references.
MAIN_QUEST_SEEN = 575        # Client command carrying a step it has shown.
MAIN_QUEST_DONE = 576        # Client command carrying a step it has completed.
KILL_TARGET = 50
RESCUE_TARGET = 3


# XP needed for each level, sent to the client bridge, which installs it in the
# client's empty native level table (read by 0x788de8). The 13.5.1 data has
# no level table; the official server supplies it. PROVISIONAL values: level 1
# uses globals.csv XP_LEVEL_1_OFFSET (200) and each later level adds 200, up to
# MAX_LEVEL (29). Replace them when the real curve is known. Every entry must be
# positive: a zero entry makes the native level loop spin forever.
XP_LEVEL_1_OFFSET = 200
MAX_LEVEL = 29
XP_LEVELS = tuple(XP_LEVEL_1_OFFSET * level for level in range(1, MAX_LEVEL + 1))


def level_for_xp(xp, levels=XP_LEVELS):
    """Displayed level for total XP, as native level loop 0x788de8 counts it
    (the last entry repeats past the end of the table), plus one."""
    level = 0
    while xp >= levels[min(level, len(levels) - 1)]:
        xp -= levels[min(level, len(levels) - 1)]
        level += 1
    return level + 1


def validate_tutorial(tutorial, step):
    if type(tutorial) is not int or tutorial not in TUTORIAL_STEPS:
        raise ValueError('Unsupported tutorial reference')
    if type(step) is not int or step != 0 and step not in TUTORIAL_STEPS[tutorial]:
        raise ValueError('Step does not belong to tutorial')


def tutorial_entries(progress):
    entries = []
    for key, step in progress.items():
        tutorial = int(key)
        validate_tutorial(tutorial, step)
        entries.append((tutorial, step))
    return sorted(entries)


def intro_quest_active(profile):
    """True while the player is on GoToPortal and Intro_3 is unfinished."""
    return profile.get('tutorials', {}).get(str(PORTAL_TUTORIAL)) == GO_TO_PORTAL


def intro_progress(profile):
    """(kills, rescues) toward Intro_3, capped at the quest targets.

    TutorialAreaBasic is the only battle this server offers, and the player
    reaches it through GoToPortal, so every saved battle outcome was earned
    during Intro_3.
    """
    battle = profile.get('battle_progress', {})
    return (min(KILL_TARGET, battle.get('kills', 0)),
            min(RESCUE_TARGET, battle.get('rescues', 0)))


def intro_quest_complete(profile):
    return intro_progress(profile) == (KILL_TARGET, RESCUE_TARGET)


def complete_intro_quest(profile):
    """Advance GoToPortal -> ClaimQuests once Intro_3 is earned. Returns True if advanced."""
    if not intro_quest_active(profile) or not intro_quest_complete(profile):
        return False
    profile['tutorials'][str(PORTAL_TUTORIAL)] = CLAIM_QUESTS
    return True


def record_main_quest(profile, command_type, step):
    if type(step) is not int or step not in MAIN_QUEST_STEPS:
        raise ValueError('Unsupported main-quest step reference')
    key = 'seen' if command_type == MAIN_QUEST_SEEN else 'done'
    steps = profile.setdefault('main_quests', {}).setdefault(key, [])
    if step not in steps:
        steps.append(step)


def intro_main_steps(profile):
    """Native MainQuestManager entries for the own-home profile.

    During GoToPortal, Intro_3 is new and carries live quest progress. From
    ClaimQuests on, Intro_3 is claimed and Tutorial_Name_10 is unlocked, as
    the client's AutoClaim would do. Steps the client later reported with
    575/576 are kept, so a reconnect restores the same list.
    """
    step = profile.get('tutorials', {}).get(str(PORTAL_TUTORIAL))
    if step is None or step != 0 and step < GO_TO_PORTAL:
        return ()  # Before GoToPortal (step 0 means the tutorial is finished).
    from home import MainQuestStep, Quest
    if step == GO_TO_PORTAL:
        kills, rescues = intro_progress(profile)
        return (MainQuestStep(INTRO_3, (
            Quest(INTRO_3_KILLS, kills, KILL_TARGET),
            Quest(INTRO_3_RESCUES, rescues, RESCUE_TARGET, 'Civilian'),
        )),)
    reported = profile.get('main_quests', {})
    seen, done = set(reported.get('seen', ())), set(reported.get('done', ()))
    claimed = {INTRO_3, TUTORIAL_NAME_10} | done
    later = sorted((seen | done) - {INTRO_3, TUTORIAL_NAME_10} - set(range(15400000, INTRO_3)))
    return tuple(MainQuestStep(ref, claimed=ref in claimed) for ref in [INTRO_3, TUTORIAL_NAME_10, *later])


# Seasons. The client shows "Season ends in" from the season track's
# remaining seconds (home._level_track). The official schedule is unknown,
# so this server runs rolling 28-day seasons from a fixed UTC start.
SEASON_START = 1767571200          # 2026-01-05T00:00:00Z, a Monday.
SEASON_SECONDS = 28 * 24 * 60 * 60


def season_seconds_left(now):
    """Whole seconds until the current local season ends (always >= 1)."""
    elapsed = (int(now) - SEASON_START) % SEASON_SECONDS
    return SEASON_SECONDS - elapsed


TO_HQ_TUTORIAL = 15600009  # tutorials.csv ToHQ (instance 9)


def cool_zone_unlocked(profile):
    """True once the ToHQ tutorial, which leads to the COOL zone, is reached."""
    return str(TO_HQ_TUTORIAL) in profile.get('tutorials', {})


# Daily jobs (the portal's map missions). A job is a native Quest with no
# data reference: +4 type 1 (defeat), +20 the monster references (the card
# reads "Hunt <first monster's TID>_M"), +60 the map card slot it belongs to.
# The pool and targets are this server's choice; the official generator and
# rewards are unknown. JOB_XP_REWARD is PROVISIONAL.
SHRINE_CANYON_SLOT = 1           # home.PORTAL_WORLDS slot ID of Shrine Canyon
JOB_POOL = (
    ((10800022, 10800027), 30),  # Hunt Drogs (weak melee and ranged)
    ((10800038,), 8),            # Hunt Jumpers
    ((10800269,), 8),            # Hunt Slashers
    ((10800449,), 1),            # Hunt Jugglers (zone boss)
)
JOBS_PER_DAY = 3
JOB_XP_REWARD = 100
DAY_SECONDS = 24 * 60 * 60


def _job_day(now):
    return int(now) // DAY_SECONDS


def daily_jobs(profile, now, account_id=0):
    """Today's jobs: saved progress for today, or a fresh deterministic pick."""
    import random
    day = _job_day(now)
    saved = profile.get('jobs')
    if saved and saved.get('day') == day:
        return saved['list']
    picks = random.Random(day * 1000003 + account_id).sample(range(len(JOB_POOL)), JOBS_PER_DAY)
    return [{'pool': pick, 'progress': 0, 'done': False} for pick in sorted(picks)]


def credit_jobs(profile, gains, now, account_id=0):
    """Advance today's jobs with credited kills {character ID: count}.

    Returns the reward XP of the jobs completed by these kills. A completed
    job is marked done (claimed) and its reward is granted once.
    """
    if not cool_zone_unlocked(profile):
        return 0
    jobs = daily_jobs(profile, now, account_id)
    reward = 0
    for job in jobs:
        monsters, target = JOB_POOL[job['pool']]
        if job['done']:
            continue
        job['progress'] = min(target, job['progress'] + sum(gains.get(m, 0) for m in monsters))
        if job['progress'] >= target:
            job['done'] = True
            reward += JOB_XP_REWARD
    profile['jobs'] = {'day': _job_day(now), 'list': jobs}
    return reward


def job_quests(profile, now, account_id=0):
    """Native Quest objects for today's jobs (home._quest).

    Jobs start once the tutorial has led the player to the COOL zone, so they
    never mix with the tutorial's own portal quests.
    """
    from home import Quest
    if not cool_zone_unlocked(profile):
        return ()
    quests = []
    for job in daily_jobs(profile, now, account_id):
        monsters, target = JOB_POOL[job['pool']]
        quests.append(Quest(0, job['progress'], target, locations=monsters, main=False,
                            claimed=job['done'], map_slot=SHRINE_CANYON_SLOT))
    return tuple(quests)


def refresh_seconds(now):
    """Seconds until the next UTC day, when jobs and the daily goal renew
    (client-home +c, "Refreshes in")."""
    return DAY_SECONDS - int(now) % DAY_SECONDS


CLOCK_MASK = (1 << 48) - 1  # 0xa832e0 keeps 48 bits of a nanosecond difference.


def unstamped_elapsed(now_ns):
    """Seconds the client subtracts from the refresh countdown when the home's
    quest collection has no clock stamp.

    The countdown (0x4bfd2c) is client-home +c minus ((now - stamp) & 2^48-1)
    ns, converted to seconds (x 1e-6, then x 0.001). When own-home is followed
    by a scene start that clones the home (return from a battle; 0x5c4d9c ->
    0x756ba8), the clone's stamp is 0 (0x78eb4c), so the client subtracts the
    real-time clock modulo 2^48 ns (about 78 hours). Adding this value to +c
    cancels it. The client clock wraps every 2^48 ns (about 78 hours); after
    that the correction is 78 hours too large, so the server reloads the home
    at the wrap (seconds_to_clock_wrap, server.GameSession)."""
    return (now_ns & CLOCK_MASK) // 1_000_000_000


CLOCK_WRAP_MARGIN = 5.0  # Seconds after the wrap, covering small client/server clock differences.


def seconds_to_clock_wrap(now_ns):
    """Seconds until the client's 2^48 ns clock window wraps, plus a margin.
    The tablet's and the PC's clocks were measured within 0.3 s of each other."""
    return (CLOCK_MASK + 1 - (now_ns & CLOCK_MASK)) / 1e9 + CLOCK_WRAP_MARGIN


# Daily goal ("DAILY GOAL") and the SERIOUS HUNTER STREAK. Native evidence:
# home.DailyGoalEvent (settings), a type-36 quest with +88 != 0 (0x78fc24)
# whose progress the client also advances by one per finished job (0x486440),
# CLAIM! sends command 569 with that quest's ID (0x4c0188), and the streak
# record client-home +130 (home._client_home). The goal is this server's
# choice: finish today's three jobs. DAILY_GOAL_XP is PROVISIONAL; the streak
# threshold (7 days) and double rewards come from the game's own texts
# (TID_DAILY_GOAL_SERIOUS_INFO). A missed day ends the streak (loss type 0).
DAILY_GOAL_EVENT = 1             # Local chronosEventId of the goal settings event.
DAILY_GOAL_QUEST_TYPE = 36
DAILY_GOAL_TARGET = JOBS_PER_DAY
DAILY_GOAL_XP = 300
STREAK_THRESHOLD = 7
STREAK_MULTIPLIER = 2
XP_REWARD_TYPE = 2               # Reward entry type read as XP (0x78e528).
EVENT_END = 0x7fffffff           # The goal settings never expire.


def _goal_saved(profile, now):
    """(today, current streak, goals finished, claimed today).

    The saved streak counts only while its last claim was today or yesterday."""
    saved = profile.get('daily_goal', {})
    day, last = _job_day(now), saved.get('last_day')
    streak = saved.get('streak', 0) if last is not None and last >= day - 1 else 0
    return day, streak, saved.get('total', 0), last == day


def goal_xp(streak):
    """XP for claiming the goal: doubled once the streak reaches the threshold."""
    return DAILY_GOAL_XP * (STREAK_MULTIPLIER if streak >= STREAK_THRESHOLD else 1)


def jobs_done_today(profile, now, account_id=0):
    return sum(1 for job in daily_jobs(profile, now, account_id) if job['done'])


def daily_goal_quests(profile, now, account_id=0):
    """Today's goal quest, or none before the COOL zone or once claimed.

    A claimed goal is left out, as after the client's own claim, so the
    popup shows its claimed state until the next day."""
    from home import Quest
    if not cool_zone_unlocked(profile):
        return ()
    _, streak, _, claimed = _goal_saved(profile, now)
    if claimed:
        return ()
    return (Quest(0, jobs_done_today(profile, now, account_id), DAILY_GOAL_TARGET,
                  quest_type=DAILY_GOAL_QUEST_TYPE, main=False, job=daily_goal_marker(profile, now),
                  rewards=((XP_REWARD_TYPE, goal_xp(streak)),)),)


def daily_goal_marker(profile, now):
    """Avatar +0 and the goal quest's +88: the client keeps the goal only
    while both match (0x78e6b0). Today's UTC day number, so a goal from an
    earlier day no longer matches; 0 (no goal) before the COOL zone."""
    return _job_day(now) if cool_zone_unlocked(profile) else 0


def daily_goal_events(profile):
    from home import DailyGoalEvent
    if not cool_zone_unlocked(profile):
        return ()
    return (DailyGoalEvent(DAILY_GOAL_EVENT, 0, EVENT_END, DAILY_GOAL_TARGET, DAILY_GOAL_XP,
                           STREAK_THRESHOLD, STREAK_MULTIPLIER),)


def streak_record(profile, now):
    """Client-home +130 integers in stream order (+0, +8, +c, +10, +14, +4).

    The client shows +8 - +0 as the streak, so the record spans the streak's
    days: from its first day to the day after its last claim."""
    if not cool_zone_unlocked(profile):
        return (0,) * 6
    _, streak, total, _ = _goal_saved(profile, now)
    if streak:
        end = profile['daily_goal']['last_day'] + 1
        return (end - streak, end, total, DAILY_GOAL_EVENT, 0, 0)
    return (0, 0, total, DAILY_GOAL_EVENT, 0, 0)


def claim_daily_goal(profile, now, account_id=0):
    """Claim today's goal if its jobs are finished. Returns the XP granted (0 if not claimable)."""
    if not cool_zone_unlocked(profile):
        return 0
    day, streak, total, claimed = _goal_saved(profile, now)
    if claimed or jobs_done_today(profile, now, account_id) < DAILY_GOAL_TARGET:
        return 0
    reward = goal_xp(streak)
    profile['daily_goal'] = {'last_day': day, 'streak': streak + 1, 'total': total + 1}
    progress = profile.setdefault('battle_progress', {})
    progress['xp'] = progress.get('xp', 0) + reward
    return reward


def daily_goal_quest_id(profile, now, account_id=0):
    """The goal quest's ID in the own-home quest collection (its position
    after the main-quest quests and today's jobs), or None without a goal."""
    if not daily_goal_quests(profile, now, account_id):
        return None
    main = sum(len(step.quests) for step in intro_main_steps(profile))
    return main + len(job_quests(profile, now, account_id))


# Boosted chaos energy (the portal orb). globals.csv: MONSTER_XP_DAILY_CAP
# 60000 boosted XP a day; the multiplier is 4x while at least 50000 is left,
# 3x from 37500, 2x from 22500, then 1x. The server applies it to kill XP.
MONSTER_XP_DAILY_CAP = 60000
BOOST_TIERS = ((50000, 4), (37500, 3), (22500, 2))


def _boost_used(profile, now):
    saved = profile.get('boost', {})
    return saved.get('used', 0) if saved.get('day') == _job_day(now) else 0


def boost_multiplier(left):
    for threshold, multiplier in BOOST_TIERS:
        if left >= threshold:
            return multiplier
    return 1


def daily_boosts(profile, now):
    """Avatar +a8 boost for today, or none once today's boosted XP is used up."""
    from home import Boost
    if not cool_zone_unlocked(profile):
        return ()
    left = MONSTER_XP_DAILY_CAP - _boost_used(profile, now)
    if left <= 0:
        return ()
    day = _job_day(now)
    return (Boost(day, boost_multiplier(left), left, day * DAY_SECONDS, (day + 1) * DAY_SECONDS),)


def boost_kill_xp(profile, kill_xp, now):
    """Multiply kill XP by today's boost and record the boosted XP used."""
    if not kill_xp or not cool_zone_unlocked(profile):
        return kill_xp
    used = _boost_used(profile, now)
    left = MONSTER_XP_DAILY_CAP - used
    if left <= 0:
        return kill_xp
    boosted = min(left, kill_xp * boost_multiplier(left))
    profile['boost'] = {'day': _job_day(now), 'used': used + boosted}
    return max(kill_xp, boosted)

