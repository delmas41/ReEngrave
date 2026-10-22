# Engraving conventions THIS REPOSITORY has measured

**Scope:** only conventions this tree has evidence for. The external literature
(Gould, Ross, Read, SMuFL) is a separate document by another hand. The value of
this half is that **every entry carries a number or is explicitly marked as
carrying none.**

**Compiled 2026-09-17** from `CLAUDE.md`, `benchmarks/*/FINDINGS.md`, module
docstrings under `tools/omr/`, `tools/omr/staged/ASSUMPTIONS.md`,
`tools/omr/staged/capture.py`, and
`docs/ask-first-conventions.md` (which lives on `origin/claude/claude-md-write-access-9nzriv`
and is NOT on main).

---

## Counts

**87 entries.**

| status | n |
|---|--:|
| **MEASURED HERE** | 67 |
| **ASSERTED (untested here)** | 13 |
| **REFUTED HERE** | 5 |
| **ENCODING (not engraving)** | 2 |

⚠️ **The status is the entry's LEADING label and it undercounts the
refutations.** Several entries are MEASURED *and* carry a refutation inside
them — C10 (the stem convention is refuted as a READER while confirmed as a
ruler), C19 (one-sided), C42 (supported and deliberately not promoted), C64
(the column count holds; the residual is refuted as evidence), C78 (the
isolation test holds; extent and fill ratio are both refuted). Read the
**Evidence** and **Known exceptions** rows, never the status word alone.

| category | n |
|---|--:|
| Staff & pitch geometry | 8 |
| Stems & beams | 9 |
| Rests & bar filling | 5 |
| Accidentals & key signatures | 7 |
| Time signatures & meter | 8 |
| Slurs, ties & phrasing | 10 |
| Dynamics & hairpins | 6 |
| Articulations & ornaments | 7 |
| Score layout & systems | 17 |
| Text & margin labels | 7 |
| Barlines & repeats | 3 |

**Rigidity, by the entry's leading word: RIGID 69 · PUBLISHER-DEPENDENT 10 ·
n/a (refuted or encoding) 4 · mixed phrasing 4.** ⚠️ The leading word also
undercounts: entries that lead RIGID may still carry a publisher or scan caveat
in their **Known exceptions** row — C39 (the tie interval is empty on an
engraving and NOT on a scan), C8 and C57 (the convention is rigid; the
deviation belongs to the SCAN), C37 (the pad's empty interval is engraved; on a
scan it is a smooth slope).

---

## What I could NOT find

Several things this project plainly relies on have **no measurement anywhere in
the tree**, and are recorded below as ASSERTED rather than quietly promoted.
The largest: **proportional horizontal spacing** — an engraver spaces notes
roughly in proportion to duration, which `docs/exploration-what-is-on-the-page-2026-09-09.md`
§B.7 says in terms is "**Measured nowhere** — `grep` for proportional spacing in
`tools/omr/` returns only unrelated hits". Also unmeasured: the **repeat-dot**
position (spaces 2+3 beside a barline — stated in
`docs/position-grammar-confusables-2026-09-04.md` §2 with no figure, and
`volta` is not in the class space at all); **beaming as beat-grouping evidence**
(named in the exploration doc, consumed by nothing); **absence of a stem meaning
a whole note** (named as "cheap to add as corroboration", never added);
**measure numbers at system starts** (one sentence, "three of four editions
print them", in `docs/position-grammar-confusables-2026-09-04.md:113`, with no
per-edition table behind it — I looked in `tools/omr/training/draft_windows.py`,
`benchmarks/omr-scan-e2e-2026-09/` and every `FINDINGS.md` and found no other
statement of it); and **which end of an arc is the APEX**, which
`tools/omr/staged/positions.py:449` records as structurally underivable from a
bounding box. I also could not find a single measurement of the **courtesy
accidental**, which `docs/exploration-what-is-on-the-page-2026-09-09.md` files
as "publisher-dependent ... Filed as curiosity". Finally, `docs/ask-first-conventions.md`
§2's table cites figures that are mostly traceable to a benchmark; the two I
could not re-source to a findings file are marked in place.

---

## Contents

