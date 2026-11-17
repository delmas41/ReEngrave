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

## Sean's answers on the 12 random written-note tiles (2026-11-16)

All 12 are real notes and all 12 carry the value we wrote (dots included; tile 3 was blue and is right; tile 6 a unison).
Who says: Sean. Limit: 12 tiles cannot show a fake rate below about one in five; it agrees with the judged page
(3 wrong / 373 right notes). `answers-2.311-written.json`; DECISIONS 2026-11-16.

## 12 random red bars read by Sean, and two small tests (2026-11-16)

Tiles `out/print/2.311-redbars` (seed 2311002, 6 per plate, pools 309 Litolff / 269 Brahms without page 0), answers
`answers-2.311-redbars.json`, key and scripts on branch `lane-2.311-redbars-tiles` (399c98770): `redbars_tiles.py`,
`farhead.py`, `dotcheck.py` and their results json.

Sean's reading against the record's first cause (our scoring):
- Brahms 7, 10, 11, 12: "two dotted quarters", tied. Record: one or both written a plain quarter READ (7, 10, 12) or
  narrowed (11); the bar sums short. A printed augmentation dot is not in the record.
- Litolff 1, 2: heads up to the 4th ledger line; record refuses a `clipped_fragment`. Litolff 5: note 3 spaces above,
  `duration_narrowed`, counted 8.
- Litolff 3 (quarter + rest): another staff's marks make a second voice. 4 (one half note, tied): `too_narrow`.
  6 (chord + rest): counted 2.25. Brahms 8: `chord_value_undecided`. 9: `flag_ink_unread`.

Test A -- Sean's hypothesis "red because the notes are far from the staff": NOT SUPPORTED as a general cause. Share of
bars red by farthest kept head: Brahms within staff 14.8%, 1-2 ledger lines 16.6%, 3+ 13.6%; Litolff 11.6 / 14.7 /
19.1% (19.3% on real heads only, 140 bars). Busy bars track red (6+ heads 24-31% red, 1-2 heads 7-11%). All 321
`clipped_fragment` refusals sit on a cell's top or bottom edge; 6 random ones are tips of a NEIGHBOUR staff's head,
rightly refused. Cell pad is 4 staff spaces, 6 where there is room (`measure_extractor.PAD_*`). clipped/too_narrow is the
first cause of 40 Litolff and 35 Brahms red bars (13% each). NOT MEASURED: whether a head beyond the pad (tiles 1, 2) is
ever seen whole by its own staff; the records hold no page-wide boxes.

Test B -- manager's hypothesis "a dot is missed because an arc is beside it": REFUTED as worded. The dot is printed and
clear of the arc; on tiles 7, 10, 12 the detector drew NO box on it (unclassified dot-size ink); on 11 the dot was boxed
and `dot_role_ambiguous`. Brahms: 21 of 276 red bars are quarters-only bars short by half-beats (11 of 16 on page 8);
Litolff 11 of 309. 117 decided augmentation dots have no dot written on a head (not checked). Why the detector skips
these dots: not measured. Note: tiles 7, 10, 12 wrote the undotted quarter PLAIN -- a wrong value, not an unread one.

Who says: the 12 readings are Sean's; the counts are ours from one saved gather per plate.

## Every red bar ranked by first cause (2026-11-16)

Branch `lane-2.311-redbar-ranking` (1fe933a53): `redbar-ranking.md` / `.json`, `redbar_classify.py`. All 585 red bars
(Litolff 309, Brahms 276), rows add up, 32 unexplained (5.5%). Against Sean's 12 readings: 11 agree, 1 partial.
The record's reasons are ours; rows resting on arithmetic only are labelled so in the file.

