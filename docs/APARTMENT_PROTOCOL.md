# Apartment implementation research — 13.5.1

The test client renders the apartment, plays the intro movie and dialogue, and
reports tutorial advancement. The current frame has no player or character;
the screenshot shows Luna's portal prompt over an empty apartment. Movement,
weapon pickup, and entering the portal have not been implemented or verified.

## What the client already supplies

The locally inspected `tutorials.csv` and `tutorial_steps.csv` define this
sequence. IDs below are typed references resolved from captured commands and
the supplied build's tables, not message IDs.

| Tutorial | Step | Action and client behavior |
| --- | --- | --- |
| Initial 15600000 | SetAge 14200000 | Age screen; player animation `Intro Idle` |
| Initial | IntroAnim 14200001 | `ShowIntro` plays the bundled intro movie |
| Initial | TakePhone 14200002 | `Intro Phone Pickup`, 1000 ms |
| Initial | FirstMessage 14200003 | `OpenMainQuests`, then wait for next tutorial |
| Portal 15600001 | Portal 14200004 | 1000 ms; `Intro Phone Idle`; `PortalAppear` music parameter |
| Portal | PortalOpen 14200005 | `WaitForCharacter`; portal changes from hidden to inactive |
| Portal | unnamed continuation | 7500 ms; look at `pf_keyitem_portal`; `Intro Bat Pickup` |
| Portal | GoToPortal 14200006 | Luna's prompt; portal pulses, then controls guide and movement/skill controls |

The actual session reported steps 0, 1, 2, 3, Initial completion, then Portal
steps 4, 5, and 6. The client reached these without new server cutscene messages.
This does not establish that the missing character performed the animations.
Use the existing animation and tutorial state machinery; first supply its
required scene/player state. Do not replace these with invented animation RPCs.

## Decoded client commands

16543/v0 contains a compact frame integer, raw 64-bit client time, compact
command count (native limit 512), then commands with raw 32-bit type IDs.
Base fields `t`, `g`, and `aid` are optional compact 64-bit values, default 0.
Their presence bits share bytes across scalar fields and command boundaries.

| Command | Evidence | Fields |
| --- | --- | --- |
| 574 | serializer 0x6866b8 | tutorial reference (class 156), step reference (class 142); step 0 appeared on completion |
| 575 | 0x688590 | step reference (class 154); exact quest semantics remain under investigation |
| 576 | 0x6849c8 | step reference (class 154); observed when the dialogue was completed |
| 524 | 0x685528 | optional compact `key` and `value`; key meanings remain unknown |
| 541 | custom decoder 0x684d68 | raw age integer after base fields |
| 560, 572, 591 | native serializers | base fields only; execution meanings remain unknown |

`commands.py` reads these layouts without executing them. Unknown types stop
decoding because commands have no independently known byte length. The private
capture inspector reports aggregate counts and tutorial references; it omits
age values, account IDs, and credentials. It decoded every observed turn in
the live session, including batches spanning multiple presence-bit bytes.

## Implement in this order

1. **Spawn the local player and character in the scene frame.** Scene-start
   23491/v0 contains SceneConfig 1003 and Frame 1200. Inspect the frame's object
   manager (0x72de54), its object collections, and reference allocation before
   inserting objects. Player type **2009** is allocated by 0x7eeccc and
   initialized at 0x73512c; serializer 0x736218 -> 0x7358c8. Character types
   **2001/2002** use 0x6dfb7c and serializer 0x6e22e8 -> 0x6e0258. The correct
   character variant, object IDs, collection indices, spawn coordinates, and
   allocation/reference format must be verified, not guessed.

   Entity base 0x72b8b0 has `replicated`, x/y/z, and rotation. Player metadata
   (0x73ab98) has accountId, battlePlayerId, name, tutorialStep, and
   currentBattleKit. Player runtime state has a character reference, health,
   and characterX/Y/Z; character state has a data reference and movement.
   The supplied Player character row uses `sc3d/pf_player` and movement speed
   350. Use the validated local guest ID and SmartBow 6700000; do not treat a
   battle-kit reference as a character reference. Verify a visible character
   before progressing to movement.

2. **Persist tutorial and quest state.** Validate decoded commands against the
   authenticated local guest and resolved table references. Derive the
   client-home tutorial collection encoding used by native 574 execution
   (0x686754, home collection +0x118), then send that same state on reconnect.
   A parser or receipt acknowledgement alone does not execute these commands.
   Preserve unknown commands and reject unsupported mutations.

3. **Capture and implement movement events.** A joystick drag in the empty
   apartment produced no 18852 frame. Repeat after a visible player exists.
   Native 18852/v0 decoder 0x765528 reads two integer fields followed by a
   structured `events` vector. Event type **1214** carries battlePlayerId,
   fields `c`, `s`, `a`, and a `stick` vector (0x71c6f4 / 0x7e55f0).
   Meanings, axes, units, and action bits require actual input captures.
   28852/v0 decoder 0x761770 reads a raw integer plus an `events` vector;
   its handler and simulation semantics still need verification. Receipt
   acknowledgements in 28851 currently keep the connection alive, but provide
   no authoritative movement or collision simulation.

4. **Finish weapon pickup and portal interaction.** The tutorial controls
   animation, visibility, and pulse states. Trace the client scene's key-item
   lookup and collision/interaction trigger once a character is present.
   Determine which key-item objects are instantiated by the client versus
   supplied in the frame. The bundled portal prefab is evidence of an asset,
   not proof of a server object or interaction message layout. Validate the
   destination against the tutorial's forced `TutorialAreaBasic` scene, then
   build a valid destination frame and send the evidenced scene-start message.
   Do not mark portal travel complete until the tablet actually enters it.

5. **Verify animation transitions and reconnects on the tablet.** Observe phone
   pickup, portal appearance, weapon pickup, movement within the apartment,
   portal entry, and resumed tutorial state. Keep the background server running
   throughout manual testing. Full gameplay follows these milestones.

All addresses and IDs above are specific to the supplied 13.5.1 client.
Original archives remain intact. Extracted tables, screenshots, runtime dumps,
and raw captures stay in ignored local directories.

During the longer research session the client also displayed its own
`Connection Idle` policy dialog. Server listeners remained alive. Warm retry
opened zero-byte sockets; relaunching only the test package restored encrypted
login. Investigate the native AFK policy and warm reconnect separately from
the already-fixed 35-second confirmed-frame gap. Do not claim that keeping the
listener open disables the client's inactivity policy.
