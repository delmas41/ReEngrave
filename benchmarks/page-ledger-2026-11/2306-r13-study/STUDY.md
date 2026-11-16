# 2.306 round 13 -- stems: what the old reader does that the new one does not (study, 2026-11-16)

STAGED, both readers. No reader, flag, ROADMAP or DECISIONS line changed. Branch `lane-2.306-r13-stems-study`
(cut from `lane-2.306-stems-beams-page` 25c244dac). Sean asked: *"what the differences are between the old
reader and the new reader, and why the old reader is still working better in certain areas ... Real diagnosis
before any fixes."*

- **OLD** = the cell stem finder (`tools/omr/line_detection.py::detect_stems`, filed as `Q.STEM` by
  `gather_cv_lines`) + the cell join (`adjudicators/stem_value.py::adjudicate_head_stem`, test
  `geometry.stem_touches_head`) + the direction reader (`rhythm.adjudicate_stem_direction`).
- **NEW** = `tools/omr/staged/page_stems.py` on the page stroke map (`page_strokes.py`, `stroke_map.py`).

**How it was measured.** ONE gather per plate: the stems lane's r12 flag-ON gather of the 8 frozen pages
(`2306-r12-lit/-bra.record.json`, tree `2306-tree-r12`, whose `page_stems.py` is byte-identical to the branch
tip) and that lane's own OFF/ON replays of it (`r6/rf12-*.json`). OLD's answer = the OFF arm's verdicts; NEW's
= the `Q.PAGE_STEM` rows as gathered. Nothing was gathered for this study. NEW was also re-run offline from
the record's rows (`replay.py`): it gives the gathered answer for 96.6% (Litolff) / 99.4% (Brahms) of readings;
the one approximation is the accidental boxes (box share instead of the ink mask).

## The answer

OLD does not read stems better. It asks less. OLD's question is "does a tall thin vertical's box touch this
head's box?" -- any side, every box that touches gets the stem, no other mark's claim is consulted, and the
direction is worked out afterwards from which end of the box sticks out. NEW asks "is this THE stem of THIS
head": at the head's side, one direction per stroke, one candidate, not ink another reader has claimed. Where
OLD stems and NEW refuses (130 Litolff / 55 Brahms heads) the stem's ink is in NEW's page map in most cases:
OLD's own touch test, run on NEW's ink, names OLD's stem for 74 of 130 and 45 of 55 (`swap.py`).
And OLD is right less often than the count suggests: in a random 30 per plate of those heads, 8 and 8 are not
notes at all by my look (a beam, an f / sf / pp, a clef, rests, tremolo slashes), and OLD writes 5 and 6 of
them into the file as notes. Against Sean: on his 58 judged stem places OLD is right on 34 and NEW on 48; on
his hand-labelled Brahms page 0 they are level (351 vs 350 of 375).

## Q1. How each reader works

**OLD, step by step (code).**
1. Picture: one measure CELL of one staff, cut from the page and enlarged about six times (a staff space is
   ~15 page px on Litolff, 100 px in the cell), staff lines erased (`cell.image_no_staff`), re-thresholded.
2. Candidates: everything shorter than 1.6 staff spaces vertically is wiped (a vertical opening); each
   connected piece left is a candidate. Kept if 2 to 8 spaces tall, at most 0.6 wide, at least 3:1, and not
   within 0.8 space of the cell's left/right edge (unless one end stands in a head box). A piece too WIDE is
   searched for the thin stem inside it (`thin_run`). A stroke lying inside a detector box of a clef, key,
   digit, accidental or rest is dropped; two close verticals are dropped as an accidental's pair unless one
   ends in a head.
3. Tie to a head (ADJUDICATE, per head box): every stem row whose BOX touches the head's detector BOX (within
   0.12 of the head's height) is "touching". One -> that is the stem (`one_stem`). None -> no stem (or the
   second's partner rule). Several -> reach out of the head, then the side named by the direction, then the
   flush test, then one-stem-per-head; else narrowed (`two_stems` / `unison_two_voices`).
