# Plan 2026-10-28: the page-wide claim order (ROADMAP 2.221)

STAGED throughout (GATHER files readings, ADJUDICATE settles who owns the ink, EXPORT counts what is left). Docs only: no code,
no gather, no test run. Read from main `3e77b8e21`. Parents: `docs/plan-2026-10-22-shared-ink-map.md` (2.194),
`docs/plan-2026-10-20-claimed-area.md` (2.178), `docs/plan-2026-10-28-ink-map-step6-fill.md` (2.220). Every number below is
quoted from a named FINDINGS, ROADMAP row or DECISIONS line. Nothing here is a new measurement.

Sean, 2026-10-28: *"my gut is that it should be page or system wide first focusing on the easier or most recognizable things
first"*, then, on the order in §2: *"I really think this is the way forward, so go ahead and get it started. Write it up."*

CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED: the marks a reader recognises soonest (staff, barlines, clefs,
words) can be read before the noteheads without the noteheads, and when they are READ, the ink they cover is theirs. Two things
would falsify it. (1) On Sean's tiles, ink an earlier layer claimed turns out to be a real note: a word box over a head, or a
barline that is a stem. (2) The earlier layers read clearly too seldom to take anything off the later ones (milestone 0 counts this).

## 1. Cause first, and the process lesson

- **There is no page-wide order today; there is a per-cell tie-break.** `stroke_owner.TIERS` (2.205, ON) lists claimants as
  area claims, then heads/ledgers, accidentals, arcs/hairpins, dynamics/text/marks/dots, rests. Stems, beams and flags come last
  as consumers. Between the box tiers the order only LISTS candidates (module doc): when two families both fit, the stroke is
  `contested`, and an earlier tier never wins. It runs per CELL, on detector boxes and area claims only.
- **Strokes are cut before heads exist.** `stroke_map.map_strokes` takes the vertical opening, then the horizontal one, and only
  then the blobs. So it breaks a hollow ring into lunes and rims (`hole_share` 0.0 on all 766 written halves, FINDINGS
  ink-map-fill-2026-10). The head is measured last, from what the strokes left over.
- **Words are read last, from what the detector left.** `gather_direction_words` runs last in `gather.gather` (a hard edge).
  `direction_text._blank_detections` erases every detected box before it looks for words, so an `f` boxed as a notehead is gone
  before the word reader can see it. Direction words and margin labels are claimants nowhere. Dynamics claim only through
  detector `dynamic*` boxes (tier 4, after heads) and the 2.107 letter look (`Q.NOTEHEAD_LETTER_INK`, read by a pair rule).
- **The tiles keep showing it.** An ff or part of one was boxed as a head and written: 2.202d tile 6, 2.204 tile 7, 2.209/2.210
  (Litolff p4 `glyph/4/1/1/4/17`), 2.220 tile 2. A flag was boxed as a head (2.220 tile 3), a head box swallowed a sharp (2.220
  tile 6), and a C-clef fragment was written as a quarter (2.205 tile 5, fixed by the 2.208 clef claim). Each one got its own
  rule downstream.
- **Process lesson.** Every pair rule (`on_a_dynamic_letter`, `on_a_barline`, `rest_is_a_barline`, `ink_is_a_barline`,
  `is_a_clef`, the 2.210 head-on-stem test) answers "this head is really X" AFTER the head has taken the ink. The order in which
  marks take ink was never written down as a decision, so each lane rebuilt it locally (`docs/ink-rules.md` lists them). The fix
  is an order that is written once, page-wide, with each step stating what it READ, not one more rule.

## 2. The order (draft Sean has seen), with each layer's evidence, its bar, and who says it's right

The order is a CLAIM order applied in ADJUDICATE over readings GATHER already filed. It is not a gather order: the detector
still runs first on the unerased page (CLAUDE §7), and every reader still files everything.