- [Staff & pitch geometry](#staff--pitch-geometry) — C1–C8
- [Stems & beams](#stems--beams) — C9–C15, C79, C80
- [Rests & bar filling](#rests--bar-filling) — C16–C20
- [Accidentals & key signatures](#accidentals--key-signatures) — C21–C26, C81
- [Time signatures & meter](#time-signatures--meter) — C27–C34
- [Slurs, ties & phrasing](#slurs-ties--phrasing) — C35–C44
- [Dynamics & hairpins](#dynamics--hairpins) — C45–C49, C78
- [Articulations & ornaments](#articulations--ornaments) — C50–C55, C87
- [Score layout & systems](#score-layout--systems) — C56–C68, C82–C85
- [Text & margin labels](#text--margin-labels) — C69–C75
- [Barlines & repeats](#barlines--repeats) — C76, C77, C86

(C78–C87 were added in a second pass and are filed at the END of their own
category sections; the numbering is therefore not sequential within a category.)

---

## Staff & pitch geometry

### C1 — A notehead is one staff space tall
- **Says:** a notehead is exactly one staff space tall, because that is what a notehead is.
- **Category:** Staff & pitch geometry
- **Predicts (mechanically):** any notehead-shaped detection much shorter than a space, **and touching a measure cell's crop edge**, is a fragment of the neighbouring staff's ink and is not a note.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID.
- **Evidence:** over **594 noteheads wholly inside their cell** across the three benchmark works, heights run **0.61–1.12 spaces and only three are below 0.80**; crop fragments run **0.29–0.56**; and notes a crop merely grazes (Flute 1's and Violin 1's F6) are **0.77–0.99** — "a note the boundary barely reaches is still almost all there … the constant below is not tuned to a corpus: it **sits in an empty band**, and the two groups differ in kind rather than degree". `_CLIPPED_NOTEHEAD_MAX_SPACES = 0.6` sits "in the empty band between the largest fragment (0.56) and the smallest genuine EDGE-TOUCHING notehead (0.77)". Worth pooled **0.2209 → 0.2137**, Brahms **1256 → 1201 edits** (ten detections, 55 edits). Sources: `tools/omr/transcribe.py:505-541`; `benchmarks/omr-ned-2026-08/probe_edge_fragments.py`; `docs/position-grammar-confusables-2026-09-04.md` §2 BOWL/BLOB.
- **Would be falsified by:** a plate whose genuine noteheads measure under 0.60 spaces, or an interior (non-edge-touching) fragment population in the 0.29–0.56 band.
- **Known exceptions:** grace noteheads are smaller (41×38 px against 51–83 in the same cell) — the rule is restricted to detections that TOUCH a cell edge for exactly this reason: "**A short notehead in the middle of a cell is some other problem and this must not have an opinion about it. Nothing is reclassified: a fragment is not a smaller notehead, it is not one.**"
- **Where it is used in the code:** `tools/omr/transcribe.py:537` `_CLIPPED_NOTEHEAD_MAX_SPACES = 0.6`, `:541` `_CELL_EDGE_TOLERANCE_PX = 1`, `:544` `_drop_clipped_notehead_fragments`, consumed at `:1791`. The worked catalogue of the seven fragments (the "g" of *legato*, the bowl of an "8", a neighbour staff's notehead) is at `tools/omr/transcribe.py:505-517`.

### C2 — A notehead sits ON a line or IN a space, on a half-space lattice
- **Says:** every notehead centre lands on the staff's half-space lattice — an even step is a line, an odd step is a space — and the lattice continues outside the staff.
- **Category:** Staff & pitch geometry
- **Predicts (mechanically):** staff position is a measurement, not a classification; and a head's ink overlap with the nearest line separates ON from IN.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID for the parity rule; the *outside-staff* half of the lattice is publisher-dependent (see C3).
- **Evidence:** measured in units of the head's OWN height on **836 heads INSIDE the staff whose line-or-space is not in doubt** — head ON a line (n=430) p5 **0.000**, median **0.022**, p95 **0.062**, max **0.143**; head IN a space (n=406) p5 **0.292**, median **0.374**, p95 **0.450**. The probe "answers ON below 0.15 and IN-A-SPACE above 0.29 and **ABSTAINS between**". Source: `benchmarks/omr-ledger-extrapolation-2026-09/FINDINGS.md` §7.
- **Would be falsified by:** the two distributions overlapping on a plate — i.e. no empty interval between 0.15 and 0.29.
- **Known exceptions:** a notehead box on that record is a median **2.62 half-steps tall**, "taller than the step it sits on", so "the rung is inside the box" also admits the neighbouring space — box-based tests of this convention are wrong by construction.
- **Where it is used in the code:** `tools/omr/pitch_resolver.py` (position → pitch); `tools/omr/annotate/ledger_grid.py` + the annotate `snap_to_staff` endpoint for the labelling UI.

### C3 — Ledger-line pitch is NOT the staff spacing, and it is publisher-dependent
- **Says:** the gaps between ledger rungs outside the staff are not the same as the staff's own line spacing, and the ratio is a property of the plate.
- **Category:** Staff & pitch geometry
- **Predicts (mechanically):** extrapolating the in-staff grid outward at 1.000× accumulates error; a reader must MEASURE the printed rungs and anchor the outside grid on them.
- **Status:** MEASURED HERE — **three independent populations, two of them detector-free.**
- **Rigid or publisher-dependent:** **PUBLISHER-DEPENDENT, in both directions.** Litolff hi-res **1.102**, hollow-08 Litolff **1.135**, Eulenburg **1.050**, Jurgenson **1.055**, Universal **1.030**; Breitkopf **0.975**, Peters **0.977**, Simrock **0.975**, Novello **0.975** (9 publishers).
- **Evidence:** (a) off the ink of hand-labelled cells, **185 rung gaps over 117 notes**: edge→1st **1.055** (n=105), 1st→2nd **1.020** (n=49), 2nd→3rd **1.017** (n=26) — `benchmarks/omr-snap-ledger-2026-09/FINDINGS.md` §2. (b) off a 600-dpi raster on **1,061 strips** (Litolff): edge→1 **1.032** (379), 1→2 **1.079** (132), 2→3 **1.048** (50), 3→4 **1.111** (10); Breitkopf over **1,354 strips**: **1.000 / 0.992 / 0.991 / 0.969 / 1.000 / 0.973**. Cumulative grid error in half-steps — Litolff **+0.065 / +0.223 / +0.319 / +0.541 (FLIPS at rung 4)**, Breitkopf **+0.000 / −0.016 / −0.034 / −0.096 / … / −0.151 at rung 6**. Cost: **66 of Litolff's 2,347 heads (2.81%) against 0 of Breitkopf's 3,337**, and 66 is explicitly "a FLOOR". `benchmarks/omr-ledger-extrapolation-2026-09/FINDINGS.md` §0, §4. (c) the detector's `ledgerLine` boxes read Litolff **1.130 / 1.090 / 1.080** — same sign, same publisher split, first gap 10% too wide; **the raster wins and no headline figure comes from the detector** (§5).
- **Would be falsified by:** a publisher whose measured rung gaps sit at 1.000 while the grid still mis-reads its ledger heads; or the in-staff span control failing (it does not — printed top→bottom span over the record's span is **1.00000 on Litolff, n=957**).
- **Known exceptions:** **a corrected CONSTANT cannot work** — swept and refused, "no single factor serves Litolff's 1.03–1.11 and Breitkopf's 0.97–1.00 at once" (`omr-snap-ledger-2026-09` §3, §5).
- **Where it is used in the code:** `tools/omr/annotate/ledger_grid.py:197` `measure_ledger_rungs` — **labelling UI only**. Its only consumers are `annotate/server.py` and its own test; the READER (`pitch_resolver`) still extrapolates at 1.000×. **No reader-side consumer found.**

### C4 — A note outside the staff is joined to it by an unbroken ladder of ledger rungs
- **Says:** an engraver prints every rung between the staff and the note; the ladder is continuous.
- **Category:** Staff & pitch geometry
- **Predicts (mechanically):** (i) a contested cross-staff notehead belongs to the staff whose ladder reaches it *unbroken*; (ii) an outside-staff notehead with NO rung at all is not a note.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID.
- **Evidence:** pooled OMR-NED **0.1506 → 0.1431**; Beethoven notes **81/81 at recall/precision 1.000**. The unladdered veto: fakes at confidence **0.45–0.53** against **0.76+** for every real one, "neither signal sufficient alone". ⚠️ The rule is **COMPLETENESS ONLY**, not a rung count — "two broken ladders are NOT evidence either way, because a found rung can belong to the other staff's note exactly as a gap can". Expected rungs are `int(d/spacing + 0.25)` because a note ON the first ledger measures ~1.0 spacings and truncation read 0.994 as needing none. Sources: `CLAUDE.md` "Which staff a contested glyph belongs to"; `benchmarks/omr-ned-2026-08/LADDER_EVIDENCE_2026-09-01.md`.
- **Would be falsified by:** a plate that omits interior rungs, or a corpus where rung *count* out-discriminates rung *completeness*.
- **Known exceptions:** the detector fires `ledgerLine` on **1,107** ordinary staff lines inside the staff on one four-page record, and "whether that path filters them is unchecked" (`omr-ledger-extrapolation-2026-09` §3). A tenuto is the same shape and is a live confusable (`docs/position-grammar-confusables-2026-09-04.md`).
- **Where it is used in the code:** `tools/omr/transcribe.py:3290` `_dedupe_cross_staff_detections` (ladder tier); `tools/omr/transcribe.py:3739` `_drop_unladdered_noteheads`.

### C5 — The engraver opens the gap above a staff PRECISELY so its ledger notes can live there
- **Says:** inter-staff white space on a conductor's page is not slack — it is reserved for one staff's ledger notes and the arcs over them.
- **Category:** Staff & pitch geometry
- **Predicts (mechanically):** "nearest five-line band" is the WRONG ownership rule for exactly the case the measure-cell padding exists for; ownership must be decided by context (ladder, written range, hugging), not distance.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID (it is a consequence of how a system is laid out).
- **Evidence:** Brahms's C Horn 2 `C3` sits **4.5 spaces below a treble staff, four pixels past its own cell**; at pad 5 the note goes to Eb Horn 3 **by 19 px** while C Horn 2 stays empty. Growing the pad to 5 costs Brahms **0.3420 → 0.3732 (+128 edits)** and takes cross-staff duplicates removed **135 → 390**. For arcs, the same argument is worth pooled **2,473 → 2,371 edits**, Brahms 1 **490 → 390**. Contested hairpin copies sat only **5–62 px** nearer one staff than the other — "distance is nearly a coin flip". Sources: `CLAUDE.md` (`OMR_ARC_ATTRIBUTION`; "Do not fix a clipped note by growing the pad"); `benchmarks/omr-ned-2026-08/WRONG_NOTE_ATTRIBUTION_2026-09-01.md`; `benchmarks/omr-hairpins-2026-09/FINDINGS.md` §6.
- **Would be falsified by:** a corpus where the nearest-band rule and the ladder/range rules agree on the contested population.
- **Known exceptions:** for **11 of 13** print-silent bars in `benchmarks/omr-phantom-notes-2026-09`, the ink was detected in ONE cell only and no contest exists at all, so no ownership rule is even asked.
- **Where it is used in the code:** `tools/omr/measure_extractor.py` (`PAD_ABOVE_STAFF_LINES`, 4 spaces or 6, never in between); `tools/omr/transcribe.py:3290`; `tools/omr/staged/ownership.py`.

### C6 — A ledger rung printed THROUGH a hollow notehead is split by the head's white counter
- **Says:** a rung drawn through an open notehead is interrupted by the counter, so it is printed as two short spans rather than one.
- **Category:** Staff & pitch geometry
- **Predicts (mechanically):** a contiguous-run rung detector is blind to exactly the rung that matters most (the one the note sits on); the detector must bridge a gap the width of a counter.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID (a property of open noteheads).
- **Evidence:** "a rung THROUGH an on-line hollow head is split by the white counter; contiguous-run detection was blind to exactly the rung that matters most, and **0.55 spaces of bridge — a half's counter**" is the bridging constant; white gaps up to **0.9 spaces** are bridged. A whole note is **1.72 spaces wide**, so its own rim reaches 0.55 — which is why a "wing recentring" fix re-imported pollution and was refused (zone 0.55–1.1: recovers 10 / breaks 13). Source: `benchmarks/omr-snap-ledger-2026-09/FINDINGS.md` §5 and its closing rules.
- **Would be falsified by:** a plate whose counters are narrower than the bridging window, making the bridge a false-merge risk instead.
- **Known exceptions:** a head TANGENT on its ledger merges rim + rung into one band and the measured centre drifts ~0.3 spaces into the head — one of the 7 adjudicated breaks, "a real miss".
- **Where it is used in the code:** `tools/omr/annotate/ledger_grid.py:197` `measure_ledger_rungs` (gap-bridging). **No reader-side consumer found.**

### C7 — The SMuFL em box is four staff spaces, so a glyph's printed size is fixed by the font
- **Says:** music fonts set the em box to four staff spaces, so `noteheadHalf` and `noteheadWhole` have exact nominal sizes in staff-space units at any rendering size.
- **Category:** Staff & pitch geometry
- **Predicts (mechanically):** a click-placed label box can be sized from the glyph name alone, with no guess; and a template search has a known scale.
- **Status:** MEASURED HERE — but see rigidity, this is a FONT fact, not a plate fact.
- **Rigid or publisher-dependent:** RIGID **within a SMuFL font**; historical plates differ — the shipped click box is deliberately TIGHTER than Sean's hand-drawn boxes.
- **Evidence:** "the committed Bravura templates trim to exactly `size_px/4` tall at every rendered size, so `noteheadHalf` is **1.000 staff spaces at aspect 1.167** and `noteheadWhole` 1.000 at **1.722**". Sean's 29 hollow-notehead boxes measure a median **199×178 px against a 100 px staff space — 1.78 spaces**; a click places **121×102**. "Do not 'fix' the difference by widening the default to match the older labels." Source: `CLAUDE.md` "Single-symbol pass mode" / `_symbol_metrics`; `tools/omr/symbol_library/data/manifest.json`.
- **Would be falsified by:** a measured plate whose noteheads are reliably 1.78 spaces wide rather than ~1.17–1.72.
- **Known exceptions:** the same file records `AUDIT.md` flagging that the older hand boxes are generous and would teach "a slightly loose box prior".
- **Where it is used in the code:** `tools/omr/symbol_library/builder.py`; `tools/omr/annotate/` (`_symbol_metrics`, click-to-box); `tools/omr/time_signature_locator.py` and `key_signature_template.py` build their templates from the same library.

### C8 — A staff's five lines are straight and evenly spaced — and on a scanned plate they are neither
- **Says:** the engraver rules five parallel lines; the SCAN then tilts and bows them.
- **Category:** Staff & pitch geometry
- **Predicts (mechanically):** a cell's stored line grid, copied as five ideal rows from the staff, can be half a space off the print at the end of a staff — so the grid must be slid onto the ink beneath it, and every *position* tolerance downstream must budget registration error rather than engraving slack.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** the convention is RIGID; **the deviation is a property of the SCAN, not of the publisher's engraving.**
- **Evidence:** a scanned staff "tilts/bows **8–17 page px** across its width"; the rigid-comb slide "recovers all seven hand-traced displacements within **0.04 spaces**" and per-line tracing ALIASES and was refused. Priced on the widened scan gate: pooled **0.8387 → 0.8345 (−233 edits)**, −217 of them on exactly the three tilted rows; the widened pool holds **8.6%** of cells past the 0.25-space parity-flip line against the old corpus's **0.4%**. Downstream: the whole-rest slot tolerance is "**STAFF-LINE REGISTRATION ERROR, NOT ENGRAVING SLACK**" — the document's own correctly-read whole rests spread over steps **2.5–5.9** against a nominal 5.5. Sources: `CLAUDE.md` `OMR_CELL_LINE_TRACE`; `benchmarks/omr-cell-grid-tilt-2026-09/WIDENED_PRICING_2026-09-04.md`; `tools/omr/staged/adjudicators/rhythm.py:2820-2826`.
- **Would be falsified by:** a scan corpus in which the traced comb and the ideal grid agree everywhere (the engraved family is a no-op by construction and was verified byte-identical).
- **Known exceptions:** engraved (vector) input — the fix is a no-op there by construction.
- **Where it is used in the code:** `OMR_CELL_LINE_TRACE` (default ON); `tools/omr/staged/adjudicators/rhythm.py:2826` `WHOLE_REST_STEP_TOLERANCE = 1.0`.

---

## Stems & beams

### C9 — A stem attaches on the RIGHT going UP, or on the LEFT going DOWN
- **Says:** right-and-up, or left-and-down. Right-and-down does not exist.
- **Category:** Stems & beams
- **Predicts (mechanically):** of the four (side, direction) cells only two are music; a vertical run of ink in the other two is a barline, a neighbour's stem, a beam or a slur edge. Where exactly one legal cell is filled, the stem is DECIDED.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID — "the only one of the four that is a rule the engraver has no freedom about".
- **Evidence:** agreement with the stems the pipeline ALREADY reads — Litolff **95.9% (900/938)**, Breitkopf **98.2% (1,468/1,495)**. Heads where exactly one legal cell is filled: Litolff **938/1,435 (65%)**, Breitkopf **1,495/1,774 (84%)**; on the `no_stem` population **472/784 (60%)** and **653/1,442 (45%)** — reach **472 + 653 = 1,125 heads that currently abstain**. It goes SILENT rather than wrong where it cannot speak: "both cells filled" is **16%** of Litolff's `no_stem` heads and **44%** of Breitkopf's. Source: `benchmarks/omr-stem-ink-2026-09/FINDINGS.md` §3.
- **Would be falsified by:** a plate on which the agreement figure falls toward the 0.506 always-the-commoner-direction baseline.
- **Known exceptions:** whole notes are excluded throughout (9 and 87 of the `no_stem` populations correctly have no stem). The **95.9% / 98.2% is REACH-adjacent, not accuracy**: it is measured where the pipeline already had an answer, "by construction, the population that was easy enough to read once".
- **Where it is used in the code:** **no consumer found.** The finding is 2026-09-17, "nothing was built and nothing was changed".

### C10 — In a single voice, a note above the middle line is stemmed DOWN
- **Says:** with one voice on the staff, the note's side of the middle line decides the stem direction.
- **Category:** Stems & beams
- **Predicts (mechanically):** staff position → stem direction, for free, with no ink.
- **Status:** MEASURED HERE — and **refuted as a READER while confirmed as a RULER.**
- **Rigid or publisher-dependent:** RIGID for one voice; **broken constantly by two-voice writing and chords**, which Sean himself stated as the precondition.
- **Evidence:** scored on the **1,443 heads a stem already decided, LEAVE-ONE-OUT**: baseline (always the commoner direction) **0.506**, this convention **0.787**, "where the beam SITS" 0.829, beam-mate majority 0.938, beam-mate unanimous **0.984**. Split by distance from the middle line in staff steps: 0–1 **0.537** (n=231), 1–2 **0.776** (n=228), 2–4 **0.860** (n=387), **4–6 0.939** (n=261), **6+ 0.765** (n=336) — it rises and then REVERSES. Sean: *"The convention is strong. The failure is elsewhere."* The reversal is the POSITION, not the rule: **44% of ledger-country heads are off-grid against 11% inside the staff**, and `benchmarks/omr-phantom-notes-2026-09` measured **14 of 25 phantom notes standing OUTSIDE the staff altogether**. Crossing with the residual does not move it (off-grid 0.757, on-grid 0.771). Source: `benchmarks/omr-stem-direction-2026-09/FINDINGS.md` §2, §4 (commit `1b01f8ec`, branch `claude/stem-direction-sideways` — **not on this branch**).
- **Would be falsified by:** the 4–6-step band failing on a second document; or the 6+ reversal surviving a corrected staff position (it does **not** — correcting the 32 own-staff heads with ink truth changes agreement by "**exactly nothing — 17 of 32 either way**", `omr-ledger-extrapolation-2026-09` §6).
- **Known exceptions:** two-voice writing, chords, and ledger country. `glyph_owner` does **not** explain the reversal (owned-by-another-staff 0.825 against no-verdict 0.780).
- **Where it is used in the code:** **deliberately not shipped as a reader** — "it would inherit the position's faults". Its intended use is as an AUDIT: "a confident stem and a confident convention that disagree name a zone to look in". No consumer found.

### C11 — A beam joins stem TIPS, so every stem on one stroke points the same way
- **Says:** a beam is drawn across the ends of the stems it joins, so a beamed group is stem-unanimous.
- **Category:** Stems & beams
- **Predicts (mechanically):** a head whose stem was not read can borrow its direction from any head sharing its beam.
- **Status:** MEASURED HERE — **shipped.**
- **Rigid or publisher-dependent:** RIGID. "The claim that works is PHYSICAL, not geometric."
- **Evidence:** beam-mate UNANIMOUS **0.984** accuracy, reach **152**; beam-mate MAJORITY 0.938, reach 167 — "unanimity costs 15 of 167 reach and buys 4.6 points". The `x`-CENTRE test rather than a box overlap "is worth 4 points on its own". `no_stem` **793 → 641**. Control **4,647 of 4,647** verdicts reproduced with the tier disabled. Source: `benchmarks/omr-stem-direction-2026-09/FINDINGS.md` §2 (commit `1b01f8ec`, **not on this branch**).
- **Would be falsified by:** a beamed group whose stems genuinely disagree — which would mean the beam is not joining tips.
- **Known exceptions:** the rule reaches nothing where no beam is read. Two beams crossing in a two-voice column are two strokes, not one.
- **Where it is used in the code:** `tools/omr/staged/adjudicators/rhythm.py` — a second tier in `adjudicate_stem_direction`, reason `beam_mate` (on `claude/stem-direction-sideways`, not on this branch).

### C12 — A beam stroke runs from the FIRST stem it joins to the LAST, and a stem stands at the SIDE of its notehead
- **Says:** the beam's ink starts and stops at stems, and a stem is offset half a notehead from the head's centre.
- **Category:** Stems & beams
- **Predicts (mechanically):** a note belongs to a beam via its **STEM**, not via its notehead centre — the outer note of every beamed group has its centre roughly half a notehead width past the stroke's end.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID.
- **Evidence:** on `beethoven-sym5-mvt4` m203-218 at 23 parts, **114 narrowed durations have a stem of their own head meeting a beam** that the centre test calls `none_over_this_note`, and the overshoot clusters at **0.35–0.47 notehead widths**. Closing it took the engraved fixture from **12 assessable / 7 correct → 16 / 16**; assessable **12 → 14** and correct **7 → 10** from the stem tier alone, `narrowed` **147 → 29**, and no bar goes right-to-wrong. Attachment is BOX OVERLAP and needs no constant: of 707 stem/beam pairs overlapping in x, **685 also overlap in y and the 22 that do not are 35 px or more apart with nothing in 1–34**; 819 heads take exactly one stem. On the scan side the stem tier is the whole gain (per-staff readings right **401 → 430 of 733**). ⚠️ `Q.STEM` "was declared in `wants` AND `composed_from` … and was read by nothing" — 916 rows on a three-page record. Sources: `CLAUDE.md` "A MARK must be attached to its notehead"; `benchmarks/omr-staged-duration-beams-2026-09/FINDINGS.md`.
- **Would be falsified by:** a plate whose beams overhang the outer stems, putting the outer head's centre inside the stroke.
- **Known exceptions:** on the scan **54 readings go wrong → right and 26 go RIGHT → wrong** — a 2:1 trade, where on the engraving every move went one way.
- **Where it is used in the code:** `tools/omr/staged/adjudicators/rhythm.py:164` `_stem_joined`, `:366` `_beam_levels`, `:102` `BEAM_EDGE_TOLERANCE_WIDTHS = 1.0`. The same argument for arcs: `tools/omr/export.py` (stem probes, `benchmarks/omr-arc-recovery-2026-09`).

### C13 — A stem is as long as the music needs it to be
- **Says:** a stem has no fixed length; a note two ledger lines above the staff beamed to notes inside it carries a stem far longer than a default.
- **Category:** Stems & beams
- **Predicts (mechanically):** a height cap on stem candidates silently un-stems exactly the notes furthest from their beam, and then the notehead-to-beam fallback cannot reach them either.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID.
- **Evidence:** over **8,746 candidates on 13 pages of 8 editions** the population "decays smoothly to 8 spaces and stops, with a second population from 10 up to the height of the cell itself — barlines and brackets crossing the crop". The constant sits on an **11× cliff**; the benchmark agrees: 6.0 → 0.1861, 7.0 → 0.1601, **8.0 → 0.1601**, 9.0 → 0.1610. ⚠️ **The population that forced 6.0 → 8.0 is still failing**: missing stems cross the 8.0 cap at **3.7× and 47×** the rate of read ones (Litolff `no_stem` p90 **9.97**, **16.9%** over 8.0, against DECIDED p90 6.54 / 4.6%) — but in absolute reach that is only **80 of 784 (10.2%)** and **31 of 1,442 (2.1%)**, "a striking ratio on a small population … it is not the bulk". Sources: `CLAUDE.md` "Durations: two units"; `benchmarks/omr-stem-ink-2026-09/FINDINGS.md` §4.
- **Would be falsified by:** re-taking the measurement that set 8.0 and finding the two populations still separate there.
- **Known exceptions:** the LilyPond beam ground truth (`benchmarks/omr-phase4-lines`) "is unchanged at every stem cap tried (6, 7, 8, 9, 12) because its music has no long stems. It could not have caught this and does not pretend to."
- **Where it is used in the code:** `tools/omr/line_detection.py:170` `STEM_MAX_HEIGHT_LINES = 8.0`.

### C14 — Two successive notes are set further apart than one accidental's own two strokes
- **Says:** the horizontal spacing between successive notes exceeds the internal spacing of a single accidental glyph.
- **Category:** Stems & beams
- **Predicts (mechanically):** two vertical strokes within 0.9 staff spaces that overlap vertically are one accidental, not two stems — so both may be dropped.
- **Status:** MEASURED HERE — **and its premise is now under direct challenge.**
- **Rigid or publisher-dependent:** **PUBLISHER-DEPENDENT.** "That premise is a claim about how tightly **this plate** sets its notes, measured on 14 hand-counted cells."
- **Evidence:** the rule's own record says it takes summed |error| **from 60 to 24 on 14 cells**. Against it: evaluating the rule's predicate on the raster at every head, the MISSING stems stand beside a close vertical partner at **94.6% (Litolff, n=496) / 79.8% (Breitkopf, n=1,037)** against **80.7% (n=1,011) / 15.7% (n=1,586)** for the stems we read — an excess of **+13.8 and +64.1 points**. "That rule DELETES BOTH MEMBERS of a pair." The predicted failure mode is **two-voice writing**, not accidentals: an up-stemmed upper voice and a down-stemmed lower voice in one column are two strokes within 0.9 spaces that overlap vertically. Source: `benchmarks/omr-stem-ink-2026-09/FINDINGS.md` §0.4, §4b.
- **Would be falsified by:** `detect_stems(..., drop_accidental_pairs=False)` — "THE DECIDING EXPERIMENT IS ONE ARGUMENT", a GATHER change needing two full re-gathers, and it must score both directions.
- **Known exceptions:** the measurement is a **PROXY that over-fires** (raw 600-dpi ink, no morphological opening) — "the differential is the evidence, not the level".
- **Where it is used in the code:** `tools/omr/line_detection.py:173` `_drop_paired_strokes` (gap **0.9 staff spaces**, vertical overlap 0.6 of the shorter).

### C15 — No stem means a whole note
- **Says:** the absence of a stem is positive evidence of duration.
- **Category:** Stems & beams
- **Predicts (mechanically):** a stemless head corroborates `whole`; the duration decision currently reads the notehead class alone.
- **Status:** ASSERTED (untested here)
- **Rigid or publisher-dependent:** RIGID.
- **Evidence:** **no figure.** Stated in `docs/exploration-what-is-on-the-page-2026-09-09.md` §B.5: "Absence-of-stem is *positive* evidence for duration … A whole note is currently read from its notehead class alone. Cheap to add as corroboration; only worth it if `adjudicate_duration` declares it." The only adjacent number is that **9 and 87** of the two `no_stem` populations are whole notes and are excluded from the stem-convention work as "the decision being right" (`omr-stem-ink-2026-09` §3).
- **Would be falsified by:** a measurable population of stemless heads that are not whole notes (beyond detector misses).
- **Known exceptions:** a head whose stem the CV rung simply missed is indistinguishable from a genuinely stemless one — which is the whole of C9's 1,125-head population.
- **Where it is used in the code:** **no consumer found.**

### C79 — Stacked beams are set 0.75 staff spaces centre to centre
- **Says:** a beam stroke is half a staff space thick and the gap between two stacked strokes is a quarter — so their centres are three quarters of a space apart.
- **Category:** Stems & beams
- **Predicts (mechanically):** clustering beam y-positions has a **known** correct tolerance; two ink rows closer than that are one fragmented stroke, not two levels.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID (a typographic convention of setting).
- **Evidence:** "exactly where engraving convention puts stacked beams: **thickness 0.5 of a staff space plus a 0.25 gap is 0.75 centre to centre**". Measured, the population is bimodal with an empty interval: **0.19–0.26, 460 pairs — one physical beam, fragmented**; **0.65–0.79, 69 pairs — genuinely stacked beams (a 16th)**. Constant `BEAM_Y_CLUSTER_FACTOR = 0.35`. Source: `tools/omr/rhythm.py:131` (the docstring carries the measurement).
- **Would be falsified by:** a plate whose stacked-beam separation falls in the 0.26–0.65 gap.
- **Known exceptions:** a **YOLO** beam box bounds the STACK, not a stroke, so it contributes a centre in the GAP between two strokes and destroys the bimodality — which is why a YOLO beam is kept only where no CV beam overlaps its x-range (union → kept: pooled **0.1917 → 0.1861**, Brahms duration rate 0.916 → 0.931).
- **Where it is used in the code:** `tools/omr/rhythm.py:131` `BEAM_Y_CLUSTER_FACTOR = 0.35`, consumed at `tools/omr/rhythm.py:1449`.

### C80 — A FLAG glyph NAMES A VALUE; it is not a tally of hooks
- **Says:** the engraver draws one flag glyph however many hooks it carries — a sixteenth's flag is one mark with two hooks — whereas beams really are drawn one stroke per level.
- **Category:** Stems & beams
- **Predicts (mechanically):** **counting is right for beams and wrong for flags.** `levels = len(flags)` reads a `flag16thUp` as one level when it is two.
- **Status:** MEASURED HERE (the fault was found and the table derived from the duration map).
- **Rigid or publisher-dependent:** RIGID.
- **Evidence:** "**A FLAG CLASS NAMES A VALUE, IT IS NOT A TALLY** … Counting glyphs is right for beam strokes, which are drawn one per level, and wrong for flags, which are drawn as one glyph however many hooks it has." The bug was `levels = len(flags)`; `_FLAG_LEVELS` is now **derived** from `rhythm._FLAG_DURATIONS` rather than restated. In the same repair, **112 flags attached (109 deciding)** where before `beam_evidence == "flag"` occurred **zero times**. ⚠️ **A flag hangs on a STEM**, not beside a notehead — which on the staged path beats the legacy rule, whose docstring says it cannot use the stem because *"the notehead's stem direction isn't reliably available from a 0-stem detector"*, stale since `gather_cv_lines` reads **916** of them. Sources: `tools/omr/staged/adjudicators/rhythm.py:206-216`; `CLAUDE.md` "A MARK must be attached to its notehead".
- **Would be falsified by:** a class space that split flags per hook.
- **Known exceptions:** ⚠️ **a note under a beam carries no flag**, so a notehead with a beam level AND a flag on its stem is a contradiction — a truth-free probe. Rate: **engraved 3 of 112 flagged notes (2.7%); Litolff scan 7 of 37 (18.9%); Breitkopf 27.5%** — "ordered engraved < Litolff < Breitkopf, i.e. **the worse the ink, the more the flag half picks up**". No gate was added.
- **Where it is used in the code:** `tools/omr/staged/adjudicators/rhythm.py:216` `_flag_levels_table`; legacy `tools/omr/rhythm.py` `_flag_for_notehead` (x-centre proximity, the weaker rule).

---

## Rests & bar filling

### C16 — A whole rest stands for THE BAR, whatever the meter
- **Says:** an engraver fills an otherwise silent bar with ONE centred whole rest of nominal 4.0 quarters, and the glyph means "this bar", not "four quarters".
- **Category:** Rests & bar filling
- **Predicts (mechanically):** a bar whose only event is a lone dotless `restWhole` takes the BAR's length; MusicXML writes it as `<rest measure="yes"/>` with **no `<type>` at all**.
- **Status:** MEASURED HERE — one of the two largest single wins in the repo.
- **Rigid or publisher-dependent:** RIGID.
- **Evidence:** **558 of 618 wrong rest durations (90.3%)** on the scan gate are such a bar, 543 of them our `whole`/4.0 against a truth measure rest of 2.0; restricting to a lone **whole** rest keeps 553 of the 558. Ledger, eleven works: `rest.type` **933 → 10**, `rest.duration_ql` **328 → 4**, `matched_exact` **3,154 → 4,077**, "every non-rest family identical to the row". ⚠️⚠️ **OMR-NED charged NOTHING for any of it** — engraved pooled **0.12138 / 2532 in both arms, identical in all 23 categories**; the scan gate **34,963 edits in both arms**. In the staged path the same convention as a consequence fires on **92 of 92** bars where the meter is DECIDED and **0 of 195** where it abstained. Sources: `CLAUDE.md` "A whole-rest glyph is not four quarters of silence"; `benchmarks/omr-rests-2026-09/FINDINGS.md` §7-§13; `benchmarks/omr-rest-sizing-2026-09/FINDINGS.md`.
- **Would be falsified by:** a plate that prints a half rest in a 2/4 tacet bar.
- **Known exceptions:** **the glyph is part of the rule.** The first cut accepted any lone rest and inflated bars holding a single detected **quarter** rest — a 34-edit cost, `brahms-sym4-mvt1` 0.1214 → 0.1225. `measure="yes"` is also withheld where the meter is UNKNOWN. And "a bar with no notes gets a measure rest because we read NOTHING in it, not because we read silence" — see C20.
- **Where it is used in the code:** `tools/omr/export.py:1739` `_is_lone_measure_rest` → `:1788` `_mxl_empty_measure`; staged: `tools/omr/staged/consequences.py:123` `size_measure_rest`.

### C17 — A whole rest HANGS under the 4th line; a half rest SITS on the 3rd; they are the same shape
- **Says:** both are a filled rectangle half a staff space tall in the same space, and they differ ONLY in which line they touch.
- **Category:** Rests & bar filling
- **Predicts (mechanically):** the vertical slot is the rest's **identity**, not decoration — no shape fact separates whole from half. A whole rest's centre sits at one staff step (bottom line 0, one step per half space) = **5.5**.
- **Status:** MEASURED HERE (the slot); the *discriminator between whole and half* is ASSERTED and unused.
- **Rigid or publisher-dependent:** RIGID — "whatever the clef, key or music — the engraver has no freedom about it".
- **Evidence:** `WHOLE_REST_STEP = 5.5`, "⚠️ **NOT TUNED** — it is the engraving convention, and it is an obligation rather than a preference, which is what makes it usable as a witness at all". Used as one of two witnesses for `OMR_WHOLE_REST_INK`: **SHAPE alone fires on 148 of 2,347 noteheads** (most not whole rests), **POSITION alone on 310** and "is nearly uninformative: the band a whole rest hangs in is where C5 and D5 live in treble"; **together they fire on 25, and all 25 were cropped and looked at — all 25 are whole rests**. ⚠️ On the second publisher the witness **INVERTS**: `slot 20 / neighbour 5` → **`slot 1 / neighbour 11`**, and of 12 fires **one is a whole rest**. Sources: `tools/omr/staged/record.py:775-795`; `tools/omr/staged/adjudicators/rhythm.py:2815-2826`; `tools/omr/staged/positions.py:303-331`; `benchmarks/omr-note-where-silence-2026-09/FINDINGS.md`; `benchmarks/omr-second-publisher-pricing-2026-09/`.
- **Would be falsified by:** a plate printing whole rests at a different slot — or, for the identity claim, any shape measurement that separates whole from half (the phantom-note census records "the census cannot tell a whole rest from a half rest").
- **Known exceptions:** **the measured step is not the printed step** on a warped scan — the document's own correctly-read whole rests spread over **steps 2.5–5.9** (see C8). **18.3% of Breitkopf's `restWhole` detections stand outside their own staff against Litolff's 3.5%**, and 64 sit more than a space BELOW it where Litolff has ZERO.
- **Where it is used in the code:** `tools/omr/staged/adjudicators/rhythm.py:2820` `WHOLE_REST_STEP` (behind `OMR_WHOLE_REST_INK`, default ON). The *position row* that would decide whole-vs-half — `Q.REST_POSITION`, `tools/omr/staged/positions.py:303` — is **PRODUCER ONLY**: `adjudicate_duration` "still reads the class name and nothing else" (`tools/omr/staged/capture.py:592`).

### C18 — A tacet part prints a whole rest in EVERY bar
- **Says:** a resting instrument's staff is filled bar by bar, not left blank.
- **Category:** Rests & bar filling
- **Predicts (mechanically):** a real whole rest always has a neighbouring whole rest within a bar or two at nearly the same height — so a neighbour can vouch for ambiguous ink.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID.
- **Evidence:** used as the second witness: `WHOLE_REST_NEIGHBOUR_BARS = 2`, "**deliberately SHORT**: a tacet part prints a whole rest in every bar, so a real one always has a neighbour within a bar or two, while a long reach would let one distant rest vouch for ink anywhere on the staff. **3, 4 and 8 all admit the same one extra glyph**, which on the crop is a blob beside a slur." `WHOLE_REST_NEIGHBOUR_STEPS = 1.5`, plateau **1.0–3.0**. The witness pair delivers **25 of 25 hand-adjudicated whole rests, 0 real notes** on Litolff. Source: `tools/omr/staged/adjudicators/rhythm.py:2827-2836`; `benchmarks/omr-note-where-silence-2026-09/FINDINGS.md`.
- **Would be falsified by:** a plate using multi-bar rest bars (`restHBar`) across a tacet run — the pipeline already abstains `unreadable_rest` on those.
- **Known exceptions:** `restHBar` / `restHNr` "name no single value, so the decision abstains rather than inventing one".
- **Where it is used in the code:** `tools/omr/staged/adjudicators/rhythm.py:2827` `WHOLE_REST_NEIGHBOUR_BARS = 2`.

### C19 — A quarter rest and a whole rest are different shapes, and the box aspect separates them
- **Says:** the two glyphs are not confusable by outline.
- **Category:** Rests & bar filling
- **Predicts (mechanically):** aspect ratio (h/w) alone rules out "our 209 quarter rests are misread whole rests".
- **Status:** MEASURED HERE — **one-sided.**
- **Rigid or publisher-dependent:** RIGID on the document measured.
- **Evidence:** on Litolff Beethoven 5 pp.1-4, `restWhole` median aspect **0.46, max 0.91**; `restQuarter` median **2.66, min 1.40** — **0 of 209 overlapping**, "an EMPTY INTERVAL", at the highest median confidence of any rest class. Source: `benchmarks/omr-rest-sizing-2026-09/FINDINGS.md`.
- **Would be falsified by:** a plate whose quarter rests read under 1.40 aspect.
- **Known exceptions:** ⚠️ **it is ONE-SIDED and establishes nothing positive** — "`arpeggiato` fires 377 times on this same document as *'a stem or a barline'*, the same tall thin shape". A tall thin box is not thereby a quarter rest.
- **Where it is used in the code:** not a shipped rule; `WHOLE_REST_INK_MIN_ASPECT = 1.63` / `MAX_ASPECT = 3.09` at `tools/omr/staged/adjudicators/rhythm.py:2807/2814` use the same axis for the inverse question. ⚠️ Those cuts **do not transfer**: the shipped band describes **89.9%** of Litolff's own whole rests and **52.5%** of Breitkopf's.

### C20 — A silent bar is still PRINTED with a rest; a genuinely blank bar means we failed to read it
- **Says:** the engraver never leaves a sounding part's bar empty — silence is written.
- **Category:** Rests & bar filling
- **Predicts (mechanically):** ink coverage in a cell separates "this instrument rests here" from "the detector found nothing here" — two facts that currently produce the identical `<rest measure="yes"/>`.
- **Status:** ASSERTED (untested here)
- **Rigid or publisher-dependent:** RIGID.
- **Evidence:** **no measurement of the discriminator.** The gap is quantified: on the four-page cleanup artefact "**66 bars hold no gathered ink at all; 178 come out with no event**", so on **112 bars the page gave us ink and no event came out". The exporter says so rather than pretending: "a bar with no notes gets a measure rest because we read NOTHING in it, not because we read silence", and `empty_bars_padded` is reported apart from `measure_rests_read`. The proposed discriminator — cell ink coverage — "`direction_text._blank_detections` already computes [it] for another purpose". Sources: `docs/exploration-what-is-on-the-page-2026-09-09.md` §B.1; `CLAUDE.md` "The staged pipeline".
- **Would be falsified by:** measuring ink coverage on hand-adjudicated silent vs unread bars and finding the distributions overlap.
- **Known exceptions:** a tacet bar of a part **held out of the file** is a third state again — `_pad_tacet_span` refuses to write one where the bar length is unknown, and counted **149 refused / 0 padded** on the only document available.
- **Where it is used in the code:** the collapse lives at `tools/omr/export.py:1788` `_mxl_empty_measure`. **No consumer of the discriminator found.**

---

## Accidentals & key signatures

### C21 — An accidental holds for its letter and octave to the end of the bar
- **Says:** an accidental is a SCOPE, not a property of one notehead.
- **Category:** Accidentals & key signatures
- **Predicts (mechanically):** reading left to right within a bar, a later notehead of the same letter+octave inherits the alteration with no glyph of its own; the absence of a mark is a positive statement about pitch.
- **Status:** MEASURED HERE (implemented and relied on) — **no isolated figure for the convention itself.**
- **Rigid or publisher-dependent:** RIGID.
- **Evidence:** implemented and exercised on every run; I found **no A/B pricing it alone**. Its structural consequence is recorded: "an accidental is not a glyph property, it is SCOPE … the staged record has nowhere to put the state. This is the clearest case where the missing quantity is a *span*, not a mark" (`docs/exploration-what-is-on-the-page-2026-09-09.md` §A). The staged `gather_coverage` files `accidental` under `FAMILY_Q_IS_ELSEWHERE` for exactly this reason — 8 detector classes with no gather quantity. Related and **measured**: the tie-pairing work found that spelled pitch is the wrong key for cross-barline ties precisely because "the far head of a cross-barline tie does not restate its accidental and the resolver spells it plain" — **11 of the engraved 20 and 11 of the scan cases** are same-STEP, accidental-differs (`benchmarks/omr-tie-pairing-2026-09/FINDINGS.md`).
- **Would be falsified by:** a plate restating accidentals per note (some modern editions do).
- **Known exceptions:** courtesy accidentals (C26) and the cross-barline tie above.
- **Where it is used in the code:** `tools/omr/transcribe.py:2211-2267` (`explicit_in_measure`, keyed on `(letter, octave)`). The staged record has **no span quantity** — no consumer there.

### C22 — A key signature's accidentals stand at fixed slots, and which slots depends on the CLEF
- **Says:** the sharps and flats of a key signature are printed at positions fixed by convention for each clef, in a fixed order.
- **Category:** Accidentals & key signatures
- **Predicts (mechanically):** **read the positions, do not count the glyphs** — a missed interior accidental is recovered by fitting the observed positions to the slot table, rather than miscounted.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID.
- **Evidence:** on two ground-truth orchestral pages (42 staves), **given the correct clef**: **18 correct, 0 wrong, 16 missed, 8 correct abstentions** (34 of the 42 carry a signature). On WTC p.17 (E major, clean engraving) the three stages separate cleanly: **counting the markers 6/10, fitting their positions 7/10, reconciling across the page 10/10** — "each step fixing a different failure". Against Sean's hand-read per-staff truth on Litolff pp.1-4 the staged reading goes **16 correct / 10 wrong / 49 abstained → 35 / 15 / 25**, and the FILE **33 right → 44 of 75**. Sources: `CLAUDE.md` "Key signatures are read by position"; `benchmarks/omr-keysig-truth-2026-09/FINDINGS.md`.
- **Would be falsified by:** a plate whose signature accidentals do not sit on the conventional slots for the read clef.
- **Known exceptions:** ⚠️ **it inherits the clef.** "a wrong clef produces wrong signatures rather than abstentions (measured: bass staves defaulted to treble read 3 flats as 2 sharps)", so a staff whose clef is only the positional default is skipped. ⚠️ **It may not INFER** — recovering slots nothing was detected at compounded five matches into *seven sharps* on a four-sharp page.
- **Where it is used in the code:** `tools/omr/key_signature_geometry.py` (slot-table fit); `tools/omr/key_signature_locator.py`; `tools/omr/key_signature_template.py`; `tools/omr/key_signature_vote.py`.

### C23 — A key signature stands BETWEEN the clef and the meter
- **Says:** the header is printed in a fixed order — clef, then key signature, then time signature.
- **Category:** Accidentals & key signatures
- **Predicts (mechanically):** the accidental search is a bounded 1-D strip, not a page search. This matters because outline correlation cannot separate the glyphs: "a flat's outline correlates with a G clef at **0.57–0.59** against real flats' **0.65–0.76**, too close to separate by score".
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID.
- **Evidence:** given the correct clef for every staff of Beethoven 5 p.1, the connected-component locator reads **2 of 12**; the bounded template search reads **11 of 12** standalone. End to end on p.1: key signatures **4/12 → 7/12 correct with 0 wrong**, exact-pitch recall **0.571 → 0.619** against unchanged step recall; over six pages, staves spoken for **29% → 39%**. Positions come from the **ink centroid inside the matched box**, not the box centre — "box centres leave ±0.5 step of jitter, enough for the fit to read three flats as five". Source: `CLAUDE.md` "Key-signature accidentals are found by template".
- **Would be falsified by:** a plate printing the meter before the key.
- **Known exceptions:** ⚠️ **the empty-window hazard** — on p2/s1, all eleven header windows measured **6.1–6.2 staff spaces** against 16.00 elsewhere, holding the margin label and the systemic rule and no music; the locator abstained and **the template answered a confident `fifths: 0`**. "*The reader that can say 'zero' is the one that must never be given an empty window*". Fixed by anchoring the margin on the MEDIAN of the per-staff left-edge estimates (`system_left_consensus`): windows with a `barline` right edge **12 → 1**.
- **Where it is used in the code:** `tools/omr/staff_header.py` (`measure_header_window`, `system_left_consensus`); `tools/omr/key_signature_template.py`; `tools/omr/time_signature_locator.py:400` `locate_time_signature` supplies the right bound.

### C24 — A key CHANGE is printed at ONE bar of ONE system, on EVERY staff of it
- **Says:** the engraver announces a key change simultaneously across the whole system, at one bar.
- **Category:** Accidentals & key signatures
- **Predicts (mechanically):** **the BAR is the shared fact even where the VALUE differs by transposition** — so a mid-staff key change no other staff of the same system also changes at the same bar can be reverted, without needing the staves to agree on the key.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID.
- **Evidence:** over 11 scanned + 11 engraved stored transcriptions, **7 of 7** spurious mid-staff flips on the scan corpus are stopped — 5 of the 7 "had already been rejected once by the cross-page header vote and the mid-staff reader overturned it anyway". Flag-ON changes **5 of 11 scan fixtures and 0 of 11 engraved**. Flag OFF is byte-identical by construction, verified with `diff`. `MIN_WITNESSES = 2`. Sources: `CLAUDE.md` `OMR_KEYSIG_CORROBORATION`; `benchmarks/omr-keysig-corroboration-2026-09/`.
- **Would be falsified by:** a real mid-staff key change that fails its own witness test.
- **Known exceptions:** ⚠️⚠️ **the corpus contains ZERO real mid-staff key changes, so only the BENEFIT is measured** — and there is "concrete reason to expect [the cost] non-trivial: later-cell key markers appear on only **15 cells across 193 scanned staves with no two sharing a bar**, so a genuine mid-staff change would more likely fail its own witness test than pass it".
- **Where it is used in the code:** `tools/omr/key_signature_corroboration.py:202` `MIN_WITNESSES = 2` (default ON since 2026-09-07). The staged mirror imports it: `tools/omr/staged/adjudicators/rhythm.py:1423` `METER_CHANGE_MIN_STAVES = 2` is **asserted equal** to it.

### C25 — The clef and key signature are reprinted at the head of EVERY system
- **Says:** a performer's eye cannot hold them, so they are restated at each system start within a part.
- **Category:** Accidentals & key signatures
- **Predicts (mechanically):** a part has many independent readings of one fact, which a cross-system vote can reconcile — and the PAGE therefore carries more clef glyphs than the encoding declares.
- **Status:** MEASURED HERE (as redundancy) / ENCODING caveat attached — see C68.
- **Rigid or publisher-dependent:** RIGID.
- **Evidence:** the cross-page vote took WTC I p.17 from **6/10 to 10/10** on key signatures. The page-vs-encoding gap is measured on the Brahms fixture: **28 G-clef glyphs against 14 `<sign>G</sign>`** in the file it was rendered from (`benchmarks/omr-reading-vs-reproduction-2026-09/FINDINGS.md`). `docs/ideal-reader-2026-09-07.md` §(b) lists it as one of the enumerable repeated facts.
- **Would be falsified by:** an edition that states the clef once per page.
- **Known exceptions:** ⚠️ the staged path **consumes none of** `key_signature_vote.reconcile`, deliberately — keyed on a wrong staff→part join it "would carry the viola's 7 onto the timpani".
- **Where it is used in the code:** `tools/omr/key_signature_vote.py` `reconcile` (legacy path only); `tools/omr/staff_header.py`. **No staged consumer.**

### C26 — A courtesy accidental is a property of the EDITION, not of the music
- **Says:** whether a redundant reminder accidental is printed varies by publisher.
- **Category:** Accidentals & key signatures
- **Predicts (mechanically):** its presence or absence is evidence about the edition, not about the pitch.
- **Status:** ASSERTED (untested here)
- **Rigid or publisher-dependent:** PUBLISHER-DEPENDENT (by assertion).
- **Evidence:** **no figure anywhere in the tree.** One sentence: "**No courtesy accidental** — publisher-dependent, so its presence or absence is evidence about the EDITION rather than the music. Filed as curiosity" (`docs/exploration-what-is-on-the-page-2026-09-09.md` §B.8). I searched `benchmarks/` and `tools/` for any courtesy-accidental measurement and found none.
- **Would be falsified by:** measuring courtesy-accidental rate per publisher and finding it flat.
- **Known exceptions:** none recorded.
- **Where it is used in the code:** **no consumer found.**

### C81 — Timpani, horns and trumpets are conventionally written WITHOUT a key signature
- **Says:** in the 18th–19th-century repertoire this project reads, the natural-horn, natural-trumpet and timpani staves carry no key signature at all — the accidentals are written in.
- **Category:** Accidentals & key signatures
- **Predicts (mechanically):** a ZERO read on one of those staves is **explained**, not a failure — so such a staff must be excluded as a witness to the page's key, and its own zero must not be treated as a disagreement.
- **Status:** ASSERTED (untested here) — declared in the code as a claim about practice.
- **Rigid or publisher-dependent:** RIGID for the repertoire named; **era-dependent** by its own statement.
- **Evidence:** **no measurement of the convention itself.** Declared verbatim at `tools/omr/key_consensus.py:86`: `NO_SIGNATURE_CONVENTION = frozenset({"Timpani", "Horn", "Trumpet", "Cornet", "Flugelhorn"})` — "⚠️ This is a claim about ENGRAVING PRACTICE, strongest in the 18th-19th century repertoire this project reads, and it is NOT derivable from the staff … **it only ever explains a ZERO.**" Consumed at `:257` (witness exclusion) and `:402` (outcome `CONVENTION_NO_SIGNATURE`). Its consequence IS visible in a measured figure: of the 33 key readings CLAUDE.md counts as "right in the file" on Litolff pp.1-4, **17 are abstentions that happen to land on a horn, trumpet or timpani** — right for the wrong reason.
- **Would be falsified by:** a work in this corpus printing a key signature on a horn or timpani staff.
- **Known exceptions:** a sibling set is declared and explicitly unmeasured — `MAY_DIFFER_NOT_A_WITNESS = frozenset({"Harp"})` at `tools/omr/key_consensus.py:101`, for pedal/enharmonic reasons, "⚠️ **DECLARED, NOT MEASURED**".
- **Where it is used in the code:** `tools/omr/key_consensus.py:86`, consumed `:257` and `:402`. `MIN_WITNESSES = 3` there is **concert-pitch staves** — a different constant and unit from `key_signature_corroboration.py:202`'s 2 (C24).

---

## Time signatures & meter

### C27 — A time signature's placement is RIGID — numerator in the upper two spaces, denominator in the lower two, centred on each other
- **Says:** the meter's two digits occupy fixed halves of the staff and are centred on one another.
- **Category:** Time signatures & meter
- **Predicts (mechanically):** turns a 2-D search into a **1-D** one — a composite template per candidate meter, slid along the header window in x.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID.
- **Evidence:** over a corpus "half of which is pages printing no meter at all": **4 correct, 0 wrong, 12 correct abstentions**, across a 600-dpi scan of 19th-century type and LilyPond pages set in a different font from the templates — "where the detector reads **zero** digits on the same page". Beethoven 5 p.1 emits 2/4 instead of 4/4 and its LilyPond bar-check failures fall **154 → 104**. Corpus total over 11 sources after the letter-meter and vote work: **12 correct, 0 wrong, 3 missed, 40 correct abstentions**, up from 3 wrong. Sources: `CLAUDE.md` "The meter is read from the header by shape"; `benchmarks/omr-timesig-2026-08/`, `benchmarks/omr-timesig-2026-09/FINDINGS.md`.
- **Would be falsified by:** a plate printing digits off-centre or spanning the middle line as a rule.
- **Known exceptions:** ⚠️ **on a bitonal plate ink bleed fuses numerator and denominator into one stroke**, so a `spans` reading "is entirely compatible with a real meter"; and the converse — two fragments in two halves is also what a **BROKEN BARLINE** looks like (Litolff p.62). Sean, 2026-09-17: *"Quick rules will give us quick results that could be poor."*
- **Where it is used in the code:** `tools/omr/time_signature_locator.py:400` `locate_time_signature` — but ⚠️ the placement is **a constraint INSIDE the template search that is then thrown away**. `Q.METER_GLYPH_POSITION` now records it (`tools/omr/staged/positions.py:357` `_meter_discriminator`) and **`adjudicate_meter` does not read it** (`tools/omr/staged/capture.py:580-591`).

### C28 — A meter is printed at a movement's START and nowhere else
- **Says:** the time signature appears once, at the head of the movement, and is not restated per system.
- **Category:** Time signatures & meter
- **Predicts (mechanically):** a system that read no meter should take the last one that WAS read — as a CANDIDATE its own bars confirm or refuse, not as a gate.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID (and the *opposite* of the clef/key convention C25, which is why both flags exist).
- **Evidence:** `OMR_METER_CARRY` (default ON since 2026-09-15). On Litolff Beethoven 5 mvt 1 pdf p1-3, systems decided **1 of 5 → 5 of 5** (`carried` ×4 at support +6.0 / +13.0 / +9.0 / +18.0), `<time>` **28 → 54 and ALL of them `2/4` in both arms**, bars that add up **54.4% → 81.2%** like-for-like over the 1,109 bars present in both arms, with **298 wrong→exact and 0 exact→wrong**. ⚠️ **DO NOT QUOTE THE RAW 90.8%** — it includes 1,159 tacet bars the ON arm adds, exact by construction. On the same document rests at 4.0 go **471 → 115**, at 2.0 **109 → 465**, `empty_bars_padded_without_meter` **168 → 0**. The boundary case is measured on an engraved render (Beethoven 5 mvt 4, 4/4 → 3/4 at bar 155): the TRUE meter scores **+8.0** (8 bars fit / 1 not) and the FALSE one **−8.0** (0 / 9). Sources: `CLAUDE.md` `OMR_METER_CARRY`; `benchmarks/omr-staged-meter-boundary-2026-09/FINDINGS.md`; `benchmarks/omr-rest-sizing-2026-09/FINDINGS.md`.
- **Would be falsified by:** a document where a carried meter propagates a misread across many systems — **which no document in the corpus supplies**: the misread-carry cell is empty in all three shapes tried.
- **Known exceptions:** ⚠️ **a carried meter must never cross a movement boundary blindly** — it does not need a movement detector, because the bars refuse it: on Litolff p.63 the carried `2/4` is refused at **−6.0** while the same bars name **3.0 at +5.0**, the printed `3/4`. ⚠️ And the *Andante* refusal is **SAFE but NOT discriminating**: scored against the `3/8` that page actually prints, it refuses that too (−1.0 and −1.0).
- **Where it is used in the code:** `tools/omr/staged/adjudicators/rhythm.py:2025` `_carry_meter`; legacy `transcribe` carries with `source="carried_from_previous_page"`.

### C29 — A meter is printed on EVERY staff of the system
- **Says:** the time signature is restated on each staff, so one system carries as many independent readings as it has staves.
- **Category:** Time signatures & meter
- **Predicts (mechanically):** vote across the staves of a system; a reading on one staff of seventeen is not a meter.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID.
- **Evidence:** the system vote is what turns a per-staff reader into a decision — "the opening reader's **16.75%** per-staff false rate is contained by the cross-staff vote": over **18 continuation header systems the shipped vote declares a meter on NONE**. The agreement floor went **0.5 → 0.70** because "every one of the 12 correct readings is agreed by **0.909** of its system or more and the one wrong reading … by exactly **0.500**". A change to common time was found on **23 staves of 23, unanimous**; a `¢` on **24 staves of 24 at support 74.0**. ⚠️ A believed meter is carried onto every later measure of its staff, so counting measures counts one reading many times — "a single `timeSig4` at confidence 0.42, on one staff of nineteen, arrived at the page vote as **eighteen unanimous votes** for common time"; `_dominant_detected_meter` now takes **one vote per staff and requires half the page's staves**. Sources: `CLAUDE.md` (meter sections); `benchmarks/omr-meter-cautionary-arbiter-2026-09/FINDINGS.md`; `docs/ideal-reader-2026-09-07.md` §(b).
- **Would be falsified by:** an edition printing the meter on only the top staff of a system.
- **Known exceptions:** ⚠️⚠️ **a fixed 3-staff quorum does NOT contain the false rate in the HEADER frame** — it fires falsely on **4 of those 18 systems, one with SEVEN staves agreeing on `C`**. The shipped vote survives because `min_staff_fraction` is a FRACTION of the system, not a count. **Do not port `METER_TEMPLATE_AT_BAR_MIN_STAVES = 3` into the header frame.**
- **Where it is used in the code:** `tools/omr/time_signature_locator.py` `vote_system_time_signature`; `tools/omr/rhythm.py` `_dominant_detected_meter`, `drop_uncorroborated_meter_changes`.

### C30 — A cautionary meter printed after a system's FINAL barline governs no bar
- **Says:** an engraver announcing a new meter prints it TWICE — as a courtesy after the last barline of the ending system, and again at the head of the next. The first governs nothing.
- **Category:** Time signatures & meter
- **Predicts (mechanically):** a meter-change candidate in a staff's LAST cell is a courtesy, not a change — unless its own bar FITS.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID.
- **Evidence:** ⚠️ **the rule was checked against the corpus BEFORE it was written**, "which is what separates it from a story fitted to its own data": **all four TRUE changes sit at a non-last cell** (Litolff p.62 cell 8 of 13, Brahms 1 i cell 1 of 8, Beethoven 5 iv cell 3 of 9, Brahms 1 iv cell 6 of 8) and **both cautionaries at a LAST cell**. Together with the meter-in-force fix, **false meter changes 10 → 3, no true change lost**, and the ENGRAVED arms go to **4 printed / 4 found / 0 false**. An independent second reading of the same convention by ink fraction: the one visible cautionary reads **1.000 on all 19 staves** against **≤ 0.118 for every other segment**. The cautionary is **RECORDED, not discarded**. Sources: `CLAUDE.md` "A meter CHANGE: against the meter IN FORCE, and a CAUTIONARY is not one"; `benchmarks/omr-staged-meter-boundary-2026-09/FINDINGS.md` §4c.
- **Would be falsified by:** a genuine meter change at a system's last bar whose own bar does not fit.
- **Known exceptions:** ⚠️ **a cautionary's VALUE is right even though its placement is not a change** — `report_boundary.TRUTH_CHANGES` records both cautionaries as `None`, "a statement about placement, not about value. A reader who meets that `None` and concludes the cautionary is junk has read the wrong column." ⚠️ Only **3 cautionaries exist in the whole committed corpus**, on ONE piece of music.
- **Where it is used in the code:** `tools/omr/staged/adjudicators/rhythm.py:1690` `_meter_changes` (last-cell discrimination).

### C31 — A letter meter (`C`, `¢`) is a complete meter, and the stroke is what separates them
- **Says:** common time and cut common are single glyphs that each state a full time signature; a `C` and a `¢` are the same glyph plus a vertical stroke.
- **Category:** Time signatures & meter
- **Predicts (mechanically):** a meter reader that demands two stacked digits is blind to an entire family; and the cut stroke must be read by POSITION after `C` has won, not by a competing template.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID.
- **Evidence:** a change to common time was detected on **23 staves of 23** at the right bar and proposed **nothing**, because `_meter_from_digits` needs two stacked digits. Fixed, it lands at support **66.0** on the exact bar. `C` is the strongest reading in the corpus: **five common-time pages at 0.745–0.761** against 0.50–0.62 for scanned digit meters. For the stroke: over **87 staves that matched C, the 24 cut ones fill 1.00 of the centre column and no other exceeds 0.48 — every threshold in 0.50–1.00 gives the same answer**. ⚠️ Adding a cut-C TEMPLATE fails **both** ways — nine false systems, and it still loses to plain `C` on real ¢ pages, "because a C is a SUBSET of a cut-C's ink and the template with less to account for scores higher". Fifteen of the 97 dossier works open on a `¢`; Mozart 40 i read **11 staves of 11** and Brahms 4 i **13 of 13** as 4/4 before the fix. Sources: `CLAUDE.md` "Common time is read; cut common was measured and withheld" and "A meter CHANGE printed as a `C`"; `benchmarks/omr-timesig-2026-09/FINDINGS.md`.
- **Would be falsified by:** a plate whose cut stroke does not reach the centre column.
- **Known exceptions:** ⚠️ **it produces a false positive on a scan** — one `timeSigCommon` at confidence **0.377** on one staff of seventeen on Litolff p.61, a page printing no time signature at all. "The hazard is `METER_CHANGE_FLOOR`, not the letter path": one staff reading a complete meter clears the floor by design. Confidence separates the populations cleanly (**0.887–0.927 engraved, 0.377–0.560 scan**) and is **deliberately not gated on** — "four rows on two documents is not a threshold".
- **Where it is used in the code:** `tools/omr/staged/adjudicators/rhythm.py:1493` `_meter_from_letter`; `tools/omr/rhythm.py` `parse_time_signature` (`symbol=` from the glyph); `tools/omr/symbol_library/builder.py` (`timeSigCommon`, `timeSigCutCommon` templates); `_looks_cut`.

### C32 — An OPENING meter sits 10–12 staff spaces into its bar, behind the clef and the key signature
- **Says:** the header's fixed order (C23) puts the opening time signature well inside the bar, unlike a mid-staff change.
- **Category:** Time signatures & meter
- **Predicts (mechanically):** the window an opening meter is read in and the window a mid-staff CHANGE is read in are different widths, and they are not interchangeable.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID.
- **Evidence:** on Brahms 1 / Breitkopf p.45, a movement start whose print was looked at (page 46, *Adagio*, full margin names, a common-time `C` on every staff): a **4-space** bar head of cell 0 reads **0 of 16** and spells `4/4`/`9/4`/`12/16`/`5/4` out of clef ink, while **14 spaces reads 16 of 16** and the shipped 16.00-space header window reads **16 of 16** (the header row is the positive control). Source: `benchmarks/omr-meter-cautionary-arbiter-2026-09/FINDINGS.md` §3.
- **Would be falsified by:** a movement start whose meter is legible in a 4-space window.
- **Known exceptions:** it does **not** argue against a 4-space window for a mid-staff CHANGE (C33) — "a mid-staff CHANGE is printed straight after a barline with no clef in front of it, which is exactly why that window is four spaces".
- **Where it is used in the code:** `tools/omr/staff_header.py` `measure_header_window` (16.00 staff spaces).

### C33 — A mid-staff meter CHANGE is printed at the bar head with no clef in front of it
- **Says:** unlike an opening meter, a change stands immediately after the barline.
- **Category:** Time signatures & meter
- **Predicts (mechanically):** a 4.0-staff-space slice of the measure cell is the right window for a change — and the same column can be probed on every staff of the system, including staves that detected nothing.
- **Status:** MEASURED HERE for the FALSE-POSITIVE side only.
- **Rigid or publisher-dependent:** RIGID.
- **Evidence:** over **1,612 mid-staff bar-head windows on ten real scanned pages of two publishers printing NO meter change**, admitted on 1 staff the reader yields **16** spurious columns, on 2 **two**, on 3 **ZERO** — hence `METER_TEMPLATE_AT_BAR_MIN_STAVES = 3`. ⚠️ **The quorum is safe AT 4 SPACES AND NOT AT 8** (false rate 0.99% / 1.55% / 2.48% at 4 / 6 / 8, and one three-staff false consensus appears at 8) — "the width and the quorum are ONE safeguard at one operating point, not two independent ones". Positive control: a real Bravura `3/4` stamped into 225 of the same windows — **225 answered, 225 right**. The false population is **13 of 16 `C`**, recorded and not gated on. ⚠️ `min_score` is deliberately not moved: the positive control's own minimum (**0.542**) sits BELOW the worst false answer (**0.6141**), so the populations overlap and no score threshold separates them. Source: `CLAUDE.md` `OMR_METER_TEMPLATE_AT_BAR`; `benchmarks/omr-meter-template-changes-2026-09/FINDINGS.md`.
- **Would be falsified by:** a real mid-staff change the 4-space window misses.
- **Known exceptions:** ⚠️⚠️ **ACCURACY IS UNMEASURED IN ONE DIRECTION** — "no page in reach prints a mid-staff change, so the false-positive side is measured and **it has never been shown this reads a real one**." Also: **38 of 51 columns (74.5%)** on Brahms 1 p1-3 are candidates, "so candidacy is NOT where the safety is".
- **Where it is used in the code:** `OMR_METER_TEMPLATE_AT_BAR` (default OFF, UNPRICED — a GATHER change); `Q.METER_TEMPLATE_AT_BAR`.

### C34 — "A meter stack is two digits aligned in x and adjacent in y" — REFUTED
- **Says:** the proposed rule was that a genuine numerator/denominator pair is distinguishable from two unrelated digits by their x-alignment and y-adjacency.
- **Category:** Time signatures & meter
- **Predicts (mechanically):** it would have separated true meter stacks from fragments — it does not.
- **Status:** **REFUTED HERE**
- **Rigid or publisher-dependent:** n/a.
- **Evidence:** "TRUE `dy` **32-548** against FALSE **26-555**. **Total overlap.**" A sibling hypothesis is refuted alongside it: "*the false ones sit at `x_canonical == 0`*" is decisive in a per-cell table but collapses once restricted to clean two-digit stacks — **1 of 110 TRUE vs 4 of 50 FALSE**. Sources: `docs/ask-first-conventions.md` §3; `benchmarks/omr-staged-meter-boundary-2026-09/FINDINGS.md` §4c.
- **Would be falsified by:** it already is. Do not re-try either form.
- **Known exceptions:** the *placement* convention C27 is a different and surviving claim — the refuted one is about separating a stack from noise by dy alone.
- **Where it is used in the code:** **nothing implements it**, deliberately. The live consequence is that Litolff p.62's `timeSig3`+`timeSig4` are **one barline broken into two fragments**, both 0.35–0.40 staff spaces wide at `x_canonical = 0`, and `_meter_from_digits` still accepts them (`benchmarks/omr-ink-gather-2026-09/FINDINGS.md`).

---

## Slurs, ties & phrasing

### C35 — A slur is drawn OVER its notes; a hairpin is drawn BETWEEN them
- **Says:** a slur arcs above (or below) the noteheads it binds and overlaps them vertically; a hairpin lives in the horizontal space between note columns, in the dynamics band.
- **Category:** Slurs, ties & phrasing
- **Predicts (mechanically):** an overlap test (`_noteheads_under`) is the right anchor rule for a slur and **structurally cannot work** for a hairpin, whose edges must be read as POINTERS to the nearest note either side.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID.
- **Evidence:** "an overlap test scores **0 of 4**" on the Mahler 5 fixture — the Trumpet's diminuendo spans page x **5922-6068** in a bar whose only notehead spans **5817-5897**, "not one pixel of overlap". Nearest-either-side pairs **4 of 8** truth hairpins and gets all 4 exactly right; "the last note at or before the edge" pairs **1** — the ink begins slightly BEFORE the note it starts on (26 px left of it, 105 px right of the previous note, on Tchaikovsky 6). Sources: `CLAUDE.md` "Hairpins"; `benchmarks/omr-hairpins-2026-09/FINDINGS.md`; `docs/ask-first-conventions.md` §2.
- **Would be falsified by:** a hairpin printed over its noteheads (a piano score's between-staves hairpin is still between note columns).
- **Known exceptions:** none recorded.
- **Where it is used in the code:** `tools/omr/export.py:2590` `_noteheads_under` (slurs); `tools/omr/export.py:2923` `_wedge_anchors` / `:2985` `_wedge_anchors_from_candidates` (hairpins).

### C36 — A slur's ink stops INSIDE both outer notehead centres
- **Says:** a slur is drawn between its notes, so the arc is narrower than the run it binds.
- **Category:** Slurs, ties & phrasing
- **Predicts (mechanically):** the arc box must be PADDED before asking which noteheads it covers, or the outer note at each end is dropped.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID.
- **Evidence:** unpadded, "the Contrabass read `n1 -> n4` in every bar whose truth is `n0 -> n5`". The pad's plateau: a notehead is UNDER the arc at **0.00–0.19 notehead widths vs 0.32** — constant **0.25 nh widths**, "identical for the pad at 0.25 or 0.5". With the pad, on top of the ledger fix, pooled **0.2263 → 0.2209**, edits **1584 → 1563**, `wrong slur` **81 → 61**, Contrabass **7/7 exact**. ⚠️ Merging *without* the pad LOWERED pooled OMR-NED (0.2449 → 0.2436) while **raising** the edit count — "the metric's symmetry rewarding extra symbols". ⚠️⚠️ **Widening `_SLUR_ARC_PAD_NOTEHEADS` was measured and REFUSED**: the constant sits in an interval the engraved Brahms fixture left EMPTY (**54 of 75 within 0.19, the next at 0.32**) while on the Litolff scan "the same distribution is a **smooth slope with no gap anywhere**, so a pad read off it would be fitted to a wish". Sources: `CLAUDE.md` "Slurs"; `benchmarks/omr-ned-2026-08/SLURS_2026-09-01.md`; `benchmarks/omr-arc-recovery-2026-09/FINDINGS.md`.
- **Would be falsified by:** an engraving whose slurs reach past the outer notehead centres.
- **Known exceptions:** the empty interval is an **engraved** property; on a scan it is a smooth slope. Do not re-tune the constant on a scan.
- **Where it is used in the code:** `tools/omr/export.py:1875` `_SLUR_ARC_PAD_NOTEHEADS = 0.25`.

### C37 — An arc over STEMMED notes is drawn stem-top to stem-top
- **Says:** the same reason as C12 — the arc is anchored at the stem tips, and a stem stands at the side of its notehead.
- **Category:** Slurs, ties & phrasing
- **Predicts (mechanically):** a notehead can be reached through its STEM, so the head-under test gains a stem probe; the span's endpoints stay the notehead centres, so the rule is purely ADDITIVE and needs no new constant.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID.
- **Evidence:** the distance from an arc's edge to the nearest head centre outside it has **median 0.52 notehead widths**. One record exported twice: `<slur>` **32 → 40**, `<tied>` **80 → 91**, `arc_binds_fewer_than_two_notes` **551 → 519**; notes, rests, dynamics, articulations, fermatas and accidentals **all identical**, note SEQUENCE unchanged (2460 == 2460), balance still an EQUALITY, tie starts resolving onto a note of their own pitch **27.5% → 30.8%**. ⚠️ `Q.STEM` "was gathered and read by nothing on this path (1,920 rows on one record) — **the third time that quantity has been found unread**". Sources: `CLAUDE.md` "PHASE 2 obs. 4"; `benchmarks/omr-arc-recovery-2026-09/FINDINGS.md`; `benchmarks/omr-arc-grammar-2026-09/SEAN_ARC_RULES.md:50-53`.
- **Would be falsified by:** a plate drawing slurs to notehead rims rather than stem tips (which would show as a different offset distribution).
- **Known exceptions:** unstemmed (whole-note) runs; and where the notes under the arc were never detected at all — **108 of 550 refused groups sit in bars where the detector produced NO notehead**.
- **Where it is used in the code:** `tools/omr/export.py` (stem probes inside the arc-to-notehead binding; imports `_stem_joined`'s box-overlap attachment). Legacy path deliberately passes no probes, asserted at the seam.

### C38 — One printed arc cut by a barline is still ONE arc
- **Says:** a slur or tie crossing a barline is one curve; the per-measure crop is ours, not the engraver's.
- **Category:** Slurs, ties & phrasing
- **Predicts (mechanically):** arcs must be paired over the STAFF in page pixels, not per measure — emitting each half writes two marks where the music has one.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID.
- **Evidence:** **120 arcs on the Brahms fixture against 82 slurs in the truth**. Three constants, each on a measured gap: "an arc was CUT by the boundary" **0.00–0.10 spaces vs 1.58** (constant 0.5); "the two halves are ONE slur" **0.02–1.14 spaces vs 8.04** (constant 2.0); "a notehead is UNDER the arc" **0.00–0.19 widths vs 0.32** (constant 0.25). "Each is a PLATEAU rather than a peak — the exported score is identical for the continuation tolerance anywhere in **1.0–6.0**". In the staged path the partition is exact: 514 arc rows → 476 merged groups, **38 arcs (7.4%) are one half of a cross-barline pair**; on another record **270 tie arcs → 261 merged groups**, and **32 of 199 arcs (16.1%) begin at their cell's left edge**. Sources: `CLAUDE.md` "Slurs"; `benchmarks/omr-ned-2026-08/SLURS_2026-09-01.md`; `benchmarks/omr-staged-arc-export-2026-09/FINDINGS.md`.
- **Would be falsified by:** the continuation-tolerance gap closing on a new edition. ⚠️ "**Re-check them when the geometry beneath them moves**: the continuation cluster's top went 0.53 → 1.14 across the system-grouping change, still inside the gap and changing no note, but it moved."
- **Known exceptions:** a slur crossing a **SYSTEM BREAK** needs a different anchor — "the resuming half begins ~**5.3 staff spaces** inside its cell, because the cell opens with a clef and a key signature, so it is anchored on the FIRST NOTE instead". Heights are compared RELATIVE to each staff's own top line. LilyPond never receives one (a LilyPond slur cannot span two Staff contexts).
- **Where it is used in the code:** `tools/omr/export.py:2498` `_merge_arcs_across_barlines`; `annotate_slurs_in_staff`, `annotate_slurs_in_slot`; `tools/omr/transcribe.py:2421` `_pair_ties_in_staff`.

### C39 — A tie's two ends are at ONE staff position, by definition
- **Says:** a tie joins two statements of the same note, so both heads sit at the same place on the staff.
- **Category:** Slurs, ties & phrasing
- **Predicts (mechanically):** among candidate flanking pairs, one whose heads share a staff position outranks one that does not.
- **Status:** MEASURED HERE — and ⚠️ **it was written in the code's own docstring and used by neither pairing rule for months.**
- **Rigid or publisher-dependent:** **RIGID on an ENGRAVING; NOT rigid on a scan** — see Known exceptions.
- **Evidence:** a **measured empty interval** on the eleven engraved fixtures, in staff spaces:

  | | n | bound |
  |---|--:|--:|
  | links whose two heads read the SAME pitch | 47 | max **0.168** |
  | ...plus the same-STEP spelling pairs | 11 | max **0.034** |
  | links whose heads read ONE STEP apart | 8 | min **0.435** |
  | links whose heads read further apart | 4 | min **0.906** |

  "An **empty interval from 0.168 to 0.435**, and a diatonic step is half a staff space by construction … 0.25 sits in the middle of it." Reach, as an upper bound on any pairing-choice repair: links whose two heads sit at one staff position **scan 122 → 183, engraved 58 → 59**; same-pitch **scan 98 → 150** (oracle 87 → 132), engraved 47 → 48. The engraved gain is **+1 link** (`bruckner-sym5-mvt1`, 3 same-position pairs → 4). Before the repair, the 20-of-79 engraved figure decomposed into **11 SPELLING** (same step, accidental differs — *the probe's* fault), **8 STEP_APART** (the arc's CLASS), **4 WIDE** (the pairing); on the scan **11 / 71 / 122**. ⚠️ **25 scan links sit at ONE staff position and disagree about pitch anyway.** Sources: `CLAUDE.md` "A tie's two heads are at ONE STAFF POSITION"; `benchmarks/omr-tie-pairing-2026-09/FINDINGS.md`.
- **Would be falsified by:** a corpus where the two distributions overlap.
- **Known exceptions:** ⚠️⚠️ **ON A SCAN THE INTERVAL IS NOT EMPTY, AND THIS IS THE ENTRY'S SHARPEST CAVEAT** — "same-pitch max **0.238** against a step-apart minimum of **0.013**". The convention is still true of the ink; what fails is our reading of the positions. "**Which is why this rule is expressed in boxes and never consults a pitch**", and why the constant may not be re-tuned on a scan. ⚠️ the rule is ADDITIVE and COMPARATIVE — it runs only where the old rule already paired both sides, "so the exported tie COUNT cannot move and every delta is a relocation". It reads **BOXES, never a pitch**, which keeps it clear of `OMR_ARC_RECLASS` (C42). ⚠️ **The scan price is unmeasured**: an export-only arm is structurally blind (the pairing runs in `transcribe`).
- **Where it is used in the code:** `tools/omr/transcribe.py:2418` `TIE_SAME_POSITION_MAX_SPACES = 0.25`, `:2421` `_pair_ties_in_staff`; mirrored at `tools/omr/export.py:2207` `_tie_flank_pair` with the constant IMPORTED, not restated.

### C40 — A TIE is drawn shallow and close to its two heads; a SLUR arcs clear of the notes under it
- **Says:** the two glyphs differ in depth relative to the notes they cover.
- **Category:** Slurs, ties & phrasing
- **Predicts (mechanically):** `depth_steps` would be the geometric half of the tie/slur grammar, which today decides on class and step-equality alone.
- **Status:** ASSERTED (untested here)
- **Rigid or publisher-dependent:** RIGID (by assertion).
- **Evidence:** **no figure.** Stated at `tools/omr/staged/positions.py:445-447`: "`depth_steps` is the fact worth having: a TIE is drawn shallow and close to the two heads it binds, a SLUR arcs clear of the notes under it. That is the geometric half of the `OMR_ARC_RECLASS` grammar". The row is now produced (`Q.ARC_POSITION`, behind `OMR_FAMILY_POSITIONS`, default OFF) and **read by nothing, deliberately**.
- **Would be falsified by:** measuring `depth_steps` over hand-adjudicated ties and slurs and finding the distributions overlap.
- **Known exceptions:** ⚠️ **CURVATURE IS NOT DERIVABLE FROM A BOX** — "a bounding box is identical for an arc opening up and one opening down", so `opens` is recorded as `None` rather than guessed. Reading it needs the ink, which `Q.INK` now gathers and nothing joins.
- **Where it is used in the code:** `tools/omr/staged/positions.py:433` `_arc_discriminator`. **No consumer** — listed as `UNREAD-POSITION Q.ARC_POSITION` in `tools/omr/staged/capture.py:630`.

### C41 — Sean's S4: an arc connected to the stem's edge AWAY from the notehead is a SLUR — REFUTED
- **Says:** where an arc meets a stem far from the head, the arc is a slur rather than a tie.
- **Category:** Slurs, ties & phrasing
- **Predicts (mechanically):** it would have supplied a tie/slur discriminator from geometry alone, needing no pitch.
- **Status:** **REFUTED HERE — at full width.**
- **Rigid or publisher-dependent:** n/a.
- **Evidence:** Sean, on being shown a first narrow refutation: ***"don't give up — adjust the rules to be broader."*** Widened (contact dropped, projected onto the head→stem-tip axis, scored ONE-SIDED as Sean stated it), reach **143 → 420 of 779**, **SIDE flat at −0.001 / −0.030**, the sweep never clearing **p = 0.079**, lift negative in all four strata. "**It is the WIDE test that fails, which is the strong negative**; the narrow sweep's non-monotonicity was a POWER problem." ⚠️⚠️ **S4's availability gradient INVERTS the usual one** — its arcs sit at median detector confidence **0.4196** against **0.5409** for those it cannot reach, so "it speaks *preferentially about the WEAKEST readings*. **A harder shape than an arbiter that merely falls silent, and it is new.**" ⚠️ The first pass had "measured a precondition and thrown it away" — 420 stemmed → **206 on the stem's side** → 143 touching stem ink, using the middle number as a FILTER and never scoring it. Sources: `CLAUDE.md` "Sean's arc rules S4/S6"; `benchmarks/omr-arc-grammar-2026-09/FINDINGS.md` §1-§2; rule text at `benchmarks/omr-arc-grammar-2026-09/SEAN_ARC_RULES.md:20`.
- **Would be falsified by:** it already is, on this document. n = 1 document.
- **Known exceptions:** **a narrow operationalisation failing is evidence about the operationalisation, not about the convention** — which is why the wide test was run, and why the wide result is the one that counts.
- **Where it is used in the code:** **not implemented anywhere.** `grep` for a stem attachment POINT returns nothing (`SEAN_ARC_RULES.md:43`).

### C42 — Sean's S6: of two arcs stacked over each other, the LOWER is a tie and the UPPER a slur
- **Says:** vertical stacking of two arcs names their kinds.
- **Category:** Slurs, ties & phrasing
- **Predicts (mechanically):** a pairwise discriminator for the only population it addresses — stacked pairs whose two readings DISAGREE.
- **Status:** MEASURED HERE — **supported, on a narrow and thin population, and deliberately NOT promoted.**
- **Rigid or publisher-dependent:** RIGID (by assertion); measured on one document.
- **Evidence:** S6's precondition (a y-disjoint sibling arc overlapping in x) is met by **442 of 779 arcs (56.7%)**, of which **181 pairs** have two readings that DISAGREE. S6 **holds at 0.740** on the tight band and "survives every relaxation while gaining only 8% population — robustness, not a bigger result". ⚠️ **The absolute-position form is already REFUTED at 0.517, so its power is PAIRWISE.** ⚠️⚠️ **The joint result is the largest finding of that job**: `OMR_ARC_RECLASS` (S2/S5) "scores BELOW its own majority baseline alone (**0.5043 vs 0.5275**) and reaches **0.750** where it concurs with S6 (**p = 0.0104**, 20,000-draw permutation null)". **Neither is promoted**: S6 would flip ~30 arcs a page and get **19 of 73 wrong** against a detector that is not truth. **The price to settle S6 is SEVENTY CROPS, not more arcs.** Sources: `CLAUDE.md` "Sean's arc rules S4/S6"; `benchmarks/omr-arc-grammar-2026-09/FINDINGS.md` §3; rule text at `SEAN_ARC_RULES.md:22`.
- **Would be falsified by:** seventy hand-adjudicated crops of stacked disagreeing pairs.
- **Known exceptions:** ⚠️ S6 may be confounded with the hugging rule `arc_owner` already applies — the findings raise it explicitly (§3, "S6 might be nothing but the hugging rule"). And "**S6 is a claim about ENGRAVING that our detector may not be able to see**" — its precondition had to be measured before the rule could be.
- **Where it is used in the code:** **not implemented anywhere** (`SEAN_ARC_RULES.md:43`).

### C43 — The tie/slur POSITION GRAMMAR (S2/S5: >2 notes ⇒ slur; different pitches ⇒ slur) — measured on both families and REFUSED
- **Says:** an arc spanning more than two notes is a slur; an arc whose flanked heads carry different pitches is a slur.
- **Category:** Slurs, ties & phrasing
- **Predicts (mechanically):** an export-time veto reclassifying the detector's arc class.
- **Status:** **REFUTED HERE** as a shipped default (the underlying convention is sound; the veto is refused for what it costs).
- **Rigid or publisher-dependent:** the convention is RIGID; the veto's cost is **document-dependent**.
- **Evidence:** engraved **0.1306 → 0.1306, +2 edits, 24 firings**; scan **0.8387 → 0.8391, +130 edits — REFUSED**, and per-direction attribution puts **ALL +130 in the tie→slur half** while slur→tie alone is edit-free and moves the tie inventory toward truth (420 → 462 of 805). ⚠️ **The figures in CLAUDE.md's knob row are stale and CLAUDE.md says so**: on the post-chord-tie tree engraved is **2530 → 2536, +6** and the scan **+149** (pre-mirror: +8 and +144). ⚠️⚠️ **Re-priced 2026-09-11: the tie→slur half is FOUR RULES that do not behave alike** — `tie_to_slur_flagged_diff_pitch` (PROVABLE: the flanked pair sits a staff step or more apart, which no tie can) fires **12** times and the three works where it fires ALONE are **−4 edits, i.e. BETTER**; every edit-positive work fires a `span` or `unpaired` rule, which are INFERRED. Scored against the tie INVENTORY the veto takes `mozart-sym41-mvt1` from **8 ties over its truth to exactly right**, summed per-work error **25 → 18**. The reason the scan side loses is structural: "a scan's resolved pitch at an arc's ends is downstream of exactly what scans get wrong (`wrong note` = 26% of that pool)". Sources: `CLAUDE.md` `OMR_ARC_RECLASS`; `benchmarks/omr-export-gaps-2026-09/FINDINGS.md`; `benchmarks/omr-tie-pairing-2026-09/FINDINGS.md` §4.
- **Would be falsified by:** the `diff_pitch` half measured alone on a scan.
- **Known exceptions:** ⚠️ it **compares STEPS, never spelled pitches** — the naive spelled-pitch key broke truth-matched cross-barline ties (+21 engraved edits, every loss a same-step `F#4→F4` pair). See C21.
- **Where it is used in the code:** `OMR_ARC_RECLASS`, default OFF, flag-off byte-identical. Staged mirror: `adjudicate_arc_kind` **RECORDS** the grammar without acting on it — available on **81 of 199** arcs, agreeing **42** / disagreeing **39**, "a coin flip", with 28 of the 39 in the expensive direction.

### C44 — A bar's first note sits 2.0–2.5 staff spaces past the barline
- **Says:** the engraver leaves a fixed indent after a barline before the first note.
- **Category:** Slurs, ties & phrasing
- **Predicts (mechanically):** it *would* let a cross-barline arc whose continuation fragment is ~0 px wide reach the next bar's first chord — and it is exactly why that reach is REFUSED.
- **Status:** MEASURED HERE — and used to **refuse** a rule, not to build one.
- **Rigid or publisher-dependent:** RIGID on the document measured.
- **Evidence:** "a bar's first note is **2.0-2.5 staff spaces past the barline on all 282 edge-reaching arcs**, so any window wide enough to admit it admits every next-bar first note and the rule degenerates to *'an arc touching a barline lands on the next bar's first note'*. That is a tie-break among candidates the ink does not distinguish — **INFER-shaped work**". Modelled, the cross-barline reach is worth **+13 alone and +19 on top of the stem rule**, and the two are **SUPER-ADDITIVE (171 → 199 → 218)**. Source: `benchmarks/omr-arc-recovery-2026-09/FINDINGS.md`.
- **Would be falsified by:** a plate whose post-barline indent varies enough to discriminate.
- **Known exceptions:** none recorded. The distribution is TIGHT, which is precisely the problem.
- **Where it is used in the code:** **deliberately no consumer** — recorded with its reach "so a session holding the print can adjudicate it".

---

## Dynamics & hairpins

### C45 — A hairpin is printed BELOW its staff, in the dynamics band
- **Says:** a wedge lives in the band from the staff's bottom line down toward the next staff's top.
- **Category:** Dynamics & hairpins
- **Predicts (mechanically):** search staff N's own band in page pixels; a reader that does this **never creates the cross-staff contest** in the first place.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID.
- **Evidence:** "**8 of 8** [hairpins] in the page truth sits below a staff and none inside one". The band is the staff's bottom line + ~0.5 spaces to the next staff's top — shipped as `BAND_TOP_SPACES = 0.3` / `BAND_BOTTOM_SPACES = 6.0`. The contrast that makes the band the *fix*: the hairpin reader "works in **page pixels per staff** so attribution is right BY CONSTRUCTION, while the letters go through per-measure cells and lose **24%** to the staff above". Reading F1 on hairpins against exact page truth is **1.000** (n=3) on engravings and ~1% on scans (1 hairpin detected against 198 `<wedge>` of truth). Sources: `docs/scope-cv-hairpin-detection-2026-09-04.md` §2; `CLAUDE.md` "Hairpins"; `benchmarks/omr-hairpin-cv-2026-09/`.
- **Would be falsified by:** a hairpin printed above its staff (piano scores put them between the staves, still below the upper one).
- **Known exceptions:** ⚠️ **the band is crowded** — it also holds slur and tie arcs and the words `pizz.`, `espr.`, `arco`; on Brahms 1 p2 two tests cut 471 band components to **69**. So the band bounds the search; it does not identify the mark.
- **Where it is used in the code:** `tools/omr/hairpin_detection.py:80-81` `BAND_TOP_SPACES = 0.3`, `BAND_BOTTOM_SPACES = 6.0`; cited at `tools/omr/staged/gather.py:957`.

### C46 — A dynamic LETTER stands in its own staff's band, below the bottom line
- **Says:** `p`, `f`, `sf` are printed in the same band as the hairpins, belonging to the staff above them.
- **Category:** Dynamics & hairpins
- **Predicts (mechanically):** a letter detected in a measure cell but standing in the band of the staff ABOVE belongs to that staff, not to the cell it was cropped in.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID.
- **Evidence:** over **1,246 letters on 18 pages of 9 publishers**, **73% of letters stand in their own staff's band, 24% in the band of the staff immediately above — distance exactly 1, no exceptions**. Pooled widest empty interval **−3.04 to −0.52 spaces**; the lower edge is a plateau (−1.5 to +0.25 changes nothing); the population runs **+0.0 to +5.6 spaces with a 2.5-space empty gap under it**. ⚠️ **A GATE IS THE WRONG FIX**: **83% of re-attributed letters are the target staff's SOLE evidence**, because `_dedupe_cross_staff_detections` already removed the twin BY DISTANCE. Re-attribution priced: canonical 11 engraved works over-emission **1.19 → 1.04**, staves exact by word **52 → 83 of 107**, no work worse; **11 scanned pages: 16 → 16** (flat, because there we UNDER-emit — 376 words against 491). Sources: `CLAUDE.md` "Dynamics letters are placed but never checked"; `benchmarks/omr-dynamics-band-2026-09/FINDINGS.md`.
- **Would be falsified by:** a plate printing dynamics above the staff as a rule.
- **Known exceptions:** on a scan the dominant dynamics error is "**a mark never found, not one on the wrong staff**", and **137 of a 129-mark shortfall come from two scans of one page**.
- **Where it is used in the code:** ⚠️ **the belonging rule has NO consumer** — `Q.DYNAMIC_BAND_POSITION` now exists (`tools/omr/staged/positions.py`, behind `OMR_FAMILY_POSITIONS`, default OFF) and "`adjudicate_dynamic` still does not read it" (`tools/omr/staged/capture.py:604-611`). The band constants are consumed only by the hairpin reader.

### C47 — A dynamic WORD is a run of adjacent letters (`f`+`f` = `ff`)
- **Says:** compound dynamics are set as separate glyphs whose boxes nearly touch.
- **Category:** Dynamics & hairpins
- **Predicts (mechanically):** assemble adjacent `dynamic*` letters by x-adjacency into a word, then look it up.
- **Status:** MEASURED HERE — and **the assembly is where it breaks.**
- **Rigid or publisher-dependent:** RIGID for the engraving; the *assembly* failure is document-dependent.
- **Evidence:** ⚠️ **a flat IoU rule inside a cell would delete real ink** — the first same-cell dynamic pair found is two `dynamicF` at IoU **0.317, 21 px apart, both real: the two `f`s of a printed `ff`**, whose boxes are wider than the gap between them. Over 255 same-cell dynamic pairs the centre offset spreads **72 / 87 / 93 / 3** across `<0.25w` / `0.25-0.5w` / `0.5-0.75w` / `>=0.75w` — "**the populations do not separate**, widest empty interval 0.097", where noteheads DO separate (405 of 458 under 0.25w). ⚠️ Against the convention: on one committed transcription **15 of 20 dropped runs are a prefix of NOTHING and the shape is `ppmsf` / `ppzmf`** — "five letters run together, which no dynamic is", an ASSEMBLY failure. Re-assembling on the MEDIAN letter width rather than the max is **not the lever** (kept runs 159 → 162, dropped still 20, `ppmsf` intact). Exporting the partial run was measured over the 20-row gate and **REFUSED**: `complete` **+15 edits**, `other` **+30**, and **NOT ONE ROW BETTER**. Sources: `CLAUDE.md` `OMR_PARTIAL_DYNAMICS` and "A CONTEST is RESOLVED, not relocated"; `benchmarks/omr-dynamics-staged-2026-09/FINDINGS.md`.
- **Would be falsified by:** a same-cell letter-pair population that separates on geometry (it does not).
- **Known exceptions:** ⚠️ **the `ffff` was one printed `ff` detected twice across two staves**, resolved by the ownership contest, not by geometry: `ffff` **11 → 2**, `sf` **9 → 34**. ⚠️ And `ff` **47 → 39** in that repair is "an unadjudicated COST, not a win" — eight words where the record supports both readings and only the print can say.
- **Where it is used in the code:** `tools/omr/export.py` `measure_dynamics` (`_DYNAMIC_WORDS`, 17 words); `OMR_PARTIAL_DYNAMICS` default `off`.

### C48 — A hairpin runs quiet → loud (or loud → quiet) and travels with a dynamic letter
- **Says:** a crescendo begins at a softer dynamic than it ends; the letters near it corroborate its direction.
- **Category:** Dynamics & hairpins
- **Predicts (mechanically):** the letter either side of a wedge is additive evidence about its direction.
- **Status:** MEASURED HERE — **strictly LOCAL, and it is a rate, not a rule.**
- **Rigid or publisher-dependent:** RIGID musically; the *reach* is document-dependent.
- **Evidence:** on the one committed reference encoding (Brahms 1, **683 hairpins**): the claim is **exact at ±1 measure (34/34)** and **wrong 31.8% at ±4**; reach **5.0% → 19.3%** across the same widening. "Keep it at ±1, ABSTAIN beyond, and it is **additive evidence over ~5% of hairpins, never a veto**". ⚠️ An earlier pass quoted "wrong three times in ten" off ONE asymmetric window — "a point on the curve, not a property of the rule". Source: `benchmarks/omr-dynamics-coupling-2026-09/probe_letter_wedge_coupling.py`; `docs/scope-dynamics-reading-2026-09-09.md`.
- **Would be falsified by:** the ±1 figure falling on a second encoding.
- **Known exceptions:** `cresc.` into a *subito* `p` is standard — which is why the window may not be loosened.
- **Where it is used in the code:** **no consumer found.**

### C49 — An ACCENT is note-anchored; a HAIRPIN is span-anchored
- **Says:** the same `<` mark is an accent when it is notehead-scale and stacked with one head, and a hairpin when it covers two or more note onsets in the dynamics band.
- **Category:** Dynamics & hairpins
- **Predicts (mechanically):** *note-anchor vs span-anchor* separates the family; **width alone does not** — one-beat hairpins exist.
- **Status:** ASSERTED (untested here)
- **Rigid or publisher-dependent:** RIGID (by assertion).
- **Evidence:** **no figure for the discriminator.** Stated in `docs/position-grammar-confusables-2026-09-04.md` §2 WEDGE (Sean's own example): "Width alone fails — one-beat hairpins exist; *note-anchor vs span-anchor* does not. (Marcato is the vertical wedge; same family.)" The nearest supporting number is indirect: on the scan corpus the truth carries **20 hairpins across the five verified rows and the detector fires on none**, so the confusion has never been priced.
- **Would be falsified by:** measuring width and anchor-count on hand-adjudicated accents and hairpins.
- **Known exceptions:** none recorded.
- **Where it is used in the code:** **no consumer found.** `gather_glyph_families` routes by CLASS (`dynamicCrescendoHairpin` carries category `dynamic`), which sidesteps rather than solves it.

### C78 — A beam is always connected to something; a HAIRPIN is connected to NOTHING
- **Says:** Sean's own test. A beam joins stems, a slur meets noteheads, a barline meets staff lines — a hairpin touches no other ink on the page.
- **Category:** Dynamics & hairpins
- **Predicts (mechanically):** compare a band component's area to the area of the full-page connected component it belongs to. For a hairpin the two are the same object; for anything attached, the page component is vastly larger.
- **Status:** MEASURED HERE — and it comes out as a **binary, not a threshold.**
- **Rigid or publisher-dependent:** RIGID.
- **Evidence:** full-page component area ÷ candidate area, over the band components of Brahms 1 p2: **p25 1.0× (44 isolated); p50 1.0×; p75 3248.0× (25 attached); p90 9167.3×** — "**Nothing lies between 1× and 3248×.** That is what a constant read off a gap looks like, and it is a binary rather than a threshold." Combined with the open-extent test, **471 components with measurable outlines → 69 candidates at 0.10 staff spaces, against ~68 hairpins on the page**. ⚠️ **Extent alone is REFUTED**: "Of 312 band components, **302** clear an open extent of 0.4 staff spaces, against ~68 hairpins." ⚠️ **Fill ratio is REFUTED** as a discriminator: "fill runs **p10 0.375, median 0.437, p90 0.737** — nothing survives below 0.35." End to end, truth `<wedge>` **198**, before **2**, after **106** — "**1% of the truth's wedges reached the file before; 54% do now.**" Source: `benchmarks/omr-hairpin-cv-2026-09/FINDINGS.md`.
- **Would be falsified by:** a plate where a hairpin's arm touches a slur or a stem (the gate would then drop it).
- **Known exceptions:** ⚠️ **yield is page-dependent, not just publisher-dependent** — over the scan gate, truth hairpins / candidates / YOLO reads **99 / 59 / 1**, and Mahler p3 gives **2 candidates against 17 truth hairpins** while Brahms p2 gives 44 against 68.
- **Where it is used in the code:** `tools/omr/hairpin_detection.py` (`MAX_COMPONENT_GROWTH = 2.0` at `:94`, the isolation gate; `MIN_OPEN_SPACES = 0.5` at `:84`; `MAX_OUTLINE_RMS_SPACES = 0.10` at `:86`). Behind `OMR_CV_HAIRPINS`.

---

## Articulations & ornaments

### C50 — An augmentation dot sits at the note's own space — half a space ABOVE for a note on a line — and NEVER below
- **Says:** a note in a space takes its dot in the same space; a note ON a line takes it in the space above.
- **Category:** Articulations & ornaments
- **Predicts (mechanically):** the dot-to-note window is **ASYMMETRIC**, and it must be expressed in STAFF SPACES (the note's unit), not in the dot's own bounding box.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID.
- **Evidence:** over the **116 dots** of three works, the signed offsets are "**bimodal and nothing else: 52 at 0.00 spaces, 52 at +0.50, nothing between +0.57 and +3.75**". The old gate was `max(dot.height, 12) * 1.2` — derived from the dot's own box, "which is small and mostly detector noise" — so the on-a-line case "landed within a few pixels of the threshold and went either way": C Horn 1's dotted half read as a half in bars 1 and 5 and as a dotted half in bars 2, 3, 4 and 6. ⚠️ **The asymmetry is forced by double stops**: Brahms's Viola plays two noteheads a space apart each with its own dot, "so the lower dot is equidistant from both noteheads, a symmetric window ties, and the upper note comes out double-dotted while the lower loses its dot". Sources: `CLAUDE.md` "Durations: two units"; `docs/position-grammar-confusables-2026-09-04.md` §2 DOT.
- **Would be falsified by:** a dot printed under its note.
- **Known exceptions:** ⚠️ **the pool must include RESTS** — "dots after rests are rarer but real". Widening the staged reader to match the legacy `_pair_dots_to_targets` moved **ZERO verdicts** on Litolff (20 `aug_dot` rows over three pages) and, on the 656-dot Breitkopf record, attaches **exactly ONE dot to a rest and that one is FALSE** (width **0.180** staff spaces against a median of 0.490, rank 1 of 656; the crop shows a clean UNDOTTED whole rest). **Of 691 `aug_dot` rows across two publishers, exactly one attaches to a rest, and it is wrong.**
- **Where it is used in the code:** `tools/omr/rhythm.py:1118` `DOT_ABOVE_NOTE_MAX_SPACES = 0.75`, `:1133` `DOT_BELOW_NOTE_MAX_SPACES = 0.25`, applied at `:1163-1164` inside `_pair_dots_to_targets` (`:1136`); staged `tools/omr/staged/adjudicators/rhythm.py:63-64`, applied at `:335-336` inside `_attached_dots` (`:284`). ⚠️ **The two copies are DUPLICATED LITERALS, not a shared import** — every other measured constant in this area (`TIE_SAME_POSITION_MAX_SPACES`, `_WEDGE_*`, `_ARC_RIVAL_*`) is imported specifically to prevent drift, so this pair is the odd one out. ⚠️ The old box-derived gate cost **193 edits**, which is the figure the articulation constant's own docstring cites as the reason to express a window in the NOTE's unit.

### C51 — A staccato or accent is printed directly above or below its notehead, on the side its class names
- **Says:** the mark is x-centred on its note, on the side away from the stem.
- **Category:** Articulations & ornaments
- **Predicts (mechanically):** match each mark to the notehead nearest it in **x**, on the side the class name states, within a notehead-width window; **a mark with no notehead on the correct side is left unattached** rather than given to the nearest thing available.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID.
- **Evidence:** swept over eight works and scored against truth by index, the window is a **flat plateau from 0.50 to 2.50** — 197 placed, precision **0.980**, placement rate **0.904** — "with a cliff below it" at 0.30 (106 placed, placement 0.486). The constant 0.75 "sits in the middle of the plateau rather than on either edge". **21 of 218** marks across the corpus have no notehead on the correct side and are abstained on — "and abstaining there is why precision is 0.980". Mozart 40 detects **exactly 102 staccati and was charged exactly 102 `insarticulation` edits** before this shipped. Sources: `tools/omr/transcribe.py:2560-2573` (the sweep table is in the source comment); `benchmarks/omr-corpus-widening-2026-09/probe_articulations.py`; `CLAUDE.md` "Articulations".
- **Would be falsified by:** the plateau disappearing on a plate that sets marks off-centre.
- **Known exceptions:** ⚠️ **this shipped while making pooled OMR-NED WORSE by 97 edits** — −122 across eight works and **+219 on `boulanger-printemps-mvt1` alone**, whose bars do not pair, "so every correct symbol added to one raises a charge already being levied whole". ⚠️ **The side taken off the class NAME is not a ruler** — "`side` is DERIVED FROM THE CLASS so it fails together with the classification, and above/below is a BIT where the question is a distribution".
- **Where it is used in the code:** `tools/omr/transcribe.py:2573` `_ARTIC_MAX_DX_NOTEHEAD_WIDTHS = 0.75`, `:2594` `_attach_articulations_in_cell`, `:2577` `articulation_kind`. The independent ruler (`measured_side`, `steps_clear_of_staff`) exists at `tools/omr/staged/positions.py:473` and is **read by nothing**.

### C52 — A FERMATA hangs over whatever sounds beneath it — which is often a whole-bar rest, not a note
- **Says:** unlike an articulation, a fermata does not attach to a notehead.
- **Category:** Articulations & ornaments
- **Predicts (mechanically):** the articulation attach rule (nearest notehead on the class's side) **structurally cannot reach more than half of this population**, so fermatas need their own router and their own distribution.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID.
- **Evidence:** **26 of 51 fermata carriers are RESTS** on Litolff pp.1-3 — "and that is why the router is by CLASS": `fermataAbove` carries the detector's `ornament` CATEGORY, shared with all ten `artic*` classes, so a category-keyed router would apply the articulation rule to them. Reach: **63 glyphs on Litolff p1-3, 0 on Brahms**; 51 decided → **37 `<fermata>`**, byte-identical outside them. ⚠️ The `nearest_in_bar` fallback **fired ZERO times**. ⚠️ The 13 "absorbed" marks are **DUPLICATE DETECTIONS, not chords**. Sources: `CLAUDE.md` "Three families wired in one pass"; `benchmarks/omr-staged-fermata-2026-09/FINDINGS.md`; `tools/omr/staged/capture.py:655-661`.
- **Would be falsified by:** a corpus where fermata carriers are overwhelmingly noteheads.
- **Known exceptions:** the two populations must not be pooled — "pooling them would average a mark that attaches to a notehead with one that does not".
- **Where it is used in the code:** `tools/omr/staged/gather.py` `gather_glyph_families` (routed by CLASS); `adjudicate_fermata_owner`. The position row `Q.FERMATA_POSITION` is kept **APART** from the articulation's, deliberately, and is read by nothing.

### C53 — A TUPLET digit stands OUTSIDE the staff over its beam; a TIME-SIGNATURE digit stands INSIDE it; a FINGERING sits beside its notehead
- **Says:** one printed digit has at least four roles, and **where it stands** is the only thing that separates them.
- **Category:** Articulations & ornaments
- **Predicts (mechanically):** both `tuplet3` and `fingering3` may be read, because a positional gate — not the class name — keeps it safe.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID.
- **Evidence:** over twelve engraved works, **33 `fingering3` against 16 `tuplet3`, and all 33 sit in a cell that holds a real triplet**; the single detection that does not is a `tuplet3`. Admitting the class took Mahler **0.0455 → 0.0331** with its duration rate **0.864 → 1.000**, and `tchaikovsky-sym6-mvt2` **0.2321 → 0.1958**. ⚠️ **This corrected a claim that stood in CLAUDE.md for a day** — the Mahler group said to "carry no marker at all, at any confidence" carries a `fingering3` at **0.72**, the highest-confidence tuplet marker on that page. Sources: `CLAUDE.md` "Tuplets"; `benchmarks/omr-corpus-widening-2026-09/FINDINGS.md`; `tools/omr/staged/positions.py:410` `_tuplet_discriminator`.
- **Would be falsified by:** a real fingering centred over a beamed group of exactly three — "no conductor's score in the corpus prints one to price that against".
- **Known exceptions:** ⚠️ one **`numeral`** class in the coarse half of the 208-class space covers meters, tuplet digits, fingerings **and measure numbers** under one name — `numeral4` is NOT `timeSig4`, and a spurious `timeSig4` once shipped a 2/4 page as common time at **390 bar-check failures**. ⚠️ `adjudicate_tuplet` fired **zero times across 286 runs** of the plumbing matrix.
- **Where it is used in the code:** `tools/omr/rhythm.py` `resolve_rhythms_for_cell` (positional gate); `tools/omr/class_aliases.py` `COARSER_THAN_CANONICAL`; `tools/omr/staged/positions.py:410` (recorded, unread).

### C54 — A tuplet DIGIT is printed over the middle of its group; a tuplet BRACKET encloses it
- **Says:** the two markers of the same fact sit differently, so they must be read differently.
- **Category:** Articulations & ornaments
- **Predicts (mechanically):** the digit's CENTRE must fall inside the group's span; the GROUP must fall inside the BRACKET's span.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID.
- **Evidence:** "detected brackets are far wider than the notes they cover (**one measured at 1846px over a 478px group**) and testing a bracket's centre rejects every one of them". Which notes are in the group comes from the **BEAM box**, not the marker, padded by a notehead width "because it bounds beam INK, which starts at the first stem — unpadded, every stem-up group loses its first note". Tuplets overall: pooled **0.2595 → 0.2489**, Mahler **0.0826 → 0.0455**, duration rate **0.318 → 0.864**, Beethoven and Brahms byte-identical. Source: `CLAUDE.md` "Tuplets".
- **Would be falsified by:** an edition centring the bracket tightly on its group.
- **Known exceptions:** ⚠️ **a GROUP is a set of notes, not a beam stroke** — a sixteenth carries two beam strokes and the ratio was applied once per stroke, giving `(1/4) × (2/3) × (2/3) = 1/9`; `mozart-sym41-mvt1` prints 40 groups of triplet sixteenths and cost **464 edits** for it. Identical member sets are now collapsed.
- **Where it is used in the code:** `tools/omr/rhythm.py` `resolve_rhythms_for_cell` / `_beamed_groups`.

### C55 — A TREMOLO rides the stem, so it has no side at all
- **Says:** unlike every other ornament, a tremolo is drawn on the stem rather than above or below the note.
- **Category:** Articulations & ornaments
- **Predicts (mechanically):** for this class the class name carries no position of any kind, so a ruler is the only thing that can place it.
- **Status:** ASSERTED (untested here)
- **Rigid or publisher-dependent:** RIGID (by assertion).
- **Evidence:** **no figure, and none is possible today.** Stated at `tools/omr/staged/capture.py:665-669`: "a TREMOLO's side is `None` because it rides the stem, so for that class the class name carries no position of any kind and the ruler is the only thing that does." The reach is zero: the detector produces **ZERO tremolo detections over 34,115**, against an eleven-work truth whose only ornaments are **twelve `<tremolo>`** — and `tremolo1`-`5` "ARE ornaments whose class names do not begin `ornament`". The label corpus carries **46** hand-labelled tremolo boxes the checkpoint does not reproduce.
- **Would be falsified by:** a detector that fires on tremolos, then measuring their offsets.
- **Known exceptions:** LilyPond is deliberately not given tremolo at all — `c4:32` is a duration SUBDIVISION, "so a wrong mapping writes a different rhythm rather than a different mark".
- **Where it is used in the code:** `tools/omr/transcribe.py` `_ORNAMENT_KINDS` (asks the kind list rather than prefix-matching); position recorded and unread.

### C87 — A TRILL, TURN or MORDENT is printed clear ABOVE its note, centred on it
- **Says:** unlike an articulation, whose side its class name states, an ornament's side is fixed by convention — above.
- **Category:** Articulations & ornaments
- **Predicts (mechanically):** it is "an articulation's geometry with the side fixed by convention rather than stated by the class name" — so the same nearest-notehead-in-x rule applies, with `above` hard-coded rather than parsed.
- **Status:** ASSERTED (untested here) — the side is a convention; only its REACH was measured.
- **Rigid or publisher-dependent:** RIGID (by assertion).
- **Evidence:** the convention carries **no sweep and no plateau**, and the code says so: `_ORNAMENT_MAX_DX_NOTEHEAD_WIDTHS = 1.0` is **"declared UNMEASURED"**, "against the articulations' swept-plateau `0.75`" — "unlike the articulation constant it copies, **no corpus exists to sweep it on**". Reach is measured: **4 of the 8 `ornamentTrill` detections find a notehead** within 1.0 notehead widths on the printed-above side (dx **4–13.5 px** against a median notehead width of ~30–40 px); placed confidences 0.70, 0.34, 0.74, 0.36, unplaced 0.31, 0.49, 0.56, 0.41. A/B: ledger rows **6086 → 6090**, `<ornaments>` in the XML **0 → 4**, **non-ornament rows identical (6086 / 6086)**. Sources: `benchmarks/omr-export-gaps-2026-09/FINDINGS-2026-09-08-ornaments-and-the-derived-check.md`; `tools/omr/transcribe.py:2677` `_ORNAMENT_KINDS`, `:2699`.
- **Would be falsified by:** a plate printing trills below the staff for a stem-up voice.
- **Known exceptions:** ⚠️ **a TREMOLO is the exception in the same family** (C55) — it rides the stem, so `above=None` means "do not test the side" at all.
- **Where it is used in the code:** `tools/omr/transcribe.py:2677` `_ORNAMENT_KINDS`, `:2699` `_ORNAMENT_MAX_DX_NOTEHEAD_WIDTHS = 1.0`.

---

## Score layout & systems

### C56 — A barline runs the FULL HEIGHT of its system, and nothing else does
- **Says:** the systemic barline and the bracket span exactly the system; a stem, a slur or a measure number does not.
- **Category:** Score layout & systems
- **Predicts (mechanically):** a column of ink inked through the whole of an inter-staff gap **VETOES** a distance-based system break; and on a braced two-staff system, a stroke spanning from the top of the upper staff to the bottom of the lower is a barline rather than a stem.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID.
- **Evidence:** within one Brahms system the inter-staff gaps run **17–237 px** and within one Beethoven system **130–345 px** — "both wider than the gaps BETWEEN systems on a piano page — and x-overlap is 1.00 for every pair, so **no distance threshold can separate them**". Connectivity grouping took Brahms **12 → 1 system**, Beethoven **4 → 1**, and Beethoven's measure count **14/8 → 8/8 exact**. For the brace case: on WTC I Prelude 1 p.4 the left hand read all four barlines of every system and the right hand "read none of them and **31 of its own stems**", so five systems of three bars came out as ONE bar (now 4,4,4,4,4,4). ⚠️ The gap test alone is **not** enough there — "a fugue's long stem crosses the brace gap and scores **1.00** connectivity". Sources: `CLAUDE.md` "System grouping is decided by CONNECTIVITY" and "A barline is a straight line"; `docs/position-grammar-confusables-2026-09-04.md` §2 VERTICAL STROKE.
- **Would be falsified by:** a non-barline object spanning a whole system (a full-system bracket is one — see C58).
- **Known exceptions:** the rescue is **ADDITIVE**: "letting the span test filter instead costs every system its opening rule, which often does not span the brace".
- **Where it is used in the code:** `tools/omr/staff_detector.py` `_gap_is_bridged`; `tools/omr/measure_extractor.py` `_spans_system`.

### C57 — A barline is a STRAIGHT line, not a vertical one
- **Says:** the engraver rules it straight; the SCAN then shears it.
- **Category:** Score layout & systems
- **Predicts (mechanically):** a barline column must be FITTED to the staves that observed it and probed along the fit, not sampled at a mean x.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** the convention is RIGID; **the drift is a property of the SCAN.**
- **Evidence:** "one barline's x drifts **monotonically by up to 40 px** between the top staff and the bottom, over **three times the clustering tolerance**", so three real barlines that had passed the vote (9, 12 and 10 of 12 staves) scored **0.27–0.36** against a 0.40 gate and were thrown away. Page 1: **17/17 barlines, 0 false, 16 measures of 16**; pages 2-6 unchanged. ⚠️ The fit uses **Theil-Sen and not least squares**, "because a note stem that joins the cluster votes too and two such among nine still dragged a least-squares fit off the line". Sources: `CLAUDE.md` "A barline is a straight line"; `docs/ask-first-conventions.md` §2.
- **Would be falsified by:** a corpus where the mean-x column and the fitted line agree (engraved input, by construction).
- **Known exceptions:** none recorded.
- **Where it is used in the code:** `tools/omr/measure_extractor.py:321` `_barline_x_at`.

### C58 — Interior barlines STOP at instrument-family boundaries
- **Says:** orchestral engraving breaks the barlines between families, so where a barline stops names a group edge.
- **Category:** Score layout & systems
- **Predicts (mechanically):** family boundaries can be INFERRED from where the interior barlines stop — no bracket detection required. And a "choir-barred" system (interior barlines stopping at choir edges) must never be flipped into open-score mode.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** **PUBLISHER-DEPENDENT** — "'what crosses this gap' is a property of the edition's convention, not of whether a system ends. B9 and B5 happen to run barlines across group gaps, which is why every signal looked perfect on them."
- **Evidence:** the inference beats reading the bracket, against hand-read print truth: Bach / Peters printed **3|3|3** — bracket reader **5 of 22** exact, incumbent pixel rule **16/22**, the columns rule **22/22 (21 exactly `[2,5,8,9]`)**; Brahms / Breitkopf printed **9|5** — bracket reader **1 of 15**, pixel rule **0/15**, columns rule **15/15 exactly `[8]`**. Within-page instability **0.384 → 0.055** over 144 pages and five publishers. ⚠️ **The pixel rule could never have worked**: the numerator is ~3 spanning objects and the denominator is how many bars the system prints, so the ratio is ≈ `3/(n_bars+3)` and crosses 0.5 near three bars a system — over **2841 gaps the largest value below the cut is 0.4962 and the smallest above is 0.5000**. Sources: `CLAUDE.md` `OMR_BRACKET_COLUMNS`, `OMR_CHOIR_GROUPING`; `benchmarks/omr-bracket-stability-2026-09/FINDINGS.md`; `benchmarks/omr-bracket-reading-2026-09/FINDINGS.md`; `NOTES.md:199`.
- **Would be falsified by:** an edition whose interior barlines cross family boundaries (B9 and B5 do — see rigidity).
- **Known exceptions:** ⚠️ `BRACKET_COLUMN_MIN_EVIDENCE = 3` is load-bearing — a LilyPond render bars per staff and "a 25-staff Bruckner system carries two crossing columns total", from which the rule manufactured **11 groups** without the floor.
- **Where it is used in the code:** `tools/omr/system_grouping.py`; `tools/omr/measure_extractor.py` (cue C); `OMR_BRACKET_COLUMNS` (default ON).

### C59 — A bracket BLOCK is an engraving unit, not an instrument family
- **Says:** publishers bracket by page layout, not by orchestral family.
- **Category:** Score layout & systems
- **Predicts (mechanically):** a consumer must not read a bracket block as "these staves are one family".
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** PUBLISHER-DEPENDENT.
- **Evidence:** "Breitkopf brackets **winds + brass + timpani as ONE block** against the strings (`out/crops/brahms-p3-gap2.png`: the bracket runs straight through the clarinet/bassoon boundary; `brahms-p3-gap8.png`: it terminates between timpani and violin I while the systemic barline runs on)." Brahms 1 p.1 reads blocks **`[2,2,2,2,2,7,1,3]`** — five PAIRS that are `2 Flöten`, `2 Oboen` and so on. Sources: `benchmarks/omr-bracket-reading-2026-09/FINDINGS.md` headline 1; `tools/omr/staged/ASSUMPTIONS.md` A-GROUP-2.
- **Would be falsified by:** an edition whose brackets track families exactly (Peters's 3|3|3 nearly does).
- **Known exceptions:** none recorded.
- **Where it is used in the code:** consumed as a **refusal** — `tools/omr/staged/adjudicators/` `group_symbol` abstains without identity rather than reading a 2-staff block as a brace.

### C60 — Some publishers print NO section bracket at all
- **Says:** whether family brackets are printed is an edition property.
- **Category:** Score layout & systems
- **Predicts (mechanically):** a reader that requires a bracket to find family boundaries fails outright on those editions.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** **PUBLISHER-DEPENDENT.**
- **Evidence:** read off the print at 600 dpi, by hand, over the five editions in the scan corpus: **Peters (Bach) yes, 3; Breitkopf (Brahms 1) yes, 2; unidentified Mahler 5 scan yes; Litolff (Beethoven 5) NO — one bracket, whole orchestra; Simrock (Dvořák 9) NO — one bracket, whole orchestra, + braces on pairs.** **Two of the five.** Source: `benchmarks/omr-bracket-reading-2026-09/FINDINGS.md` headline 1.
- **Would be falsified by:** re-reading those plates and finding section brackets.
- **Known exceptions:** none recorded.
- **Where it is used in the code:** the bracket reader `tools/omr/bracket_reader.py` exists with **no consumer, no flag** — "Recommendation: do not wire it in."

### C61 — No left-edge object ever bridges a system break
- **Says:** a bracket, brace or systemic barline belongs to exactly one system.
- **Category:** Score layout & systems
- **Predicts (mechanically):** the connectivity VETO is safe — an object at the left edge can merge two staves but never two systems.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID.
- **Evidence:** over **57 pages, 0 of 147 read blocks span two systems**. ⚠️ **But Sean's stronger hypothesis — that these objects define a system's EXTENT — is only half right**: "on a section-bracketed edition the maximal left-edge object is a section bracket, so the reading **over-splits on 27 of 57 pages** (Bach **0 of 11** exact, against Litolff's one-bracket pages at **7 of 12**)". Source: `benchmarks/omr-bracket-reading-2026-09/FINDINGS.md` headline 4.
- **Would be falsified by:** a left-edge object crossing a system gap.
- **Known exceptions:** the property licences a VETO only, not a positive system reader.
- **Where it is used in the code:** `tools/omr/staff_detector.py` `_gap_is_bridged` (the existing veto relies on exactly this property).

### C62 — A printed score may OMIT a tacet part; it may never REORDER one
- **Says:** the staves of a short system map to the full lineup in strictly increasing order.
- **Category:** Score layout & systems
- **Predicts (mechanically):** a short system's unnamed staves are constrained by their named neighbours above and below; enumerate every order-preserving assignment and take a slot only where **every** surviving assignment agrees. Joining by ORDINAL, by contrast, grafts one instrument's music onto another the moment an interior staff is suppressed.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID.
- **Evidence:** the name rule reproduces its probe "in every cell — **50 placed / 50 correct / 0 wrong / 25 abstained**", with the arms differing on **28 of 75** staves; **75 fragments → 37 parts, 12 grafts → 0**. Against the ordinal incumbent on the same 75 staves: ordinal **75 placed, 63 correct, 12 WRONG, 0 abstained**; name rule **50 / 50 / 0 / 25**. "**'It fixes 12' would be FALSE**": 3 grafts become the right slot, **9 become abstentions**, **16 staves the ordinal placed correctly are withdrawn**, and **0 new grafts**. Both offending systems are **interior suppression** (p3/s1 suppresses Oboi/Trombe/Timpani; p4/s0 suppresses Timpani). Placing unnamed staves by position instead scores *more* correct (66 vs 50) and **grafts 9 staves** doing it — "the guess wearing a number, priced". Sources: `CLAUDE.md` "The slot index"; `benchmarks/omr-slot-index-2026-09/FINDINGS.md`; `benchmarks/omr-unnamed-staves-2026-09/probe_forced_by_clef.py`.
- **Would be falsified by:** a plate that reorders staves between systems.
- **Known exceptions:** ⚠️ the ordinal join is **right** for a score that suppresses only its LAST staves. ⚠️ **The graft is silent and fragments are loud** — "a Timpani part holding the Viola's bars and key signature reads as wrong notes, and mis-ranking the work is the one failure a cleanup count exists to prevent".
- **Where it is used in the code:** `tools/omr/staged/adjudicators/` `adjudicate_slot_index` (`_forced_pairing`); `tools/omr/export.py` `_stitch_slots` / `_slots_are_ordinals`.

### C63 — The strings are the LAST block of a system, and a short string section is short at its FOOT
- **Says:** orchestral score order puts the strings at the bottom; where the section is short, the missing staff is the lowest.
- **Category:** Score layout & systems
- **Predicts (mechanically):** a bottom-contiguous unnamed block that exactly fills the reference's trailing same-family run has ONE order-preserving map and takes it (FORCED); a block one slot short sits on that run five ways (NARROWED, to be resolved by INFER).
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID for the ordering; the LABELLING of it is publisher-dependent (C70).
- **Evidence:** Sean, 2026-09-17: *"If we had 4 or 5 staves that showed up last in the system without a name in the margin they are almost surely strings. If the first 2 clefs are treble the 3rd is alto and the 4th is bass clef it is further reinforcement."* Measured on Litolff Beethoven 5 pp.1-4, one gather decided four ways, CONTROL **75 of 75** committed slot verdicts reproduced with the branch disabled: **25 abstained → 5 DECIDED + 20 NARROWED → 15 collapsed, 5 left narrowed**; **25 of 25 placements correct against the hand-read PRINT, ZERO grafts**; the 5 left narrowed are the condensed `Violoncello e Basso` — "abstained on, not picked". In the FILE, running alone: `staff_not_identified` **783 → 141 (−642)**, `events_written` **1472 → 2114 (+642)**, every other bucket identical, `balanced: True` in every arm; pitched notes **965 → 1527**; parts stay 12 and measures 1332. Per part: Violin I +189, Violin II +176, Viola +74, Contrabass +27. Source: commit `a3e064ce` (branch `claude/unnamed-staves-alignment`); `benchmarks/omr-unnamed-staves-2026-09/`.
- **Would be falsified by:** a short string section short at its HEAD.
- **Known exceptions:** ⚠️⚠️ **the second publisher has NO POPULATION** — Breitkopf Brahms 1 p0-3 reaches **ZERO**, because **97 of 97 slot verdicts are already DECIDED**: "that plate labels nearly every staff on every system. **n = 1 document for correctness.**" ⚠️ The CLEF is a term "that can pull into abstention and never as a gate".
- **Where it is used in the code:** `adjudicate_slot_index` (`family_block`, `family_block_not_forced`); INFER rule `collapse_slot_index_to_family_block` (on `claude/unnamed-staves-alignment`).

### C64 — A column through a system is one INSTANT of music
- **Says:** on a conductor's page, notes at the same x across different staves sound together. "That is not a convention, it is the defining property of a conductor's score."
- **Category:** Score layout & systems
- **Predicts (mechanically):** a 21-staff system is twenty-one independent readings of one stretch of time — the only large source of REDUNDANT evidence on the page.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID.
- **Evidence:** on the committed Brahms 1 / Breitkopf transcription (51 bars, 6 systems, **3,006 events**), against a **circular-shift null** that keeps every within-staff interval and destroys only the PHASE: columns needed for the same events **1,483 real vs 2,409 null (1.62×)**; corroboration rate **0.498 vs 0.292 (1.71×)**; events standing alone **744 vs 1,706 (2.29×)**. ⚠️ **The rate rises with density while the information falls** — sparse bars 0.437 vs 0.212 (**2.06×**), dense bars 0.530 vs 0.348 (1.52×) — "a consumer reading corroboration without [density] cannot tell evidence from crowding". ⚠️ **DO NOT READ THE RESIDUAL AS EVIDENCE**: median residual **0.0734 real vs 0.0704 null (1.00×)** — "a column is BUILT to lie within the tolerance". Independently reproduced from a different population (ink components rather than note events, different document): unclassified ink aligns at **0.63× the columns and 0.43× the rows standing alone**. Sources: `CLAUDE.md` "Cross-staff simultaneity"; `benchmarks/omr-onset-columns-2026-09/FINDINGS.md`; `benchmarks/omr-ink-gather-2026-09/FINDINGS.md`.
- **Would be falsified by:** the real/null ratio approaching 1.0.
- **Known exceptions:** ⚠️ **a column is an instant on the SYSTEM, so a staff playing a half note while its neighbours play eighths SKIPS columns** — the INFER stage's first rule required strict adjacency and inferred **1** of 357; generalised to "the witness ENDS WHERE THIS NOTE ENDS" it reached **7**.
- **Where it is used in the code:** `Q.ONSET_COLUMN` + `adjudicate_onset_column` (`Kind.SYSTEM`, `Mode.ADDITIVE`); consumed by `tools/omr/staged/inferences.py` `collapse_duration_by_column` and `collapse_duration_to_barline` behind `OMR_INFER` (default OFF). `ONSET_COLUMN_MIN_WITNESSES = 2` at `tools/omr/staged/adjudicators/rhythm.py:2459`.

### C65 — A BRACE means ONE PLAYER
- **Says:** a brace states who plays, not how many staves.
- **Category:** Score layout & systems
- **Predicts (mechanically):** the brace/bracket choice should key on the group's INSTRUMENT FAMILY (keyboard or harp → brace), never on `len(staves) == 2`.
- **Status:** ASSERTED (untested here)
- **Rigid or publisher-dependent:** RIGID (by assertion).
- **Evidence:** **no measurement — the assumption is declared with its falsifier and is a pure no-op.** The counter-evidence to the incumbent IS measured: "All three incumbent sites decide it by **staff count** — `export.py:681` and `:3523` on `len(staves) == 2`, `:3446` on `len(slots) == 2`. A bracket block of two staves is *not* a grand staff: Brahms 1 p.1 reads blocks **`[2,2,2,2,2,7,1,3]`**, five **pairs** that are `2 Flöten`, `2 Oboen` and so on, and consuming 'block of 2' as a brace **declares five wind pairs to be pianos**." Source: `tools/omr/staged/ASSUMPTIONS.md` A-GROUP-2.
- **Would be falsified by:** its own stated test — "Count pages whose 2-staff group is a real keyboard against those whose 2-staff group is a wind pair. Also: find a braced instrument outside `BRACE_FAMILIES` (organ with pedal is 3 staves; celesta; accordion)."
- **Known exceptions:** organ-with-pedal is three staves.
- **Where it is used in the code:** `Q.GROUP_SYMBOL` — "With identity stubbed this **always abstains**, so today it is a pure no-op and the incumbent rule stands everywhere."

### C66 — An engraver spaces notes roughly in PROPORTION TO DURATION
- **Says:** a wide horizontal gap after a notehead is evidence the note is long.
- **Category:** Score layout & systems
- **Predicts (mechanically):** a duration signal **independent of every other one** — it needs neither the stem, the beam, nor the notehead class.
- **Status:** ASSERTED (untested here)
- **Rigid or publisher-dependent:** RIGID musically; strongly perturbed by justification.
- **Evidence:** **none. "⚠️ Measured nowhere — `grep` for proportional spacing in `tools/omr/` returns only unrelated hits. This is the one entry here that is a genuine *measurement* of the raster nobody takes"** (`docs/exploration-what-is-on-the-page-2026-09-09.md` §B.7). I re-ran the grep across `tools/` and `benchmarks/` and found no measurement.
- **Would be falsified by:** measuring inter-onset x-gaps against known durations on an engraved fixture, where the truth is exact.
- **Known exceptions:** the doc names two, unmeasured: "scanned spacing is noisy and justification stretches the last bar of a line".
- **Where it is used in the code:** **no consumer found.**

### C67 — Whether one printed staff label means ONE part or TWO is a property of the ENCODING, not the engraving
- **Says:** a condensed staff (`Flauti`, `Violoncello e Basso`) carries several players; how many `<part>` elements a reference file splits it into is an editorial decision about the FILE.
- **Category:** Score layout & systems
- **Predicts (mechanically):** nothing on the page can supply the count. **Do not build a page-side rule for it.**
- **Status:** **ENCODING (not engraving)**
- **Rigid or publisher-dependent:** neither — it is a property of the encoder.
- **Evidence:** "Staves carrying the SAME printed label are encoded as 1 part in some editions and >1 in others (Litolff/Simrock/Breitkopf `Viola` = 1, **Peters `Violen` = 2**), so whether a reference splits is a property of the ENCODING, not the engraving; **a label-derived rule is 74/74 on Beethoven/Brahms and +2,181 edits on Dvořák**, and **eleven page-side signals separate the two populations no better than chance (best ensemble 0.526 vs the `always 1` baseline's 0.538)**." What IS a convention, and is measured: over every condensed staff-measure in the truths, **silent 51.5% + unison 18.3% = 69.8% is exact duplication** (divisi 27.6% is approximated by duplication, so these are a floor). Ceiling with oracle counts: scan pool **−4,195 edits alone, −4,557 with `OMR_SLOT_STITCH`**; `entire staff` **8,453 → 2,060**. Sources: `CLAUDE.md` `OMR_CONDENSED_PARTS`; `benchmarks/omr-condensed-parts-2026-09/FINDINGS.md`; `docs/ask-first-conventions.md` §3.
- **Would be falsified by:** a page-side signal that separates the populations (eleven were tried).
- **Known exceptions:** the duplication convention (69.8%) is real and page-side; only the COUNT is encoding-side.
- **Where it is used in the code:** `OMR_CONDENSED_PARTS`, default `0` (off) — "Measured, dormant, and blocked on a count source." Flag-off is byte-identical (22/22 fixtures).

### C68 — A PAGE truth is not an ENCODING truth
- **Says:** MusicXML and the engraver count the same music differently — a `<slur>` is written at each END while the engraver draws ONE arc; a clef is printed at every system and declared once.
- **Category:** Score layout & systems
- **Predicts (mechanically):** any recall or precision figure taken by counting elements in a reference file against glyphs on a page is measuring the difference between two notations as well as the reader.
- **Status:** **ENCODING (not engraving)** — measured as a discrepancy.
- **Rigid or publisher-dependent:** n/a.
- **Evidence:** on the Brahms fixture, against the file it was rendered from: dynamics **19 glyphs vs 19 `<dynamics>` (agree)**; G clefs **28 glyphs vs 14 `<sign>G</sign>`**; slurs **82 arcs vs 164 `<slur>` tags**. A second instance: Verovio draws **one accidental per `<alter>`, not per `<accidental>`** — Brahms 1 has **54 `<accidental>` and 149 `<alter>`** and it drew 149; Beethoven 5 has **ZERO `<accidental>` and 13 `<alter>`** and it drew 13, so the `accidental` family scored recall **0.257** and is **excluded from the pooled reading F1 (0.898 → 0.919)**. A third: the Litolff plate condenses **18 encoded parts onto 12 printed staves**, so the four-page arc denominator (truth **111 slurs and 300 tie links** against our 32 and 80) supports "an understatement of the right sign" and **no recall rate**. Sources: `benchmarks/omr-reading-vs-reproduction-2026-09/FINDINGS.md`; `benchmarks/omr-arc-recovery-2026-09/FINDINGS.md`; `docs/ask-first-conventions.md` §3.
- **Would be falsified by:** n/a — it is an observation about two notations.
- **Known exceptions:** ⚠️ **what caught the accidental artefact was a CONTRADICTION with an existing number** — `wrong pitch` is zero on those works, "which cannot be true of a reader missing three quarters of the accidentals".
- **Where it is used in the code:** `tools/omr/page_truth.py` `render_fidelity` (measures the disagreement per work and declares a family unreliable); `score_reading` marks it `(RENDER)` and keeps it out of the pool.

### C82 — SCORE ORDER is a convention strong enough to resolve a label by
- **Says:** an orchestral score lists its instruments in a fixed family order — woodwind, brass, percussion, strings — and within each family from high to low.
- **Category:** Score layout & systems
- **Predicts (mechanically):** a monotone alignment of a page's staves against a canonical layout is a positional identity channel, independent of the margin text.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** **RIGID for symphonic repertoire, with one named exception class (Baroque) and a measured residue of real variation.**
- **Evidence:** measured against the Gradus MusicXML library (**507 works**): lexicon coverage **93% → 99%** of **2,345** real part names, and symphonic works in score order **74 → 95 of 105**. ⚠️ **Every one of the 30 order violations fixed there was a LEXICON misreading, not a layout** — "the 10 that remain are real variation and were left alone", and Baroque is "confirmed as a genuinely different layout". Source: `benchmarks/omr-score-order-2026-08/findings.md`.
- **Would be falsified by:** the 95-of-105 figure falling when the lexicon improves further (it rose, which is the test passing).
- **Known exceptions:** ⚠️⚠️ **the prior can overturn a CORRECT lexicon reading** — the canonical layout puts the timpani after the trombones while Litolff's Beethoven 5 prints it BETWEEN the trumpets and the trombones, so a correctly-read `Tp.` was aligned onto a second-trumpet slot. The repair was C71, not a change to the order. ⚠️ And the residual 7 errors on an 88-page run are **MIS-SLOTTING, not mis-naming**: "an off-by-three in the monotone DP over a reduced system: 12 staves against a 17-slot reference needs five deletions and it deleted 12/13/14 instead of 9/10/11".
- **Where it is used in the code:** `tools/omr/score_layouts.py`, `tools/omr/slots.py` (`align`, `assign_slots`); `tools/omr/instruments.py` supplies the names.

### C83 — The only ink crossing a family gap is the SYSTEMIC BARLINE, and it is about 0.16 staff spaces wide
- **Says:** where interior barlines stop (C58), one thin rule still runs the full height at the system's left edge — and it sits at exactly the x where the staff lines begin.
- **Category:** Score layout & systems
- **Predicts (mechanically):** a family gap is bridged by **one narrow column at `x_start`** and nothing else; an inter-system gap is bridged by nothing at all.
- **Status:** MEASURED HERE (on a synthetic LilyPond score) + SOURCED (Bravura metrics).
- **Rigid or publisher-dependent:** stated as "**near-universal across publishers and eras**"; ⚠️ 19th-century plate practice is explicitly **UNSOURCED** — "the agent found NO authoritative source … Refused to guess. **This is the biggest hole.**"
- **Evidence:** on an 8-staff LilyPond score at 200 dpi (staff space 13.8 px), columns ≥99% inked: gaps INSIDE a bracket are bridged at **bracket 218–224, systemic bar 235–237, final barline 1493–1495**; gaps BETWEEN groups at **235–237 only**; the **inter-system gap at nothing (max column ink 0.16)**. "**The systemic barline sits at exactly `x_start`**" — mimicking `Staff.x_start` gave **235**, "the same 3 px". Widths (Bravura, staff spaces): `staffLine` **0.13**, `thinBarline` **0.16**, `bracket` **0.5** — in pixels, a 4 mm pocket score at 300 dpi is **1.9 / 5.9**, at 600 dpi 3.8 / 11.8 — "**a bracket is ~3× the barline's ink everywhere**". ⚠️ **Degradation is measured and it inverts the answer**: "At staff-space ≤7.6 px … the analyser reported **17 bridging columns across a real inter-system gap — a false MERGE produced purely by resolution.**" Source: `benchmarks/omr-system-grouping-2026-09/research/publisher-conventions.md`.
- **Would be falsified by:** its own published prediction table (per-boundary detect rate × boundaries: 0.97 → 0.913 / 0.885; 0.96 → 0.885 / **0.849**; 0.95 → 0.857 / 0.815).
- **Known exceptions:** **vocal staves are never joined by barlines even when bracketed** (C86), so a choir gap is bridged by the bracket and the systemic rule and by no barline at all.
- **Where it is used in the code:** `tools/omr/staff_detector.py` `_gap_is_bridged`; `tools/omr/system_grouping.py` (cue A/B); `OMR_BRACKET_COLUMNS`.

### C84 — A BRACE is curved, so it never forms a full column — and "a bracket spans exactly the system" is FALSE
- **Says:** the two left-edge enclosures are different objects. A bracket is a straight-sided rule that spans **a family group**, not the system; a brace is a curved flourish that spans one player's staves.
- **Category:** Score layout & systems
- **Predicts (mechanically):** a brace can never satisfy a "column of ink through the whole gap" test, and a bracket's extent must not be read as the system's extent.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID for the geometry; WHICH brackets are printed is publisher-dependent (C60).
- **Evidence:** "**[MEASURED+SOURCED] 'A bracket spans exactly the system' is FALSE and is an error in our CLAUDE.md**" — the test score prints "per-family brackets (**2 staves each in the test, 4 brackets for an 8-staff system**) plus the systemic barline". Bracket geometry relative to `x_start`: outer edge ≈**1.23 sp** left, inner ≈**0.87 sp** left, thickness ≈**0.4 sp**. "Braces (piano/harp/divisi) are curved → **never a full column** [MEASURED]" — they "peaked **0.5–0.7**" of the gap. Independently, **0 of 147 read left-edge blocks span two systems** over 57 pages (C61), and reading the bracket over-splits on **27 of 57 pages**. Source: `benchmarks/omr-system-grouping-2026-09/research/publisher-conventions.md`; `benchmarks/omr-bracket-reading-2026-09/FINDINGS.md`.
- **Would be falsified by:** an edition printing one bracket per system (Litolff and Simrock do exactly that — see Known exceptions).
- **Known exceptions:** ⚠️ **the falsifier is already met on two of five editions** — Litolff and Simrock print ONE bracket for the whole orchestra, where "a bracket spans the system" is accidentally true. That is why the claim must not be relied on: it holds on some plates and not others, and CLAUDE.md states it unconditionally.
- **Where it is used in the code:** the brace/bracket choice is `Q.GROUP_SYMBOL` (C65, always abstains today); `export.py:681`, `:3523`, `:3446` still decide it by `len(staves) == 2`.

### C85 — Staff SPACING cannot separate a system from a group — REFUTED as a discriminator
- **Says:** the proposed rule was that the vertical gap between systems is larger than the gap between staves.
- **Category:** Score layout & systems
- **Predicts (mechanically):** it would have given a distance threshold for system grouping. It cannot, **by construction**.
- **Status:** **REFUTED HERE**
- **Rigid or publisher-dependent:** n/a.
- **Evidence:** **[SOURCED] LilyPond's shipped defaults (staff spaces), basic / minimum**: staff-inside-group **9 / 7**; across-group-boundary **10.5 / 8**; system→system **12 / 8** — "Under compression both floor at **8** → **no distance threshold can separate them, by construction.**" **[MEASURED]** on a real 2-system page: within-group **4.98**, across-group **6.50**, between-system **8.02** — "and a denser variant's within-system gap hit **8.09**, larger than the other page's inter-system gap". Independently, within one Brahms system the gaps run **17–237 px** and within one Beethoven system **130–345 px**, "both wider than the gaps BETWEEN systems on a piano page" (C56). Verdict: "**Demote spacing to a tie-breaker at most.**" Sources: `benchmarks/omr-system-grouping-2026-09/research/publisher-conventions.md`; `CLAUDE.md` "System grouping is decided by CONNECTIVITY".
- **Would be falsified by:** it already is, twice — from LilyPond's own defaults and from a real page.
- **Known exceptions:** none. This is why grouping is decided by CONNECTIVITY (C56) rather than distance.
- **Where it is used in the code:** `tools/omr/staff_detector.py` — distance proposes a break and **connectivity vetoes it**; the veto can merge an over-split page, never split a correct one.

---

## Text & margin labels

### C69 — An instrument label is printed in the MARGIN, at the left of its staff
- **Says:** the name stands outside the system, left of the staff's own start.
- **Category:** Text & margin labels
- **Predicts (mechanically):** crop the margin band per staff and OCR it; and conversely, anything found INSIDE the system's x-range is not a label.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID for placement; **PUBLISHER-DEPENDENT for whether it is printed at all** (C70).
- **Evidence:** the cascade reads **50 labels over 75 staves** on Litolff pp.1-4 — **12 of 12 on the opening system**, naming the full lineup — against **50 of 50 CORRECT** on a truth assembled from hand-read suppression lists and `works.json`'s hand-confirmed names (deliberately NOT `printed-lineups.json`, whose own provenance says its names came from the OCR). The free text-layer rung reads **0 of 75** on this 1870 scan. ⚠️ **A block taller than half the system's tick span is not a label** — two bad reads sat at **1.04×** the span against **1.5–4.7%** for all 17 blocks Surya correctly split on Boléro's dense page, "a ~22× gap with 0.5 in the middle of it". Sources: `CLAUDE.md` "Instrument identity"; `benchmarks/omr-margin-labels-blob-2026-09/FINDINGS.md`.
- **Would be falsified by:** an edition printing names above the staff rather than beside it.
- **Known exceptions:** ⚠️ **stacked instrument NUMBERS are printed left of the bracket and are not labels** — 24 of Mahler's 41 clef-locator false positives. ⚠️ The margin also holds plate numbers.
- **Where it is used in the code:** `tools/omr/staff_labels.py`, `staff_labels_surya.py`, `staff_labels_vision.py`; `tools/omr/contextual.py` `_labels_for_page`.

### C70 — Some publishers stop labelling CONTINUATION systems — and the family they drop is the strings
- **Says:** after the opening system a plate may name only some staves, and which it drops is systematic.
- **Category:** Text & margin labels
- **Predicts (mechanically):** label evidence is **structurally unavailable exactly where it would help most** — the families that default to treble (winds, brass) keep their labels; the families that need a non-treble clef (strings, low brass) lose them.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** **PUBLISHER-DEPENDENT.**
- **Evidence:** over the 20-row scan corpus (**217 truth-carrying staves, 5 publishers**), the unresolved staves whose family defaults to something OTHER than treble — "the entire population [`clef_correction`] could ever be handed" — number **29, and 29 of 29 are in the class 'no label printed at all'**. "None is a lexicon refusal, a group-label fragment or an OCR miss: Litolff Beethoven's `Viola` and `Violoncello e Basso` on continuation systems, Simrock Dvořák's whole p6/p7 lineup, margins measuring zero ink." Contrast: Breitkopf Brahms 1 p0-3 has **97 of 97** slot verdicts already DECIDED — "that plate labels nearly every staff on every system". And page 3's 8-stave system reads `Fl.` `Cl.` `Fag.` `Cor.` — **no `Ob.`: the PRINT itself confirming the suppression**. Sources: `CLAUDE.md` "ON SCANS, MORE LABEL READING CANNOT LIFT THE CLEF NUMBER"; `benchmarks/omr-staff-identity-labels-2026-09/FINDINGS.md`.
- **Would be falsified by:** an edition labelling its strings on every system — "**that would move it**", stated as the explicit limit.
- **Known exceptions:** ⚠️ this establishes only that the labels are ABSENT; "this says nothing about whether `clef_correction` would get those staves RIGHT if handed them".
- **Where it is used in the code:** consumed as a **reason to prefer a label-free second witness** — `clef_register_warning` "needs NO instrument label, which is what makes it worth having". No direct consumer of the publisher property.

### C71 — An engraver does not name one section with two different abbreviations on ONE system
- **Says:** within a system, one instrument section gets one abbreviation.
- **Category:** Text & margin labels
- **Predicts (mechanically):** a positional prior may **not** move a staff onto an instrument that a different alias on the same system already names.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID.
- **Evidence:** over the **1422-label corpus**, **86 of 158** ambiguous-alias occurrences clash — 52 `cor`, 18 `tp`, 9 `tr bas`, 7 `basso`/`bassi` — and hand-adjudicated the rule "**keeps or restores the right answer in 86 of 86 and blocks a correct overturn in 0**". Same-tree A/B on `--pages 23,44`: **24/29 → 26/29 correct**, the 17-staff finale system **16/17 → 17/17 exact**, `Timpani -> Trumpet` ×2 eliminated, **exactly 3 staff records change**. ⚠️ **The constraint is ASYMMETRIC** — it refuses only an OVERTURN and never removes the lexicon's own answer, because on p.48 `Tr. Bas.`'s two candidates (Trombone, Trumpet) are **both** separately named on its system. Sources: `CLAUDE.md` "THE SAME PAGE, THE SAME EVIDENCE, AND THE THIRD INSTANCE"; `probe_ambiguous_cooccurrence.py`.
- **Would be falsified by:** an orchestral page naming one section two ways — "**The probe FAILS if an orchestral source ever joins that list.**"
- **Known exceptions:** ⚠️ **Handel's *Messiah* prints `BASSO` (the bass VOICE) and `Bassi` (the string basses) on one page** and needs both first answers as they stand; there the two labels block each other, "which is the rule doing the right thing". ⚠️ A real *tromba bassa* on a page that also prints `Tr.` would be blocked from a correct overturn — "nothing in either corpus prints one".
- **Where it is used in the code:** `tools/omr/contextual.py` (the uniqueness guard); pinned by `tools/omr/tests/test_contextual_ambiguity_uniqueness.py`.

### C72 — A TROMBONE section is scored by REGISTER; a TRUMPET section by NUMBER AND KEY
- **Says:** `Tr. Alt. / Tr. Ten. / Tr. Bas.` names trombones; `Tr. I`, `Trombe in C` names trumpets. The abbreviation is the same; the qualifier names the family.
- **Category:** Text & margin labels
- **Predicts (mechanically):** `tr alt` / `tr ten` / `tr bas` must outrank the bare `tr`; and a size word may not beat an instrument noun.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID (a convention of scoring, not of one plate) — and the fix is reader-independent: "the lexicon is reader-independent … which means the paid reader returned the same answer for the same printed string".
- **Evidence:** `Tr. Alt.` had been reading as **Alto, a singer, at high confidence**; Beethoven 5 p.48 went 0 → 12 labels and **three resolved to the wrong instrument**. Beethoven 5 p.47 prints both `Tr.` (trumpets) and `Tr. Alt. / Tr. Ten. / Tr. Bas.` (trombones) four staves below. ⚠️ `Tr. B.` is **deliberately NOT** among the trombone aliases — that is a trumpet in B-flat. The second half was a mechanism gap: `VOICE_QUALIFIERS` was HAND-LISTED with spelled-out `alto`/`tenor`, so an abbreviated `Alt.` never reached it; **derived** from the voice instruments' own aliases it also fixes `Fl. Alt.`, `Cl. Alt.` and `Trb. Tenore`. Validated on **1380 margin labels across 10 editions**. Sources: `CLAUDE.md` "Instrument identity"; `benchmarks/omr-margin-labels-2026-08/LEXICON_TR_ALT_2026-08-31.md`.
- **Would be falsified by:** a plate numbering its trombones and registering its trumpets.
- **Known exceptions:** ⚠️ **a cross product must be DERIVED, not hand-listed** — the contrabassoon is a bassoon noun plus a contra- qualifier across four languages, the hand list held **six of about twenty-five**, and the missing ones "did not abstain": `Contra-Fagott` and `Cont. Fag.` read as **Bassoon** at HIGH confidence. The live cost was **ten staves** of the scan benchmark's Brahms 1 (`K. Fag.`).
- **Where it is used in the code:** `tools/omr/instruments.py` (`_CONTRA_ALIASES` generated from `_BASSOON_ALIASES`; `VOICE_QUALIFIERS` derived).

### C73 — Direction words are printed INSIDE the system, not in the margin
- **Says:** `legato`, `Allegro con brio`, `cresc.` stand within the staff's own x-range.
- **Category:** Text & margin labels
- **Predicts (mechanically):** clamp every candidate band to the staff's `x_start..x_end` — which makes "inside a system vs a margin" true BY CONSTRUCTION rather than a test.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID.
- **Evidence:** "`find_candidates` clamps every band to the staff's own `x_start..x_end`, so **0 candidates are ever in a margin**; **all 98 are `placement: below`** and the `above` band is **UNEXERCISED by both documents**." Reach: Litolff p1-3 **42 word-shaped candidates, 2 accepted**; Breitkopf p0-3 **56 candidates, 10 accepted**. Equivalence against the legacy path over the same four Brahms pages: **10 accepted vs 10, and 7 of 7 `(page, text)` pairs agree exactly**. Sources: `CLAUDE.md` "Direction words reach the file"; `benchmarks/omr-staged-direction-2026-09/FINDINGS.md`.
- **Would be falsified by:** a tempo mark printed clear above the system that the clamped band cannot reach — which the `above` band exists for and neither document exercises.
- **Known exceptions:** ⚠️ `Q.DIRECTION_BAND_POSITION` is the fact "that separates a `cresc.` standing in the dynamics row from an `Allegro con brio` printed clear above the system, which `placement` cannot" — **recorded and read by nothing**. ⚠️ **EQUIVALENCE, not truth: no word has been checked against the print.**
- **Where it is used in the code:** `tools/omr/direction_text.py` `find_candidates`; `OMR_DIRECTION_TEXT` (default ON).

### C74 — The printing TRADITION (Italian vs German) is a property of the document, and its own unambiguous labels reveal it
- **Says:** a plate that prints `Flauti/Corni/Trombe` is Italian-tradition throughout; one printing `Flöten/Hörner/Trompeten` is German.
- **Category:** Text & margin labels
- **Predicts (mechanically):** a document-level language read off its own unambiguous labels settles abbreviations the global lexicon resolves one way for every score.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** **PUBLISHER/DOCUMENT-DEPENDENT** by definition.
- **Evidence:** **167 of 1422 labels ambiguous, 167 reachable, 9 re-decided** — all `Tb.` → Trombone on Litolff's Beethoven 6, "a work whose IMSLP roster has 2 trombones and no tuba". ⚠️ It decides **ONLY aliases `AMBIGUOUS_ALIASES` does not declare** — "a declared one is owned by the clef-informed position channel, and **two signals sharing an ancestor are one signal**". DETECTION is unconditional and recorded; only the re-decision is behind the flag. Sources: `CLAUDE.md` `OMR_SCORE_LANGUAGE`; `benchmarks/omr-score-language-2026-09/FINDINGS.md`.
- **Would be falsified by:** a plate mixing traditions.
- **Known exceptions:** none recorded; the 9 re-decisions are one work.
- **Where it is used in the code:** `OMR_SCORE_LANGUAGE` (default OFF); `contextual.score_language`.

### C75 — Measure numbers are printed at system starts
- **Says:** the engraver has already told us how many bars are on the line.
- **Category:** Text & margin labels
- **Predicts (mechanically):** an **independent witness** to `measure_partition`, which is currently decided from barline columns alone — "the only page-side quantity that could corroborate a bar count without a reference file". Rehearsal marks do the same and anchor ACROSS parts.
- **Status:** ASSERTED (untested here)
- **Rigid or publisher-dependent:** **PUBLISHER-DEPENDENT** (by assertion).
- **Evidence:** **one sentence, no table**: "measure numbers at system starts (the row-drafting work found **three of four editions** print them)" — `docs/position-grammar-confusables-2026-09-04.md:113`. I could find no other statement of it and no per-edition measurement; see the "what I could not find" note above.
- **Would be falsified by:** counting printed system-start numbers per edition.
- **Known exceptions:** ⚠️ **it is not trivially reachable**: the numbers are small text (the `direction_text` rung's problem) and the coarse `numeral*` class "covers meters, tuplet digits, fingerings *and* measure numbers under one name" (the `class_aliases` `COARSER_THAN_CANONICAL` trap).
- **Where it is used in the code:** **no consumer found.**

---

## Barlines & repeats

### C76 — Repeat dots are a vertical PAIR in spaces 2 and 3, adjacent to a barline
- **Says:** the repeat sign's dots straddle the middle line, beside the barline they belong to.
- **Category:** Barlines & repeats
- **Predicts (mechanically):** the barline is already a classical-CV object, "so the anchor exists without the model" — dots + CV barline is the anchor pair for reading repeats, with no model change.
- **Status:** ASSERTED (untested here)
- **Rigid or publisher-dependent:** RIGID (by assertion).
- **Evidence:** **no figure.** Stated in `docs/position-grammar-confusables-2026-09-04.md` §2 DOT and §5. The reach limit IS recorded: "the `repeat` family is **`repeatDot` ONLY — we have the dots, not the sign** — and **`volta` is not in the class space at all** (checked, not assumed)", and an earlier audit of the class space found `repeatDot` ×4 on the benchmark. "MusicXML repeat signs are dropped on export" has stayed a TODO "because the ink for the barline half is not detected either".
- **Would be falsified by:** measuring detected `repeatDot` positions against the middle line on a plate that prints repeats.
- **Known exceptions:** F-clef dots are the confusable — but they are separable: they are **header-window only, straddling line 4, past the clef body's right edge (0.94–1.79 notehead-widths — the region where a C clef has nothing)**, which the dot-veto work priced exactly (clef-locator false positives **48 → 13 → 5**).
- **Where it is used in the code:** **no consumer found** for repeats. The F-clef half is live in `tools/omr/clef_locator.py` (`dot_clear_right_fraction`, `dot_single_clear_is_enough`).

### C77 — A DOUBLE BARLINE marks a section end — and nothing in this pipeline can read one
- **Says:** the engraver prints a double or heavy barline at a structural boundary.
- **Category:** Barlines & repeats
- **Predicts (mechanically):** it *would* be a cheap independent witness to a movement or section boundary, which the meter family wants badly.
- **Status:** **REFUTED HERE as an available signal** (the convention itself is not in doubt; its readability is).
- **Rigid or publisher-dependent:** RIGID musically.
- **Evidence:** `tools/omr/staged/ASSUMPTIONS.md` A-DUR-6 named the double barline as "the cheap independent reader" and **that entry is corrected in CLAUDE.md**: "the double barline is **not** the cheap independent reader that entry calls it (`Q.BARLINE_COLUMN` is a per-staff *count of cells*, and **no barline-type classification exists**)". Independently: `barlineSingle` is the only barline class the labelling guidance mentions, custom barline classes were tried in Phase 3.4 and "caused catastrophic forgetting (F1 cratered to **79.3%**)", and barlines are classical-CV, which measures columns rather than classifying them. The one place a double barline is visibly load-bearing went the other way: Litolff p.62's printed `3/4` stands "right after the double barline under *Tempo I.*" at **cell 6**, and the pipeline's own record put it at cell 8 — on **one barline broken into two fragments** read as `timeSig3` + `timeSig4` (`benchmarks/omr-ink-gather-2026-09/FINDINGS.md`).
- **Would be falsified by:** a barline-type classifier existing and working.
- **Known exceptions:** none recorded.
- **Where it is used in the code:** **no consumer found.** `tools/omr/measure_extractor.py` detects barline COLUMNS and does not type them.

### C86 — VOCAL staves are not joined by barlines, even when they are bracketed
- **Says:** in a choral system the barlines stop at each vocal staff (the "choir-barred" or Mensurstrich practice), so the bracket encloses staves that no barline connects.
- **Category:** Barlines & repeats
- **Predicts (mechanically):** a bracketed group whose interior gap **nothing in-window crosses** is the choir-barred signature — "impossible for a true open score" — so such a system must never be flipped into open-score mode by aligned stems out-voting its barlines.
- **Status:** ASSERTED (untested here) as a convention; its **consequence is MEASURED.**
- **Rigid or publisher-dependent:** RIGID for vocal music; it is a property of the MUSIC's layout, not of one publisher.
- **Evidence:** the convention is stated with a source but **no count**: "vocal staves never joined by barlines even when bracketed", with the encodings' own vocabulary as corroboration — MusicXML `<group-barline>` ∈ {`yes`, `no`, **`Mensurstrich`**}, MEI `@bar.thru`; and in the LilyPond test score the **S–B gap inside the ChoirStaff is bridged by bracket 218–224 and systemic bar 235–237 — and by no barline** (`research/publisher-conventions.md`). What IS measured is the repair it forces: `OMR_CHOIR_GROUPING` cue C takes the Bach Brandenburg 3 stress row from **0.9241 → 0.8152** OMR-NED, **6735 → 6236 edits**, and measure-cells **122 → 11 against a true 10**; all ten pooled scan rows are byte-identical and the 11-work engraved benchmark is **edit-for-edit identical (0.1306 / 2745)**. Over a 969-page library probe, **757 examined break-gaps read 0 ×735 / ≥4 ×22 with nothing at 1–3**, and the 10 pages that change were each hand-adjudicated toward the truth (7 exact heals including both operas' vocal systems; **zero false merges**).
- **Would be falsified by:** a choral edition running barlines through its vocal staves.
- **Known exceptions:** ⚠️⚠️ **bracket-groups ALONE was FALSIFIED on the engraved benchmark** — "LilyPond open scores manufacture 'groups' from bridging jitter; pooled **0.1306 → 0.8560**, nine works' barlines deleted". The second condition (a window-blind internal gap) is what makes it safe: **do not loosen it.**
- **Where it is used in the code:** `tools/omr/measure_extractor.py` (`OMR_CHOIR_GROUPING` cue C, default ON since 2026-09-05).

---

## ⚠️ Where this registry disagrees with `CLAUDE.md`

This repo's own rule is that **the tree outranks the ledger**. Six places where I
preferred a findings file or the source over `CLAUDE.md`:

0. ⚠️⚠️ **"The bracket encloses exactly the system" (C84) — a findings file calls
   this an error in `CLAUDE.md` in those words.** `CLAUDE.md` states, in the
   dossier section, "a barline runs a system's full height and **the bracket
   encloses exactly it**".
   `benchmarks/omr-system-grouping-2026-09/research/publisher-conventions.md`
   answers: "**[MEASURED+SOURCED] 'A bracket spans exactly the system' is FALSE
   and is an error in our CLAUDE.md**" — an 8-staff test score carries **four
   per-family brackets**, and 2 of the 5 real editions in the scan corpus print
   one bracket for the whole orchestra while 3 print section brackets. The
   BARLINE half of that sentence is sound; the bracket half is not, and the
   sentence is still in `CLAUDE.md` as written. **This is the one entry here I
   would raise with Sean directly.**

0b. **A tie's ends at one staff position (C39) is stated in `CLAUDE.md` without
   its scan caveat.** The knob-adjacent text gives the engraved empty interval
   (0.168 / 0.435) and does not carry
   `benchmarks/omr-tie-pairing-2026-09/FINDINGS.md`'s finding that **on a SCAN
   the interval is not empty at all** (same-pitch max 0.238 against a
   step-apart minimum of 0.013). A reader taking the rule as RIGID everywhere
   would re-tune the constant on a scan, which the findings file forbids.

1. **Ledger pitch provenance (C3).** `CLAUDE.md` says Litolff prints rungs
   "~1.10× the staff spacing, Peters/Breitkopf/Simrock ~0.975×, **measured over
   the 357 hollow-campaign labels**". The findings file is narrower: the PITCH
   was measured on "**185 rung gaps over 117 notes**"
   (`omr-snap-ledger-2026-09/FINDINGS.md` §2); the 357 rows are the corpus the
   FIX was *scored* on (§3). Two different denominators, conflated in the ledger.
2. **`OMR_ARC_RECLASS`'s engraved cost (C43).** The knob row states "+2 edits";
   `CLAUDE.md` itself then flags the figure as **stale** and gives **+6** on the
   post-chord-tie tree with the scan at **+149**, not +130. I quote both and mark
   the row's headline as superseded.
3. **Litolff p.62's printed `3/4` (C77, C34).** `CLAUDE.md` carries the cell-8
   reading in several meter sections; `benchmarks/omr-ink-gather-2026-09/FINDINGS.md`
   put a crop on it and found **cell 6**, with the cell-8 `timeSig3`+`timeSig4`
   being **one barline broken into two fragments** (0.35–0.40 staff spaces wide,
   `x_canonical = 0`), and **cell 6 firing ZERO `timeSig*` on any of 17 staves**.
   That in turn **inverts** an earlier correction in
   `omr-staged-meter-carry-2026-09`, which had called the cell-6 bar math "two
   cells early". CLAUDE.md records the inversion but the older cell-8 figure is
   still quoted around it.
4. **The stem-direction convention's reach (C10).** `CLAUDE.md` does not carry
   this thread at all — the measurement (0.787 overall; 0.939 at 4–6 steps;
   0.765 reversing at 6+) lives in
   `benchmarks/omr-stem-direction-2026-09/FINDINGS.md`, on
   `claude/stem-direction-sideways`, which **is not on this branch or on main**.
   Anyone reading only `CLAUDE.md` would not know Sean's stem convention has
   been measured, nor that the reversal is a PITCH fault.

One further tension, resolved rather than a disagreement: **C35 and C36 sound
contradictory** — "a slur is drawn OVER its notes" (`docs/ask-first-conventions.md`)
against "a slur is drawn BETWEEN its noteheads" (`NOTES.md:313`, `CLAUDE.md`
"Slurs"). Both are true on different axes: a slur overlaps its notes
*vertically* (which is why `_noteheads_under` works for slurs and scores 0 of 4
on hairpins) and stops inside them *horizontally* (which is why the arc box needs
a 0.25-notehead pad). They are kept as two entries for that reason.
