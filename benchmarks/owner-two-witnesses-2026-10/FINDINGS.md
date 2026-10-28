# ROADMAP 2.216 -- owner from two witnesses: the count (read-only phase)

Lane `lane-2.216-owner-two-witnesses`, 2026-10-28. Path: STAGED, ADJUDICATE `glyph_owner` then EXPORT. No pipeline run, no gather, no
pytest; only saved JSON. Records: `library/_shared-records/{beethoven5-litolff,brahms1-breitkopf}-mvt1-whole-20261022-night.record.json`
(latest full adjudicated; the owner path does not read beams, so 2.202 does not move these numbers). "Frozen" = the 8 pages per plate of
`benchmarks/lane-report/sample.json`. Scripts: `extract_owner_witnesses.py`, `classify_owner_witnesses.py`, `disagreement_tiles.py`.

## Cause and process lesson

The brief ("the stem can overturn the ledger") is half true. STAGED `glyph_owner` (`adjudicators/ownership.py`) already ABSTAINS when the
stem and a ledger reading name different staves (`stem_disagrees`, lines ~716-760, 919); it does not overturn. The stem DECIDES only where
no ledger witness decided: `_stem_ruling()` replaces `distance`, `far_no_rungs`, `ledger_all_refuted` and `tied`. The real gap is
downstream: `stem_disagrees` (and `far_no_rungs`, `tied`, `ledger_witnesses_disagree`) are in `OWNER_NOT_READ_REASONS`, so
`export.py:1491` drops the head as `owner_not_read`. Both copies of a contested head abstain (one per staff's cell), so the ink is
lost entirely. The plan is therefore an EXPORT change (write it blue, both staves) far more than an adjudicator change; the
adjudicator only has to hand over both candidates. Lesson: a refusal that is already correct in ADJUDICATE can still be a
silent loss one stage later; count at the exported file, not at the verdict.

## 1. Where each witness names an owner (code)

- Ledger: `_note_first_ledger_owner` (FAR_HEAD_OWNER_LEDGER, reason `ledger_note_first`), `_ledger_owner_comparison`
  (`ledger_owner_density`), `_contest_ledger_reading` (`ledger_direction`/`ledger_refuted`), the ladder term in the score sum.
- Stem: `_stem_owner` (HEAD_STEM_REACH, flag `OMR_STEM_OWNER` default ON); speaks only for a head >= 0.9 sp outside both staves.
- Clash: `_stem_clash` after note_first/density/direction -> abstain `stem_disagrees` (detail: `stem_owner`, `ledger_owner`);
  `stem_disagrees` also at ~919 against a ladder/range-veto/hairpin sum. Stem fills in: ~864, ~876, ~909, ~914.
- Drop: `ownership.OWNER_NOT_READ_REASONS` -> `export.py` ~1485-1492 `_drop("owner_not_read", s)`.
- Gap: only the `ledger_note_first` ruling records `stem_agrees`; density/direction rulings do not, so "agree" below is a lower bound.

## 2. Counts (far = has a `head_stem_reach` or `far_head_owner_ledger` row; one row per detected copy)

Litolff whole movement, 4605 far heads: both agree 2270 (recorded); disagree 13 copies = 6 distinct heads (all stems UP, stem names the
upper staff); only stem readable 310; only ledger readable 1259 (stem silent, or agreed in the unrecorded paths); neither: nearness
decided 470, abstained 4 (`far_no_rungs`) + 1 ledger-vs-ledger; in-staff (staff_band) 278.
Litolff frozen pages, 2186 far: agree 1108; disagree 10 copies = 5 heads; stem only 159; ledger only 602; neither 229 + 2 abstained; in-staff 76.

Brahms whole movement, 10193 far heads: agree 4945; disagree 44 copies = 22 heads (28 stem DOWN, 16 stem UP); stem only 126;
ledger only 2797; neither: nearness 801, abstained 66 (`far_no_rungs`) + 7 (`tied`); in-staff 1389; `dot_follows_note` 18.
Brahms frozen pages, 2887 far: agree 1522; disagree 2 copies = 1 head; stem only 42; ledger only 739; neither 215 + 8 abstained; in-staff 355.

Not far, no witness at all (`tied`, both candidates equidistant, no stem and no ledger row): Litolff 104 copies = 52 heads (frozen 59/29);
Brahms 378 outside the far set + 7 inside = 385 copies = 175 heads (frozen 52/27).

So the disagreement is RARE: 0.3% of Litolff far heads, 0.4% of Brahms; 5 heads / 1 head on the frozen pages. The frozen sample is
too thin to measure a lane on (one Brahms head); the whole movement is the overnight's job.

## 3. Who is right (Sean's judged answers)

- Disagreement copies touching a judged note: 0 on either plate (join of `judged-tiles.json` subjects to the 57 disagreement copies;
  the single apparent Brahms hit is a Litolff tile whose key collides with a Brahms key, not a real match).
- Judged heads where the stem and ledger WOULD have disagreed (record at the time): Sean's tile 7, Litolff p4 (`glyph/4/1/2/4/3`),
  DECISIONS 2026-10-08: "Clarinet" -- STEM right, ledger wrong (ledger reading counted a slur and neighbouring heads as ledgers).
  Tile 3, Litolff p14: "Trumpet - the stem should make it obvious" -- stem right, against `distance`, ledger silent.
  Today both are `stem_toward_staff` and stay right.
- Sean's 92 far-head tiles (`1.7-far-notes-review`, Brahms p0, all answered right on the ledger owner): re-read on the 10-22 record,
  101 copies still decided, all to the same staff, 0 abstained, 0 changed; stem agrees on 49 (recorded), silent on the rest, clashes on 0.
- Tally: judged ledger-right 92/92 with no clash; judged stem-right-ledger-wrong 1 (tile 7). Judged answers going right->wrong
  under a decided/blue rule: 0 to be expected (no judged head is in the disagreement set).
- The 57 disagreement copies themselves are UNJUDGED (the 2026-10-08 gallery tiles 4, 8, 10 were never answered). Rule 7 applies:
  eight crops follow.

## 4. Crops for Sean (nothing of ours drawn: head boxed, two staves named, ruler)

`out/print/2.216/tile_01.png` .. `tile_08.png`, `questions.txt`, `key.json` (answer key: what the stem and the ledger said; NOT on the tiles).
4 Litolff (p6 sys1, p6 sys2, p14, p16) and 4 Brahms (p3, p7, p11, p24 sys2); both stem directions; A/B seeded shuffle.

## 5. What the build needs

Confirmed. `export.py` ~1485-1492 drops any head whose `glyph_owner` abstained for a reason in `OWNER_NOT_READ_REASONS` (count in
`notes_not_written`, reason `owner_not_read`). The build: (a) `stem_disagrees` (and `ledger_witnesses_disagree`) carry BOTH staves as
`candidates` on the abstention (today only `stem_owner`/`ledger_owner` sit in `detail`; the verdict `candidates` list is empty);
(b) EXPORT writes the head GUESSED/blue with both staves instead of `_drop`; the contested ink is detected twice (once per
cell), so write ONE note, not two (`is_relocated_copy`/dedupe path) -- today's drop hides the duplicate; (c) which staff's bar it sits
in until a musician decides must be a stated rule (the stem's staff is the natural default; Sean's 2026-10-27 line says only
"both staves as candidates").
Notes it would bring into the file (distinct inks, whole movement): disagreements 6 Litolff + 22 Brahms; if
`far_no_rungs`/`ledger_witnesses_disagree` ride along: +3 Litolff, +35 Brahms; if `tied` (no witness) also: +52 Litolff, +175 Brahms
(not all are noteheads that survive the earlier drops, so these are upper bounds). On the frozen pages: 5 / 1 for disagreements alone.
