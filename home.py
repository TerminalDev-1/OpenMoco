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
XP_POINT = 300020    # resources.csv XpPoint (Meta), instance 20.


@dataclass(frozen=True)
class Quest:
    """One active quest, e.g. Intro_3_1 'defeat 50 monsters'."""
    reference: int          # main_quest_step_quests data reference (155xxxxx)
    progress: int
    target: int
    event: str = None       # QuestEventTypeCond, e.g. 'Civilian'


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
    writer.compact(1)                     # +4
    writer.compact(min(quest.progress, quest.target))  # +8 progress
    writer.compact(quest.target)          # +c target
    writer.compact(0)                     # +18 objective list
    writer.compact(0)                     # +28 reference list
    for _ in range(4):                    # +34..+37
        writer.bit_boolean(False)
    writer.string(quest.event)            # +38 event-type filter
    writer.bit_boolean(False)             # +40
    writer.bit_boolean(True)              # +41 main-quest quest
    writer.compact(0)                     # +44
    _ref(writer, quest.reference)         # +48 quest data
    _zeros(writer, 5)                     # +50..+60
    writer.compact(-1)                    # +30 (constructor default -1)
    writer.compact(0)                     # +64
    writer.bit_boolean(False)             # optional +68 object absent
    writer.bit_boolean(False)             # optional +80 object absent
    _zeros(writer, 2)                     # +88, +8c


def _quest_state(writer, main_steps):
    """Home +a0 quest collection, +e8 auxiliary quests and +f0 main quests."""
    quests = [quest for step in main_steps for quest in step.quests]
    # +a0 header: next quest ID, then three unknown integers.
    writer.compact(len(quests))
    _zeros(writer, 3)
    writer.compact(len(quests))
    for quest_id, quest in enumerate(quests):
        _quest(writer, quest_id, quest)
    writer.compact(0)  # +e8 auxiliary quests.
    writer.compact(len(main_steps))  # +f0 MainQuestManager entries.
    for step in main_steps:
        _ref(writer, step.reference)
        writer.compact(0)
        writer.bit_boolean(not step.claimed)  # new
        writer.bit_boolean(step.claimed)      # claimed


def _client_home(writer, account_id, battle_kit, age_category, tutorials, main_steps):
    writer.raw(struct.pack('>Q', account_id))  # Home's two raw ID words.
    # Empty resources, home events, and native default battle-kit entry.
    _zeros(writer, 3)
    # 0x77e1bc collection, entries 0x779ab4: raw key/value integers.
    writer.compact(1 if age_category else 0)
    if age_category:
        writer.integer(7).integer(age_category)
    _zeros(writer, 8)
    writer.string('')  # Default build name, native SCString encoder 0x8d6964.
    _zeros(writer, 5)
    writer.raw(struct.pack('>Q', battle_kit))  # Selected battle-kit data record.
    _zeros(writer, 3)
    writer.bit_boolean(False)
    _zeros(writer, 2)  # +90 count, +98.
    _quest_state(writer, main_steps)
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
    for _ in range(5):
        writer.bit_boolean(True).compact(0)
    writer.compact(0)  # +128 object 0x781f14: one count, always encoded.
    writer.bit_boolean(True).compact(0)  # +30 conditional collection.
    # +130 object 0x7717b0 reads six integers. Writing one moved the avatar
    # start five bytes early (the native decoder read through 0x7717b0 into
    # the avatar), which made it misread the XP resource and over-read the payload.
    _zeros(writer, 6)


def _avatar_and_suffix(writer, xp):
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
    _zeros(writer, 1 + 14)  # Key/value collection, then the rest of the avatar.
    _zeros(writer, 3)       # Own-home suffix.


def own_home(account_id, battle_kit=SMART_BOW, age_category=0, tutorials=None, main_steps=(), xp=0):
    if not isinstance(account_id, int) or not 0 <= account_id < 1 << 64:
        raise ValueError('Home account ID is outside the native 64-bit range')
    if battle_kit != SMART_BOW:
        raise ValueError('Only the evidenced starter battle kit is supported')
    if age_category not in (0, 2, 3):
        raise ValueError('Unsupported native onboarding category')
    if type(xp) is not int or not 0 <= xp <= 0x7fffffff:
        raise ValueError('Invalid saved XP')
    for step in main_steps:
        for quest in step.quests:
            if not 0 <= quest.progress <= 0x7fffffff or not 0 < quest.target <= 0x7fffffff:
                raise ValueError('Invalid quest progress')
    from progress import tutorial_entries
    entries = tutorial_entries(tutorials or {})
    writer = Writer().raw(struct.pack('>QQ', 0, account_id))
    writer.bit_boolean(False).string('').bit_boolean(False)
    for _ in range(3):
        writer.integer(0)
    _client_home(writer, account_id, battle_kit, age_category, entries, tuple(main_steps))
    _avatar_and_suffix(writer, xp)
    return writer.bytes()
