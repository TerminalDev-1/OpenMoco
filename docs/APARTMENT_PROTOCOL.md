# Apartment implementation research — 13.5.1

## Warm transition repair — October 14, 2026
13223/v0 `00` must first receive 24548 own-home. The normal client then sends
13222/v0 with flag true, scene 10900005, auxiliary 0/0, references 0/6700000.
Only then send the existing Home apartment snapshot; this restricted mapping
does not implement the SocialHub/COOL scene or its unlock requirements.
Sending both responses immediately froze warm transitions; a one-second delay
was inconsistent, and omitting the home profile caused a native null crash.

Empty 13224/v0 follows scene loading, before the new scene's 18851/18853 pair.
Factory constructor 0x7637d0 and getter 0x763804 identify this empty type;
native caller 0x60ea10 emits it. Treat it as the acknowledgement boundary:
ignore old ready frames until this message, reset confirmed frame, and send a
28851 acknowledgement for the first new 18853 using the most recent clock echo.
Waiting for another clock request can leave the client at its prediction limit.
Fresh snapshots also require a fresh server simulation clock; retaining the
connection clock fast-forwarded later scenes thousands of frames and left
actors frozen or absent. Preserve the echoed client clock while resetting the
server elapsed clock for each new scene.

## Verified portal checkpoint — October 14, 2026
Continuation: authenticated 574 updates persist home +0x118 tutorial/step pairs,
encoded as raw 64-bit references by 0x7969a0. Reconnect restores these entries
and the last supported scene. Native re-encoding of the restored 196-byte profile
matches Python exactly, and the tablet resumes without replaying its intro.
The map hit target is hidden in tutorial scenes by battlehud 0x499b0c; the local
bootstrap overrides that predicate only at this UI call site. The actual map
Leave Battle control emits 13223/v0 with `00`; Python returns saved 24548 plus
23491 apartment and persists the home scene. Real return-home travel is verified.

The normal client now renders the apartment player, bow and HomeItem 2010 portal.
The user confirmed entering Downtown Chaos, with screenshots showing the player
and recruits and captures showing subsequent movement. The older ordered plan
below records the research sequence; its player/portal milestones are complete.
13222/v0 selection 10900001 triggers an encrypted 23491/v0 tutorial frame of 498
bytes. Both player identities are bound to the authenticated local account.
Repeated requests do not duplicate scene-start responses.

The native tutorial map is `server_scene/tutorial_oa00_basic_v3.map_bin`, with
spawn tile (60,72), centered coordinates (3964928,4751360). A selected battle-start
configuration replaces the empty default: 65 bytes rather than 54. The original
487-byte template keeps its last four bytes; the metadata begins 58 bytes from
the end. Python's full result matches the native encoder byte for byte. The
selection decoder is 0x77a54c; 0x77a46c is its encoder. The empty selection caused
the earlier 0x486150 crash; the corrected normal path enters the destination.

The local-network client suppresses signature-checked automatic idle closure
at 0x7fe3d8 and keeps its foreground screen awake. Neither prevents physical
network/ADB loss. The Python server acknowledges received frames and decodes
movement; authoritative simulation, full quest persistence and return travel
remain unfinished. Native animation and NPC behavior are not proof of those
server implementations. Current evidence and tests are in PROJECT_STATUS.md.


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

The native home.map_bin asset decoder identifies a spawn layer with the UUID
for logic_assets/spawn. Its sole packed coordinate is 0x00430016 (tile 22,67).
The native OpenWorld caller centers tiles with `(tile<<16)|0x8000`, giving
(1474560,4423680). The same map has key-item tags for wardrobe, portal, and
weapon loadout at (1684275,4502323), (1500774,4561305), (1331761,4538660).
These are map entries, not proof that the corresponding frame entities exist.

scene.py supplies a constrained native-derived starter template with two
dynamic local account identities. A decoded message's byte stream must be
reset before re-encoding: the initial 599-byte probe result retained an empty
112-byte scene and failed to render the player when sent from Python. Resetting
the stream with 0x8d7b2c produces the standalone 487-byte scene. All research
flags remain disabled in release APKs.

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

   Once the native player probe populated the frame, the tablet sent **18854**.
   Decoder 0x76536c reads raw frame and sequence integers, then 0x71ca2c reads
   a compact controller field and stick (0x7e5898). Stream slots +110/+f8 are
   compact signed32/signed byte. The stick header stores strength as
   (signedHeader+128)>>3, mode in bits 1..2, and presence in bit 0. An absent
   stick has zero axes; mode 2 reads two compact coordinates; other present
   modes read a signed angular byte. movement.py decodes this without executing
   it. 28854 is a different layout: raw frame, raw sequence, length-prefixed
   byte buffer (limit 900000); do not echo the input payload into it.

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

## Initialized monster checkpoint (October 14)

The native-derived tutorial frame now contains one DragonlingWeakMeleeTutorial
(character data 10800020), initialized with five default gear entries and
health/base health 624. Helpers 0x696d20, 0x6f1148, 0x6f0ec8, 0x6f18a0 and
0x703c60 fill the gear and health fields after factory/placement. The initial
position (3964928,4882432) is two tiles south of the player spawn. The resulting
650-byte body binds two account references dynamically at offsets 50 and 480;
the synthetic-account SHA-256 is
`de824bed3661cbe4a620754408e30d56e54f6233a3e16b7e7dda8413bb215356`.

The user verified that the monster renders and takes damage, but flees quickly.
Native client simulation currently drives that behavior. Python supplies the
initial snapshot and frame acknowledgements; authoritative combat, repeated
spawns, death rewards and inventory changes are still to implement. A regular
dragonling experiment loaded but did not verify a better fight, so it is not
used in the normal server snapshot. Tutorial completion is not fabricated.

## Populated street checkpoint

`populated_tutorial_scene` replaces the single-enemy body on normal portal
entry and saved-scene reconnect. The final native-derived frame is 3104 bytes:
twelve enemies (one 10800020, eleven 10800021) and six civilians (10800092).
`0x63be18` initializes gear, health/base health, initial spawn IDs and frame
registration; its native caller selects faction 1 for character types >16,
otherwise 0. Enemies start at 624/1890 health, civilians at 5000.

The first groups were behind the starting truck/buildings. Moving down the
screen decreases world Y. Corrected groups follow the open street at X
57.5..63.5 and Y 57.5..70.5, with civilians interspersed at X 58.5/62.5.
Native placement `0x6dfea0`, recalculation and base-health copy normalize their
state before encoding. Dynamic account references are at 50/2934 for the
synthetic test identity. The full native golden SHA-256 is
`a1d45249710edf1c43aaa6b9f6926016d6d13a98b6b048dd59a848558d5007a2`.

Hands-off native observation shows civilian health falling from 5000 through
4040/3080/2120/200, verifying monster attacks. The normal client renders Spirit
civilians and dialogue from Python's final snapshot. Client simulation drives
combat and recruit behavior; Python does not yet maintain authoritative kills,
rescues or rewards. These are initial encounters refreshed on entry/reconnect,
with continuous spawning still to implement.
