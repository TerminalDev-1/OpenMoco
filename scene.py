"""Minimum 13.5.1 apartment scene, derived from the native encoder.

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


def apartment_scene(account_id):
    """Bind the two evidenced accountId fields to a valid local namespace.

    Native metadata serializer 0x73ab98 starts with accountId; the second
    occurrence is the character's linked player identity. The native
    487-byte sample used the same nonzero local ID for both. Presence bits
    remain fixed, so zero/production identities are deliberately rejected.
    """
    if not isinstance(account_id, int) or not 128 <= account_id >> 32 <= 255 or not account_id & 0xffffffff:
        raise ValueError('Apartment requires a nonzero local guest identity')
    identity = Writer().compact(account_id, 64).bytes()
    return _PREFIX + identity + _MIDDLE + identity + _SUFFIX