4. Direction (separate decision): the stem box against ALL head boxes it overlaps -- whichever end sticks out
   further is the way it points. The side of the head is not used. No stem: a beam-mate may lend a direction.
5. Chords: each head asks alone; heads that name the same stem row are a chord afterwards. Two voices: only
   via step 3's narrowing.
6. Refuses: only "no row touches" or "two rows and no tie-break".
7. Hands on: the stem row id (join), the direction, and the cell rows the tip / beam readers measure on.
8. Claims: nothing. A `Q.STEM` row is a box in cell pixels; no ink is named, nothing is put on the page
   ledger (in the record every `stem` claim is NEW's). The same stem seen from two cells is two rows.

**NEW, step by step (code).**
1. Picture: the PAGE stroke map: page pixels reduced to at most 16 px per staff space, staff lines erased
   inside each staff's band; ink already split into strokes (vertical >= 1.5 spaces / horizontal / curve /
   blob), fused pieces cut at their joins (a stem is cut from its head; the head keeps the stub).
2. Candidates: vertical strokes no earlier claim holds (page-stroke claims, READ area claims -- barline, clef,
   key, meter, word, bracket -- and strokes half inside a detector accidental box). Pieces in one column are
   joined into one stem across an erased line, a covering chord head, a second, a crossing stroke
   (`join_runs`). No upper length limit.
3. Tie to a head (the 2.290 page head: its ink oval, else its strongest box): the stem's centre line within
   0.4 space of the head's RIGHT edge and running 1.5 spaces up, or LEFT edge and 1.5 down, its head end
   within 2 spaces. Else, since r11: the stem's column touches the head's own ink (through chord mates), side
   from the column against the ink's middle; at the middle -> abstain.
4. Direction: the side IS the direction (right = up, left = down).
5. Chords / voices: heads on one stroke are a chord. A stroke read up by one head and down by another is
   given to the side whose heads have head ink / stand at its head end, else nobody gets it
   (`stroke_read_both_ways`). One up and one down candidate -> `two_voices` (settled only for a clean pair).
   A head on the stroke's other side next to a holder -> the second's displaced head.
