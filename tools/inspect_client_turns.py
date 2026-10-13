"""Summarize private decrypted session captures without credentials or age values.

Usage: python tools/inspect_client_turns.py captures/game/SESSION.session.bin
Unknown command types are reported; they are never silently skipped.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from commands import decode_client_turn, UnsupportedCommand
from protocol import FrameDecoder


def inspect(path):
    decoder = FrameDecoder()
    messages, command_types = Counter(), Counter()
    transitions, unsupported = [], Counter()
    turns = 0
    with path.open('rb') as capture:
        while chunk := capture.read(65536):
            for frame in decoder.feed(chunk):
                messages[frame.message_type] += 1
                if frame.message_type != 16543 or frame.version != 0:
                    continue
                try:
                    turn = decode_client_turn(frame.payload)
                except UnsupportedCommand as error:
                    unsupported[error.command_type] += 1
                    continue
                turns += 1
                for command in turn.commands:
                    command_types[command.command_type] += 1
                    if command.command_type == 574:
                        transitions.append({key: command.fields[key] for key in ('tutorial', 'step')})
    return {'messages': dict(messages), 'decoded_turns': turns,
            'command_types': dict(command_types), 'unsupported_commands': dict(unsupported),
            'tutorial_transitions': transitions,
            'trailing_frame_bytes': len(decoder.pending)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path, help='Ignored private .session.bin capture')
    args = parser.parse_args()
    print(json.dumps(inspect(args.capture), indent=2))