| # | layer | readers today (on main) | "read clearly" bar | who says it's right |
|---|---|---|---|---|
| 1 | structure: staff lines, system barline/bracket/brace column, interior barlines, clefs, key, meter | `gather_geometry`/`gather_measures` (`staff_detector`, `measure_extractor`; `Q.STAFF_LINES`, `Q.CELL_BOX`, `Q.BARLINE_COLUMN`); register `leading_column`, `clef` (2.181), `clef_slot` (2.208), key (2.183/2.187), meter (2.177), all ON | a convention places it (only a clef before the key, fixed key order, a meter on every staff at one bar) AND a reader saw it there | the print; Sean's 2.176/2.181 tiles |
| 2 | words and expressions OUTSIDE the staves: tempo, technique, instrument names, dynamics between staves | `gather_direction_words` (lexicon gate, last), `gather_margin_labels` (cascade), `gather_dynamic_letters` + `adjudicate_dynamic`, `gather_letter_look` (2.107), printed bar numbers | two sources: the lexicon accepts the string, and its letters' ink lies outside the staff lines measured at its own x | the lexicon is a convention; Sean for the extent (a letter's box is wider than its ink) |
| 3 | noteheads (and, open question 1, accidentals/rests/dots) | detector boxes (`gather_detections`, rescues, views); one-head check = 2.220 fix A (`Q.HEAD_INK`, not built), 2.210 head shape (parked) | the box holds ONE head's ink: no sharp, flag or letter inside it (2.220 fix A) | Sean's tiles; the print |
| 4 | words INSIDE the staves, after heads | letter look on head/rest groups (2.107); dynamic boxes inside the staff | the same two sources as layer 2, on ink no head READ | Sean (`OMR_DYNAMIC_INK_PICK` was rejected: the ink picked the wrong dynamic 2 of 2) |
| 5 | strokes: stems from the head's edge, beams, ledger lines, slurs/ties, hairpins | stems: old finder ON, 2.204 stroke stems PARKED; beams: 2.202 ON; ledgers: old far-head reader (2.217 PARKED, old 9/9 vs stroke 0/9); arcs: `Q.SYSTEM_ARC` (2.166) + detector slur/tie; hairpins: CV reader | the stroke's own shape fits its family (`stroke_owner.shape_fit` `clear`) on ink no earlier layer READ | Sean's tiles per family (2.202 rounds 3-4, 2.216) |
| 6 | whatever is left | `Q.INK` per-cell summary (ON); `stroke_owner.census` `unclaimed` per cell | counted, never dropped | the accounting equality (2.194 §2.4, not built) |

**The governing rule.** A layer claims only what it READ. What it did not read clearly it leaves open for a later layer.
A later layer whose reading also fits claimed ink may MARK the disagreement (the box is narrowed, the candidates are carried,
and the conflict is counted), but it never takes the ink. This is Sean's never-overturn-a-DECIDED ruling (CLAUDE §3, 2.148)
applied to ink. Two marks inside one layer keep today's 2.205 rule: decided where the shape clearly fits one family, contested
(abstained, counted) where it fits both.

**How it differs from today**, layer by layer. (1) Interior barlines and brackets claim nothing: `family_of` returns None for
`barline*`/`bracket`/`brace`; `bracket_reader.py` has no consumer outside its test; the brace is not read (page-facts §4 gap).
So a barline's vertical stroke is free for a stem reader (2.204 round 3's `stem_readers_disagree` barline cost). (2) Words are
read last and claim nothing; dynamics stand after heads. (3) Heads are not checked to hold one head before they claim.
(4) In-staff words exist only as the 2.107 pair rule. (5) This layer already matches the plan: consumers read only unclaimed
strokes (2.205). (6) Leftover ink is counted per cell; nothing checks it per page.

## 3. Shared ink versus owned ink

- **Staff lines are claimed by POSITION and are see-through.** A head, a beam or a ring that sits on a line shares that line's
  rows. The line never takes them, and no mark loses them to the line. Today the stroke map reads the erased raster. The
  see-through cases are already patched one by one: 2.202b reads thickness on the unerased raster, 2.206 fixed the eraser's walk,
  and 2.220 milestone 1 re-joins a ring's pieces where line rows lie between them. 2.221 states those as one rule: line rows
  that lie between one mark's own pieces belong to that mark as well. Never erase before the detector.
- **Contact is not ownership.** A stem touching a head, a tie ending at a head, a beam crossing a stem: the touching pixels are
  CONTACT (`Q.STROKE.touches`), and each mark owns its own extent. The stem starts at the head's edge (2.194 §2.5 order:
  head -> stem -> beam/flag -> shared stem -> slash), and the 2.205 crossing rule stays.
- **Owned means one mark.** Owned ink is never a witness for another mark (rule 8: a claimed stroke is never a "clean tip").

## 4. Convention (may decide) versus guess (may only narrow)