By family (the manager's grouping of the 38 rows):
- a note's value held or wrong because of its beam, flag or stem, or a chord on one stem left undecided: about 180 (31%)
  -- `chord_value_undecided` 48, `beam_discounted_uncertain` 47, `beams_ambiguous` 41, short with beamed values 23, small rows 22.
  Owner `rhythm.py::adjudicate_duration`; this is the stems/beams lane's ground (2.306).
- rests (a stroke read as a rest, a rest refused, shape and place disagree, a whole rest beside notes): about 85 (14%).
- bookkeeping, not reading (all marks given to another staff 28, a rightly refused neighbour mark filed as a gap 21,
  the same boxes written in two voices 20, edge note 5, double head 3): about 77 (13%).
- never boxed by the detector (heads/rests 46, dots 23): about 69 (12%).
- a narrow mark refused as not a note, or refused as barline/word/dynamic ink: 66 (11%).
- dots decided wrongly or held: 20 (3%). Meter may be stale: 14. Pitch not placed: 12. Other small rows.

Correction: the manager told Sean stems were a small part of red bars (from 12 tiles). The ranking says the
beam/stem/chord-value family is the largest.

## Second 12 red bars read by Sean (2026-11-16)

`answers-2.311-redbars-b.json`; DECISIONS same date. Over his 24 bars (our grouping of his readings against the record):
beam / flag / chord value 7; a neighbouring staff's marks counted here, or far notes 5; a printed dot not in the record 4;
a rest not read 4 (two bars are nothing but a whole rest); a Litolff half note read black or refused 3; unknown 1.
The classifier agreed with him on 11 of the first 12 but only about 6 of the second 12: rows "every mark owned by
another staff" and "refused as barline ink" hid two bars that hold only a whole rest. The ranking's family sizes hold
roughly; its bookkeeping rows need the question "what is printed here that the record does not hold" before a count.

## 2.311 small test: augmentation dots (2026-11-17, STAGED, measurement only; saved `bra-a` / `lit-a` gather, nothing re-gathered)

Diagnosis tested: "dots are lost because the detector never draws a box on them, so some bars go red and a dotted note is written plain and READ."
Scripts: `dotcount.py` (Brahms p0 vs Sean's labels), `dotbars.py` (red bars short by one dot, the look sample, the tiles); results `dotcount-results.json`, `dotbars-results.json`.
They need `redbars.py` / `redbar_classify.py` from `origin/lane-2.311-redbar-ranking` on PYTHONPATH (not on main yet).

**Prior work.** ROADMAP 2.151 landed ON (dot family, `OMR_DOT_BOXED_AS_A_HEAD`; Sean's hand truth 131 dots on Brahms p0), 2.127 aug-dot join and 2.128 dot position (a dot stands in a SPACE right of its head) landed ON;
2.251 step 3 (a page dot finder) PARKED under 2.223; page-facts: a dot is right of the head, in a space, staccato is centred above/below; ink-rules: `adjudicate_dot_role`, `aug_dot_join.py` kept.
Dropped: 2.133 (line removal did not separate wedges from dots). Earlier 2.311 check (`dotcheck.py`): the dot was never boxed and a nearby arc did not hide it.

**Cause and lesson.** Where Sean has labelled (Brahms p0) the detector drew a box on 116 of his 117 dots in swept cells (99%) and 114 reach their note: the dot is not lost at the detector there. The "dots never boxed" diagnosis came from red bars on
other pages, where a dot-sized ink piece beside a plain note plus a bar short by half the note was read as "a dot never boxed". That test is right about half the time and the ink test alone is almost always wrong (below). Lesson: a rule built from
the bar sum plus an ink blob is a witness pair that shares one source (the sum), so it needs Sean's labels or a crop to price it.

**Counts, Brahms p0 (his 117 dots in fully swept cells; his 131 across the page: claim readout 130 hold dot-kind ink, 1 nothing).**
(a) detector box on the dot: 116. Of these 114 attached to their note; 2 sit on notes that were not written at all. (b) boxed but note written with fewer dots: 0.
(c) no box, an unboxed dot-sized ink piece on it: 1. (d) no box, no ink piece: 0.
Cost on his 102 dotted heads: 99 written dotted right, 2 not written, 1 written plain and READ (the one in (c); it sits in a red bar, so not hidden), written plain GUESSED 0. Hidden wrong (plain, READ, bar not red): 0 of 102.
Reverse: notes written dotted that he did not dot: 0 (114 dotted on both).
Ink-only test ("plain READ note, dot-sized piece with no box right of it"): fires on 78 notes of p0, 1 of them dotted by him, 77 not: precision 1 of 78.

**Other frozen pages (no labels).** 585 red bars; short by exactly one dot's worth (a plain note whose half fills the shortfall, with dot evidence): 25 (Brahms 22, Litolff 3), 23 off p0. On p0 the same row fired on 2 bars: one real (the dot above), one wrong (a bar whose
third note he labelled a quarter and we wrote an eighth: no dot).
Seeded 20 of the 23 (seed 2311101), my own look at the crop (ours, not Sean's): dot visibly beside the boxed note 13 (12 Brahms, 1 an unattached boxed dot on a half note), unclear 1, no dot 6 (beamed Litolff groups, a note with an accidental and a rest beside it, a lone note with none).
For the 12 visible unboxed dots no box of any class lies on them (checked): the detector really drew nothing, but the page is not blank for them: each has an unboxed dot-sized piece in the ledger (recall 13 of 13 by construction of the test).
So about 15 of 560 non-p0 red bars (under 3%) come from a missed dot; a dot-ink finder alone would fire on about 1250 plain READ notes of the frozen pages (35 of them in these bars).

**Verdict.** The diagnosis does NOT survive as stated: (1) the detector boxes about 99% of dots where labelled; (2) the wrong-note-written-READ harm is 1 of 102 and that note sits in a red bar; (3) missed dots exist (p8 holds 12 of the 20 Brahms bars) but are a minor share of the red bars.
An ink check (c) finds the missed dots (it is the only witness that sees them) but cannot decide: alone 1 in 78 is a dot; with the bar sum 13 of 20. A dot reader from ink would need shape and place (round, in a space, level with the head, a head-width right) and must stay GUESSED
until measured on Sean's tiles. Not built. Not measured: why p8 misses so many (page-specific detector behaviour); the shape/place test's own precision.

**Tiles for Sean.** `out/print/2.311-dots/` (sheet.png + tile_01..12; key `out/print/2.311-dots-key.json`, outside the folder). Question: "is the boxed note dotted?" 6 notes written plain and READ with an unboxed dot-sized piece right of them (not in a red bar), 6 candidate notes of the bar-short-by-a-dot red bars; mixed in one seeded order (2311104).
Seeds 2311102 (ink), 2311103 (bars). One staff per tile, thin box on the head plus 2 spaces to its right. A neighbouring staff shows at the edge on a few tiles (tight systems, note on ledger lines).
