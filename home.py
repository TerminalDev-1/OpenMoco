"""13.5.1 minimum own-home profile, based on native encoder/decoder evidence.

24548/v0: outer decoder 0x786fdc, own-home 0x755e34,
client-home 0x77e0b8, avatar 0x77c010. Unknown fields retain native zero defaults.
This initializes the home UI/onboarding; it does not implement gameplay.
"""
import struct
from stream import Writer

OWN_HOME_TYPE = 24548
SMART_BOW = 6700000  # Loaded battle-kit record; its weapon link is ArcherWeapon.


def _zeros(writer, count):
    for _ in range(count):
        writer.compact(0)


def _client_home(writer, account_id, battle_kit):
    writer.raw(struct.pack('>Q', account_id))  # Home's two raw ID words.
    # Empty resources, home events, and native default battle-kit entry.
    _zeros(writer, 12)
    writer.string('')  # Default build name, native SCString encoder 0x8d6964.
    _zeros(writer, 5)
    writer.raw(struct.pack('>Q', battle_kit))  # Selected battle-kit data record.
    _zeros(writer, 3)
    writer.bit_boolean(False)
    _zeros(writer, 14)
    writer.raw(struct.pack('>QQ', 0, 0))
    _zeros(writer, 3)
    writer.string('').string('')
    writer.compact(0)
    # Conditional collections at home +e0, +120, +18, +20, +28.
    # The native UI dereferences these even when their counts are zero.
    for _ in range(5):
        writer.bit_boolean(True).compact(0)
    writer.compact(0)  # +128 auxiliary collection, always encoded.
    writer.bit_boolean(True).compact(0)  # +30 conditional collection.
    _zeros(writer, 1)  # +130 auxiliary collection.


def _empty_avatar_and_suffix(writer):
    # Native empty avatar's resource/gear/progression collections, then the
    # own-home auxiliary-event count and two compact suffix integers.
    _zeros(writer, 25)


def own_home(account_id, battle_kit=SMART_BOW):
    if not isinstance(account_id, int) or not 0 <= account_id < 1 << 64:
        raise ValueError('Home account ID is outside the native 64-bit range')
    if battle_kit != SMART_BOW:
        raise ValueError('Only the evidenced starter battle kit is supported')
    writer = Writer().raw(struct.pack('>QQ', 0, account_id))
    writer.bit_boolean(False).string('').bit_boolean(False)
    for _ in range(3):
        writer.integer(0)
    _client_home(writer, account_id, battle_kit)
    _empty_avatar_and_suffix(writer)
    return writer.bytes()
