# 2.120 — Read by elimination: design + truth-side measurement

**ROADMAP 2.120. STAGED path only. DESIGN + MEASURE; nothing under `tools/` changed, no flag, no gather.**

```
CONVENTION ASSUMED   A mark's rough size, its ink fill and where it stands (in the staff / just outside /
                     far; clef-key slots / bar head / body / margin / on a barline) rule out most symbols
                     before any classifier is asked; what survives is 1-3 things, and today's cut-offs then
                     only have to separate those few.
WHAT WOULD FALSIFY IT  (1) a true mark whose own symbol is eliminated and the table entry cannot be
                     widened without letting most symbols back in; (2) survivor sets that stay large
                     (median > 3) on truth; (3) on a second publisher, survival collapsing under the same
                     numbers (Litolff MERGES, Breitkopf SHATTERS).
NOT CONFIRMED        Measured on ONE page (Brahms 317803 pdf 0, Breitkopf, Sean's 1,566 truth boxes),
                     one publisher. The detector-side half (c) and the twins check (e) are NOT available —
                     see "Provenance". Nine table entries are ASSUMED (questions for Sean in TABLE.md).
```

## Provenance — read first

- The measurement was first run by a Sonnet sub-agent (Sean, 2026-10-14: *"opus for design and let it
  send out its own sonnet agent to measure"*). **A machine reboot wiped `/private/tmp` mid-session,
  including that agent's outputs, before its final report reached the design agent.** Its scripts and
  numbers are lost; nothing below is quoted from it. The one partial file the design agent read before
  the wipe (`results_a.json`) said truth n 1566, 0 outside the table, survive-conv 1566, survive-all 1537 —
  **reproduced exactly** by the re-run below.
- The **truth-side** measurement ((a), (b), (d)) was re-run by the design agent from inputs that live in
  the repo (truth json + the PDF): `measure/truth.py` -> `measure/truth.out`, `measure/groups.py` ->
  `measure/groups.out`. `table.py` / `descriptors.py` were rebuilt verbatim from the design agent's own
  context (one addition: `cfill`, the centre-window fill used by G3).
- **(c) detector boxes and (e) twins are NOT measured here**: their inputs (lane 2.119's `out/brahms_p0.json`
  extract of the 20261013-night record, its `pairs.csv`, and `scratchpad/brahms_glyphs.pkl`) were in the
  wiped `/private/tmp`. Redoing them needs one load of
  `library/_shared-records/brahms1-breitkopf-mvt1-whole-20261013-night.record.json` (via
  `record_io.load_record`, under the 15 GB RSS rule) and 2.119's pairs rebuilt. **Pending.**
- The design agent saw the lost agent's crop FILE NAMES only. Its (C) crops were keyed q751, q399, q871 —
  the same marks this re-run lists as failures; its (A)/(B) crops were detector subjects
  `glyph/0/0/0/0/13`, `glyph/0/0/0/5/2`, `glyph/0/0/9/7/0` (caught) and `glyph/0/0/4/4/7`,
  `glyph/0/0/11/6/27`, `glyph/0/0/4/5/5` (re-identifiable) — **what they showed is unknown; do not cite.**

## Prior art (rule 1) — this is not a new principle, it is a new table

- `docs/position-grammar-confusables-2026-09-04.md` §4 **R3** *"veto the impossible first, reclass only when
  decisive, abstain otherwise"* and **R5** *"'matches nothing' is an output"* — stated, never built as one
  mechanism; rediscovered per symbol (its §3 lists nine precedents).
- In the tree (STAGED), elimination exists only as separate yes/no refutations of the detector's one class
  (`adjudicate_notehead_is_not_a_notehead`, `notehead_precision.py` ~2930-3277: `is_a_clef`,
  `notehead_in_a_key_signature_slot` (2.100, a convention), `is_a_dot`, `on_a_barline`, `is_a_meter_digit`,
  `is_a_time_signature_digit`, `on_a_dynamic_letter`, beam piece, tremolo slash; `family_precision`'s rest
  twins; `not a ledger -- inside the staff`; `not a arc -- ink is a staff line`). **Each returns only
  `value=True, reason=…`; the mark is dropped, never handed on as the thing the reason names.** That is the
  manager's reading, confirmed in the tree.
- 2.37 built an all-rungs ledger *elimination* rule and left it UNWIRED (ROADMAP 2.37 row).
- Ink-first falsifier (2026-09-22, `benchmarks/omr-ink-first-breitkopf-2026-09/`): no ink axis beat the
  box's own width on either plate -> the unit here is **the box + the ink inside it**, never a component.

## The design

**Four descriptors** (`descriptors.py`), deliberately coarse, all in the LOCAL staff space at the mark's x
(the truth page's own per-bar staff lines; the NEAREST staff, not the filed one):

| descriptor | values | kind |
|---|---|---|
| size w, h (sp) | per-symbol envelope | CUT — narrow only |
| ink fill (dark fraction in the box) | per-symbol range | CUT — narrow only, ASSERTED values |
| place vs staff | IN (lines ±0.5 sp) / NEAR (≤ 8 sp) / FAR | IN-vs-out = the staff lattice (CONV); 8 sp = CUT |
| place in the bar | MARGIN / KEYSLOT (< 9 sp into the system's 1st bar) / HEADER (< 14) / BARHEAD (< 5) / BARTAIL / BODY; `edge` = ≤ 0.6 sp from a bar boundary | rule = CONV (only a clef before the key; meter at a bar head; a barline IS a boundary); widths = CUT |
| context: stem run off the box corner (2.119 `stem_side`) | up/down/none | recorded only, not used to eliminate |

On a detector box the size is NOT a second witness (box and class are one assertion — noteheads dossier
§2); fill (the ink) and place (staff geometry, another reader) are.

**The table** (`table.py`): 29 symbols (DSv2 classes folded by `symbol_of`), each with envelope, fill range,
allowed places, allowed zones, a source per entry, 9 entries ASK. `candidates()` returns `conv` (only
convention rules — what may DECIDE) and `all` (+ cuts — what may only NARROW). The readable view
(`cellview.py` -> `cellview.md`) is derived from it, not typed.

## Measurements (truth: Brahms 317803 pdf 0, 1,566 boxes, 33 classes, state `labeling`)

Command: `cd scratchpad/2.120 && nice -n 10 python3 measure/truth.py` (-> `measure/truth.out`).

**(a) Survival of the true symbol.**
- conventions only: **1566 / 1566** (100%).
- all rules: **1537 / 1566 (98.1%)**. Every one of the 29 failures is a CUT or ASK rule; **no convention
  eliminated a true mark.**

The 29, grouped by rule, with what the crop/inspection says:

| rule | n | marks | verdict |
|---|--:|---|---|
| text: place IN not allowed (ASK) | 10 | b2967 b2962 b2893 b2889 b2879 b2794 b2789 b2686 b2683 b2595 | **table bug** — margin instrument labels stand level with their staff; the "text is never IN" ASK is wrong for the MARGIN zone (crop C6) |
| brace: zone KEYSLOT (ASK) | 6 | b4171 b4011 b3991 b3979 b4309 b3027 | **descriptor bug** — the first bar's cell begins AT the brace (cell x0 1220 = brace x), so a brace never reads as MARGIN |
| dynamic letter: width > 3.6 sp | 3 | q159 q299 (6.6 sp), q922 (12.4) | **table bug** — Sean boxes a dynamic WORD (or letter + word) as one `dynamicF/P` box; the envelope is a single letter's |
| tie: fill > 0.60 | 3 | q648 q660 q710 | **table bug** — a short tie end arriving at a barline, lying on a staff line, reads thick (crop C5) |
| barline: fill < 0.15 | 2 | b4161 q405 | **table bug** — a long thin box over a slightly tilted barline is mostly paper |
| tie: height > 2.2 | 1 | b4010 (12.7 x 2.4 sp) | table bug — a long tie arcs higher |
| flag: width > 1.9 | 1 | q399 (2.06 sp) | table bug — a real flag, wide (crop C3) |
| beam: height < 0.25 | 1 | q871 (4.3 x 0.23 sp) | table bug, marginal — a flat beam boxed tight (crop C4) |
| black head: width < 0.9 | 1 | q751 (0.46 x 0.43 sp) | **truth question** — the crop shows an augmentation DOT beside a chord, not a head; the table keeps `dot` (crop C1) |
| quarter rest: width + height | 1 | q880 (0.26 x 1.43 sp, on a barline) | **truth question** — the crop shows a barline segment below the third line, no rest (crop C2) |

So: 27 table/descriptor bugs, all in CUT/ASK entries and all fixable by widening one envelope or one zone
without letting a new symbol class in; 2 marks the table refuses that look like **truth label errors**
(ask Sean before counting them either way). Under rule 7 this is the control failing where it should be
able to: the table *can* drop a true mark, and does, visibly.

**(b) Candidate-set size** (`measure/truth.out`, "PER CLASS"). Table size 29.
- all rules: **median 3, p90 9**; **784 / 1566 (50%) of marks have ≤ 3 survivors**.
- conventions only: **median 25** — **conventions alone eliminate almost nothing**; the narrowing is done
  by the size envelopes, i.e. by measured cut-offs. Sean's "convention may decide, cut-off may only
  narrow" therefore means: elimination is a NARROWING tool here, not a deciding one.
- Per class (all-rules median): stem 1 (209/277 sets are `{stem}` alone), augmentation dot 1, beam 2,
  clef G 2, black head in a space 3 (`{beam, head_black, tremolo}` x123), key flat 3
  (`{key_accidental, meter_digit, slur}` x20), barline 3 (`{arpeggiato, barline, stem}`), slur 4, ledger 5
  (`{beam, ledger, rest_block, tenuto, tremolo}` x91), whole rest 5, black head on a line 6, tie 7,
  meter digits 8, half heads 8-10, accidentals 9-10, tremolo 10. **The tall glyphs (accidentals, meter
  digits, rests, flags) stay 8-10 wide**: size and place cannot tell a sharp from an 8 from a quarter
  rest; that needs the detector's class or a shape reader — elimination does not help them.

**(c) Detector boxes — PENDING** (inputs wiped; see Provenance). Not measured: detector errors caught,
false alarms, refused marks re-identifiable.

**(d) Today's cut-offs as 2-3-way questions** (`measure/groups.py` -> `measure/groups.out`; on TRUTH boxes,
Sean's tight boxes — a detector's partial boxes will be worse):

| today's cut-off | after elimination it separates | on truth | verdict |
|---|---|---|---|
| `too_narrow` (black head w < 1.0 sp) | nothing it was built for: every stroke it catches (stems, barlines, uprights) is already gone by shape (w ≤ 0.6 & h ≥ 1.5). The head's survivors are ledger, half head, tremolo, whole/half rest, tie, meter digit — **all wider than 1.0** | costs 1/378 heads (q751, the truth question); separates 0 of the co-survivors | **width is the wrong axis after elimination**; head vs ledger separates by fill (G4) and height, head vs rest by place on the lattice |
| `is_a_dot` (both sides ≤ 0.75 sp) | dot vs head | dots 0.33-0.58 (n 131); 1 head-labelled mark at 0.46 (q751) | **clean** with margin, bar the truth question |
| head interior (2.88) — *proxy*: dark fraction of the centre 40% x 40% window, NOT 2.88's reader | half head vs black head | black 1.00 (all 185 co-surviving), half 0.16-0.89; threshold 0.9 -> **0 errors** | **clean on Breitkopf truth boxes**; Litolff's sliver hole (page-facts §3) is the known risk, unmeasured |
| ledger vs flat strokes | ledger vs tie / slur / beam / head | by fill: ledger 0.58-0.99 vs tie 0.22-0.49, slur 0.28-0.43 -> 0 errors; vs beam / head (n 2 each) not by fill | **clean against arcs by fill**; vs beam piece / head needs height (ledger 0.15-0.44 vs beam 0.58-0.69, head 0.52-0.59 -> 0 errors) |
| stem vs barline | stem vs barline vs brace | height overlaps (15 errors at best threshold); **`edge` separates: barlines 30/30 at a bar boundary, stems 0/277** | **clean by place, not by size** |
| tie vs slur | — | ties whose set holds slur 81/84; slurs whose set holds tie 41/69 | as expected: **one glyph; context (two heads, same pitch), not shape** |
| header (clef / key / meter) | key flat -> {key accidental, meter digit, slur}; clef G -> {clef, slur}; meter digits -> 8 | | key vs meter is a SLOT question (zone width = cut) |
| owner distance / `glyph_owner` | — | not an identity cut-off (which staff, not what) | out of scope |

**(e) Twins — PENDING** (2.119's `pairs.csv` wiped with the scratchpad; 2.119 must republish it). What is
known from the pairs file before the wipe (its `split_group` column, counted by the design agent, not
measured): 53 of 69 pairs split at a stage AFTER identity (A duration narrowed 24, B bar-sum hold-out 21,
D partial-bar gap 6, G chord value 2), which elimination cannot change; 16 are identity splits (C detector
no box 8, E refused not-a-notehead 5, F wrong class 3) that elimination could touch, and C (no box) it cannot — a box the detector never drew has no subject (CLAUDE.md §7).

## Recommendation

**Where it belongs.** GATHER files the four descriptors as facts on each box (no decision). ADJUDICATE
runs the table: conventions eliminate (DECIDED exclusions), cuts narrow; the detector's class becomes
**one witness among the survivors** (it may choose among them, never revive an eliminated one); the
result is DECIDED when one survives, NARROWED (candidates + margins, 2.106 style) when 2-3 survive. INFER
may collapse only among those survivors and writes GUESSED (blue). EXPORT unchanged.

**What it replaces.** The chain of yes/no refutations in `adjudicate_notehead_is_not_a_notehead` and the
rest twins in `family_precision` becomes one table; a refused mark is no longer dropped — it is
re-identified as its survivor (dot, barline, ledger, key accidental, digit) or, with none, counted.

**What it must never do.** Never turn "cannot tell" into an answer: zero survivors is UNREAD (red), never
a guess — **except** a PIECE of an adjacent mark (a flat's bowl in the key slots, an F-clef dot, a
natural's upright, a tie end at a barline): the table names symbols, not pieces, so a build needs a fourth
outcome PIECE-OF, decided only by overlap with an adjacent box, never by the table. Never let a cut
decide alone (P1). Never let the detector's class revive an eliminated symbol, and never count the box's
size as a second witness for the detector's own class.

**Phased plan.**
1. Fix the 27 table bugs (widen 7 envelope/fill entries, allow text IN when in the MARGIN, and define MARGIN
   as left of the staff lines' start, not the first cell's edge), ask
   Sean the 2 truth questions and the 9 ASKs, then re-measure (a)/(b) on this page AND on a second
   publisher's truth (Litolff 984073 idx 1) **before** any wiring — the numbers here are one Breitkopf page.
2. Measure (c) on the 20261013-night record (one load): detector errors caught, false alarms, refusals
   re-identifiable.
3. **First slice: dots vs noteheads vs ledgers vs strokes inside the notehead decision** — the head's
   survivor set (filled oval: head / ledger / beam piece / tremolo / rest block / dot) with the three
   clean separators above (dot size; fill + height for ledger and beam piece; `edge` for strokes on a
   barline). Output: a refused head becomes a DOT / LEDGER / BARLINE re-identification or stays refused;
   a head is never created.
4. Then the header slice (key vs meter vs clef by slot), then rests vs heads by lattice place.

**Kill criterion for the first slice:** on Sean's blind tiles of the re-identified marks (two
publishers), if more than 1 in 20 re-identifications is wrong, or if any real head is lost that today's
path keeps, or if survival on the second publisher's truth falls below 97% with the same table — stop,
and keep today's refutations.

## Files (scratchpad/2.120/)
`table.py`, `descriptors.py`, `cellview.py` + `cellview.md`, `measure/truth.py` + `truth.out` +
`truth.json`, `measure/groups.py` + `groups.out`, `measure/crops.py`, `crops/C1-C6*.png`, `TABLE.md`.

---

# Round 2: Sean's answers + table fixes (2026-10-14, lane agent; DESIGN + MEASURE, nothing under `tools/` changed, no flag, no gather)

STAGED path only (the table is a design for ADJUDICATE; LEGACY untouched). Round 1 above is kept as written; round-2 files sit beside it
(`table2.py`, `descriptors2.py`, `cellview2.py/.md`, `measure2/`, `truth_overrides.json`, `TABLE.md` rewritten, `TABLE-round1.md` kept).

```
CONVENTION ASSUMED   Sean's 11 answers (SEAN-ANSWERS-2026-10-14.md) are conventions and may ELIMINATE only where he said never
                     (Q5 hairpin inside the staff, Q11 brace/bracket away from the left edge). "Not standard / exceptions / very rare"
                     (Q3 dynamic on the staff, Q4 direction word on the staff, Q10 arpeggio) is KEEP with a low prior ("rare").
                     Every number I added is a MEASURED cut-off (may only narrow), derived as 1.15x / 0.85x the truth extreme.
WHAT WOULD FALSIFY IT  (1) survival < 99.5% on the Brahms truth page; (2) survival < 97% on a second publisher with the same table
                     (the round-1 kill criterion) -- ** this one IS TRIPPED ON WHAT EXISTS, see "Litolff" **; (3) a correct detector
                     class eliminated more than rarely.
NOT CONFIRMED        Litolff has NO full-page truth: only 49 hollow half heads. 27 of 29 table symbols have no second-publisher test.
                     Widened tails are NOT validated out of sample (split-half below). The three right-edge "brace" labels are unresolved.
```

## 1. Sean's answers applied, and the two label rulings

`truth_overrides.json` (his words, date): `q751` noteheadBlackOnLine -> augmentationDot ("aug dot"); `q880` restQuarter -> barlineSingle
("only barline"). Applied **in the measurement only**; `data/hand-truth/` is not edited (truth read through `tools.omr.hand_truth.store`,
1,566 boxes, 2 overridden). New table concepts (table2.py): `prior` (`normal | rare | very_rare`), `extra` allowances that lift ONE loc/zone
rule (a rare allowance never eliminates and is reported separately as `common` vs `all`), a `needs_left_edge` rule and one new descriptor
`xs`/`left_edge` (round 1's "brace" bug: the first bar's cell starts AT the brace, so a brace never read as MARGIN).

| Sean | table effect |
|---|---|
| Q5 hairpin inside staff: no | unchanged (already NEAR/FAR); source is now his ruling |
| Q11 brace only left | zone rule replaced by `left_edge` (xs -3..+2 sp of the system's first cell x0; Brahms braces measure -0.67..+1.03); BARTAIL no longer allowed |
| Q3 dynamic on staff | `dynamic_letter` +IN, **rare** |
| Q4 direction word on staff | `text` +IN, **rare** (normal in MARGIN: the 10 round-1 text failures were instrument names level with their staff) |
| Q10 arpeggio | `arpeggiato` **very_rare** |
| Q6/Q7 rests outside the staff, whole/half off their lines | kept (NEAR stays; no line pinning), `loc_kind` ASK -> CUT |
| Q8 mid-bar clef | kept (zones unchanged) |
| Q9 courtesy accidental | `accidental` +KEYSLOT (normal) |

Cost of Sean's answers alone (`measure2/seaneffect.out`): `text` joins 346 marks' sets (336 only as a rare allowance), `dynamic_letter` 162 (all rare),
`accidental` 26 (key-slot marks: key flats 3 -> 5 members; **round 1 caught 4 accidental-vs-key-accidental detector errors; this answer un-catches them**),
`brace` joins 6, leaves 10 (barlines/strokes at the right edge no longer list `brace`). Recovered true marks: 16 (6 braces, 10 text). Lost: 3 (below).

## 2. The too-tight numbers, widened from measured truth (15% margin; `measure2/derive.py`)

| symbol: bound | before | after | truth range (n) | marks recovered / cost |
|---|---|---|---|---|
| dynamic_letter width max | 3.6 | **14.29** | 1.94-12.43 sp (17) -- Sean boxes a dynamic WORD as one mark | 3 / +104 marks gain it |
| barline fill min | 0.15 | **0.11** | 0.13-0.82 (31) | 2 / +2 |
| barline height min | 3.0 | **1.22** | 1.43-15.68 (31, incl. q880 "only barline") | 1 / +1 |
| flag width max | 1.9 | **2.37** | 0.92-2.06 (42) | 1 / +20 |
| tie (short end on a staff line / barline) | fill max 0.60 | **alt envelope** w 0.9-1.6, h 0.3-0.6, fill <= 0.83 | fill 0.04-0.72 (84) | 3 / +24 (a GLOBAL 0.83 cost +320) |
| tie (long, high arc) | height max 2.2 | **alt envelope** w >= 8, h <= 2.75 | h 0.32-2.39 (84) | 1 / small (global cost +65) |
| beam (wide flat piece) | height min 0.25 | **alt envelope** w >= 3.8, h >= 0.20 | h 0.23-1.38 (50) | 1 / +1 (global cost +42; wider than any ledger, 3.6) |
| detector-box widening (measured on the detector's own boxes, the SAME page: not out of sample) |||||
| meter_digit height min | 1.2 | **0.87** | detector boxes on 8/6 digits are 1.02-1.08 sp | 3 correct detections + 2 refused boxes were eliminated |
| rest_hook width max | 1.9 | **2.38** | detector box 2.07 sp (q818) | 1 |
| Litolff (49 clean hollow TEST heads): head_half fill max | 0.85 | **1.0** | 0.64-0.88 | 3 / head_half joins 239 more Brahms sets |

Each is a CUT (may only narrow). The tie/beam alternatives are shaped to the failure that was measured -- **fitted to 3/1/1 marks**.
Split-half control (`derive.py`; one system on the page, so even/odd staves): each bound fitted on half the staves loses 1-2 tail marks of the
other half at 15%, and still 1 at 50% -- **tail bounds do not generalise from one page**; they are placeholders until a second plate measures them.

## 3. Brahms 317803 pdf 0: truth survival (`measure2/truth2.out`; unit = Sean's box + ink; 1,566, 2 overridden)

| table | survives | conventions only | set size all (median / p90 / mean) | common (median / mean) | marks with <= 3 |
|---|--:|--:|---|---|--:|
| round 1 (overrides applied) | 1538 (98.21%) | 1566 | 3 / 9 / 4.39 | 3 / 4.39 | 784 |
| + Sean's answers only | 1551 (99.04%) | 1563 | 4 / 10 / 4.73 | 4 / 4.30 | 731 |
| + widening only | 1550 (98.98%) | 1566 | 4 / 9 / 4.47 | 4 / 4.47 | 760 |
| round 2 (S + W) | 1563 (99.81%) | 1563 | 4 / 10 / 4.83 | 4 / 4.38 | 696 |
| + detector-box widening | 1563 | 1563 | 4 / 10 / 4.85 | 4 / 4.40 | 696 |
| **final (+ Litolff head_half fill)** | **1563 (99.81%)** | 1563 | 5 / 10 / 5.00 | 4 / 4.55 | 522 |

**Target 99.5%: met (99.81%).** Remaining failures, all three the same cause: `b4230`, `b4041`, `b4023` (Sean labelled `brace`, at the far right of the
system, xs 128.7-130.6 sp, w 0.21-0.55, h 6.5-14.1, on a bar boundary). They fail by **Sean's Q11 convention** (a CONV elimination -- round 1 said
"no convention eliminated a true mark"; this is the first, and it is a ruling). Crops D1-D3: a double vertical line at the system's right end running
through the staff, i.e. most likely a closing barline mislabelled `brace`; **a label for Sean to confirm** (TABLE.md Q1), not a table bug. If they are
barlines they survive (barline sets contain `barline`). Also `b3027` (a left-edge brace top, crop D4) survives via `left_edge`.

Candidate-set size per class, final (median; round 1 in brackets): stem 1 (1), augmentation dot 2 [1 common] (1), beam 3 [2 common] (2), barline 4 [2 common] (3),
black head in space 4 (3), on line 6 (6), ledger 5 (5), tie 7 (7), slur 5 (4), key flat 5 [4 common] (3), clef G 3 [2 common] (2), whole rest 6 (5), time-sig digits 10 [8 common] (8),
accidentals 9-11 (9-10), half heads 10 (8-10), tremolo 12 (10), eighth rest 11 (9). The "common" sets (rare allowances left out) equal round 1 within 0.01 on the mean (4.40 vs 4.39); the
growth is the rare extras (409 of 1,566 marks carry a rare member) and the Litolff fill fix (black head 5.06 -> 5.57 mean, `head_half` joins 239 sets, marks with <= 3 survivors 696 -> 522).
**Round 1's finding stands: size and place cannot separate the tall glyphs (8-12 survivors).**

## 4. Litolff 984073 idx 1, hollow TEST cells (`measure2/litolff.py`, `litolff.out`)

Truth = Sean's 59 hollow heads (all half heads) in 104 TEST cells; 2.112's 9 leaked cells dropped (a table has no training, so leakage cannot inflate it -- dropped for parity with 2.119/2.4b),
one clean cell (`s8-m12`) has no record glyph to fix its canonical->page map: **49 heads**. Canonical -> page is an exact per-cell affine map read off the record's own
glyph pairs (residual ~1e-12), staff lines from `cells.json`, ink from the 600 dpi page: nothing was cut or invented.

- Truth head: 1.19-1.21 x 0.38-1.02 sp, ink fill 0.64-0.88, centre-40% fill 0.16-1.00 (17/49 >= 0.9: the sliver hole is washed out).
- **Round-1/Brahms-measured table: 46/49 = 93.9% -- below the 97% kill criterion.** The 3 failures are head_half's fill cap (0.85): fills 0.85-0.88; their sets were `{beam, head_black, tremolo}` etc.
- After widening one number (head_half fill max 0.85 -> 1.0, measured on these same cells): 49/49. **Not out of sample.** At 1.0 the fill axis no longer separates half from black on this plate at all;
  round 1's "head interior is clean (threshold 0.9, 0 errors)" is a Breitkopf result and **does not transfer** to Litolff (cfill 0.16-1.00 for hollow heads).
- Detector side (these 49): 29 have a detector box at IoU >= 0.5 (20 none: the detector never drew them -- no stage can repair that, CLAUDE.md s7); 27 hollow-class boxes, 26 keep their class under the table
  and the head symbol is in the set for 26; the 2 black-class boxes on true hollow heads (hollow called black, 2.119 group F) are **not caught** (head_black stays in their sets).

**What Litolff cannot test yet:** there is no full-page Litolff truth. Untested on a second publisher: every symbol except `head_half` (stems, ledgers, beams, dots, ties, slurs, barlines,
rests, accidentals, clefs, key/meter digits, text, braces, dynamics) -- 27 of 29 table symbols and every class-by-class set size; the whole-note heads (no Litolff whole in the test cells);
Litolff's MERGING (one box holding two marks -- the test boxes are Sean's tight 121x102 canonical boxes); stem side, tuplets, hairpins. The kill criterion "Litolff survival below 97%" is
therefore reported on one class: **93.9% as the table stood, 100% after a one-number retune on the same data**; both statements are true and neither is the real second-publisher test.

## 5. (c) Detector boxes on Brahms p0 (record `20261013-night`, loaded once via `record_io.load_record`, 1,776 p0 boxes -> `measure2/brahms_p0.pkl`; `measure2/detector.py`)

Unit = the detector box + its ink; each box matched to Sean's truth at IoU >= 0.5 (1,269 strong; 394 partial; 113 no overlap). The 66 `staff` boxes are outside the table.

- **Detector class errors** (strong match, table symbol both sides): 110 of 1,269. **Caught** (the table eliminates the detector's class): **29 of 110 (26%)**; the true symbol is in the set for all 29.
  Caught: beam->slur 24, beam->tie 2, black head->dot 1, quarter rest->barline 1, whole head->meter digit 1. **Not caught: slur<->tie 56** (one glyph, context decides), beam->tie 5, black->tremolo 3, arpeggio->stem 2,
  accidental->flag 2, accidental->key accidental 4 (caught in round 1; un-caught by Q9).
- **Correct detections the table would eliminate: 0 of 1,159** (round 1: 13, after the widening of the box numbers above); truth symbol absent from the detector box's set: 0 of 1,269 (round 1: 15).
- **False alarms** (no truth overlap, a table class): 111; the table eliminates **15 (14%)**: black heads in a space 7/9, on a line 4/9, ledger 3/8. Beam 27 and tie 26 false alarms are not touched (their shape fits).
- **Refused boxes** (225): arcs 131 `ink_is_a_staff_line`, ledger 37, notehead 52 (too_narrow 19, clipped_fragment 10, stacked_head_duplicate 7, head_cut_piece 4, is_a_time_signature_digit 4, tremolo 3, duplicate box 3, beam piece 2, ...).
  Of the 52 refused noteheads, **20 sit on a real head** (clipped 10, stacked 6, cut 3, duplicate 1): wrongly refused by those readers; the table keeps `head_*` in their sets (it never names them anything else and must not),
  so it can neither rescue nor rename them. Of the 32 refused noteheads with no head under them (`measure2/refused.out`): **14 have an EMPTY set** (`too_narrow` 14: brace pieces in the key slot 4, a barline fragment 1, unlabeled ink 9 -- a PIECE-OF, not a symbol),
  **3 name their true symbol in a set of <= 3** (`too_narrow`: dot 1 -- `q751` Sean's "aug dot" --, tremolo 2), **7 hold it in a set > 3** (tremolo 5, time-sig digit 2), 5 have no truth under them, 3 lose the true symbol (a ledger; 2 meter digits boxed partially).
  **`too_narrow`, specifically: 19 refused; 1 re-identified (dot), 2-3 narrowed to a tremolo-ish set, 14 empty.** Re-identification yield on this page is ~3-4 marks.

## 6. (e) Twins (`measure2/twins.py`; 2.119's `pairs.csv` via `git show origin/lane-2.119-twins:benchmarks/omr-twins-2026-10/out/pairs.csv`)

69 pairs, 66 resolved (3 Litolff ids not unique per cell). The missed twin's true head symbol is in its set in **66/66** (and the twin's too); the two twins have the **same** set in 32/66, and where they differ the
difference is box noise (`head_whole/rest_hook`, `dynamic_letter/text` ...), never `head_*`. The table catches **no** wrong detector class on a missed twin (the one wrong class, Litolff group F, is a black box on a hollow head: not caught).
53 of the 69 pairs split at a stage AFTER identity (A, B, D, G), which elimination cannot change; of the 16 identity splits, C 8 is "no box" (untouchable), F 3 is not caught, E 5 is a wrong `stacked_head_duplicate`
refusal of a true head the table keeps as a head. **Elimination moves 0 of 69 twins.** It does not explain them either: the twins differ in the ADJUDICATE duration reader and the bar sums.

## 7. Recommendation

**The first slice (dot vs ledger vs beam piece vs barline stroke inside the notehead decision; a refused head is renamed or stays refused, never becomes a head) is NOT ready to build.**
- Payoff on the only labelled page is small: 3-4 of 52 refused noteheads re-identified, 14 empty (pieces); the refusal readers already name digits/beam pieces/dots by reason.
- The designed separators hold on Brahms (dot size; ledger vs beam piece by height/width; barline by `edge`) but fill does not travel to Litolff.
- The second-publisher criterion is tripped on what exists (93.9% as the table stood) and passes only after a same-data retune.
- Where the table IS strong is a different job: **reject** a detector class that cannot be (26% of detector errors, 0 harm of 1,159, 14% of false alarms) -- worth wiring only after Litolff.

**Next, in order (all measure-only):** (1) one **full Litolff page** of truth from Sean (every mark); (2) re-measure survival and set sizes with the final numbers UNCHANGED; (3) blind tiles of the table's rename/refuse proposals for Sean.

**Kill criterion for the first slice (restated):** build it only if, with the table frozen (no retuning on the test page), a full second-publisher truth page gives survival >= 97% (target 99%) over all classes and
0 hollow/black heads lost; then on Sean's blind tiles of the re-identified marks on two publishers, more than 1 wrong in 20, or any real head lost that today's path keeps, kills it and keeps today's refutations.
Today: survival 99.81% on Brahms, **93.9% on Litolff hollow (as stood)** -- the criterion fails.

## Files (this round)
`table2.py` (CHANGES list = before/after; `build(sean, widen, detector, litolff)`), `descriptors2.py`, `cellview2.py` -> `cellview2.md`, `truth_overrides.json`, `TABLE.md` (round 2), `TABLE-round1.md`,
`measure2/{derive,truth2,onebyone,seaneffect,extract_record,detector,refused,litolff,twins,crops2}.py` + `.out`, `measure2/*_rows.json`, `measure2/{brahms_p0,litolff_p1}.pkl` (the one-time extracts of the record),
`measure2/derived_bounds.json` (the round-1-failure bounds as first proposed; the tie/beam ones became alternative envelopes). Crops D1-D4: `out/print/2.120-elimination/`.
Run order from `benchmarks/omr-elimination-2026-10/` (cwd; `git show origin/lane-2.119-twins:benchmarks/omr-twins-2026-10/out/pairs.csv > pairs.csv` first for twins):
`python3 measure2/truth2.py; derive.py; seaneffect.py; onebyone.py; extract_record.py <record> <page> <pkl>` (record loads ONLY via `record_io.load_record`), `detector.py; refused.py; litolff.py; twins.py` (all `nice -n 10`).
