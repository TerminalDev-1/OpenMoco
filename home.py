"""13.5.1 minimum own-home profile, based on native encoder/decoder evidence.

24548/v0: outer decoder 0x786fdc, own-home 0x755e34,
client-home 0x77e0b8, avatar 0x77c010. Unknown fields retain native zero defaults.
This initializes the home UI/onboarding; it does not implement gameplay.

Optional tutorial main-quest state (Intro_3) follows the native decoders:
quest collection home+0xa0 (0x78ecf8), Quest 0x78da48 and MainQuestManager
home+0xf0 (0x784638, entries 0x7850fc).
"""
from dataclasses import dataclass
import struct
from stream import Writer

OWN_HOME_TYPE = 24548
SMART_BOW = 6700000  # Loaded battle-kit record; its weapon link is ArcherWeapon.
# Weapons the account owns (client-home +0x78). Only the starter bow so far.
OWNED_WEAPONS = (SMART_BOW,)
XP_POINT = 300020    # resources.csv XpPoint (Meta), instance 20.
# Local ID of the player-level track (avatar +0x40) and its client-home +0xe8
# progress record. The official ID is unknown; the client only matches the two.
PLAYER_LEVEL_TRACK = 1
# Battle scenes the portal can list as world cards (battle_scenes.csv).
# TutorialArea (10900002) is refused by the portal's start check 0x682df0
# (its scene flag +0x170 blocks it while the portal has no tabs).
SHRINE_CANYON = 10900006     # W01_OA01, scene/w01_oa01.json
PORTAL_WORLDS = (SHRINE_CANYON,)
# Portal card titles (map slot +38 text). The game's own name for W01_OA01 is
# TID_AREA1 "SHRINE VILLAGE"; the user asked for "Shrine Canyon".
WORLD_NAMES = {SHRINE_CANYON: 'SHRINE CANYON'}
# Free default faces (slot 3) and hairstyles (slot 2): the rAssetCosmetic
# records with pool 0 and enabledForPlayers. The character editor (signup
# screen, list builder 0x570be4) lists only owned vanity items of the chosen
# slot (0x797cf0 over client-home +0xe0); with none it shows
# TID_BUILDS_POPUP_NO_SKIN_CANDIDATES and an empty list.
STARTER_FACES = (2900434, 2900435, 2900436, 2900437, 2900438, 2900439, 2900440,
                 2900792, 2900793, 2900794, 2900795, 2900796, 2900797, 2900798,
                 2901569, 2901570, 2901571, 2901572, 2901573, 2901574, 2901575,
                 2901576, 2901577, 2901578, 2901579, 2901580)
STARTER_HAIRSTYLES = (2900441, 2900442, 2900443, 2900444, 2900445, 2900446, 2900447,
                      2900448, 2900449, 2900869, 2900870, 2900871, 2900872, 2900873,
                      2900874, 2900875, 2900876, 2900877, 2900878, 2900879, 2900880,
                      2900881, 2900882, 2900883, 2900884, 2900885, 2900886, 2900887,
                      2900888, 2900889, 2901620, 2901621)