- **Convention:** the structure layer's positions (page-facts §2, §3); the lexicon gate; one stem shares one value; the ledger
  names the owner (2.216). A READ claim resting on one of these may REFUSE a later box.
- **Measurement, so it NARROWS:** the order between layers 2, 3 and 4 is a reliability ranking on two plates, not an engraving
  convention (the 2.178 plan said the same of its own §1 order). The extent of a word's claim is a measurement too: the
  first `on_a_dynamic_letter` build refused two real notes beside an *sf* (notehead_precision §2.76 comment). So until a third
  publisher or Sean's tiles confirm a layer-2-over-layer-3 rule, a READ word that covers a head box narrows the head (blue,
  both candidates). Only a clean head/word separation of the ink (the head's ink entirely inside the word's own letters) refuses it.

## 5. Conflicts with the 2.194 plan and the in-flight 2.220 steps (honest list)

1. **`stroke_owner` tiers.** Today dynamics/text are tier 4, after heads and arcs, and tiers never decide. 2.221 moves READ
   words outside the staff ahead of heads and lets an earlier READ claim stand. This changes the 2.205 module doc's
   "it never picks a winner". It is not an argmax: no confidence is compared, the earlier layer had to READ, and the later one is marked.
2. **The direction reader's hard edge.** `_blank_detections` needs the detections and blanks head boxes. For the word layer to
   claim an ff that the detector called two heads, the word candidate pass must see ink under head boxes that failed the one-head
   check. That is a GATHER change and needs a re-gather. It is placed last (milestone 6). Until then, layer 2 uses what is on the record:
   accepted `Q.DIRECTION_WORD` boxes, `Q.DYNAMIC_LETTER`, and the letter look.
