"""Battle end summary (23200/v0) for the 13.5.1 client.

Router case 0x5aa0 (0x5bef00) builds the battle-end screen (0x488950) from
this message while a battle is running. Decoder 0x760bd8:
- compact +0x9c;
- four lists (+0xa0 entries 0x764b30, +0xa8 0x761aa4, +0xb0 0x76431c,
  +0xb8 0x76036c), each a compact count; the first three are sent empty,
  +0xb8 holds the local player (the screen needs its 'is me' entry);
- compact +0xc0;
- object +0xc8 (0x77a54c): raw data reference (the battle scene), three
  optional objects behind adjacent booleans, then two compacts;
- the drops list +0xd0 (entries 0x763c94): compact +0, raw data reference
  +8 (resolved to the data object), compacts +0x10 (amount), +0x14, +0x18.
  The screen hands the list to the gained-items screen 0x4d1598 (mode 3).
  Gear drops reveal straight into the LOOT row; other kinds wait behind an
  "OPEN CHAOS CORE(S)" button (0x48ad10). Verified on the tablet 2026-10-17:
  three power gems reveal, then EXIT sends 13223 body 01;
- compact +0xd8;
- seven optional objects (+0xe0..+0x110), each behind an adjacent boolean;
- a string +0x118.
Field meanings beyond the ones named here are not known yet.
"""
from dataclasses import dataclass
import struct

from stream import Writer

BATTLE_END = 23200
# Drop kinds handled by the gained-items screen (switch 0x4d1d64). Only gear
# (power gems) is used: kinds 0x15/0x1b are battle-kit shader unlocks
# (0x4a844c), 0xa/0xb skins, and the generic resource path 0x4de0e4 needs a
# home HUD widget that is null after a battle (it crashed at 0x4de43c).
GEAR_DROP = 0xc


@dataclass(frozen=True)
class Drop:
    kind: int          # +0
    reference: int     # +8 raw data reference
    amount: int = 1    # +0x10
    b: int = 0         # +0x14
    c: int = 0         # +0x18


def _player(writer, account_id, name, battle_kit):
    """+0xb8 entry 0x76036c. The screen (0x48e740) needs the entry whose
    +8 'is me' flag is set; without one it dereferences null."""
    writer.raw(struct.pack('>Q', account_id))  # +0 account ID
    writer.bit_boolean(True)                   # +8 the local player
    # +0x10 summary 0x75eff4: name, four compacts, two raw references, a
    # flag, a compact, a reference list, two compacts.
    writer.string(name)
    writer.compact(0).compact(0).compact(0).compact(0)
    writer.raw(struct.pack('>Q', battle_kit)).raw(struct.pack('>Q', 0))
    writer.bit_boolean(False)
    writer.compact(0).compact(0).compact(0).compact(0)
    writer.compact(0)                          # +0x18 list (entries 0x7776cc)
    writer.compact(0).compact(0).bit_boolean(False)  # +0x28 look 0x786a40: dyes, references, flag
    for _ in range(8):                         # +0x30..+0x48, +0x50
        writer.compact(0)


def battle_end(scene, drops=(), account_id=0, name='', battle_kit=6700000):
    writer = Writer()
    writer.compact(0)                      # +0x9c
    for _ in range(3):                     # +0xa0, +0xa8, +0xb0
        writer.compact(0)
    writer.compact(1)                      # +0xb8 players
    _player(writer, account_id, name, battle_kit)
    writer.compact(0)                      # +0xc0
    writer.raw(struct.pack('>Q', scene))   # +0xc8 object: battle scene reference
    for _ in range(3):
        writer.bit_boolean(False)
    writer.compact(0).compact(0)
    writer.compact(len(drops))             # +0xd0 drops
    for drop in drops:
        writer.compact(drop.kind)
        writer.raw(struct.pack('>Q', drop.reference))
        writer.compact(drop.amount).compact(drop.b).compact(drop.c)
    writer.compact(0)                      # +0xd8
    for _ in range(7):                     # +0xe0..+0x110 absent
        writer.bit_boolean(False)
    writer.string('')                      # +0x118
    return writer.bytes()
