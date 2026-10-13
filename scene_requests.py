"""Evidenced minimal 13.5.1 scene-selection requests (13222/v0)."""
from dataclasses import dataclass
from stream import Reader


@dataclass(frozen=True)
class SceneRequest:
    flag: bool
    scene_id: int
    auxiliary: tuple
    data_reference_a: int
    data_reference_b: int
    final_flag: bool


def decode_scene_request(payload):
    """0x778560 -> selection 0x77a46c; only empty optional objects verified.

    Data references use raw uint64 (0x83c16c), not reflection compact64.
    Selection has three adjacent object-presence bits and two compact ints.
    Requests containing additional objects or vector entries remain unsupported.
    """
    reader = Reader(payload)
    flag = reader.bit_boolean()
    scene = int.from_bytes(reader.raw(8), 'big')
    if any(reader.bit_boolean() for _ in range(3)):
        raise ValueError('Unimplemented scene-selection optional object')
    auxiliary = (reader.compact(), reader.compact())
    references = tuple(int.from_bytes(reader.raw(8), 'big') for _ in range(2))
    if reader.compact() != 0:
        raise ValueError('Unimplemented scene-selection vector')
    final_flag = reader.bit_boolean()
    if reader.remaining:
        raise ValueError('Unexpected scene-request suffix')
    return SceneRequest(flag, scene, auxiliary, *references, final_flag)