# Free default skin, eye and hair colours: slot -3 dyes with pool 0. A build
# keeps equipped dyes as their graphicAsset UUID strings (see _client_home).
STARTER_DYES = {
    2900415: ('skin', '4b9f0096-c119-fd32-813d-5e4ac4a503ec'),
    2900416: ('skin', '4b9f0096-6eff-3136-cea4-9531df6bf6ee'),
    2900417: ('skin', '4b9f0096-0303-aae8-c3f1-7346443d6290'),
    2900418: ('skin', '4b9f0096-7606-b721-36de-d369d136fbf7'),
    2900419: ('skin', '4b9f0096-3fe2-6c29-ff90-f33fc826c375'),
    2900420: ('eye', '4b9f0096-1723-2356-7703-a48d2fc83608'),
    2900421: ('eye', '4b9f0096-4009-fbd0-00fa-4229ccaf34ec'),
    2900422: ('eye', '4b9f0096-4829-33f5-8894-030e84aca5b8'),
    2900423: ('eye', '4b9f0096-3754-3c0a-77e6-2b31b46fe7e1'),
    2900424: ('eye', '4b9f0096-40de-a598-e05e-75c897fece02'),
    2900425: ('hair', '4b9f0096-2420-a384-e491-60a9a0b51e29'),
    2900426: ('hair', '4b9f0096-91fe-e57f-51e1-f56baa110186'),
    2900427: ('hair', '4b9f0096-7319-e582-d349-6fe9c9807d29'),
    2900428: ('hair', '4b9f0096-f8d2-34b7-9876-56e1bc1853f9'),
    2900429: ('hair', '4b9f0096-8d88-a927-0dab-044fa85b21e3'),
    2900430: ('hair', '4b9f0096-33bc-7777-d36f-cea216caf472'),
    2900431: ('hair', '4b9f0096-ec46-6a1f-4c56-066175cabe2c'),
    2900432: ('hair', '4b9f0096-05ea-b1ff-8501-398bd560ba29'),
    2900433: ('hair', '4b9f0096-931a-bd76-f31a-74b6756bcfc9'),
}
STARTER_VANITY = STARTER_FACES + STARTER_HAIRSTYLES + tuple(STARTER_DYES)
# Shown until the player chooses: the head the apartment scene already
# renders, and the dyes marked canBePreset (mid skin, brown eyes, brunette).
DEFAULT_LOOK = {'3': 2900435, 'dye_skin': 2900417, 'dye_eye': 2900422, 'dye_hair': 2900426}


def cosmetic_slot(cosmetic):
    """Saved look key of an owned starter item: its native slot (data +0x30),
    or dye_<kind> for slot -3 dyes, where one dye of each kind is equipped."""
    if cosmetic in STARTER_FACES:
        return '3'
    if cosmetic in STARTER_HAIRSTYLES:
        return '2'
    if cosmetic in STARTER_DYES:
        return 'dye_' + STARTER_DYES[cosmetic][0]
    raise ValueError('Cosmetic is not an owned starter item')


def equipped_look(saved):
    """Current-build cosmetics from a saved {look key: cosmetic} profile entry."""
    look = dict(DEFAULT_LOOK)
    for key, cosmetic in (saved or {}).items():
        if cosmetic in STARTER_VANITY and cosmetic_slot(cosmetic) == key:
            look[key] = cosmetic
    return tuple(look[key] for key in sorted(look, reverse=True))


@dataclass(frozen=True)
class Quest:
    """One active quest, e.g. Intro_3_1 'defeat 50 monsters'."""
    reference: int          # main_quest_step_quests data reference (155xxxxx), or 0
    progress: int
    target: int
    event: str = None       # QuestEventTypeCond, e.g. 'Civilian'
    quest_type: int = 1     # +4, QuestType (1 = defeat monsters)
    locations: tuple = ()   # +20 raw data references, e.g. battle scenes
    main: bool = True       # +41, a main-quest quest (False for map missions/jobs)
    claimed: bool = False   # +40; 0x78e108 counts a quest complete when progress >= target and not claimed
    job: int = 0            # +88, nonzero for the type-36 daily goal (0x78fc24)
    map_slot: int = 0       # +60, the portal map card (avatar +48 slot ID) a daily job belongs to


@dataclass(frozen=True)
class MainQuestStep:
    """A main-quest step (e.g. Intro_3) and its active quests."""
    reference: int          # main_quest_steps data reference (154xxxxx)
    quests: tuple = ()
    claimed: bool = False


def _zeros(writer, count):
    for _ in range(count):
        writer.compact(0)


def _ref(writer, reference):
    writer.raw(struct.pack('>Q', reference))


