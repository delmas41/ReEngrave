# Plan 2026-11-08 -- beams and flags: why the value stays narrowed, and what will work (ROADMAP 2.278)

Sean 2026-11-08: "I feel like we have done this before so I want to understand why it isn't working and know what will work
before we build." DIAGNOSIS ONLY. No pipeline code was changed. Evidence: `benchmarks/page-ledger-2026-11/FINDINGS.md` "2.278";
probes `probe/2.278/`; records `library/_shared-records/*-20261104-night.record.json`, exported by main ede3692d8.
Everything below names its path: the narrowing is STAGED ADJUDICATE (`rhythm.adjudicate_duration`) and the refusal is STAGED EXPORT
(`export._place_notes`). LEGACY (`tools/omr/rhythm.py`, `export.annotate_beams`) is frozen and is covered in section 2.

## 1. The cause, by size

Litolff, 20261104-night, current tree: 256 notehead boxes are `duration_narrowed`; **219 (86%) are the beam family**
(`beams_ambiguous` 122, `beam_discounted_uncertain` 89, `beam_certain_not_joined` 8); flags only 10; head fill / head class 22; dots 5.
Inside the beam family (the verdict's own recorded detail, `probe/2.278/causes.py`, `cdeep.py`, `tipvs.py`):

| cause (first point the evidence was lost) | Litolff heads |
|---|--:|
| two readers of one raster disagree and the rule narrows: the cell beam reader (A) counts a beam level at this stem, the page stroke map's tip reading says "no beam at this tip" (`beams_from_strokes: disagree_narrowed`, before [1,1], after [0,1]) | 49 |
| no own stem row for the head, so no tip is ever read (`stems_attached == 0`) | 45 + 24 (discounted family) |
| every stroke over the stem refused by a per-stroke test (`owned_by_another_mark`, `through_heads`, `too_thin`) and none certain | 54 |
| tip reader says the stem IS beamed (`stem_beamed: True`), the cell reader has the stroke only as a "candidate", rule narrows | 11 (+13 of the 49 above) |
| first level certain, second level only possible (eighth or sixteenth) | 17 |
| certain stroke, join reader says not joined | 8 |

Brahms, same records and tree: 703 boxes `duration_narrowed` (696 distinct ink); **645 (92%) are the beam family**
(`beam_discounted_uncertain` 323, `beams_ambiguous` 302, `beam_certain_not_joined` 20); flags 23; dots 22; head fill / class 13.
The shape differs from Litolff because the Brahms ink is clean and the notes are shorter:

| cause (Brahms) | heads |
|---|--:|
| first beam level certain, second only possible (eighth or sixteenth): fused double beams; the cell reader counts 2 levels, the tip reading 1 on 35 of them | about 190 |
| a detector `beam` box kept, no beam stroke in the ink at all (`cv_beams` 0, `yolo_kept` > 0): the box is a hairpin or slur, the head is a plain or dotted quarter, the tip window sees the hairpin's ink and is "not clean" | 248 |
| every stroke refused by the ink test (`too_thin`, `owned_by_another_mark`, `through_heads`) and none certain | 194 |
| no own stem row, no tip is ever read | 109 + 89 |

My look at 40 seeded Brahms narrowed heads (ours, not evidence): a clear printed beam 17 (at least 7 of them double beams), a flag seen 4,
a plain or dotted quarter with nothing on the stem but a hairpin or slur nearby 15, a rest or other false head 4. So on Brahms about
half the narrowed heads have an answer a reader of the stem tip can see; the 15 plain quarters should already be decided by 2.146
("clean tip means no beam") and are not because the tip window reports another mark's ink.

**The cause is not any one reader. It is that a beam is never an object.** Each head asks, on its own, in its own cell, five or six
readers (detector beam box, cell strokes A, ink test C, join reader, tip reader, stroke map) whether "a stroke over my stem" is a
beam. Every refusal rule is per stroke and per head, and any disagreement between the readers becomes a *possible* level, which
ADJUDICATE narrows and EXPORT refuses. Nothing ever says "this stroke is a beam; it joins stems S1..Sn; every stem under it is
beamed". 2.278's crops show the beam is usually there to the eye (my look at 40 seeded Litolff heads, ours not evidence: 10 clear
printed beams over the stem, 4 bare quarter stems, 3 hollow halves, 17 heads fused into staff-line/barline ink with no readable
stem, 6 unclear); the readers disagree about it.

