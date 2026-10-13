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
        if command_type not in (524, 541, 560, 572, 574, 575, 576, 591):
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
        elif command_type == 574:  # 0x6866b8: tutorial and step data refs.
            fields = {'tutorial': reader.compact(64), 'step': reader.compact(64)}
        elif command_type in (575, 576):  # 0x688590 / 0x6849c8.
            fields['step'] = reader.compact(64)
        commands.append(Command(command_type, tick, game_id, account_id, fields))
    if reader.remaining:
        raise ValueError('Unexpected client-turn suffix')
    return ClientTurn(frame, client_time, tuple(commands))
