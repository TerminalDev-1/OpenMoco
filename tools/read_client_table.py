"""Read the supplied 13.5.1 client's compressed CSV tables into an analysis file.

These assets use five LZMA property bytes and a four-byte little-endian plain
size, instead of the eight-byte size used by the standard LZMA-alone header.
No APK or original archive is modified.
"""
import argparse
import lzma
from pathlib import Path
import zipfile

MAX_SIZE = 64 * 1024 * 1024


def decode_table(encoded):
    if encoded.startswith(b'Name,'):
        return encoded.decode('utf-8-sig')
    if len(encoded) < 9:
        raise ValueError('Truncated client table header')
    size = int.from_bytes(encoded[5:9], 'little')
    if not 0 < size <= MAX_SIZE:
        raise ValueError('Client table size exceeds the analysis limit')
    decoder = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE, memlimit=MAX_SIZE)
    try:
        plain = decoder.decompress(encoded[:9] + bytes(4) + encoded[9:], max_length=size + 1)
    except lzma.LZMAError as error:
        raise ValueError('Invalid client table compression') from error
    if len(plain) != size or not decoder.eof or decoder.unused_data:
        raise ValueError('Client table length or compressed stream does not match its header')
    return plain.decode('utf-8-sig')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('apk', type=Path, help='Local asset-pack APK to inspect')
    parser.add_argument('--entry', default='assets/csv_logic/battle_scenes.csv')
    parser.add_argument('--output', type=Path, default=Path('analysis/battle_scenes.csv'))
    args = parser.parse_args()
    with zipfile.ZipFile(args.apk) as archive:
        info = archive.getinfo(args.entry)
        if info.file_size > MAX_SIZE:
            parser.error('Archive entry exceeds the analysis limit')
        text = decode_table(archive.read(info))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding='utf-8', newline='')
    print(f'Decoded {len(text.encode("utf-8"))} bytes to {args.output}')


if __name__ == '__main__':
    main()