**Process lesson.** Eleven beam efforts since 2.18 each made one reader or one refusal rule better and measured the heads that
rule touches; each decided a few dozen heads and left the structure that makes the rest "possible". The page-level effort (M4a/M4b)
swapped only the SOURCE of the strokes (page map instead of cell) and kept the per-head A + C + join voting on top of them, so the
disagreement bucket came with it (M4b: Litolff -63 notes). Reading the ink once on the page does not help while the decision stays
"per head, by vote". The unit that has to be read once is the beam group, not the stroke.

**A premise of 2.275 does not hold.** `chord_value_undecided` (Brahms 183 heads / 81 groups: one stem in 14 groups, dotted-versus-undotted in about
40, half-versus-quarter in 26; 5 of the first 8 crops I looked at are not heads at all: an F-clef piece, dynamic letters, beam pieces) and (Litolff 98 heads / 42 groups) is not a stem whose value stayed
narrowed. In 41 of 42 groups the heads are NOT on one stem (21 groups on two stems, 20 with a head that has no stem); in only 1 group
do all heads share one stem. The disagreement is half-versus-quarter in 30 groups (a hollow head and a head read black: fused ink, or
a flag / rest piece boxed as a head: crops 3, 10, 11, 13 of my 16), eighth-versus-quarter in 11. Fixing beams will not
shrink this bucket; it needs head fill and the false-head claims (2.277), and should not be scored as a beam gain.

## 2. Why each earlier effort did not fix it

See the history table in the findings. In one line each: 2.18/2.25/2.38 (stroke counted by x range / not this note's beam / join
witness): per-head refusal rules, merged ON, the narrowing stayed for what they could not tell. 2.121/2.146 (confirm the beam at the stem end;
clean tip means no beam): decides the BARE quarters (33/33 right) and cannot decide a beamed head. 2.153/2.154/2.162 (bar sum never picks;
a bar with an undecided note has no length): correct, and make every narrowing cost a note. 2.155 (join misses clear joins): fixed a
window, not the vote. 2.170: found "no beam at the tip" (1,319 Brahms) is the commonest and decided it; the beam-present rest remained.
2.202 (beams from the stroke map, ON): added the stroke map as one more voter; its disagreement with the cell reader IS the 49-head
bucket today. 2.259 (last head of a beamed group, parked): found the cell cut the beam; patched a downstream reader, parked for M4.
M4a (page beams): built the page object but filed slurs/staff-line residue as beams because the claims did not exist; OFF. M4b: page
strokes into the old per-head vote; lost on Sean's tiles (tile 11 a fragmented foot, tiles 2/7 fused double beams) and Litolff -63 notes.
M6 (heads once): measured; did not fix M4b's loss. LEGACY `export.annotate_beams` (benchmarks/omr-beam-gap-2026-09, frozen) only
repaired how begin/continue/end are WRITTEN over notes already read (449 -> 31 wrong flag/beam edits); it never read a beam from ink, so
LEGACY offers no reading method to return to.

## 3. The proposal: beam groups bound on the page, certain or absent

Design, in the order of the claim order (CLAUDE section 3). STAGED, GATHER (read, claim) then ADJUDICATE (consume). One flag, default OFF.

1. **Page-wide, after the earlier claims** (staff, barlines/brackets, clef/key/meter, words/dynamics, hairpins, arcs, tremolo
   slashes (2.276) have claimed and named their page strokes), and after stems are read as page strokes and heads are read:
   find beam candidates on the page raster, unerased thickness measured against that staff's own line thickness and spacing.