6. Refuses: no stroke / held by another claim / two candidates / both ways / contact at the middle.
7. Hands on: per head the stroke, direction, side, candidates and margin; a cell `Q.STEM` row (the cell
   reader's own row on that stroke, else a view) for the old tip and beam readers.
8. Claims: each stem's page strokes, once, owner `stem`.

**The differences, one sentence each.**
- D1 PICTURE. OLD re-reads each cell's enlarged crop; NEW only sees the strokes the page map kept, cut where
  the map cut them.
- D2 WHAT A CANDIDATE IS. OLD: 2-8 spaces tall, away from the cell edge, never inside a detector box of
  another mark. NEW: any free vertical of 1.5 spaces or more, any length.
- D3 THE TIE. OLD: the two BOXES touch, either side, anywhere along the stem. NEW: at the head's engraving
  side (box edge +-0.4 space) or touching the head's own ink off its middle, with reach and head-end tests.
- D4 ONE STROKE, ONE DIRECTION. OLD lets every box that touches a stem have it; NEW gives a stroke one
  direction and refuses all its heads when two boxes read it opposite ways.
- D5 UNIQUENESS. OLD rarely sees two candidates (its finder already dropped pairs and short strokes); NEW
  sees every vertical piece and abstains on two.
- D6 CLAIMS. OLD consults no claim (only detector boxes, at 80% / 50% inside); NEW may not take a stroke any
  earlier claim holds.
- D7 DIRECTION. OLD: which end of the box sticks out past the heads; NEW: which side of the head.
- D8 LENGTH. OLD refuses a vertical over 8 spaces and one at the cell edge; NEW has neither limit.
- D9 INK. OLD holds a box and claims nothing; NEW holds named strokes and claims them once.
- D10 HEAD. OLD uses the detector box of each glyph; NEW uses the 2.290 page head (oval), and inherits it.

**Code against docstring (findings).** `rhythm._stems_on` and `adjudicate_stem_direction` say "box overlap
with NO tolerance / NO CONSTANT"; the code calls `stem_touches_head`, which adds 0.12 of the head's height.
`detect_stems`' docstring says the opening kernel is one line spacing; the code uses 1.6. `gather_cv_lines`
says the notehead gate on the pair rule is "default ON since 2026-11-02"; `stem_notehead_gate_enabled`
defaults OFF. `page_stems`' module doc describes only the edge test; the contact pass (r11) is the larger part
of the code.

## The population (our own output; `census.py`)

Real heads of their own staff: Litolff 4,552 / Brahms 4,810.

| | Litolff | Brahms |
|---|---|---|
| both stem (direction agrees) | 3,827 (3,756) | 4,532 (4,499) |
| OLD stems, NEW refuses | 130 | 55 |
| NEW stems, OLD names none | 180 | 117 |
| NEW says two voices (OLD stems / OLD none) | 88 / 213 | 20 / 59 |
| neither | 114 | 27 |

(The lane's retire blocker is 136 / 55; mine is 130 / 55 because OLD is taken from the OFF arm.)

## Q2. OLD stems, NEW refuses: by the difference that decides

**Swap experiment (`swap.py`, all 130 / 55, our own output).** OLD's touch test on NEW's whole vertical runs:
one run touches, in OLD's column, free 62 / 34; the same but another claim holds it 12 / 11; several runs
touch 19 / 4; no vertical run of the page map touches the head box 28 / 4; other 9 / 2. So for 57% / 82% the
ink is there and the RULE or the CLAIM decides.

**Random sample, 30 per plate, print-checked by my look (`my_look_A.json`, a lead).**
Is it a note with a printed stem, OLD's direction right: 19 / 21. Not a note: 8 / 8. Could not tell: 3 / 1.

By difference, the real notes only (Litolff 19 / Brahms 21; `tally_A.py`):
- D6 claims hold the stem (word 2, accidental 1, barline 1 / accidental 5, clef 2, key signature 1): 4 / 8
- D4 another box reads the same stroke the other way: 3 / 7 (in Brahms the other box is a tremolo slash or
  a beam junction boxed as a head in the cases I could see)
- D5 two strokes fit: 4 / 0
- D3 side, stem more than 0.4 space off the head box edge: 1 / 5; contact at the middle: 2 / 0; reach: 1 / 0
- D1 no vertical piece in the page map on the stem: 2 / 1
- no_stroke with a free vertical touching the box, cause not isolated: 2 / 0

Whole population sorted the same way without a look (Litolff 130 / Brahms 55): one stroke one direction
25 / 15; no vertical piece 25 / 3; two strokes 20 / 2; claims 19 / 14; contact at the middle 13 / 7; side off
the box edge 7 / 11; reach 3 / 1; not isolated 18 / 2. Rule 7, how many sampled members of each bucket were
real notes with a printed stem: claims 4 of 4 / 8 of 8; one stroke one direction 3 of 7 / 7 of 10; two
strokes 4 of 4 / -; side off the edge 1 of 1 / 5 of 6; contact at the middle 2 of 4 / 0 of 2; no vertical
piece 2 of 4 / 1 of 3; not isolated 2 of 5 / -. The buckets "one stroke one direction", "contact at the
middle", "no vertical piece" and "not isolated" hold as many non-notes as notes: as counts of lost stems
they are WITHDRAWN; only as "what NEW answered" do they stand.

OLD holds no ink for any of these: a box in cell pixels and a direction.

## Q3. Is OLD right where it "works better"?

**(a) Sean's judged places** (`judged48.py`; the five answer files hold 60 tiles; 59 are boxes of this
gather, the sixtieth is a rest). Truth from his answer: a note he names has a stem (r10: with its direction), a mark he
names as not a note has none, r1's strokes are stems.

| | right | missed | stem on a non-note |
|---|---|---|---|
| OLD | 34 | 22 | 3 (tremolo slash, part of a p, part of an f) |
| NEW | 48 | 10 | 1 (part of an f) |

These tiles were drawn from changes and refusals, not at random: r1 from NEW's own strokes, r10 from NEW's
refusals. They say who is right at the places the readers differ, not a rate over the page.

**Sean's hand-labelled Brahms page 0** (`p0truth.py`; his 411 noteheads, 277 stems; 375 of his noteheads
carry a stem label and a real head box of ours): OLD his stem and direction 351, wrong direction 7, no
direction 1, no stem 12. NEW 350, wrong direction 8, no stem 5, two voices 8. Level. (36 of his noteheads
have no stem label touching them; both readers stem 34-35 of them; not scored. Direction is derived from his
stem box, by me.)

