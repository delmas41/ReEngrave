# Note-loss funnel -- ROADMAP 2.311 (diagnosis, 2026-11-16)

STAGED, main with default flags. Measurement only; no reader changed. Written by the manager from the
measurement agent's report (the agent's own FINDINGS write was refused by the worktree hook); scripts in
this directory, branch `lane-2.311-note-loss-funnel` b44b81ca6.

**Why.** Sean: "Correctly diagnosing the problem is my main concern now." Three stems rounds and three arc
rounds each ended at "the notes handed to the reader"; nobody had measured it against truth.

**Truth.** Sean's hand-labelled Brahms page 0, ONLY the 104 measure cells he swept completely (382 heads).
Limit: 369 of those 382 heads are the detector's own boxes he confirmed, so "never boxed" cannot be measured
from this page. No fully judged Litolff cell exists.

## 1. The count: wrong / right / unread (Brahms p0, product file today)

note 3 / 373 / 9 - note value 4 / 369 / 9 - rest 1 / 15 / 1 - accidental 4 / 31 / 2 - dot 0 / 114 / 5 -
stem (record's direction) 5 / 359 / 16 - beam 22 / 161 / 2 - flag 19 / 32 / 0 - tie 4 / 33 / 8 -
slur 26 / 29 / 9 - clef / key / meter 0 wrong, 11 / 6 / 10 right.

- **On this page the notes are not the loss: 98 of 100 printed notes are written, values right.** The loss is
  in the marks between notes: slurs (26 wrong: 10 a second arc on the same two notes, 15 matching no labelled
  arc -- 5 of 6 crops a real slur with a wrong end), flags/beams (20 notes printed with a flag are written
  beamed, 5 of 5 checked real), ties (8 unread).
- Note wrongs: 1 tremolo slash written as a note; 2 real heads Sean did not box (label gaps). Unread notes,
  first stage: one box for two heads 3, value held 3, refused as not a note 3.
- Who says: Sean's labels for the marks; every ATTACHMENT (stem/beam/flag/dot/accidental to a head) is the
  scorer's own geometry, print-checked and corrected four times. Pitch is not scored (his labels carry none).
  Values are coarse (half / quarter / shorter + dots). Not scorable by place: ledger lines, barlines, words,
  dynamics, braces, tremolo.
- **Paused readers, same page, one gather per arm:** stems ON (25c244dac) stem wrong 5 -> 4, right 359 -> 367,
  unread 16 -> 9. Arcs ON (f0c9e499f) slur wrong 25 -> 18 (double arcs 10 -> 4), tie wrong 3 -> 2, unread
  unchanged. Nothing worse; neither touches the flag-written-beamed notes or the wrong-ended slurs.

## 2. Why a red bar is red (20 random red bars per plate, by crop; Brahms 276 red bars, Litolff 309)

Brahms / Litolff: a whole or bar rest not read 5 / 3; real notes whose value is held in doubt 4 / 4; every
mark written but the values do not add up 2 / 9; a real note refused as not a note 2 / 1; pitch unread after a
mid-bar clef change 1 / 0; a real note never boxed 0 / 1; cannot tell from the crop 6 / 2.
The agent's look, not Sean's. The record-only tally over ALL red bars was withdrawn (matched the crops on only
11 of 20 Brahms bars: it blames rightly refused slivers and neighbouring staves' notes in the cell's padding).

## 3. Noise floor

Same page set, two gathers: identical files (the detector cache makes that part identical by design). A page
gathered ALONE vs inside a larger run differs: Litolff p1-2, 39 pitches and 92 blue marks, mostly two staves.
**22 of the stems lane's 29 gathers ran with Surya not installed** (no `.venv-surya` link in that worktree):
staff names could not be read there -- a likely part of the "gather variation" 2.306 r12 reported.

## 4. Process lessons

- The page we tune and check on most is the page we read best; the hand truth says notes are fine THERE and
  cannot say whether they are fine elsewhere. Red bars (the visible loss) are about rests, held values and sums.
- `lane_report.parse_symbols` reads every beamed chord member as a flagged note (53 of 228 short notes on
  Brahms p0): every flag/beam count in past lane reports inherits it.
- A lane worktree without the OCR link silently reads no staff names; the lane's numbers then measure that.
- Sean's tile answers are biased toward what lanes have since fixed: they guard regressions, they give no rate.

## 5. How to run the count for any lane

`PYTHONPATH=. python3 benchmarks/note-loss-funnel-2026-11/extract.py REC.record.json REC.facts.json` (from the
tree and flags that made the record), then
`PYTHONPATH=.:benchmarks/note-loss-funnel-2026-11 python3 benchmarks/note-loss-funnel-2026-11/judge.py REC.facts.json`.

## 6. Open

12 random written-note tiles (seed 2311, 6 per plate) in `out/print/2.311-written`, with Sean. Smallest extra
labelling with the largest payoff: one Litolff page swept all-ink; then the 8 unswept Brahms p0 cells.
