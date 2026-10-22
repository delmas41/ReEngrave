# Pre-registered, before a single Part B arm was run

Written after Part A's first six page-runs and **before** `run_arms.sh` was
invoked, for the reason the cleanup count's `CATEGORIES.md` was committed
alone and first: a prediction written afterwards fits itself to what was
found, and commit order is the only form of that claim a later reader can
check.

## The numbers this rests on

**Part A (this session, 6 of 12 page-runs at the time of writing).** One
margin-label read, no detector, `OMR_SURYA_KEEP_ALIVE=0`, no resident server:

| | page 1 (12 staves, 1 system) | page 2 (22 staves, 2 systems) |
|---|--:|--:|
| text layer | 0.08 s, **0 labels** | 0.10 s, **0 labels** |
| Surya, first spawn | 17.9 / 17.4 / 17.4 s, 12 labels | 16.3 / 17.1 / 16.8 s, 14 labels |
| Surya, second spawn *same process* | 17.8 / 17.2 / 16.6 s | 16.6 / 16.5 / 16.8 s |
| Tesseract | 0.86 s, 12 labels | 1.49 s, 14 labels |
| **attributable (Surya + Tesseract)** | **18.8 / 18.2 / 18.3 s** | **17.8 / 18.6 / 18.3 s** |

**The committed 2026-09-11 pair**, arithmetic re-derived here from the
`.timing` files rather than taken from the scope: 10:48:18 → 11:14:38 =
**1580 s** with no flags; 19:23:10 → 19:54:12 = **1862 s** with
`--surya --ocr`. Difference **+282 s over 4 pages = 70.5 s/page, +17.8%**.

## The prediction

`--surya --ocr` adds exactly ONE Surya spawn and ONE Tesseract read per page
— the direction reader already spawns Surya on every page under
`OMR_DIRECTION_TEXT`, which is on by default in both arms. So:

> **L − C should be ≈ 18.3 s/page ≈ 73 s over the four pages.**

If Part B reproduces the 09-11 pair's **282 s** instead, the attributable
number is *not* the whole story and something in a real gather costs more
than the rung does in isolation — and that residue is the finding, not the
flag.

## What would distinguish the two outcomes

| result | reading |
|---|---|
| L − C ≈ 70–80 s | the 09-11 pair's residue was its own confounds (different trees — the control ran *no* label rung at all — plus the shared-server queueing of that same day). Part A is the number. |
| L − C ≈ 280 s | the rung costs 4× more inside a gather than alone. **Do not flip** until that is explained; the first suspect is a second Surya consumer interacting, which the LD arm is built to see. |
| L − C < 0, or the L1/L2 spread ≳ the L − C gap | the machine's own noise floor dominates and neither number means anything. Report the spread, flip nothing. |

## Two things already settled, and neither depends on Part B

1. **The model load is NOT shared between calls in one process.** Two
   consecutive `read_staff_labels_surya` calls cost 17.9 s and 17.8 s. So
   the per-page cost is per SPAWN, and scope §7's single-subprocess merge is
   worth ~17 s/page — *more than the flag itself*, whichever way Part B goes.
2. **The cost does not scale with the page.** 12 staves / 1 system and 22
   staves / 2 systems both cost ~17 s. The "1.5 s per system" term is real
   and is noise beside a fixed ~16 s spawn+load.

## The decision rules are §9's, unchanged

Flip both ON if Part A median attributable ≤ 30 s/page, max ≤ 60 s over the
12 page-runs, **and** Part B's L − C ≤ 25 % of C or within the ABAB noise
floor. Part A's median is already ~18.3 s and its max so far 18.8 s, so the
first clause is on track to be met; **the decision rests on Part B.**
