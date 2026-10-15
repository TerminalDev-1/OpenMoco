"""Hunter-name screen messages (tutorial 15600002, step 14200011).

Pressing SIGN sends 17582/v0 (native ctor 0x76c31c, sender 0x5b28c8):
a string name followed by a boolean the sender sets to 1 (0x76c35c).
The popup then greys SIGN until the server replies.

28350/v0 is the reply the client dispatcher (0x5be8b8) routes to the
name popup (0x4e492c). Its decoder 0x75e8a4 reads boolean +0x99,
big-endian int +0x9c (0x8d764c) and string +0xa0. A false boolean calls
the popup's success slot (0x5bf2f4); true maps the int (codes 1..6,
table 0x75e5cc) to an error text and re-enables SIGN. The meanings of the
individual error codes are not known yet, so this server only accepts.
"""
from stream import Reader, Writer

NAME_CHANGE = 17582
NAME_CHANGE_RESULT = 28350
MAX_NAME_BYTES = 60  # Command 14 decoder 0x688e9c reads at most 60.


def decode_name_change(payload):
    reader = Reader(payload)
    name = reader.string()
    flag = reader.boolean()
    if name is None or reader.remaining:
        raise ValueError('Unexpected name-change layout')
    return name, flag


def name_change_result(name, failed=False, code=0):
    return Writer().boolean(failed).integer(code).string(name).bytes()