def _quest(writer, quest_id, quest):
    """Native Quest 0x78da48; fields as created from Intro_3_1/2 by 0x78e130."""
    writer.compact(quest_id)              # +0 unique ID from collection +0 (0x78ff08)
    writer.compact(quest.quest_type)      # +4 quest type
    writer.compact(min(quest.progress, quest.target))  # +8 progress
    writer.compact(quest.target)          # +c target
    writer.compact(0)                     # +18 objective list
    writer.compact(len(quest.locations))  # +28 count, +20 raw references (0x83c13c)
    for location in quest.locations:
        _ref(writer, location)
    for _ in range(4):                    # +34..+37
        writer.bit_boolean(False)
    writer.string(quest.event)            # +38 event-type filter
    writer.bit_boolean(quest.claimed)     # +40 claimed
    writer.bit_boolean(quest.main)        # +41 main-quest quest
    writer.compact(0)                     # +44
    _ref(writer, quest.reference)         # +48 quest data
    _zeros(writer, 4)                     # +50 (bounty when > 0), +54, +58, +5c (0 = daily job)
    writer.compact(quest.map_slot)        # +60 map card slot: jobs filter 0x78eeb4 categories 2..4, 25
    writer.compact(-1)                    # +30 (constructor default -1)
    writer.compact(0)                     # +64
    writer.bit_boolean(False)             # optional +68 object absent
    writer.bit_boolean(False)             # optional +80 object absent
    writer.compact(quest.job)             # +88 job marker
    writer.compact(0)                     # +8c


def _track_record(writer, track, xp):
    """Client-home +e8 entry 0x788054: track progress, keyed by track ID.

    +0 track ID, +4 XP (native add-XP 0x7565b8 adds to it), +8, bit +c, +10
    (a linked track ID; 0 = none), +14, bit +18, +1c, then six empty vectors.
    """
    writer.compact(track).compact(xp).compact(0)
    writer.bit_boolean(False)
    writer.compact(0).compact(0)
    writer.bit_boolean(False)
    _zeros(writer, 1 + 6)


def quest_collection(writer, quests):
    """Quest collection 0x78ecf8 (client-home +a0, battle configuration +20):
    header (next quest ID, then three unknown integers), then the quests."""
    writer.compact(len(quests))
    _zeros(writer, 3)
    writer.compact(len(quests))
    for quest_id, quest in enumerate(quests):
        _quest(writer, quest_id, quest)


def _quest_state(writer, main_steps, xp=0, jobs=()):
    """Home +a0 quest collection, +e8 track progress and +f0 main quests."""
    quest_collection(writer, [quest for step in main_steps for quest in step.quests] + list(jobs))
    # +e8 track progress (0x78723c): the player-level record holds saved XP.
    writer.compact(1 if xp else 0)
    if xp:
        _track_record(writer, PLAYER_LEVEL_TRACK, xp)
    writer.compact(len(main_steps))  # +f0 MainQuestManager entries.
    for step in main_steps:
        _ref(writer, step.reference)
        writer.compact(0)
        writer.bit_boolean(not step.claimed)  # new
        writer.bit_boolean(step.claimed)      # claimed


def _vanity_items(writer, items):
    """Client-home +e0 vanity items (0x79716c; entry 0x796ba8).

    Each entry is a raw cosmetic data reference (stream +0x120) and a count of
    8-byte sub-entries (0x797034), which stays zero here.
    """
    writer.compact(len(items))
    for item in items:
        _ref(writer, item)
        writer.compact(0)


def _owned_weapons(writer, kits):
    """Client-home +0x78 entries 0x768794: battle-kit data reference, two
    adjacent booleans (+0x28, +0x29), then two raw-int-counted reference
    lists (+0x08, +0x18). Their meaning is unknown; they stay false/empty."""
    writer.compact(len(kits))
    for kit in kits:
        _ref(writer, kit)
        writer.bit_boolean(False).bit_boolean(False)
        writer.integer(0).integer(0)


