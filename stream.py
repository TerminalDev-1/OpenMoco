"""Bounded 13.5.1 byte streams: compact signed integers and packed booleans.

Native readers: 0x8d7f24 (32-bit), 0x8d8464 (64-bit), 0x8d724c
(booleans). A boolean byte is shared across intervening integer/string fields;
it advances only after eight boolean operations.
"""
import struct


class Writer:
    def __init__(self):
        self.data = bytearray()
        self.bit_count = 0
        self.bit_index = None
        self.sequential_bits = 0

    def boolean(self, value):
        self.sequential_bits = 0
        if self.bit_count == 0:
            self.bit_index = len(self.data)
            self.data.append(0)
        if value:
            self.data[self.bit_index] |= 1 << self.bit_count
        self.bit_count = (self.bit_count + 1) % 8
        return self

    def bit_boolean(self, value):
        """Native 0x8d7034: share a byte only with adjacent booleans."""
        if self.sequential_bits == 0:
            self.data.append(0)
        if value:
            self.data[-1] |= 1 << self.sequential_bits
        self.sequential_bits = (self.sequential_bits + 1) % 8
        return self

    def raw(self, value):
        self.sequential_bits = 0
        self.data.extend(value)
        return self

    def integer(self, value):
        return self.raw(struct.pack('>i', value))

    def compact(self, value, bits=32):
        if bits not in (32, 64) or not -(1 << (bits-1)) <= value < (1 << (bits-1)):
            raise ValueError('Compact integer is out of range')
        end = -1 if value < 0 else 0
        first = (value & 63) | (64 if value < 0 else 0)
        value >>= 6
        encoded = bytearray([first | (128 if value != end else 0)])
        while value != end:
            part = value & 127
            value >>= 7
            encoded.append(part | (128 if value != end else 0))
        return self.raw(encoded)

    def string(self, value):
        if value is None:
            return self.integer(-1)
        encoded = value.encode('utf-8')
        return self.integer(len(encoded)).raw(encoded)

    def bytes(self):
        return bytes(self.data)


class Reader:
    def __init__(self, data):
        self.data = memoryview(data)
        self.position = 0
        self.bit_count = 0
        self.bit_value = 0
        self.sequential_bits = 0
        self.sequential_value = 0

    def _read(self, size):
        self.sequential_bits = 0
        if size < 0 or self.position + size > len(self.data):
            raise ValueError('Truncated byte stream')
        value = self.data[self.position:self.position+size]
        self.position += size
        return bytes(value)

    def boolean(self):
        self.sequential_bits = 0
        if self.bit_count == 0:
            self.bit_value = self._read(1)[0]
        result = bool(self.bit_value & (1 << self.bit_count))
        self.bit_count = (self.bit_count + 1) % 8
        return result

    def bit_boolean(self):
        """Native 0x8d711c: integer/string operations end the current byte."""
        if self.sequential_bits == 0:
            self.sequential_value = self._read(1)[0]
        result = bool(self.sequential_value & (1 << self.sequential_bits))
        self.sequential_bits = (self.sequential_bits + 1) % 8
        return result

    def raw(self, size):
        return self._read(size)

    def integer(self):
        return struct.unpack('>i', self.raw(4))[0]

    def compact(self, bits=32):
        if bits not in (32, 64):
            raise ValueError('Compact integer width must be 32 or 64')
        first = self._read(1)[0]
        negative, value, width = bool(first & 64), first & 63, 6
        continuation = bool(first & 128)
        while continuation:
            if width >= bits:
                raise ValueError('Compact integer exceeds its width')
            part = self._read(1)[0]
            value |= (part & 127) << width
            width += 7
            continuation = bool(part & 128)
        if negative:
            value -= 1 << width
        if not -(1 << (bits-1)) <= value < (1 << (bits-1)):
            raise ValueError('Compact integer is out of range')
        return value

    def string(self, limit=900000):
        size = self.integer()
        if size == -1:
            return None
        if size < 0 or size > limit:
            raise ValueError('Invalid string size')
        return self.raw(size).decode('utf-8')

    @property
    def remaining(self):
        return len(self.data) - self.position
