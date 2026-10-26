# Next task (temporary file; delete it when the task is finished)

Written 2026-10-26 by Claude at the user's request. The user wants this done
as soon as they are back with fresh usage limits (their 5-hour limit reset),
without being asked first. Claude can't watch usage limits itself; this file
works because CLAUDE.md points every new session here.

## What to do when you read this

1. Start straight away. Don't ask whether to begin, and don't stop to ask
   between steps (CLAUDE.md: keep going, push every verified checkpoint,
   partial ones included). Ask only before starting a separate new session
   (the user's global rule); helper subagents for research inside this
   session are fine.
2. Tell the user in one line that you're starting the task from next-task.md.
3. Read AGENTS.md and the newest sections of PROJECT_STATUS.md first.
4. Do the task below, then the queue after it, in order.
5. When the task below is finished and verified, delete this file (or move
   the next queue item up into "The task" if the user wants to keep going),
   commit, and push.

## The task: shop offers

The COOL zone's SHOP opens but is empty. Goal: the SHOP screen lists offers
the server provides, and buying one with an in-game currency works and is
saved by the server. Real-money purchases stay out of scope (never charge
anything; billing must stay disabled in the test client).

Where to start (findings so far, see PROJECT_STATUS.md "Next: server-side
jobs, mission quests and chaos cores" and the COOL zone section):
- Offers are server data. Client tables: analysis/csv/csv_client__shop_items.csv,
  csv_logic__shop_panel_layouts.csv, csv_logic__pricepoints.csv,
  csv_client__billing_packages.csv, csv_meta1__m1_shop_items.csv.
- The shop is a COOL zone HomeItem; the MERCH SHOP feature unlock is
  6300009 (command 583, decoded but not persisted).
- Find where own-home (or another message) carries the shop's offers: look
  for the shop screen's data source in libg the way the daily goal was
  found (strings like "shop", TID_SHOP_*, then the reader, then the
  decoder). Tools: tools/disassemble_runtime.py and the scratch helpers
  described in PROJECT_STATUS.md (runtime dump analysis/runtime/game,
  base 0x7b460ae000).
- Purchases will arrive as a client command; any unknown command makes the
  server drop the whole client turn, so decode it in commands.py.

Verify on the tablet (normal build, adb input with the foreground check in
CLAUDE.md): the SHOP lists offers, a purchase works, and the result survives
a relaunch. Back up .local/accounts.sqlite3 before any test that changes the
real account, and restore it afterwards.

## Queue after the shop

1. P.E.R.K rewards for finished daily goals: the popup's "Finish a total of
   <VALUE> Daily Goals" line needs completionRewards in the daily goal event
   (entries: points, firstItemOfLoop, a polymorphic reward object;
   claim command 603). Needs a reward type that exists on the server.
2. A release soak (more than 4 clean battle/home cycles) and, if the user
   wants it, a new public client release (only if the APK changed; the
   recent work was server-only).