def _client_home(writer, account_id, battle_kit, age_category, tutorials, main_steps, vanity, look, xp,
                 weapons=OWNED_WEAPONS, jobs=()):
    writer.raw(struct.pack('>Q', account_id))  # Home's two raw ID words.
    # Empty resources, home events, and native default battle-kit entry.
    _zeros(writer, 3)
    # 0x77e1bc collection, entries 0x779ab4: raw key/value integers.
    writer.compact(1 if age_category else 0)
    if age_category:
        writer.integer(7).integer(age_category)
    # Collections +0x48 (0x770c74), +0x58 (0x7852c4) and +0x68 (0x777610).
    _zeros(writer, 3)
    # +0x78 owned weapons (0x768de8, entries 0x768794), listed by the WEAPONS
    # screen (0x4a53e4 reads client-home +0x78).
    _owned_weapons(writer, weapons)
    # +0x80 (0x7798ac), then the +0x88 build manager (0x76b378): build count,
    # then the current build (0x769988): two integers and its name.
    _zeros(writer, 4)
    writer.string('')  # Default build name, native SCString encoder 0x8d6964.
    # Current build +0x18: equipped dyes, each a string (0x83c214, at most 50
    # characters) parsed into an asset handle; 543 replaces one per kind
    # (0x769e70). Unparsable strings are skipped natively (0x86c8cc).
    dyes = [STARTER_DYES[item][1] for item in look if item in STARTER_DYES]
    writer.compact(len(dyes))
    for dye in dyes:
        writer.string(dye)
    # Current build +0x40: other equipped cosmetic references. The character
    # editor shows these (0x77f2b8 -> 0x76a214 by slot) and 543 updates them.
    others = [item for item in look if item not in STARTER_DYES]
    writer.compact(len(others))
    for cosmetic in others:
        _ref(writer, cosmetic)
    _zeros(writer, 3)  # Current build +0x50, then manager +0x20 and +0x30.
    writer.raw(struct.pack('>Q', battle_kit))  # Selected battle-kit data record.
    _zeros(writer, 3)
    writer.bit_boolean(False)
    _zeros(writer, 2)  # +90 count, +98.
    _quest_state(writer, main_steps, xp, jobs)
    _zeros(writer, 4)  # +f8, +100 (header + count), +110.
    # Home +0x118, collection 0x7966e8, entry 0x7969a0.
    # Each entry encodes tutorial first, step second, as raw 64-bit refs.
    writer.compact(len(tutorials))
    for tutorial, step in tutorials:
        writer.raw(struct.pack('>QQ', tutorial, step))
    writer.raw(struct.pack('>QQ', 0, 0))
    _zeros(writer, 3)
    writer.string('').string('')
    writer.compact(0)
    # Conditional collections at home +e0, +120, +18, +20, +28.
    # The native UI dereferences these even when their counts are zero.
    writer.bit_boolean(True)
    _vanity_items(writer, vanity)
    for _ in range(4):
        writer.bit_boolean(True).compact(0)
    writer.compact(0)  # +128 object 0x781f14: one count, always encoded.
    writer.bit_boolean(True).compact(0)  # +30 conditional collection.
    # +130 object 0x7717b0 reads six integers. Writing one moved the avatar
    # start five bytes early (the native decoder read through 0x7717b0 into
    # the avatar), which made it misread the XP resource and over-read the payload.
    _zeros(writer, 6)


