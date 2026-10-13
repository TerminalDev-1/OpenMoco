"""13.5.1 controller inputs; decoding does not advance a game simulation."""
from dataclasses import dataclass
import struct

from stream import Reader


@dataclass(frozen=True)
class Stick:
    strength: int
    mode: int
    angle: int | None = None
    x: int = 0
    y: int = 0


@dataclass(frozen=True)
class ControllerInput:
    frame: int
    sequence: int
    controller: int
    stick: Stick


def decode_controller_input(payload):
    """18854/v0: 0x76536c -> 0x71ca2c -> 0x7e5898.

    The stream's +0x110 reader is compact signed32 (0x8d7f24);
    +0xf8 is signed byte (0x8d769c). A present stick in mode 2 has
    two compact coordinates. Other modes carry one angular byte, whose
    native fixed-point trigonometry is not reproduced by this decoder.
    """
    reader = Reader(payload)
    frame, sequence = reader.integer(), reader.integer()
    if frame < 0 or sequence < 0:
        raise ValueError('Negative controller frame or sequence')
    controller = reader.compact()
    header = struct.unpack('b', reader.raw(1))[0]
    strength, mode = (header + 128) >> 3, header & 6
    if not header & 1:
        stick = Stick(strength, mode)
    elif mode == 2:
        stick = Stick(strength, mode, x=reader.compact(), y=reader.compact())
    else:
        stick = Stick(strength, mode, angle=struct.unpack('b', reader.raw(1))[0])
    if reader.remaining:
        raise ValueError('Unexpected controller input suffix')
    return ControllerInput(frame, sequence, controller, stick)
