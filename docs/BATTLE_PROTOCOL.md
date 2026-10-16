# Battle protocol (13.5.1 client) — how the official server drives a battle

Research for server-authoritative combat, 2026-10-16. All addresses are libg
offsets in the supplied 13.5.1 build, read from the saved runtime segments
(`analysis/runtime/game`, `tools/disassemble_runtime.py`). Nothing here was
sent to the tablet; no layouts were guessed.

## Summary

A battle is a **deterministic rollback (lockstep) simulation**. Every client
and the official server run the same simulation from the same initial frame
and the same input events. The server does not send hits, damage, health,
deaths or positions. It sends:

- the input events of every participant, stamped with the frame they apply to
  (28852 / 28855),
- acknowledgements that move the client's own inputs to the frame the server
  applied them at (28853),
- the confirmed frame (28851, 28853),
- **checksums of its own simulated frame** (28854).

The client compares each server checksum with a checksum of its own frame. A
mismatch is treated as a desync (out-of-sync, "OOS"): the client asks the
server for the frame as JSON, then reports the mismatch to the server and stops
accepting server battle events.

Consequence for OpenMoco: the server can only decide combat by running the
**same simulation, bit for bit**, as the native client. There is no message
that sets a monster's health, kills it, or overrides a hit. A Python simulation
that is merely "plausible" would disagree with the client's own simulation;
the client would either ignore the server (no checksum sent) or desync (wrong
checksum sent). See "What server authority needs" below.

## Server -> client battle messages

Router 0x5be224 dispatches them to handlers that queue a battle event
(queue 0x5c2290). The battle updates them in order (0x5c2c34 loop):

| Message | Decoder | Handler | Queued type | Applied by |
|---|---|---|---|---|
| 28851 clock | 0x763028 | 0x5c3268 | 3 | 0x610d78 confirmed frame (already implemented) |
| 28852 events | 0x761770 | 0x5c3470 | 0 | 0x6110ac |
| 28853 input ack | 0x764c4c | 0x5c3578 | 1 | 0x61127c |
| 28854 checksum | 0x761964 | 0x5c3614 | 2 | 0x610d8c |
| 28855 batch | 0x75fc68 | 0x5c3340 | 0 per frame, then 1 per ack | as above |

### 28852 — input events for one frame
Decoder: raw int frame (+0x9c, reader 0x8d764c), then the `events` vector of
typed logic objects (+0xa0, count +0xac). 0x6110ac takes the frame's history
entry (0x71e830), adds each event to it (0x72b374), lowers the rollback frame
(+0x2930) to that frame for events whose +0x10 is 0, and raises the confirmed
frame (+0x2924). The simulation then rolls back and re-simulates from the
earliest changed frame. If the battle is desynced (+0x944) or waiting for
frame JSON (+0x946), the events are destroyed unused.

### 28853 — acknowledgement of a client input
Decoder 0x764c4c: four ints at +0x9c..+0xa8 (the first is a raw int via
0x8d764c; the other three readers are behind unresolved trampolines, so their
wire encoding is not confirmed). 0x61127c(a, b, c, d):
- d raises the confirmed frame (+0x2924);
- c is the sequence of a pending local input; the matching node is removed
  from the pending list (+0x29b0, count +0x29b8);
- b - a is recorded as latency statistics (+0x2a48/+0x2a4c/+0x2a78 buckets);
- if a != b, the client's own input is moved from frame a to frame b
  (0x72b46c) and the simulation rolls back to min(a, b). Moving from a frame
  that is no longer in history logs "failed to move events from an already
  discarded frame" and sets the desync flag.

This explains why the earlier guessed four-integer 28853 crashed or broke
the battle: the values must name real pending inputs and live frames.

### 28854 — frame checksum
Decoder 0x761964: raw int frame (+0x9c), int checksum (+0xa0), then an
optional length-prefixed byte buffer (+0xa8, limit 900000) holding frame JSON.
Handler 0x610d8c:
- frame outside the kept history: log "Received battle frame checksum of
  frame %d that we don't currently have" and ignore;