**(b) the Q2 sample by my look**: OLD's answer is right for 19 / 21 of 30; 8 / 8 are stems on non-notes.

**(c) the cost of OLD's willingness.** 30 random OLD-stemmed head BOXES per plate from all boxes: 0-1 / 0
non-notes (coarse look). So OLD does not invent stems in general; its invented stems sit exactly in the set
where NEW refuses: 8 of 30 on each plate, and of those OLD writes 5 (Litolff) and 6 (Brahms) as notes in the
file (both arms write most of them today, because pre-retire the ON arm still falls back to OLD).
On Sean's page 0, head boxes on none of his noteheads: OLD stems 11 kept boxes (10 written), NEW 9 (9
written); not looked at one by one.

## Q4. The reverse

**NEW stems, OLD names none: 180 / 117** (`bwhy.py`, our own output). OLD's finder filed no stem row on
NEW's stem: 110 / 93 -- of which NEW's stem is longer than 8 spaces 49 / 29 (D8), stands at the cell edge
19 / 0 (D8), is shorter than 2 spaces 3 / 4 (D2), other 39 / 60. A row exists but its box does not touch the
head box 13 / 16 (D3). OLD saw two rows and narrowed 57 / 8 (D5 the other way round).
Print look: the over-8-space stems, 6 of 6 and 6 of 6 are real stems of wide chords. A random 10 per plate
of all 180 / 117: real note, stem printed where NEW holds it 8 / 9; not a note 1 (part of an ff) / 1 (a
quarter rest); unclear 1 / 0.

**Both stem, directions differ: 34 / 20** (`dirs.py`). Same stroke, and OLD's direction contradicts
up-right / down-left on OLD's own stem box: 26 / 7. Different strokes: 8 / 13 (7 of the Brahms ones are
NEW's two-voice rule). Over all OLD-stemmed heads OLD's direction goes against its own stem's side 85 / 31
times and OLD has a stem but no direction 52 / 15 times. Who says it is right: the convention in page-facts;
my look at 10 Litolff cases: NEW's direction right on the 5 that were clear, OLD wrong on 2 of them.

## Q5. The inputs

For the sampled real notes (19 / 21):
- **The stem's ink in the page map**: one whole free vertical 7 / 11; a vertical held by another claim 4 / 8;
  a vertical on only part of the stem (the rest fused with a beam, a head or a slash) 7 / 1; no vertical at
  all (the stem is inside a blob or curve stroke) 1 / 1. None was cut into pieces by staff-line erasure.
- **Who holds it first**: detector accidental boxes (a down stem stands on the side the accidental stands),
  the word claim (`cresc.` over half-note stems), clef / key-signature claims over the first note after a
  clef change, a barline claim. In every sampled case the print shows a stem (12 of 12).