2. **A stroke is a beam only if it joins at least two stems at their ends** (Sean 2026-10-09: "A beam must not only connect to its
   note but also to another note"; a slash joins one stem; a slur and a hairpin join none; page-facts "a beam never has an arc").
   The join is judged on the page (a staff line between stem and beam is not a gap, 2.126; "there is no gap", 2.155). Two stems or
   more under it: **certain**. Fewer: **not a beam**. There is no "possible".
3. **Bind by width** (Sean 2026-10-28: "the beam covers the width of where those notes with stems occur ... even though the ink is
   broken"): every stem whose tip lies under the beam's x-extent on the beam side is owned by that beam, including a last head fused
   into a barline column or a head whose own join ink is broken. Beams stay inside one bar (DECISIONS 2026-11-04), so a group never
   spans a barline; but the stroke is read on the page, so a beam that stands outside the staff-padded cell or in two cells is ONE
   stroke (the 2.259 cut and the M4 "vertical is hard" case disappear by construction).
4. **Levels** = number of parallel strokes under the stem's x (a fused double beam is one stroke whose thickness is about two beams;
   it is split by the thickness ratio and the gap profile, never by a cell cut). A second level that cannot be shown is reported
   as unread, not as possible.
5. **Flags** are read at the tip of stems no beam owns (2.69 hook count, 2.83 flag shape, both landed): a hook seen = at least eighth;
   a clean tip = the head's own value (2.146, 33/33). A flag boxed as a head or a rest piece is a claim problem (2.277), not a duration.
6. **ADJUDICATE consumes one row per stem** (`stem -> owning beam or none, levels`) and `adjudicate_duration` stops asking six
   readers. Where the page reading is "no beam owns this stem" and the tip is clean, the value is the head's own; where the stem is
   not found, the head stays narrowed AND the missing stem is counted under its own name (the 45 + 24 heads are a STEM problem,
   2.204/M6, not a beam problem, and are reported as such).

**Rule that owns each value it would change.** Duration level of a stemmed head: CLAUDE section 4 ("an eighth only on evidence: a flag
or beam read on its stem", bar sum confirms only) and DECISIONS 2026-10-28 (a beam owns the stemmed notes under its width);
every note on one stem shares one value (page-facts, EVALUATE `share_stem_value`); a hollow head is never beamed (2026-09-30);
a tuplet only where its mark is seen (section 4). Stem ownership of a head: page-facts reading order "notehead first, stem second,
beam or flag third". Nothing here supplies a value from the bar.

**How it composes with the running lanes.**
- 2.277 (claimed ink is final): a certain beam stroke becomes a `beam` claim after the earlier page marks, so later readers get
  `claimed_by:beam` (the 27 Litolff `is_a_beam_piece` and the beam-ink-as-head tiles, e.g. M4b tile 6, are exactly this). This design
  needs that refusal to exist; it should be built after, or with, 2.277's generic `claimed_by:<kind>`.
- 2.276 (tremolo slashes read once): the order test it runs (slashes before or after heads) decides step 1's input. A slash
  crosses ONE stem and joins no other, so the two-stem rule separates a slash from a beam without a shape test; build 2.276
  first so slash strokes are named and skipped.
- 2.274 (arcs from the page ink): arcs claim before beams; a stroke an arc names is never a beam (M4a step 0 already holds:
  0 of 246 / 105 page beams lay on an arc-named stroke).
- M6 (heads once on the page) supplies the heads and their stems; the stem-not-found bucket waits on it.

## 4. Micro test, before any build (pre-registered)

Offline probe, no pipeline code, on frozen material only; kill at the first failed bar.

1. **Hand truth** (the only labelled beams, Brahms imslp317803 p0: 50 beams, 277 stems, 42 flags; Sean's boxes): from the page raster
   alone (M4a `page_beams` strokes + 2.269 names, already on main, OFF), apply steps 2-4 (two-stem join, bind by width, levels) and compare each
   truth stem's beamed/bare/flag class. **Pass: every stem bound to a beam is beamed in the truth (precision >= 0.98), and the
   bound stems cover at least 90% of the truth-beamed stems that have a stem row** (the cell readers' number on the same page is
   the control; the probe must beat it).
2. **The narrowed heads** (Litolff 8 frozen pages, Brahms p0+p5; the 20261104-night record): of the beam-family narrowed heads the rule
   would decide, the share decided must be at least 50%, and every head Sean has judged (`judged build`; value answers on both plates)
   must keep its answer: **judged right->wrong = 0** (a right->narrowed counts as a failure to explain, not a pass).
3. **Sean's blind tiles** (out/print/2.278, 12 tiles): the probe's value, where it decides, must match Sean on at least 11 of the
   tiles it decides; any tile where it decides and Sean disagrees kills the rule until the cause is found.
4. **A control that can fail**: the same probe with the beam stroke shifted 12 px (about 0.75 staff space) must fail bar 1 (precision
   falls); the same probe run with the two-stem rule removed must admit the slur/hairpin strokes M4a filed as beams (the count of
   non-truth bound strokes must rise); if either does not move, the probe is a computation, not a measurement.

Kill / pivot: precision below 0.95, or fewer than 30% of the beam-family narrowed heads decided, or any judged right->wrong. Then
the loss is the page raster (fused ink on Litolff, 17 of my 40) and the next lane is the stem and head split (M6), not a beam reader.
A pass opens one build lane, default OFF, measured on the frozen sample with the three measures (file diff, 12 tiles, judged
right->wrong 0); the whole movement is the overnight's job.

## 5. What this plan does not do

It does not propose a threshold change, a new per-head refusal, or a fill/dot fix. It does not touch `chord_value_undecided`
(head fill and false heads; owner 2.277 / M6). It does not claim the beam-family bucket is all recoverable: on Litolff 17 of my 40
heads are fused into barline or staff ink with no readable stem, and those stay narrowed and counted.
