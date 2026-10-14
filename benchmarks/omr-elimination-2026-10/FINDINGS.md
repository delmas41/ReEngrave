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
