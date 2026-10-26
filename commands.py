"""Read evidenced 13.5.1 client turns; this does not execute game commands.

16543/v0: decoder 0x774668; command factory 0x67d5e0 / 0x67db3c.
Reflection base 0x67cdb4 reads three optional compact longs, sharing presence
bits across commands (0x8ed3dc). Unknown command lengths cannot be skipped.
"""
from dataclasses import dataclass
from stream import Reader


class UnsupportedCommand(ValueError):
    def __init__(self, command_type, offset):
        self.command_type = command_type
        self.offset = offset
        super().__init__(f'Unsupported command {command_type} at byte {offset}')


@dataclass(frozen=True)
class Command:
    command_type: int
    tick: int
    game_id: int
    account_id: int
    fields: dict


@dataclass(frozen=True)
class ClientTurn:
    frame: int
    client_time: int
    commands: tuple


def decode_client_turn(payload):
    reader = Reader(payload)
    frame = reader.compact()
    client_time = int.from_bytes(reader.raw(8), 'big')
    count = reader.compact()
    if not 0 <= count <= 512:
        raise ValueError('Invalid client command count')
    commands = []
    for _ in range(count):
        offset = reader.position
        command_type = reader.integer()
        # 603 (0x67b6f4, daily goal completion reward) has only the base fields.
        if command_type not in (524, 541, 543, 560, 569, 572, 574, 575, 576, 583, 591, 593, 603):
            raise UnsupportedCommand(command_type, offset)
        tick, game_id, account_id = (
            reader.compact(64) if reader.boolean() else 0 for _ in range(3)
        )
        fields = {}
        if command_type == 524:  # 0x685528: two optional compact integers.
            fields = {name: reader.compact() if reader.boolean() else 0
                      for name in ('key', 'value')}
        elif command_type == 541:  # Custom decoder 0x684d68, raw integer.
            fields['age'] = reader.integer()
        elif command_type == 543:  # 0x68732c: equip a cosmetic (data type 0x1d).
            fields['cosmetic'] = reader.compact(64)
            fields['slot'] = reader.compact() if reader.boolean() else 0
        elif command_type == 569:  # 0x67c790: claim quests, +28 quest ID list (also the daily goal, 0x4c0188).
            count = reader.compact()
            if not 0 <= count <= 64:
                raise ValueError('Invalid main-quest claim count')
            fields['quests'] = tuple(reader.compact() for _ in range(count))
        elif command_type == 574:  # 0x6866b8: tutorial and step data refs.
            fields = {'tutorial': reader.compact(64), 'step': reader.compact(64)}
        elif command_type in (575, 576):  # 0x688590 / 0x6849c8.
            fields['step'] = reader.compact(64)
        elif command_type == 583:  # 0x687fa8: feature unlock shown, "featureunlocks" ref.
            fields['feature'] = reader.compact(64)
        elif command_type == 593:  # 0x6864ac: one data reference (type 0x6d).
            fields['reference'] = reader.compact(64)
        commands.append(Command(command_type, tick, game_id, account_id, fields))
    if reader.remaining:
        raise ValueError('Unexpected client-turn suffix')
    return ClientTurn(frame, client_time, tuple(commands))
