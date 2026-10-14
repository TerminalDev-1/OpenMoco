"""Minimum 13.5.1 apartment and tutorial scenes, derived from native encoders.

23491/v0: SceneConfig 1003, Frame 1200, OpenWorld handler 1240,
Player 2009 and linked character. The fixed starter template preserves
native defaults whose field meanings remain under investigation. Both
compact player identity fields are supplied by the authenticated server.
This is a constrained scene checkpoint, not a general scene serializer.
"""
from stream import Writer

HOME_SPAWN = (1474560, 4423680)  # Tile (22,67), centered in 16.16 units.

_PREFIX = bytes.fromhex(
    "e9a0c8b20aa0c8b20a9813007f907f01f80101a0a2eabe0180aea60a8080b401"
    "80809c043480aea60a80aea60a0000000000"
)

_MIDDLE = bytes.fromhex(
    "020000028080b40180809c047f7f020000000f80801ca0b802a0b8027f0000c1"
    "020300c07f7f060101027f01017f008080801419a4010a0a6205abc9e30abfff"
    "ffff0f01880500007f237f7facc9e30a96bfffffff0f0101053800007f7f7f62"
    "aec9e30abfffffff0f0189020500007f237f7fafc9e30a96bfffffff0f010305"
    "3800007f7f7f62adc9e30abfffffff0f0189040500007f237f7f00a0f6cbbf01"
    "000200000200000000000f918aaa01918a9204aff5bd01aff5a504127f038080"
    "b40180809c0400019387e202000000e000000000000101a0f6cbbf0100000200"
    "01a0efb1060000000000000000000000a0a2eabe0100208080501fa0b8028080"
    "b40180809c048080b40180809c04000049"
)

_SUFFIX = bytes.fromhex(
    "0101020000000c4c6f63616c2048756e7465720000000004acc9e30aaec9e30a"
    "afc9e30aadc9e30a00040000000000000000000000000000a0efb106a0efb106"
    "000044000000000000000000000001027f000000000000000000000000010000"
    "0000000000000000000000000000000000000000000000000000000000000000"
    "000000000000000000000000000000000000000000000000"
)

_PORTAL_SUFFIX = bytes.fromhex(
    "0101020000000c4c6f63616c2048756e7465720000000004acc9e30aaec9e30a"
    "afc9e30aadc9e30a00040000000000000000000000000000a0efb106a0efb106"
    "0000fc01018091d8bf0100a699b70199e6ac0414fb5d268a65c3f9f625886b20"
    "e2b934c3022400000000000000000000017f0000000000000000000000000100"
    "0000000000000000000000000000000000000000000000000000000000000000"
    "0000000000000000000000000000000000000000000000000000"
)


def apartment_scene(account_id, portal=True):
    """Bind the two evidenced accountId fields to a valid local namespace.

    Native metadata serializer 0x73ab98 starts with accountId; the second
    occurrence is the character's linked player identity. The native
    487-byte sample used the same nonzero local ID for both. Presence bits
    remain fixed, so zero/production identities are deliberately rejected.
    """
    if not isinstance(account_id, int) or not 128 <= account_id >> 32 <= 255 or not account_id & 0xffffffff:
        raise ValueError('Apartment requires a nonzero local guest identity')
    identity = Writer().compact(account_id, 64).bytes()
    return _PREFIX + identity + _MIDDLE + identity + (_PORTAL_SUFFIX if portal else _SUFFIX)


_TUTORIAL_PREFIX = bytes.fromhex(
    "e9a1c8b20aa1c8b20a9813007f907f01f80101a0a2eabe0180aea60a8080e403"
    "8080c4043480aea60a80aea60a0000000000"
)

_TUTORIAL_MIDDLE = bytes.fromhex(
    "020000028080e4038080c4047f7f020000000f80801ca0b802a0b8027f0000c1"
    "020300c07f7f060101027f01017f008080801419a4010a0a6205abc9e30abfff"
    "ffff0f01880500007f237f7facc9e30a96bfffffff0f0101053800007f7f7f62"
    "aec9e30abfffffff0f0189020500007f237f7fafc9e30a96bfffffff0f010305"
    "3800007f7f7f62adc9e30abfffffff0f0189040500007f237f7f00a0f6cbbf01"
    "000200000200000000000f918ada03918aba04aff5ed03aff5cd04127f038080"
    "e4038080c40400019387e202000000e000000000000101a0f6cbbf0100000200"
    "01a0efb1060000000000000000000000a0a2eabe0100208080501fa0b8028080"
    "e4038080c4048080e4038080c404000049"
)

