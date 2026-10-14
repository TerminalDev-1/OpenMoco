"""Recover previously received tutorial steps from private local server captures.

Requires the matching decrypted login/session files, existing local credentials,
and account database. Never creates an account or prints credentials. Defaults
to inspection; --apply saves validated transitions after backing up the database.
"""
import argparse
from collections import Counter
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from accounts import AccountStore
from commands import decode_client_turn
from progress import validate_tutorial
from protocol import FrameDecoder, decode_login_request


def recover(session_path, database, apply=False):
    suffix = '.session.bin'
    if not session_path.name.endswith(suffix):
        raise ValueError('Expected a private .session.bin capture')
    login_path = session_path.with_name(session_path.name[:-len(suffix)] + '.login.bin')
    login = decode_login_request(login_path.read_bytes())
    if not login.account_id or not login.token or not database.is_file():
        raise ValueError('Recovery requires an existing local account and token')
    store = AccountStore(database)
    account = store.authenticate(login.account_id, login.token)
    decoder = FrameDecoder()
    updates, scene, unsupported = [], None, Counter()
    for frame in decoder.feed(session_path.read_bytes()):
        if frame.message_type == 16543 and frame.version == 0:
            try:
                turn = decode_client_turn(frame.payload)
                for command in turn.commands:
                    if command.command_type == 574 and command.account_id in (0, account.account_id):
                        tutorial, step = command.fields['tutorial'], command.fields['step']
                        validate_tutorial(tutorial, step)
                        updates.append((tutorial, step))
            except ValueError as error:
                unsupported[type(error).__name__] += 1
        elif frame.message_type == 13222 and frame.version == 0:
            from scene_requests import decode_scene_request
            try:
                request = decode_scene_request(frame.payload)
                if request.scene_id in (10900000, 10900001):
                    scene = request.scene_id
            except ValueError:
                unsupported['scene'] += 1
    if apply:
        backup = database.with_name(database.name + '.before-progress-recovery')
        if backup.exists():
            raise ValueError('Recovery backup exists; preserve it before another recovery')
        with sqlite3.connect(database) as source, sqlite3.connect(backup) as target:
            source.backup(target)
        for tutorial, step in updates:
            store.record_tutorial(account.account_id, tutorial, step)
        if scene is not None:
            store.record_scene(account.account_id, scene)
    print(f'Validated {len(updates)} tutorial transitions; supported scene={scene}; '
          f'unsupported turns={sum(unsupported.values())}; applied={apply}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('session', type=Path)
    parser.add_argument('--database', type=Path, default=Path('.local/accounts.sqlite3'))
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    recover(args.session, args.database, args.apply)
