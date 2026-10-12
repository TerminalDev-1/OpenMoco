"""Inspect saved ARM64 runtime segments without modifying the client.

Requires capstone from .tools/python. Addresses are relative to libg.so.
"""
import argparse
from pathlib import Path
import sys
import struct

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.tools' / 'python'))
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM


def disassemble(root, start, limit=3000):
    segments = [(int(p.stem.split('-')[1], 16), p.read_bytes())
                for p in root.glob('game-*.bin')]
    decoder = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
    def read64(address):
        data = next((b[address-va:address-va+8] for va, b in segments
                     if va <= address and address+8 <= va+len(b)), None)
        if data is None:
            raise ValueError('Missing runtime table')
        return struct.unpack('<Q', data)[0]
    def hash64(data, seed):
        for value in data:
            seed = ((seed ^ value) * 0x100000001b3) & ((1 << 64) - 1)
        return seed
    def resolve_call(call):
        # Read-only reproduction of this build's trampoline lookup.
        data = (0xfe1a28 - call - 4).to_bytes(8, 'little', signed=True)
        count = read64(0xfe2df4)
        seed = read64(0xfe2dfc + (hash64(data, 0xcbf29ce484222325) % count)*8)
        index = hash64(data, seed) % count
        value = read64(0xfed90c + index*8)
        kind = read64(0xff841c + index*8)
        if kind == 1:
            return (0xfe1a28 + value) & ((1 << 64) - 1)
        return None
    todo, visited, lines = [start], set(), []
    while todo and len(visited) < limit:
        address = todo.pop()
        while address not in visited and len(visited) < limit:
            data = next((b[address-va:address-va+4] for va, b in segments
                         if va <= address < va+len(b)), b'')
            instruction = next(decoder.disasm(data, address), None)
            if instruction is None:
                lines.append(f'{address:#x}: unavailable/invalid')
                break
            visited.add(address)
            op, args = instruction.mnemonic, instruction.op_str
            if op == 'bl' and args == '#0xfe1a28':
                try:
                    target = resolve_call(address)
                    if target is not None:
                        args += f' ; resolved {target:#x}'
                    else:
                        args += ' ; trampoline instruction fragment'
                except (ValueError, ZeroDivisionError):
                    pass
            lines.append(f'{address:#x}: {op} {args}')
            if op == 'b':
                address = int(args.lstrip('#'), 16)
                continue
            if op.startswith('b.') or op in ('cbz', 'cbnz', 'tbz', 'tbnz'):
                todo.append(int(args.rsplit('#', 1)[1], 16))
            if op in ('ret', 'br', 'brk'):
                break
            address += 4
    return '\n'.join(lines) + '\n'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('address', type=lambda x: int(x, 0))
    parser.add_argument('--root', type=Path, default=ROOT/'analysis/runtime/game')
    parser.add_argument('--limit', type=int, default=3000)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = disassemble(args.root, args.address, args.limit)
    if args.output:
        args.output.write_text(result, encoding='utf-8')
    else:
        print(result, end='')