_TUTORIAL_SUFFIX = bytes.fromhex(
    "0101020000000c4c6f63616c2048756e7465720000000004acc9e30aaec9e30a"
    "afc9e30aadc9e30a00040000000000000000000000000000a0efb106a0efb106"
    "000044000000000000000000000001027f000000000000000000000000010000"
    "0000000000000000000000000000000000000000000000000000000000000000"
    "000000000000000000000000000000000000000000000000"
)


def tutorial_scene(account_id):
    """Native-derived TutorialAreaBasic 10900001 starter frame, without mobs."""
    if not isinstance(account_id, int) or not 128 <= account_id >> 32 <= 255 or not account_id & 0xffffffff:
        raise ValueError('Tutorial requires a nonzero local guest identity')
    identity = Writer().compact(account_id, 64).bytes()
    body = _TUTORIAL_PREFIX + identity + _TUTORIAL_MIDDLE + identity + _TUTORIAL_SUFFIX
    # Battle-start 0x761c60/0x762244 configuration +18 must contain a
    # selection. The battle UI dereferences it at 0x486148..150.
    # Native 0x766160/0x76622c -> 0x77a46c/0x77a54c golden body: 65 bytes.
    selection = Writer().raw(bytes(3)).bit_boolean(True)
    selection.raw((10900001).to_bytes(8, 'big'))
    selection.bit_boolean(False).bit_boolean(False).bit_boolean(False)
    selection.compact(0).compact(0).raw(bytes(50))
    return body[:-58] + selection.bytes() + body[-4:]


# Native-encoded initial tutorial monster: DragonlingWeakMeleeTutorial
# Character data 10800020, health 624, position (4161536,4620288).
_MONSTER_PREFIX = bytes.fromhex(
    "e9a1c8b20aa1c8b20a9813007f907f01f80101a0a2eabe0180aea60a8080e403"
    "8080c4043480aea60a80aea60a0000000000"
)

_MONSTER_MIDDLE = bytes.fromhex(
    "020000028080e4038080c4047f7f020000000f80801ca0b802a0b8027f0000c1"
    "020300c07f7f060101027f01017f008080801419a4010a0a6205abc9e30abfff"
    "ffff0f01880500007f237f7facc9e30a96bfffffff0f0101053800007f7f7f62"
    "aec9e30abfffffff0f0189020500007f237f7fafc9e30a96bfffffff0f010305"
    "3800007f7f7f62adc9e30abfffffff0f0189040500007f237f7f00a0f6cbbf01"
    "000200000200000000000f918ada03918aba04aff5ed03aff5cd04127fc38080"
    "e4038080c40400019387e20200010180bdf6be0194aea60a878080fc038080b4"
    "0494aea60a94aea60a0000000000020000028080fc038080b4047f017f020000"
    "78808022b009b0097f000008067f7f00367f7f0101107f08087f0000cc808014"
    "a4010a0a000000a00200000200000000007f918af20307918aaa04aff58504af"
    "f5bd04897f8080fc03018080b404000000000000380000000101a0f6cbbf0100"
    "800001a0efb1060000000000000000000000a0a2eabe010000c8808050a0b802"
    "8080e403478080c4048080e4038080c4040000"
)

_MONSTER_SUFFIX = bytes.fromhex(
    "9201010000000c4c6f63616c2048756e746572000000000004acc9e30aaec9e3"
    "0aafc9e30aadc9e30a00040000000000000000000000000000a0efb106a0efb1"
    "060000910000000000000000000000017f000000000000000000000000010000"
    "00010000000000a6522100000000000000000000000000000000000000000000"
    "0000000000000000000000000000000000000000000000000000000000000000"
    "00000000"
)


def monster_tutorial_scene(account_id):
    """Initial enemy snapshot; authoritative combat is not implemented here."""
    if type(account_id) is not int or not 128 <= account_id >> 32 <= 255 or not account_id & 0xffffffff:
        raise ValueError('Tutorial requires a nonzero local guest identity')
    identity = Writer().compact(account_id, 64).bytes()
    return _MONSTER_PREFIX + identity + _MONSTER_MIDDLE + identity + _MONSTER_SUFFIX
