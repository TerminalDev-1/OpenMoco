"""Server -> client battle events (28852/v0) for the 13.5.1 client.

The battle is a deterministic rollback simulation (docs/BATTLE_PROTOCOL.md).
28852 adds logic events to one simulation frame; the client stores them in
that frame's event list (0x6110ac -> 0x71e830), rolls back and re-simulates
from it, and runs each event's execute method inside the simulation.

Wire layout (decoder 0x761770, binary archive reader 0x8ed2d4):
- raw int frame;
- `events` vector (0x724efc): compact count, then per event a presence bit,
  a compact logic type (the vector is polymorphic, type -1) and the
  event's archive fields. Archive int fields are a presence bit (value
  differs from the default 0) followed by a compact value; archive booleans
  are one bit. Bits use the stream's persistent packed booleans.

Only the XP grant is implemented: LogicXpEvent 1217 (serializer 0x74df98:
battlePlayerId, xp, questSpeciality, dropCoins). Its execute 0x74e0cc finds
the player whose metadata +0x10 equals battlePlayerId and calls 0x739fc4,
which adds the XP to the player's battle XP (+0x1a0). The HUD bar reads
that field, so the XP shows natively and survives rollback.
"""
from stream import Writer

BATTLE_EVENTS = 28852
XP_EVENT = 1217
LOCAL_BATTLE_PLAYER = 0   # Every captured 18854 input names controller 0.
MAX_EVENT_XP = 1 << 20


def _int_field(writer, value):
    writer.boolean(value != 0)
    if value != 0:
        writer.compact(value)


def xp_event(frame, xp, battle_player_id=LOCAL_BATTLE_PLAYER):
    """28852/v0 payload granting `xp` battle XP to one player at `frame`."""
    if type(frame) is not int or not 0 < frame < 1 << 31:
        raise ValueError('Invalid battle frame')
    if type(xp) is not int or not 0 < xp <= MAX_EVENT_XP:
        raise ValueError('Invalid battle XP')
    if type(battle_player_id) is not int or not 0 <= battle_player_id < 1 << 31:
        raise ValueError('Invalid battle player')
    writer = Writer().integer(frame).compact(1)
    writer.boolean(True).compact(XP_EVENT)
    _int_field(writer, battle_player_id)
    _int_field(writer, xp)
    _int_field(writer, 0)     # questSpeciality
    writer.boolean(False)     # dropCoins
    return writer.bytes()
