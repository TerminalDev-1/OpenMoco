"""13.5.1 tutorial references evidenced by the supplied client tables.

574 updates client-home +0x118: pairs of raw tutorial/step data references.
Native 0x686754 and 0x7969a0 store a null step when a tutorial finishes.

Intro_3 is the main-quest step for the Portal tutorial's GoToPortal step
(tutorial_steps.csv MainQuestStep). Its quests (main_quest_step_quests.csv)
are Intro_3_1, defeat 50 monsters in TutorialAreaBasic, and Intro_3_2, rescue
3 civilians there. The server counts these from client-reported battle
outcomes (battle_bridge.py) and sends the progress in the own-home profile.
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
