"""Create a persistent local-only Curve25519 key; never print the private key."""
import argparse
import json
from pathlib import Path
from nacl.public import PrivateKey

ROOT = Path(__file__).resolve().parents[1]


def load_or_create(path):
    if path.exists():
        record = json.loads(path.read_text(encoding='utf-8'))
        key = PrivateKey(bytes.fromhex(record['private_key']))
        if bytes(key.public_key).hex() != record['public_key']:
            raise ValueError('Local key pair is inconsistent')
        return key
    path.parent.mkdir(parents=True, exist_ok=True)
    key = PrivateKey.generate()
    record = {'private_key': bytes(key).hex(), 'public_key': bytes(key.public_key).hex()}
    with path.open('x', encoding='utf-8') as stream:
        json.dump(record, stream, indent=2)
        stream.write('\n')
    return key


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'.local/server-key.json')
    args = parser.parse_args()
    key = load_or_create(args.output)
    print('Local server key ready:', args.output)
    print('Public key:', bytes(key.public_key).hex())