- **The head**: Brahms all 21 have an ink oval, but for 5 the stem stands more than 0.4 space outside it
  (oval narrower than the head). Litolff: 14 of 19 have NO oval -- the page head reader found no head ink and
  NEW falls back to the detector box. Over all real heads 70% (Litolff) / 90% (Brahms) have an oval; among
  the heads NEW refuses and OLD stems only 38% / 76%.
- **Is the head a head**: 8 of 30 on each plate are not notes. Brahms: tremolo slashes 4, a beam and a beam
  junction, a quarter rest, a clef. Litolff: f / sf / pp pieces 4, beam pieces 2, an accidental, a rest block.

Unlike the arcs, this is not one story. About a quarter of the "lost stems" are fake heads; of the real ones
roughly a third are lost to claims made before the stems (inputs), about a third to tests of the stem reader
itself that OLD does not have (one direction per stroke, uniqueness, side), a few to the page map's cut, and
on Litolff most sit on heads the head reader gave no ink.

## Q6. What OLD knows or does that NEW does not

As a musician's rule OLD has almost none: "a long thin vertical that touches a notehead is its stem". That is
a real reading of the page where the head is real and the vertical is the only one there -- the common case,
which is why it is right on 351 of 375 of Sean's page-0 noteheads. Its advantages over NEW in the 130 / 55 are
mechanisms, not rules: it ignores which side the stem is on (so a narrow or misplaced head box costs
nothing), it lets a slash, a beam piece and the real head all hang on one stem (so a fake head next to a real
one costs the real one nothing), it never meets two candidates because its finder threw the short and paired
strokes away first, and it has never heard of a claim (so a word, clef or accidental box cannot take a stem
from it). The first and the last are guesses that happen to be right often; the same looseness is what gives
stems to an f, a clef and a quarter rest, gives 85 / 31 heads a direction against their own stem's side, and
loses every chord stem longer than 8 spaces. The one thing OLD does that is a reading NEW lacks: its stem box
runs THROUGH the head and through a chord in one piece, because it reads the un-split ink of the cell;
NEW's stems stop where the page map cut them.

## What I could not determine

- Whether my "not a note" calls are right (16 of 60) and the 4 "unclear": Sean, a few tiles.
- NEW's 301 / 79 two-voice heads: not sampled. They keep the old join under retire, so they are outside the
  130 / 55, but nobody has checked how many are real unisons.
- 18 Litolff `no_stroke` heads with a free vertical touching the box where no single relaxed test restores
  the stem, and the 25 heads my replay does not reproduce: the path inside the contact pass was not traced
  step by step.
- Why 30% of Litolff real heads have no oval: the head reader's question, not looked at here.
- Whether the claims that hold real stems are wrong claims or right claims over shared ink: needs the claim
  rows read one by one against the print.
- All rates are 8 pages per plate, one gather. The lane measured gather-to-gather variation it could not
  explain (OCR word claims); the word-claim bucket may move with it.

## Tiles for Sean

`out/print/2.306-r13/sheet.png` (12 tiles, two columns; `tiles/tile01..12.png`), key outside the folder:
`out/print/2.306-r13-key.json`. Seed 2306013; 6 heads per plate drawn from ALL page heads NEW considered,
not filtered by outcome. Orange box = the stem ink exactly as NEW holds it (none on tile 5: NEW refuses);
orange tick under the head. Question: "The tick marks a notehead. Is the boxed ink all of that note's stem
-- yes, only part, not its stem -- or, if there is no box, does that note have a stem (up or down)?"

## Files

`load.py` (record -> pickle), `census.py`, `replay.py` (NEW offline), `trace.py` (one test relaxed at a
time), `swap.py` (OLD's rule on NEW's ink), `sample.py` + `addrows.py` (seeded samples), `look.py` (crops for
my look), `my_look_A.json` + `tally_A.py`, `judged48.py`, `p0truth.py`, `dirs.py`, `bwhy.py`, `tiles.py`.
Scratch (pickles, traces, sheets): `<session scratchpad>/r13/`.