def _avatar_and_suffix(writer, xp, season_seconds=1, worlds=(), boosts=()):
    """Avatar 0x77c010, then the own-home auxiliary-event count and suffix.

    The avatar's first collection holds resources (entry 0x791cc8: data
    reference and two raw integers). Earned XP is the XpPoint resource
    (resources.csv instance 20). Every other avatar field stays empty: the
    key/value collection (0x779ab4) and the rest of the avatar, which the native
    decoder reads as 14 zero bytes when empty (measured on the tablet).
    The own-home suffix is three integers: the 0x79b1d0 object count, +54, +10.
    The native reader has no bounds checks, so these counts must be exact:
    reading past the payload consumes stale heap bytes.
    """
    writer.compact(0)
    writer.compact(1 if xp else 0)
    if xp:
        _ref(writer, XP_POINT)
        writer.integer(xp).integer(0)
    _zeros(writer, 3)  # Key/value collection, +28 (0x796584), +38 (0x78575c).
    # +40 tracks (0x78d04c). The home XP badge reads the player-level track.
    writer.compact(1 if xp else 0)
    if xp:
        _level_track(writer, PLAYER_LEVEL_TRACK, season_seconds)
    # +48 portal map cards (0x786524, entries 0x785f44).
    writer.compact(len(worlds))
    for slot_id, scene in enumerate(worlds, 1):
        _map_slot(writer, slot_id, scene, season_seconds, WORLD_NAMES.get(scene))
    # +50 Versus cards (0x782f80, entries 0x782890, card 0x515a84) and +58
    # dungeon sets (0x7743c4) stay empty, then +70, +78, +88, +60, +68 and +98.
    _zeros(writer, 8)
    # +a8 chaos energy boosts (entries 0x77b430), read by the portal orb.
    writer.compact(len(boosts))
    for boost in boosts:
        _boost(writer, boost)
    writer.compact(0)  # +b8 (entries 0x781b38)
    _zeros(writer, 3)  # Own-home suffix.


@dataclass(frozen=True)
class Boost:
    """Avatar +a8 chaos energy boost (0x77b430): the portal orb and the boost
    bar (0x4b4050) use the first one active now (start <= now < end, seconds),
    its multiplier (+8) and amount (+c), minus the amount used, which
    client-home +f8 entries (0x76dba8, +30) record by boost ID."""
    boost_id: int
    multiplier: int
    amount: int
    start: int
    end: int


def _boost(writer, boost):
    writer.bit_boolean(True)  # The boost's info object (0x77b54c) is present.
    writer.compact(boost.boost_id).compact(0).compact(0)
    writer.compact(boost.start, 64).compact(boost.end, 64)
    writer.compact(boost.multiplier).compact(boost.amount)


def _text(writer, text):
    """Text object 0x8381cc (versioned archive 0x8e55bc, fields 0x838244):
    version, 'type' and 'content', each a presence bit plus value. Type 0
    (the default) is literal content, 1 a TID, anything else empty (0x4e803c)."""
    writer.boolean(False).boolean(False)   # version 0, type 0 (literal)
    writer.boolean(text is not None)
    if text is not None:
        writer.string(text)


def _map_slot(writer, slot_id, scene, ends_in, name=None):
    """Avatar +48 portal map card, entry 0x785f44 (card 0x5150b4).

    Five integers +20..+30: +28 opens-in and +2c ends-in seconds. The card
    (0x5150b4) is state 1, active, while opened and not ended; only that
    state reacts to presses (0x516f80 -> 0x511de0). Both -1 gives state 0,
    which ignores presses, and a positive +28 makes 0x682e98 refuse the
    start. Slots here open now and end with the season. Two text objects:
    +38 is the map popup title (0x4f7510 -> 0x4f7380; when empty the
    client shows "HUNTING"), +40 another text (not shown here). Then an empty list, an empty
    path/sha object, then the map object 0x78636c: the battle scene as a raw
    data reference and six integers. +8 must equal the season track's +68
    season number (0, 0x6832b4); +14 is the tutorial portal set (0 = shown
    outside the sets, filter 0x6832f0). Then base 0x779e68 (slot ID and an
    empty list), a raw data reference (null) and an empty list.
    """
    writer.compact(0).compact(0).compact(0).compact(ends_in).compact(0)
    _text(writer, name)
    _text(writer, None)
    writer.compact(0)
    writer.boolean(False).boolean(False).boolean(False)
    _ref(writer, scene)
    _zeros(writer, 6)
    writer.compact(slot_id).compact(0)
    _ref(writer, 0)
    writer.compact(0)


