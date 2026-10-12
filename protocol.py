"""Passive framing inferred from the captured 13.5.1 initial client packet.

Observed layout: big-endian uint16 type, uint24 payload length, uint16
version, followed by payload. This does not implement a server handshake.
"""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Frame:
    message_type: int
    version: int
    payload: bytes

    def encode(self):
        if not 0 <= self.message_type <= 65535 or not 0 <= self.version <= 65535:
            raise ValueError('Frame type/version must fit uint16')
        if len(self.payload) > 0xffffff:
            raise ValueError('Frame payload must fit uint24')
        return (self.message_type.to_bytes(2, 'big') + len(self.payload).to_bytes(3, 'big')
                + self.version.to_bytes(2, 'big') + self.payload)


def decode_client_hello(payload):
    """Observed 10100 layout; field meanings remain partially unresolved."""
    if len(payload) < 24:
        raise ValueError('Truncated client hello')
    values = [int.from_bytes(payload[i:i+4], 'big', signed=True) for i in range(0, 24, 4)]
    length = values.pop()
    if length < 0 or length > 1000 or len(payload) < 24 + length + 12:
        raise ValueError('Invalid client hello string length')
    tail = payload[24+length:]
    if len(tail) != 12 or tail[8:] != b'\xff\xff\xff\xff':
        raise ValueError('Unsupported client hello trailing fields')
    return {'initial_integers': values, 'fingerprint': payload[24:24+length].decode('ascii'),
            'trailing_integers': [int.from_bytes(tail[i:i+4], 'big', signed=True) for i in range(0,12,4)]}


def server_hello(challenge):
    """20100 byte-array schema from native decoder 0x8e3c4c (13.5.1)."""
    if not 1 <= len(challenge) <= 1000:
        raise ValueError('Hello challenge must contain 1..1000 bytes')
    return Frame(20100, 0, len(challenge).to_bytes(4, 'big') + challenge)


def decode_login_prefix(payload):
    """Inspect the native plaintext 10101 prefix; the remaining fields are opaque.

    This must never be applied directly to encrypted wire data.
    Token contents are deliberately omitted from the returned diagnostics.
    """
    position = 0
    def integer():
        nonlocal position
        if position + 4 > len(payload):
            raise ValueError('Truncated login prefix')
        value = int.from_bytes(payload[position:position+4], 'big', signed=True)
        position += 4
        return value
    def string():
        nonlocal position
        length = integer()
        if length == -1:
            return None
        if length < 0 or length > 900000 or position + length > len(payload):
            raise ValueError('Invalid login string length')
        value = payload[position:position+length].decode('utf-8')
        position += length
        return value
    high, low = integer(), integer()
    token = string()
    versions = [integer(), integer(), integer()]
    fingerprint = string()
    return {'account_id': ((high & 0xffffffff) << 32) | (low & 0xffffffff),
            'token_present': token is not None and bool(token), 'version_fields': versions,
            'fingerprint': fingerprint, 'remaining_bytes': len(payload) - position}


@dataclass(frozen=True)
class LoginRequest:
    account_id: int
    token: str | None = field(repr=False)
    version_fields: tuple
    fingerprint: str | None
    remaining: bytes = field(repr=False)


def decode_login_request(payload):
    """Preserve reconnect credentials internally; never include them in diagnostics."""
    position = 0
    def read(size):
        nonlocal position
        if size < 0 or position+size > len(payload):
            raise ValueError('Truncated login request')
        value = payload[position:position+size]
        position += size
        return value
    def integer():
        return int.from_bytes(read(4), 'big', signed=True)
    def string():
        size = integer()
        if size == -1:
            return None
        if size < 0 or size > 900000:
            raise ValueError('Invalid login string length')
        return read(size).decode('utf-8')
    account_id = int.from_bytes(read(8), 'big')
    token = string()
    versions = tuple(integer() for _ in range(3))
    fingerprint = string()
    return LoginRequest(account_id, token, versions, fingerprint, payload[position:])


def login_reply(account, version_fields):
    """13.5.1 type 29125/v1, mandatory prefix from native decoder 0x835d6c.

    Field order is also checked against the native encoder's default payload.
    Unknown fields retain zero/null defaults; consumed configuration strings
    are present as empty strings rather than null pointers.
    """
    def integer(value):
        return value.to_bytes(4, 'big', signed=True)
    def string(value):
        if value is None:
            return integer(-1)
        encoded = value.encode('utf-8')
        return integer(len(encoded)) + encoded
    identity = account.account_id.to_bytes(8, 'big')
    body = identity + identity + string(account.token) + string(None)
    body += b''.join(integer(value) for value in version_fields)
    body += integer(0) + string(None) + integer(0) * 3
    body += string(None) * 2 + integer(0) + string(None) * 2
    body += integer(0) + string(None) * 2 + integer(-1)
    # Three bit-packed booleans occupy one byte, then a zero compact VInt.
    body += bytes(2) + string('') * 4
    return Frame(29125, 1, body)


class FrameDecoder:
    def __init__(self, max_payload=4 * 1024 * 1024):
        self.pending = bytearray()
        self.max_payload = max_payload

    def feed(self, data):
        self.pending.extend(data)
        frames = []
        while len(self.pending) >= 7:
            size = int.from_bytes(self.pending[2:5], 'big')
            if size > self.max_payload:
                raise ValueError(f'Payload length {size} exceeds capture limit')
            if len(self.pending) < 7 + size:
                break
            frames.append(Frame(int.from_bytes(self.pending[:2], 'big'),
                                int.from_bytes(self.pending[5:7], 'big'),
                                bytes(self.pending[7:7 + size])))
            del self.pending[:7 + size]
        return frames