- a predicted input still pending for that frame: log and ignore;
- client checksum (frame vtable +0x78 = 0x8e56e0) equals the server value:
  store it as the last verified frame (+0x2928);
- mismatch, no buffer: "checksum mismatch! (server:%d, client:%d) -
  requesting frame json"; 0x5c35b0 sends 18853 with frame 0x7fffffff and its
  flag set, and +0x946 blocks further server events;
- mismatch with buffer: "checksum mismatch! reporting to server"; 0x5c3654
  sends 18855 (0x49a7) with the server JSON and the client's own frame JSON,
  then sets the desync flag +0x944.

The checksum (0x8e56e0) runs the frame's complete field serializer (Frame 1200
vtable +0x60: sceneData, frameId, handler with every entity, random, counter,
difficulty, areaEffect fields, debug flags) into a hashing stream (0x8d86f8 /
0x8d89a4). It covers the whole battle state, including the random generator.

### 28855 — batch
Decoder 0x75fc68: repeated (frame, events) groups, then a list of
acknowledged frames, then a trailing int (+0xd0). Handler 0x5c3340 queues one
type-0 event per group and one type-1 acknowledgement per listed frame.

### Client -> server
- 18851 clock, 18853 frame-ready (int frame + two flags; the second flag is
  the "send frame JSON" request above), 18854 controller input (movement.py),
  18852 the client's own input events.
- 18855 desync report (two strings: server JSON, client JSON). Never seen so
  far, because the server has never sent a checksum.

## Logic event types the server may put in an events vector

Logic object factory 0x7eeaec (jump table 0x18cbb8 for 1001..1245). Field
names come from each type's serializer (vtable +0x70; +0x58 is execute).

| Type | Fields | Meaning (from names/strings) |
|---|---|---|
| 1210 | player | player joins (execute places a NewLocationMarker) |
| 1211 | accountId | player leaves (probable) |
| 1212 | character | adds a character ("Character already found in frame") |
| 1213 | accountId | player state change keyed by account (unknown) |
| 1214 | battlePlayerId, c, s, a, stick | controller input |
| 1215 | battlePlayerId, newLevel | level up |
| 1216 | battlePlayerId, debugEventType, param | debug event |
| 1217 | battlePlayerId, xp, questSpeciality, dropCoins | XP grant |
| 1218 | mapEvent | spawn a map event (invasions; needs LogicOpenWorldHandler) |
| 1219 | value, replacedChar, newChars, newCharWeights | character replacement table |
| 1220 | FileName, Row, Column, ArrayIndex, NewValue | CSV value change |
| 1221 | accountId, battleKit, skins, dyes, xpLevel, battleKitLevel, gears (+update flags) | player update |
| 1201 | events | event container |

Types 1230..1236 are entity sub-objects (buffs with damage/source, resource
drops, ...), not events. Every one of these events is executed inside the
deterministic simulation on all participants; injecting one changes the
simulation for the client and therefore must also be simulated by the server.
None of them reports a kill to the server.

## What server authority needs

Because outcomes are never transmitted, a server that decides kills, rescues
and XP has to run the native battle simulation itself:
1. Port the logic deterministically: frame/entity model, fixed-point math and
   the frame `random`, characters and gear, monster AI, skills, projectiles,
   buffs (1231), zones and their spawn logic (0x74ea90), civilians,
   pathfinding/collision on the map data, loot (1232) and XP events.
2. Feed it the same input events as the client (18852/18854 -> 28852/28853).
3. Prove agreement with 28854 checksums every frame (the client's own
   0x8e56e0 hash of the full serialized frame). Any difference desyncs the
   client.
4. Only then derive kills/rescues/XP from the server's frame.

The battle logic occupies roughly the 0x6b0000..0x7f0000 range of libg
(hundreds of thousands of instructions). Without source or a reference
server, step 1 is a full reverse-engineering port, and nothing can be verified
on the tablet until the entire frame hashes identically, because the checksum
covers everything at once.

Unknowns still open: the three unresolved 28853 int encodings; the 18855 and
frame-JSON formats; whether the official server ever sends 1216 debug events;
how 1217 XP grants interact with the empty client level table (see
"In-battle XP bar" in PROJECT_STATUS.md).