def _level_track(writer, track, season_seconds=1):
    """Avatar +40 entry 0x78b29c, the player-level track.

    The home HUD (0x57e33c) and the player-level getter (0x756a30) use the
    first track whose +68 type is 1, with +24 == 0 and +28 > 0. Its +68
    levels (+28 data, +34 count) are the XP per level for level loop
    0x788de8, and its XP is the client-home +e8 record with the same ID.
    Without it the home HUD level table is empty and the badge stays at 1.
    This first type-1 track is also the season (0x4f76e0 -> 0x78d170): +28
    is the season's remaining seconds when received. The portal and home HUD
    show it minus the time since then ("Season ends in", 0x526c48).
    The meaning of +20, +2c and +d8 is not known; +d8 keeps the constructor
    default -1.
    """
    from progress import XP_LEVELS
    if type(season_seconds) is not int or not 0 < season_seconds <= 0x7fffffff:
        raise ValueError('Invalid season time')
    writer.compact(0).compact(0).compact(season_seconds).compact(0).compact(-1)  # +20 +24 +28 +2c +d8
    for _ in range(2):
        # +30, +38: structured objects 0x8381cc (versioned decoder 0x8e55bc);
        # version, integer and string are each an absent optional field.
        writer.boolean(False).boolean(False).boolean(False)
    _zeros(writer, 4 + 1)  # +40..+58 collections (0x779590), +60.
    # +68 (0x78cdd4): type 1, two integers, data reference, two integers,
    # data reference, the levels, then a raw 64-bit value.
    writer.compact(1).compact(0).compact(0)
    _ref(writer, 0)
    writer.compact(0).compact(0)
    _ref(writer, 0)
    writer.compact(len(XP_LEVELS))
    for xp in XP_LEVELS:
        writer.compact(xp)
    _ref(writer, 0)
    _zeros(writer, 6 + 1)  # +70..+c0 collections, +d0 (0x77a090).
    writer.compact(track)  # Base 0x779e68: +8 ID, then an empty +10 collection.
    writer.compact(0)


def own_home(account_id, battle_kit=SMART_BOW, age_category=0, tutorials=None, main_steps=(), xp=0,
             vanity=(), look=(), name=None, season_seconds=1, worlds=(), weapons=OWNED_WEAPONS, jobs=(),
             boosts=()):
    if not isinstance(account_id, int) or not 0 <= account_id < 1 << 64:
        raise ValueError('Home account ID is outside the native 64-bit range')
    if battle_kit != SMART_BOW:
        raise ValueError('Only the evidenced starter battle kit is supported')
    if any(kit not in OWNED_WEAPONS for kit in weapons):
        raise ValueError('Unsupported owned weapon')
    if age_category not in (0, 2, 3):
        raise ValueError('Unsupported native onboarding category')
    if type(xp) is not int or not 0 <= xp <= 0x7fffffff:
        raise ValueError('Invalid saved XP')
    if any(type(item) is not int or not 0 < item < 1 << 63 for item in vanity):
        raise ValueError('Invalid vanity item reference')
    if any(item not in vanity for item in look):
        raise ValueError('Equipped cosmetic is not owned')
    if name is not None and (not isinstance(name, str) or not name or len(name.encode('utf-8')) > 60):
        raise ValueError('Invalid hunter name')
    for step in main_steps:
        for quest in step.quests:
            if not 0 <= quest.progress <= 0x7fffffff or not 0 < quest.target <= 0x7fffffff:
                raise ValueError('Invalid quest progress')
    from progress import tutorial_entries
    entries = tutorial_entries(tutorials or {})
    writer = Writer().raw(struct.pack('>QQ', 0, account_id))
    # Profile 0x755e34: optional +28 long, name +30, name-set flag +48. The
    # hunter-name popup opens only while the flag is false (0x6278c0).
    writer.bit_boolean(False).string(name or '').bit_boolean(name is not None)
    for _ in range(3):
        writer.integer(0)
    _client_home(writer, account_id, battle_kit, age_category, entries, tuple(main_steps),
                 tuple(vanity), tuple(look), xp, tuple(weapons), tuple(jobs))
    if any(scene not in PORTAL_WORLDS for scene in worlds):
        raise ValueError('Unsupported portal world')
    _avatar_and_suffix(writer, xp, season_seconds, tuple(worlds), tuple(boosts))
    return writer.bytes()