3. **`map_strokes` cuts strokes before blobs** (2.220's cause). 2.221 does NOT rebuild the stroke map's order: 2.202 beams (ON)
   and 2.205 rest on its populations, and the step 1 parity was proven on them. The head layer is 2.220's `Q.HEAD_INK`
   (milestone 1 + fix A). Inside one head box, 2.220 subtracts the strokes that run past the head first. That is the same
   order seen from inside the box (the stem starts at the head's edge), so 2.220 proceeds as written and becomes layer 3's producer.
4. **2.220 fix B** (blue, never overturn a black our fill reader READ) is the governing rule applied to fill, so the two agree.
   **2.220 fix A** (head-hood check) is layer 3's bar, so 2.221 depends on it and does not duplicate it.
5. **2.194 step 8** (claimed-area steps 4, 5, 7 as ink claims) and the 2.178 plan's order (dynamics step 4, arcs step 5) are
   re-ordered: words move ahead of heads and arcs move after them. Step 8 then becomes "layers 2 and 4 file `unit: ink` claims".
6. **Parked lanes this touches:** 2.204 stems (its barline abstentions are a layer-1 gap), 2.210 head shape and 2.212 twin heads
   (both become the layer-3 check, via 2.220), 2.214 slash ends (layer 5), and 2.217 ledgers (layer 5 keeps the old reader: its
   lesson stands, check the old reader is failing first).
7. **Scope.** Ownership is per cell, and words and brackets are page or system objects. A page claim enters a cell through the
   cell's padded crop. Which staff a mark belongs to stays `glyph_owner`'s question (page-facts §3), and that runs after.

## 6. What retires (parity first, deleted only in 2.194 step 10; fates in `docs/ink-rules.md`)

If layer 1 holds: `notehead_precision` `on_a_barline`, `family_precision` `ink_is_a_barline`, the barline branch of
`rest_is_a_barline`, and `adjudicate_dot_role` `on_a_barline`. If layers 2/4 hold: `on_a_dynamic_letter` / `head_in_letter`,
`rest_on_a_dynamic_letter`, the 2.210 head-on-stem letter case (never built), and tier-4 contested dynamic strokes.
`is_a_clef` and `on_the_staffs_leading_barline` already go through the register (2.181). Nothing is deleted on principle,
only where the claim refuses or narrows every box the old rule did.

## 7. Build order (small milestones; each proven cheaply, FILE vs FILE, same stages, pages and tree; CLAUDE §6)

| # | milestone | proof | level |
|---|---|---|---|
| 0 | **Census, read-only, saved records of the frozen sample (no gather, no flag).** Per plate: written notes and head boxes whose ink lies (a) on an interior barline column, (b) inside an accepted direction word or a spelled dynamic's letters, (c) under a READ clef/key/meter claim (expected ~0: control). 12 crops to Sean. FINDINGS `benchmarks/page-claim-order-2026-10/` | counts by layer; Sean's tiles say how many are real notes. Gate: if (a)+(b) are near zero on the file, layers 1-2 are not the next lane | READER census + print |
| 0b | **Does the order matter? (Sean's question 1 test, read-only.)** On the same saved records, count the ink that accidental, rest and dot boxes share with written head boxes; only that shared ink can change with the order. If it is small, the order is settled by the convention (after); if not, crop up to 12 shared cases for Sean | record query + tiles, no flag | READER |
| 1 | **Words outside the staff claim before heads** (cheapest high-value: every row it needs is already on the record). New claimant tier ahead of heads in `stroke_owner.own_strokes`, fed by accepted `Q.DIRECTION_WORD` / adjudicated `Q.DYNAMIC` letters / `Q.LETTER_LOOK_COVER`; READ words refuse only on clean separation, else narrow. Flag `OMR_CLAIM_ORDER`, default OFF | re-adjudicate the milestone-0 saved gather OFF vs ON; `lane_report` by place: judged right->wrong 0, unwritten->wrong 0, invented->removed counted; 12 blind tiles incl. 2.220 tile 2, 2.210's ff, 2.204 tile 7 re-shown | FILE vs FILE |
| 1b | **Brackets and braces claim first, with structure** (Sean q3). Wire `bracket_reader.py` (no consumer today) and read the brace at the system's left edge; their ink is a structure claim no head or stroke may take. Milestone 0 adds a count of written notes/head boxes whose ink lies on a bracket or brace; 12 tiles to Sean | same saved gather, OFF vs ON | FILE vs FILE |
| 2 | **Interior barlines claimed by position:** the vertical stroke at a cell edge spanning the staff (`Q.CELL_BOX`, `Q.BARLINE_COLUMN`) is an `ink` claim; consumers cannot take it | same saved gather; parity with `on_a_barline` / `ink_is_a_barline` / `rest_is_a_barline` (every box they refuse is refused or narrowed); 2.204's barline abstentions counted with stems ON in both arms | FILE vs FILE |
| 3 | **Heads claim after the one-head check** = 2.220 milestones 1-2 with fix A (owned by 2.220); 2.221 adds only that a passing head claims before layers 4-5 | as 2.220 | FILE vs FILE |
| 4 | **Words inside the staff** claim only ink no head READ | re-adjudicate as in 1 | FILE vs FILE |
| 5 | **Leftover ink per page** at EXPORT: the 2.194 §2.4 partition (claimed by layer / contested / unaccounted) in `status_census`, a test that the parts sum | record query, file byte-identical | READER |
| 6 | **Word candidates see under failed head boxes** (`direction_text` candidate pass), the GATHER change of §5.2 | small gather, 2 pages per plate, detector cache, OFF vs ON | FILE vs FILE |

Brackets and braces: milestone 1b (Sean 2026-10-28, question 3). Word-vs-head (question 2): a clearly read word takes the ink outright. Each milestone
reports the three measures (`docs/measuring.md` §0). Lanes run on Sonnet.

## 8. Questions for Sean

1. ~~Should accidentals, rests and dots claim with the noteheads, or after them?~~ ANSWERED 2026-10-28 (DECISIONS): AFTER the noteheads, "because they're a little bit harder to read"; Sean is open to a small test of whether the order matters (milestone 0b).
2. ANSWERED 2026-10-28 (DECISIONS): the word takes it outright; words claim first ("a small box grabbing a part of a word can be mistaken for a lot of things"). Was: When a word or dynamic we read clearly covers ink the detector also called a notehead, may the word take it outright, or should the note be written blue until more scores confirm it? (2.107's "it is letters" covered the sf case only.)
3. ANSWERED 2026-10-28 (DECISIONS): YES, brackets and braces claim first with structure ("a lot of notes claimed ink that were actually brackets"); milestone 1b. Was: Do we need the brackets and braces read before anything else, or is the system's left barline enough for now?
4. ANSWERED 2026-10-28 (DECISIONS): "Words inside staff are almost always short" -- a convention prior for milestone 4, narrowing only. Was: Inside the staff, is a word ever anything other than a dynamic or a short word like *pizz.* or *dolce*?
