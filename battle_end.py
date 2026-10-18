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
  +8, compacts +0x10 (amount), +0x14, +0x18. Sent empty: the screen then
  shows RETURN HOME (0x48ad10). The server rolls no battle loot (chaos cores
  were removed on 2026-10-18; generic reward kinds crash after a battle at
  0x4de43c);
- compact +0xd8;
- seven optional objects (+0xe0..+0x110), each behind an adjacent boolean;
- a string +0x118.
Field meanings beyond the ones named here are not known yet.
"""
import struct

from home import STARTER_DYES
from stream import Writer

BATTLE_END = 23200
def _player(writer, account_id, name, battle_kit, look):
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
    # +0x28 look 0x786a40, the same layout as the home build's look: dye
    # strings (0x83c214), raw cosmetic references (0x83c16c), a flag.
    dyes = [STARTER_DYES[item][1] for item in look if item in STARTER_DYES]
    writer.compact(len(dyes))
    for dye in dyes:
        writer.string(dye)
    others = [item for item in look if item not in STARTER_DYES]
    writer.compact(len(others))
    for cosmetic in others:
        writer.raw(struct.pack('>Q', cosmetic))
    writer.bit_boolean(False)
    for _ in range(8):                         # +0x30..+0x48, +0x50
        writer.compact(0)


def battle_end(scene, account_id=0, name='', battle_kit=6700000, look=()):
    """look: equipped cosmetics, as home.equipped_look returns them."""
    writer = Writer()
    writer.compact(0)                      # +0x9c
    for _ in range(3):                     # +0xa0, +0xa8, +0xb0
        writer.compact(0)
    writer.compact(1)                      # +0xb8 players
    _player(writer, account_id, name, battle_kit, look)
    writer.compact(0)                      # +0xc0
    writer.raw(struct.pack('>Q', scene))   # +0xc8 object: battle scene reference
    for _ in range(3):
        writer.bit_boolean(False)
    writer.compact(0).compact(0)
    writer.compact(0)                      # +0xd0 drops: none
    writer.compact(0)                      # +0xd8
    for _ in range(7):                     # +0xe0..+0x110 absent
        writer.bit_boolean(False)
    writer.string('')                      # +0x118
    return writer.bytes()
