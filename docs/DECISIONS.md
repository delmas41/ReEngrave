# Decisions

Append-only. One dated line per decision, who made it, and the reason in a
clause. A decision is a fact about what the project does from that day; the
measurement behind it lives in the benchmark `FINDINGS.md` it names. Nothing
here is ever edited in place — a reversal is a new line.

Format: `YYYY-MM-DD · who · the decision · because · (pointer)`

---

- 2026-09-22 · Sean · **The staged pipeline is the product path. The legacy
  reader (`transcribe.py`, `export.py`, `contextual.py`) is FROZEN: bug fixes
  only, no new mechanisms, no new flags.** · because every decision since
  09-08 is on staged and the product was still running legacy ·
  (`docs/plan-2026-09-22-from-here-to-a-finished-score.md` §5 Phase 0.1)
- 2026-09-22 · Sean · **CLAUDE.md is archived as `docs/chronicle-2026-09.md`
  and replaced by a spec under 6,000 words; `DECISIONS.md` and `ROADMAP.md`
  are the two living documents beside it; handoff documents stop.** ·
  because a 132,000-word chronicle read as a spec is where the bad premises
  came from · (plan §5 Phase 0.3)
- 2026-09-22 · manager, on Sean's delegation · **The acceptance set is:
  Beethoven 5 mvt 1 / Litolff `984073` (scan); Brahms 1 mvt 1 / Breitkopf
  `317803` (scan); Beethoven 5 mvt 1 bars 1–24 rendered by Verovio
  (engraved).** · because they are the two publishers every lane measured on,
  the only scans with hand-verified windows, and the only input with an exact
  page truth · (plan §4)
- 2026-09-22 · manager, on Sean's delegation · **The cleanup-count pages are
  Litolff pdf page index 3 (works row `…984073-p3`: two systems, 19 staves,
  the 8-staff suppressed system, bars 49 on), Breitkopf pdf page index 1
  (works row `…317803-p2`: two systems, 27 staves, bars 8 on, holds the 9/8
  bar), and page 0 of the engraved render.** · because each is the hardest
  page its document offers that still has a hand-verified window · (plan §4)
- 2026-09-22 · Sean · **No lane cap while a manager session is in charge.**
  · because the cap was a substitute for coordination, and the manager is the
  coordination · (plan §5 Phase 0.5, amended)
- 2026-09-22 · Sean · **Flag triage proceeds: every flag gets promote /
  delete / research; the product path reads at most 15.** ·
  (`docs/flags-2026-09.md`)
- 2026-09-22 · manager · **Legacy-only flags (39) are frozen with the legacy
  path and are not triaged**; they are listed in `docs/flags-2026-09.md` as
  FROZEN and may not be read from `tools/omr/staged/`. · because triaging a
  frozen path is work with no consumer.
- 2026-09-22 · Sean (rule) / manager (form), after the crops · **A staff the
  family-block rule narrows to exactly [Cello, Contrabass] is PLACED on BOTH
  slots: the printed line goes to the Cello part and, doubled with
  `<transpose>` −8ve and a `condensed_from` mark, to the Contrabass part.** ·
  because the page says both sections play that line (Litolff condenses where
  the reference is 94–100% identical and splits where it is not), the count
  is the narrowing's own candidate set and not a name or an encoding, and a
  single shared part would leave the Contrabass with holes on a document
  that also prints it apart · `OMR_CONDENSED_PARTS` stays off — this is
  narrower and does not need the count it lacked ·
  (`benchmarks/omr-cello-bass-convention-2026-09/FINDINGS.md`)
- 2026-09-22 · Sean · **`OMR_ENGRAVED_KEYSIG` defaults ON: on a document
  MEASURED engraved, the key signature is read from the template before the
  locator.** · because the shipped precedence's stated reason — *"the locator
  loses accidentals to broken ink"* — is refuted on a vector render, where the
  locator loses them anyway 24 times in 30 and the template over-counts
  nowhere (right 26 → 47 of 50; bars exact 313 → 322 of 360, 4 parts better
  and 0 worse); it is safe to default because the rule is ONE-SIDED and every
  other input keeps the shipped precedence, verified by
  `test_keysig_second_reader.py` passing unmodified · ⚠️ n = 1 engraved
  document, 1 renderer, **no print consulted**, and the scan side is shown
  only to be a no-op ·
  (`benchmarks/omr-document-identity-2026-09/FINDINGS.md`)
- 2026-09-22 · Sean · **`OMR_DOCUMENT_IDENTITY` defaults ON, and the
  scanned-vs-engraved verdict is a SEPARATE quantity (`Q.INPUT_DOMAIN`,
  `source_kind: "container"`) from the catalog row.** · because the printing
  should be gathered in the first stage (his words), and because the catalog
  cannot supply the domain where it is most needed — the engraved fixture the
  rule is proven on is a render in no catalog, so the catalog row ABSTAINS
  `not_in_catalog` on it while the container reader answers · ⚠️ the catalog's
  `image_type` is kept beside the measurement as a second witness and is NOT
  what any decision keys on; measured over all 289 editions the two agree 279
  of 279 wherever the label exists, so its failing is ABSENCE not error ·
  (`benchmarks/omr-document-identity-2026-09/FINDINGS.md` §1-2)
- 2026-09-22 · manager, on print evidence · **Two notehead-precision refusals ship
  on the staged path: `too_narrow` (a `noteheadBlack*` box under 1.0 staff space
  in the cell's own unit) and `clipped_fragment` (the ported edge-sliver rule).
  `unladdered` is HELD BACK (computed, recorded, never acts).** · because against
  the 255 print-adjudicated boxes the two cost 1 of 29 and 1 of 74 confirmed
  noteheads and catch 10 of 19 and 32 of 44 confirmed non-noteheads, while
  `unladdered` cost 4 and 4 for 0 and 2 caught — the cell carries no ledger
  detection at all, a recall gap the rule cannot see past · reversible here;
  12 fresh crops await Sean in `benchmarks/omr-notehead-precision-2026-09/out/print/`
  · (`claude/notehead-precision-2.4a` 5dbd0758)
- 2026-09-22 · Sean (crops) / manager (record check) · **The 2.4a refusals stand,
  print-checked: 12 of 12 fresh crops correct.** · because the six `too_narrow`
  boxes are five barline pieces and an eighth rest, and the six
  `clipped_fragment` boxes are the tips of notes belonging to the NEIGHBOURING
  staff, each of which is fully boxed in its own staff's cell at 0.66–0.85 ·
  (`benchmarks/omr-notehead-precision-2026-09/out/print/ADJUDICATION-sean-2026-09-22.json`)
- 2026-09-22 · session, on measurement (roadmap 1.1b) · **A staged record FILE
  pools its repeated verdict id lists (`tools/omr/staged/record_io.py`), and a
  record file is read through `record_io.load_record`, never bare `json.loads`.**
  · because an `arc_owner` verdict is 99.2 % three copies of its system's
  ~1,800 glyph ids (`considered`/`basis`/`correlated`), identical for every arc
  in the system, and the content is load-bearing (`basis` → `Log.closure` →
  the circularity filter) so only the SPELLING may change; pooled, Breitkopf
  goes 59.3 → 13.2 MB/page and Litolff 18.8 → 8.0, both under 1.1's 20 MB/page
  · ⚠️ a naive `json.loads` reader sees a dict where a list was and a
  `quantity_of.get(rid)` walk silently drops it — which is why the loader is a
  rule and not a convenience; nothing in memory is pooled, `Log`/`Verdict`/every
  stage are untouched, and the writer proves its own round trip on every call ·
  (`benchmarks/omr-ink-gather-2026-09/FINDINGS.md` §12)
- 2026-09-23 · Sean · **The two INFER duration rules read `Q.GLYPH_OWNER`, and
  a glyph whose ownership names another staff is DROPPED from the walk — never
  relocated, and never dropped on silence (a glyph with no ownership verdict was
  never contested and is kept).** · because 3 of 3 crops he adjudicated against
  the print sat on a NEIGHBOURING staff's first ledger line while the rules
  borrowed a length from the detection cell's own neighbours — on
  `glyph/4/0/9/5/7` ownership already said Basso, the rule inferred 0.25 from
  Violoncello's columns, and the note is a Basso eighth (print and encoding
  agree) · measured: reach 16 → 13, **0 surviving values changed**, control
  19,563/19,563 unchanged; `export.py` already refused the same copies under
  `owned_by_another_staff`, so the omission was confined to these two rules ·
  both rules stay default OFF; the default decision is still open ·
  (`benchmarks/omr-infer-duration-print-2026-09/FINDINGS.md` §7–§9b)
- 2026-09-23 · Sean (convention) · **A note stands far from a staff only through
  a ladder of ledger lines connecting it back; a note one space beyond a
  neighbouring staff's outer line is that staff's, on its first ledger line.**
  · in his words: *"notes should never be that far away from a staff unless
  there are ledger lines close to the staff connecting the note conceptually to
  the staff"* · measured on 3 of 3: 1.41 / 1.55 spaces from the staff he named
  against 3.60 / 3.77 from the filed staff, which would need a three-rung
  ladder; it confirms `glyph_owner`'s ladder-first ordering, and the rungs that
  would prove it were NOT detected (nearest `ledgerLine` 7.34 spaces off in one
  cell, zero in another — the recall gap that made 2.4a's `unladdered` net
  negative) · ⚠️ **not yet in `tools/omr/conventions.py`**: an entry nothing
  reads becomes an open finding in `staged.check`, so it goes in with its
  consumer, not before · (same FINDINGS, §8)
- 2026-09-23 · Sean · **`OMR_INFER` flips OFF→ON: both INFER duration rules
  (`collapse_duration_by_column`, `collapse_duration_to_barline`) ship on
  (roadmap 2.3).** · because the three subjects he adjudicated against the
  Litolff print were each wrong for the same reason — the rules read a glyph
  ownership had awarded elsewhere — and are right once `Q.GLYPH_OWNER` is in
  their `reads`; measured OFF→ON on both whole-movement records, balanced,
  Litolff 0→69 and Brahms 0→287 inferences · ⚠️ Breitkopf's funnel inverts
  (by-column dominates) and 0 of its subjects are print-checked; a session
  that finds one wrong files a crop and asks, it does not flip the default
  back · (`6f269360`, `benchmarks/omr-infer-default-2026-09/FINDINGS.md` §7)
- 2026-09-23 · Sean · **The in-bar accidental goes on the roadmap as item
  2.7** — GATHER a staff-position reading of the printed glyph, ADJUDICATE
  which notehead it modifies (immediately right, same height, may abstain),
  EVALUATE a bar-scoped override of the key-derived spelling, EXPORT
  `<accidental>` through the legacy renderer already reused · because 1,531
  glyphs are detected on the Litolff movement and 0 reach any verdict, so
  every alteration in the file comes from the key alone — the largest thing
  the first cleanup count found · ask first how Litolff prints courtesy
  accidentals before writing `parentheses="yes"` · (ROADMAP 2.7)
- 2026-09-23 · Sean (instruction) / session (measurement) · **`glyph_owner`'s
  domain is roadmap item 2.6, and the fix is in GATHER, not in the
  adjudicator**: `gather_ownership_evidence` compares smufl names and IoU 0.5
  where the frozen legacy contest compares `category` and IoU 0.3, and the
  name encodes on-line-vs-in-space — the quantity in dispute · because all
  161 never-contested glyphs lack a band-distance row of any state (0
  abstentions, 0 scope faults), and the 8 'elsewhere' all resolved to their
  own staff or tied · `subjects_from=Q.GLYPH_BAND_DISTANCE` stays; the 38 with
  no twin are not handed in · (`64c83c5f`,
  `benchmarks/omr-infer-duration-print-2026-09/FINDINGS.md` §10)
- 2026-09-23 · Sean, on the count pages · **The first cleanup count is NOT
  taken; its result is three sentences.** *"the amount of fixes is still too
  many to count — we are not even close to getting the noteheads correct"*;
  *"it is allowing for math that doesn't add up at all"*; *"the key signatures
  don't make sense either — they don't match each other on the same page, even
  the engraved Beethoven."* · because each was measured true within the hour:
  68 of 408 staff-bars on the Litolff count page do not sum to 2/4 and export
  never checks; the engraved page writes one flat on 9 of 18 parts against a
  truth of three; Viola on that page has 24 heads written against 49 printed ·
  the count is read as *what to fix next* (CLAUDE.md §6a) and it has said so
  · (ROADMAP 2.8, 2.9; START HERE)
- 2026-09-23 · Sean · **A bar whose durations do not sum to the meter is HELD
  OUT — exported as the marked empty bar a bar we read nothing in gets, its
  heads counted under a named refusal — not kept with a mark.** · *"hold out —
  I don't care about print right now — I want to know what we are getting
  correct"* · rule 8: a bar we could not read to its meter is a bar we could
  not read; nothing pads, trims or re-times it · (ROADMAP 2.8)
- 2026-09-23 · Sean · **A key signature is decided per SYSTEM by MAJORITY of
  its staves, transposition-normalised; a tie abstains and carries.** · *"majority"*,
  asked against the alternative (abstain and carry on any dissent) · because a
  key change is printed on every staff of a system (CLAUDE.md §10), so a lone
  staff's different key is a misreading of that staff, and the other staves are
  independent witnesses of the same plate fact · the dissent stays recorded ·
  (ROADMAP 2.9)
- 2026-09-23 · Sean · **The accidental build (2.7) is stopped and parked**
  (`claude/accidental-2.7` `69d64d95`, code committed, unmeasured) · because
  accidentals on wrong heads under wrong keys are wasted work; resume after
  2.8, 2.9 and notehead recall · (ROADMAP 2.7)
- 2026-09-23 · Sean, after the trace · **The key signature is READ OFF THE
  DETECTOR'S HEADER BOXES; the fitters corroborate; the system agreement is a
  CHECK, not a vote — this AMENDS the majority line above.** · *"it seems like
  we don't even need the majority rule — we have gathered all the info we need
  to make the correct assessment — we just need to know what to do with the 3
  boxes around the 3 flats on every staff"* · because the engraved acceptance
  record shows three `keysig_marker` rows on every staff of the system and a
  `fitted` verdict of −1 on every treble staff, from a locator fit that says
  one accidental — the decision declared the markers in `wants` and read none
  of them; and a concert-normalised majority on that page is 8 vs 8 · a fit
  that disagrees with the markers is recorded, never silently dropped; markers
  absent → the fit speaks alone, named `fitted_no_markers`; a staff disagreeing
  with every other decided staff of its system is superseded to ABSTAINED and
  carried · ⚠️ the acceptance record predates `Q.INPUT_DOMAIN`, so 2.2's
  engraved rule never fired on it — re-gather before scoring · (ROADMAP 2.9)
- 2026-09-23 · Sean · **A staff whose clef cannot be read, on a part whose
  instrument is decided, takes the clef the same part shows on OTHER SYSTEMS
  of the document, else the instrument's conventional header clef; gaps only,
  in INFER, labelled.** · *"yes — viola staff with unreadable clef reads as
  alto and it should check other systems if the alto clef can be found"* ·
  because on Litolff p3 the detector boxed 48 Viola heads and the file holds
  0: the alto clef is merged into the lines, boxed as two noteheads, the clef
  abstained, and every head died at export as `no_pitch` — while the same
  part one system down, clef read, writes 24 of 27 · the fact sheet already
  speaks a supplied clef gaps-only (§8); identity-upstream is the 09-05
  inversion · a READ clef is never overruled · (ROADMAP 2.10)
- 2026-09-23 · Sean (convention) · **A clef's size is consistent with the
  staff and its position with the edge of the first measure of the system;
  clef-sized ink at the header IS the clef, and a notehead box on it is the
  error.** · *"it also looks like the clef box is too small. the size of clefs
  are consistent to the staff and the edge of the first measure on the system
  — that should be helpful geometrically"* · because on Litolff p3 the CV
  locator found a 4.5-space cluster on the Viola staff at the header and
  abstained `occupied` for two noteheads of conf 0.64/0.36 sitting on it — a
  1-space symbol vetoing a 4.5-space read · a READ by geometry outranks 2.10's
  inference · (ROADMAP 2.11)
- 2026-09-23 · Sean · **Build the stage review (roadmap 3.4): a staff on a
  system, every stage's evidence and decisions shown in turn, his corrections
  filed as WITNESSES the stages re-decide with, never as edits; first on the
  Litolff p3 Viola staff.** · *"yes — build it on the viola staff, corrections
  as witnesses — I mainly want this information so that we can then use it to
  determine how to refine the build, rules and decisions — structurally. All
  of the info would be given to you to turn into fixes."* · because the three
  faults found today (key, clef, bar sums) were each found by following one
  staff through the stages by hand, and the record already files every
  decision against a subject with the rows it used · the output of a review
  pass is a feedback FILE for a session, not a corrected score · (ROADMAP 3.4)
- 2026-09-23 · Sean · **SHAPE FROM THE CLASS, ROLE FROM THE GEOMETRY — the
  methodology for every symbol.** A detector class is TWO claims: the SHAPE
  (a flat; a black notehead; a C-clef), which the detector is good at, and
  the ROLE (key-signature flat vs in-bar accidental; on-line vs in-space;
  clef vs notehead on clef-sized ink), which is a guess about context made
  from a crop. GATHER files the shape and the position and records the
  detector's role-guess as ONE witness; ADJUDICATE decides the role from
  geometry on the record. **No gather filter may key on the role-half of a
  class.** · *"YES — record that because it needs a methodology for all
  symbols. it seems that our staged model would require it to look at all
  the blobs and come up with a list of potential ways it could be labeled
  with boxes, yolo/CV choices all connected to the ink, and then allow the
  other stages to decide. There is probably a lot of code and architecture
  hiding in that."* · because the same collision was found three times in
  one day and fixed three times by hand: `_KEYSIG_CLASSES` drops a header
  flat the detector labelled `accidentalFlat` (53 Litolff and 84 Breitkopf
  header cells hold only such flats), the ownership contest refused twins
  spelled OnLine/InSpace (2.6), and a notehead label on clef-sized ink vetoed
  the clef read (2.11) · the direction this implies: the INK COMPONENT is the
  subject, every box is a reading attached to ink, a box may carry several
  candidate labels (detector top-k, CV locators), and the stages decide —
  `Q.INK` already exists as that population, read by nothing; the audit
  (ROADMAP 2.12) sizes the rest · (ROADMAP 2.12)
- 2026-09-23 · Sean, from his first stage-review pass · **What the detector
  boxed as `ledgerLine` on the Viola staff and he marked as nothing was
  "often a staff line, a bar line or extra ink."** · so the convention the
  refusal claims: a LEDGER LINE stands OUTSIDE the staff, at a whole number of
  spaces beyond the top or bottom line, short and horizontal; a `ledgerLine`
  box lying on a staff line's y is a staff-line fragment, a tall one is a
  barline or a stem, and neither is a ledger line · because 11 of the 18
  'nothing' labels that reached no stage were `ledgerLine` boxes, and ledger
  lines feed `glyph_owner`'s ladder term, so a false rung is a false witness
  in the cross-staff contest · (ROADMAP 3.4g, first family)
- 2026-09-24 · Sean, on 13 ledger-line crops · **Two ledger-line conventions,
  stronger than the three geometric rules built the day before: (1) a ledger
  line is only ever OUTSIDE the staff — a `ledgerLine` box inside the band
  between line 1 and line 5 is not one, whatever its distance to a line; (2)
  a ledger line only exists where there are notes — a bar holding only a
  whole rest has none, and a rung with no head on or near it is not a rung.**
  · *"a couple of obvious rules: the ledger lines will only be on the outside
  of the staff and only happen if there are actual notes in the staff"* ·
  measured on the crops: `on_a_staff_line` 4/4, kept 3/3, `tall_not_a_rung`
  2/3 (one real rung refused), the held-back rung-step rule 2/3 (would refuse
  a real rung — stays held back) · (ROADMAP 3.4g-2)
- 2026-09-24 · Sean · **The in-bar accidental (roadmap 2.7) is UN-PARKED and
  placed AHEAD of 2.3, at the head of Phase 2.** Kept as 2.7, not renumbered to
  2.6 as first asked: 2.6 is the merged ownership-domain item, and renumbering
  breaks every branch name, commit and pointer that cites either. · because
  two whole movements now measure it — Litolff 1,531 accidental glyphs
  detected and 0 read into a verdict, Breitkopf 6,533 and 0: **8,064 of 8,064
  unread**, every `<alter>` in both files from the key signature alone — and
  the first cleanup count named it the largest single fault on the page ·
  reverses the 2026-09-23 park, whose own condition (resume after 2.8/2.9)
  was met overnight; the notehead recall (2.4b) is NOT waited for · the code
  on `claude/accidental-2.7` (`69d64d95`) is unmeasured and needs a merge, not
  a fast-forward; merging is not completion — the 2.7 gate stands ·
  (`benchmarks/acceptance/out/*/…coverage.json` → `accidental_reading`;
  `benchmarks/omr-cleanup-count-2026-09/counts/README.md`)
- 2026-09-28 · overnight manager, by CLAUDE.md §4a (not Sean) · **2.9c: the
  slot placement STAYS in INFER, and the ADJUDICATE part check speaks to a
  NARROWED slot only when every candidate reaches the identical expected key.**
  · `collapse_slot_index_to_family_block`'s own docstring says its answer is
  BEST rather than FORCED (a tacet Violino II or another condensed pair would
  shift the block), so moving it into ADJUDICATE would promote a guess;
  whereas "every candidate part expects −3" FOLLOWS whichever candidate is
  right · Litolff key changes 18 → 0, wrong staves 9 → 0, Brahms and engraved
  byte-identical · (ROADMAP 2.9c, merge `2d2352fb`)
- 2026-09-28 · Sean · **maestroAnalyst stays OFF by default and its INFER
  role is PARKED (ROADMAP 2.16).** Scoped in chat: it fits INFER (choose among
  a narrowed verdict's own candidates, labelled) but not meter/key, and today
  it is not in the container, reads nothing on the staged path, and its output
  is displayed nowhere · *"it feels less important than what we already have
  to get done and I'm worried about scope creep"* · recorded so the idea is
  not lost; no lane until he un-parks it
- 2026-09-28 · Sean · **Build and wire; stop burning runs on proof.** A lane
  proves its change with RED→GREEN unit tests, ONE count page or ONE saved
  record read, and a handful of crops for Sean — NOT whole-movement base-vs-arm
  re-adjudications or re-gathers, unless the item exists to move the
  whole-movement number. Re-gather once at the end of a batch, not per change ·
  *"I feel like we are burning through a lot of my limit for test runs … we
  should be building and wiring"* · what the night showed: the cheap checks
  (one record read → the Brahms funnel; six crops → 2.4c's text marks) paid;
  the expensive ones (2.11b ~5 h for one clef; 2.14 two re-gathers for zero)
  did not, and per-rule deltas on a file 78% held out say little
- 2026-09-28 · overnight manager, by CLAUDE.md §4a (not Sean) · **ROADMAP 4.2:
  a movement is a MEMBERSHIP fact, not a new `Kind` in the `Subject` path.**
  The plan's own text says "`Kind.MOVEMENT` between DOCUMENT and PAGE", but
  inserting a level would change every subject id (`glyph/p/s/st/c/g`) this
  repo has ever saved a record under, including the three acceptance records
  adopted this same day — so `Kind`/`Subject` stay untouched and a movement is
  `Q.MOVEMENT_SPANS`, an ordinary external-fact Observation on the DOCUMENT
  (human-supplied via `--movements`, the same admissibility as `Q.DOSSIER_
  FACT`/`Q.ROSTER_ENTRY`), read by `tools.omr.staged.movements`'s pure
  `same_movement`/`movement_of`/`movement_boundaries`. A record with none of
  these rows is untouched — the single-movement default — and EXPORT can
  split an already-adjudicated record with no re-gather at all (build
  `claude/movements-4.2`)
- 2026-09-28 · Sean · **A meter change holds until the plate prints a change
  back; the return is always printed.** · *"Anytime the meter changes it must
  show a change back to the original meter or it stays at the new meter"* ·
  corrects CLAUDE.md §10's "a meter is printed at a movement's start and
  nowhere else". Consequence: Brahms 1/i m. 9's return to 6/8 is a READING
  miss (printed on ~13/14 staves, never boxed — 2.12h.b), and the file gets
  6/8 back today only because the bars weigh against carrying 9/8. Where the
  bars overturn a carried change, the switch must be LABELLED as an inferred
  unread return and the bar marked (→ ROADMAP 2.12k), never silent
- 2026-09-28 · Sean, looking at the o26b ownership crops · **Two ownership
  conventions: (1) the ledger lines name the owner — a note far from its
  staff has ledger lines between it and the staff it belongs to, and none
  between it and the other staff; (2) a hairpin always sits UNDER its staff,
  so a note between a staff and the hairpin beneath it belongs to that
  staff.** · *"there have to be ledger lines in between wherever that note is
  and the staff that it's connected to … if the note is above the hairpin …
  it belongs to the staff that's between the hairpin and that staff"* · both
  should decide a contest BEFORE distance; on the f4168dfd Brahms record
  2,046 of 3,590 dropped heads were decided by distance alone · the hairpin
  is a witness from a different glyph family, not correlated with the
  notehead reading (§10) · → ROADMAP 2.6c, which waits on Sean's o26b
  verdicts
- 2026-09-28 · Sean, correcting the manager's reading of the 2.7b verdicts ·
  **The ledger lines are AUTHORITATIVE for which staff a far note belongs
  to; nearness is only a hint and never overrides them.** · *"Nearer to the
  staff is not always going to be right but ledger lines will be. If it is
  not working out that way right now then the tests are off"* · so when a
  ledger-based answer disagrees with the print, the fault is in FINDING or
  CREDITING the rungs (staff-line fragments boxed as rungs, a rung attached
  to the wrong head, a wrong direction), never a reason to prefer nearness;
  a far note with no rungs found either way is a reading gap and abstains ·
  2.7b's 18/18 nearer-staff refusals stand as results, not as the principle
- 2026-09-29 · Sean · **Work through the wiring conceptually, proved by
  MICROSCOPIC tests — not pricing runs.** A lane states the connection or
  convention in a paragraph and proves it with small RED→GREEN tests built
  from a handful of real rows (a fixture of the actual observations/verdicts
  for 2–3 real subjects) plus a positive control. No gathers, no base-vs-arm
  re-adjudications, no crop batches per change · *"our process spends too
  much time and context on pricing runs"* · tightens 2026-09-28's "build and
  wire": the one-record read and the crops are no longer the default proof;
  a whole-movement number is taken rarely, as a nohup script, never by a lane ·
  clarified the same day (Sean): *"I dont mind anything that costs machine
  time if it doesnt cost context or tokens"* — so long runs are FINE as
  unattended nohup scripts that write a small summary file; what is
  forbidden is an AGENT waiting on, reading, or iterating over a run
- 2026-09-29 · Sean, answering 2.27b's six placement questions
  (`benchmarks/omr-owner-domain-2026-09/PLACEMENT-CONVENTIONS.md`) · (1)
  displaced rests in multi-voice staves DO occur in this orchestral corpus —
  wire them; (2) the grand-staff rows (pedal marks, between-staff dynamics,
  cross-staff beaming) — BUILD anyway, though no keyboard/harp work is in the
  acceptance set; (3) bowing marks — *"I don't see bowing marks very often,
  don't know the rules"* → research, don't guess (ASSUMED stays unbuilt);
  (4) *"all text should be categorized, and tempo markings, titles,
  composers' names should all be wired, but low priority"* → a roadmap item,
  after the ownership wiring; (5) grace notes and fingerings inherit their
  target note's decided owner TOGETHER with the `dot_role` fix; (6) octave
  brackets occur both above (8va) and below (8vb) the staff
- 2026-09-29 · Sean, answering the voice-split question
  (`benchmarks/omr-voice-split-2026-09/QUESTION.md`, 8 crops) · **All 8 crops
  are ONE voice.** The convention: (1) notes on the SAME beat with stems in
  different directions are ALWAYS two voices; (2) two voices can also be NOT
  lined up — a human knows them because each line on its own has a FULL
  measure of durations and the two are spaced apart on the staff, one above
  and one below; (3) a line whose durations add up to one measure as a single
  line is one voice (*"those crops would obviously be 1 voice because the
  measure math adds up to 1 measure"*) · the bar sum here is Sean's stated
  witness for VOICE COUNT, not a meter check — where neither one line nor two
  full, vertically separated lines add up, the voicing abstains (rule 8)
- 2026-09-29 · Sean · **Biggest difference first; guard against scope creep.**
  *"We're in phase 2 of a bigger plan … my main concern is that we're putting
  our energy in things that actually make the biggest difference first."* ·
  applied as the plan's own Phase 2 rule (plan §Phase 2: "work the funnel from
  the top, largest loss first, and re-read the funnel after each item — the
  ranking is the trace's"): every lane brief names the FUNNEL BUCKET it moves
  and its size on the whole-movement records; an item that moves no top
  bucket is PARKED on the roadmap, not built; the funnel is re-read (one
  unattended script) after each batch. Parked by this: 2.28 page text,
  pedal/ottava MusicXML output, bowing-mark research, and 2.31 except the
  structural gaps that starve a top bucket
- 2026-09-29 · manager, on Sean's instruction to find out *"for certain why these are not working"* · **Round 6's conclusion ("every specialist deletes its own class because the labels are incomplete") is WITHDRAWN.** Re-run under round 6's own recipe and its own counting instrument, the rest specialist does not collapse (rest8th 12, restQuarter 7 unchanged; recall 0.80 → 0.68 over four epochs — slow erosion, not deletion); completing the labels (arm B) changes nothing measurable; a hollow specialist with ZERO rest labels scores the same on rests. Round 6's raw outputs were destroyed and its box truncated downloads, so the original collapse cannot be re-derived — treat it as unexplained, not as evidence · consequences: grafting is NOT doomed and more labeling is NOT the proven lever for rests; production already finds 0.909 of held-out rests, so the rest problem that holds bars is FALSE rests (precision), which the staged refusals address; `merge_class_head.py` restores class rows only, never the shared box-regression head (flagged, not fixed) · `benchmarks/omr-labeling-survey-2026-09/REST_SPECIALIST_EXPERIMENT.md`, `UNBOXED-AUDIT.md`
- 2026-09-29 · Sean · **How new weights are tested: graft them into a COPY of production and compare the two on the output of the first two stages (GATHER + ADJUDICATE) — same pipeline, same pages, only the weights differ.** *"Better reading is better reading — how we use it matters … the only way to really test is to take newly grafted weights and add them to a copy of production and compare the 2."* Detector-level box counts against a different model (apples vs oranges) are not the test · and two rest conventions, CONVENTION ASSUMED until he confirms the edges: (1) *"whole and half [rests] will always be found geometrically near the horizontal middle of the bar — I saw some false whole and half rests far off to one side of the bar"*; (2) rests are not found as far above/below the staff as noteheads on ledger lines (*"I don't think rests are found as high as note heads on the ledger lines"*) — so a rest's own vertical window is tighter than a notehead's
- 2026-09-29 · Sean, on rest-vs-notehead confusions in the rests queue · *"I think it went both ways but I think a common mistake was a black notehead was called a whole or half note rest. The rest should never touch 2 different staff lines."* · convention: a whole rest hangs from ONE line, a half rest sits on ONE line; a black notehead in a space fills it and touches the lines ABOVE and BELOW — so a whole/half-rest box whose ink touches two staff lines is a notehead, not a rest (applied to whole and half rests only; quarter/8th rests span lines by shape) · where a rest box and a notehead box are the same mark, this test decides; where it cannot, neither reading is chosen (rule 8)
- 2026-09-29 · manager (ROADMAP 2.34) · **`merge_class_head.py`'s graft was backwards, and the shipped production graft carries the bug.** The plain `--ft`/`--base` path (what `compose_specialists.sh` and every round-5/6 ship command called) started from the FINE-TUNE's whole state dict and restored only the non-kept classes' `cv3` rows from `--base` — so `model.22.cv2.*` (box regression), the DFL layer, the backbone/neck, and every KEPT class's own row rode along as the fine-tune's, unrestored. This sharpens the previous entry's "flagged, not fixed" into a confirmed fact: a read-only tensor diff of `hollow-graft-shift09-2026-09-04.pt` (`0e9f005b`) against its recorded base (`hollow-ft-2026-09-03.pt`) and donor (`round5-sweep/distill25/epoch0.pt`) shows 589 of 595 tensors — including every box-regression tensor and the whole backbone — bit-identical to the fine-tune, not the base. Production's box-placement network today is `distill25`'s, not `hollow-ft-09-03`'s. Not necessarily worse (round 5's own three-axis gate passed this exact checkpoint on all three before shipping), but a different, more invasive object than every downstream composability check in this benchmark line has assumed. **Fixed**: the graft now anchors on `--base` unconditionally and writes only the kept classes' `cv3` rows onto it — the same shape `--import-rows` and `transplant_class_rows.py` already used correctly. Whether to re-ship a graft built with the fixed tool is Sean's call, not made here · `benchmarks/omr-weights-ab-2026-09/FINDINGS.md`
- 2026-09-29 · Sean, via the manager, mid-lane on 2.34 · **`tools.omr.staged` gained `--through {gather,adjudicate,evaluate,infer}`** (default `infer`, every stage, unchanged): *"if we try grafting weights can we do that in the first 2 stages of production … where it just handles gathering ink and boxing and identifying before it goes to all of the other stages?"* `--through adjudicate` runs GATHER+ADJUDICATE only, stamps `stopped_after`, and refuses `--musicxml`/`--lilypond`/`--pdf` together with anything but `infer` (EXPORT needs what EVALUATE/INFER derive). A CLI option, not an `OMR_*` flag — read once per run, like `--movements`/`--sheet`. `benchmarks/omr-weights-ab-2026-09/`'s A/B harness uses it so a weights arm is compared with no consequence rule able to make the two agree or disagree for a reason unrelated to the weights
- 2026-09-29 · Sean ran option A · **Keep today's production weights. The accidental near-full fine-tune (2.34) reads hollow noteheads BETTER than the graft that was intended on 09-04.** Same pipeline, stages 1–2 only (`--through adjudicate`), control P-vs-P = zero differences. Beethoven 5 p1 (68 half notes printed): hollow heads found production **31** vs intended graft 17; pitch recall 0.63 vs 0.50; recall with duration 0.52 vs 0.37. Rests roughly equal (Brahms p1–4 against Sean's verdicts: 26 vs 24 matched); the intended graft adds 89 `restHBar` boxes on Brahms that all end `unreadable_rest` · consequences: the fine-tuned "eyes" (backbone/neck/box head), not only the 7 class rows, carry the hollow gain — so future grafts are trained FROM and stacked ON today's production; and "fine-tuning deletes classes" (round 5) deserves the same re-check round 6 got, since production IS a fine-tune that passed every gate · `benchmarks/omr-weights-ab-2026-09/out-A/`, `benchmarks/omr-labeling-survey-2026-09/hollow_eval_*-intended-2026-09-29.json`
- 2026-09-29 · manager, answering Sean's weights question · **"Fine-tuning deletes classes" survives rule 7, narrowed: the deletion is in the last layer only.** Production and `round5-sweep/distill25/epoch0.pt` differ in exactly `model.22.cv3.{0,1,2}.2` and read 127 vs 0 beams (19 vs 0 ties, 15 vs 0 sharps) on the same 30 cells — the print shows the beams. Production is round 5 §3's own design (fine-tune + base rows restored for 201 untaught classes); the 2.34 entry above calling the 09-04 tool "backwards" is corrected: it was backwards relative to CLAUDE.md §9's summary, not to the design, and option A shows the design is the better direction. CLAUDE.md §9 rewritten. `ledgerLine` is the one class whose FEATURES moved (11 vs 57 pre-hollow on engraved cells), but engraved pages route to the pre-hollow weights and scans show no loss (240 vs 268, the difference mostly staff lines) · no re-ship, no training · `benchmarks/omr-weights-ab-2026-09/FINDINGS.md` §5, `out/print/weights-question-2026-09-29/`
- 2026-09-29 · Sean, on the weights-question crops · confirmed against the print: the ledger boxes the pre-hollow weights draw on the engraved cells are real ledger lines, and production's beam boxes the raw fine-tune lacks are real 8th/16th beams · the last-layer deletion finding and the engraved-only ledger loss stand on his verdict · `benchmarks/omr-weights-ab-2026-09/FINDINGS.md` §5
- 2026-09-29 · Sean, on the Breitkopf ledger crop · cells 1–2: the older weights' extra boxes are staff lines; cells 3–4: they are real ledger lines production missed · geometric split over 110 scan cells: outside-the-staff boxes only the older weights find 37, only production finds 54; inside-the-staff (false) 58 vs 16 — production is not worse on scan ledgers, both miss some · FINDINGS §5
- 2026-09-29 · Sean · **Ledger lines are a CV job, not a training job** (*"Wait! Shouldn't ledger lines be CV?!"*, after the manager proposed a row-only ledger graft) · a ledger line is a thin horizontal run at the staff's own line thickness, at a whole number of spaces outside the outer line, a little wider than the head it serves — every term known from the staff frame, none needing a detector; the detector's ledger boxes brought staff-line false positives (58 boxes on staff lines across 110 scan cells, older weights; 16 for production) that a refusal (`ledger_is_not_a_ledger`) then had to clean · consequence: no ledger training run; ROADMAP 2.37 makes 2.6d's ink reader the primary witness

- 2026-09-29 · Sean · run 2.37 now as a THIRD concurrent lane (the two-lane cap is his, and he lifted it for this one)
- 2026-09-29 · Sean · **"There is no such thing as a far note with no ledger line."** Every head beyond the first space outside the staff has ledger lines toward its own staff · consequences: "no rungs found either way" is never a page fact — it is a missed rung, a misread head, or a note that is not far (abstain, count it as a reader failure); and a CLEAN empty ink reading at a step candidate A would require refutes A, so an owner can be DECIDED where every other candidate is refuted · CLAUDE.md §10 amended; sent to the 2.37 lane
- 2026-09-29 · Sean, on 2.35 · **drop both beat-slot refusals.** (B) a rest after the bar's decided beats are used up is not forced to be the false event — drop. (A) *"what I was originally asked was if the same thing was boxed could it be both a rest and a notehead. They can't, but they can be very close together"* — the same-mark case is 2.33's, and nearness between a real rest and a real note is legitimate, so a box-overlap refusal between two different marks proves nothing · §20d's "limited space geometrically" is not to be rebuilt as a proximity rule · branch `claude/rest-beat-slot-2.35` kept unmerged as a record
- 2026-09-29 · Sean, on `brahms_ledger_missed.png` (8 heads where the ink reader found no ledger and the detector boxed every rung) · *"Those are all ledger lines. Any note outside of the staff is either touching the outside staff lines, touching a ledger line or has one going through it. Any distance more than a notehead above the staff has ledger lines involved."* · the ink reader's misses are real (its overhang test fails short Breitkopf ledgers — 2.37 fixes the reader before its elimination rule may run); the three states are the convention `_ledger_expected` must match
- 2026-09-29 · Sean · **Pitch outside the staff is geometric; seeing the ledger lines matters less than knowing they are there** (*"we should be able to geometrically know based upon distance of spaces and ledger lines where a note is falling"*) · already true of pitch (`restate_pitch` reads `Q.NOTEHEAD_STAFF_POSITION`, never a ledger); the ledger READ is needed only for OWNERSHIP of a note between two staves, and there the manager narrowed 2.37 to a RELATIVE test — compare ledger ink on the two sides of the head at the one rung position geometry names toward each staff; the own-staff side has it, the far side never does; comparable → decline. The all-rungs elimination rule stays unwired
- 2026-09-29 · Sean · *"Why are note head boxes different sizes? All regular noteheads are the same size so the box should be predictable."* · measured median ≈ 1.4 × 1.1–1.3 staff spaces on both count pages, tails are slivers (Brahms p10 0.28 sp wide) and merged ink (Litolff) · ROADMAP 2.39: a standard head box from the staff's spacing around the detector's centre
- 2026-09-30 · Sean · *"Clean up count is not helpful at this stage because we are still too far away. It would be too many to count."* · the fix-action count (plan §4 measure 3, ROADMAP 1.4) is DEFERRED until the output is close enough to count; the Litolff p3 page + empty sheet built today (`counts/beethoven5-litolff-p3-SEAN-2026-09-30.csv`) stay for then · what to fix next comes from the machine funnel and Sean's eye on crops, not a count
- 2026-09-30 · Sean, reading Litolff p3 print vs output · *"On many of the Litolff bars there were dyads - 2 note per stem and most of those would show as one for us and then when it was a single note it would often print 2 notes either on top each other or a second apart. It looked like a double box on a single note issue"*; also *"Ties are almost nonexistent"* · the notehead COUNT per stem (missed dyads on a merging plate, doubled boxes surviving 2.30 as chord seconds) goes ahead of the beam residuals; diagnosis lane dispatched
- 2026-09-30 · Sean · *"Yes - a second is always on opposite sides of the stem"* · two heads a second apart on the SAME side of one stem are one head boxed twice (refuse the duplicate, never write a chord second); a real second puts one head on each side of the stem
- 2026-09-30 · Sean · *"We need to be able to isolate the output … for all of our initial tests I want to be comparing the output of just the first two stages"* · ROADMAP 1.5 (stage readout, one Opus lane at Sean's request); every initial test of a change is a GATHER+ADJUDICATE comparison (`--through adjudicate`), never the exported file
- 2026-09-30 · Sean, on a crop of Litolff p3 `glyph/3/0/0/2/4`+`/9` (two heads stacked on one stem, both in spaces above the staff, boxes overlapping, written F6+E6) · *"Those are simple 3rds"* · the detector boxed both heads right; EVALUATE's position rounding wrote a third as a SECOND. Some of what Sean saw as doubled heads are real dyads with a pitch a step wrong -- the duplicate rule must not refuse them
- 2026-09-30 · Sean · *"Correct, open noteheads are never beamed except tremolo"* · an OPEN (hollow) head's duration takes no beam level: a beam box cannot narrow a hollow head (a tremolo stroke through a hollow head's stem is a tremolo, not a beam level). Found by Sean on the stage readout: 28 of 49 undecided lengths on Litolff p3 were clear half notes narrowed by a stray detector 'beam' box the ink said was not over the note · ROADMAP 2.43
- 2026-09-30 · Sean, on the ruler crop of Litolff p3 bar 50 flute chords (`glyph/3/0/0/2/4`+`/9`, `/1`+`/3`) · *"Confirm D and F"* · both chords are F6 over D6 ⚠️ **CORRECTED the same day, below: the second chord is E6 over C6** (this confirmation was given on a crop whose ruler extrapolated the staff spacing); the fixed test for ROADMAP 2.42's pitch rule (the base wrote F6/E6, 2.42's first fit G6/E6)
- 2026-09-30 · Sean, on the ruler crop above Litolff p3 staff/3/0/0 · *"the ledger lines look like they are not evenly separated"* · measured: top line 449.5, printed ledgers at 431.5 / 418.5 / 398.5 (gaps 18 / 13 / 20) vs staff spacing 15.75 -- extrapolating the staff's spacing past the staff is ~4 px (half a step) off by the third ledger, which is what wrote Sean's D6 as E6 · Sean: *"Start it"* -- ROADMAP 2.44: a head OUTSIDE the staff takes its position from the PRINTED ledgers; 2.42 keeps only its duplicate-box refusal
- 2026-09-30 · Sean · *"start with geometry since it gets most of them correct and then measure back down to the staff through the ledger lines as a check... the geometry will be close and the ledger lines can rule out the confusion"* · ROADMAP 2.44 redesigned: a far head's position is today's geometry unless it sits within a margin of the rounding boundary; only then do the printed ledgers choose between the two neighbouring slots. Data (Litolff p3): the one wrong geometric read was 0.06 from the boundary; the two heads a ledger-first reader broke were 0.44/0.48 (confident, right)
- 2026-09-30 · Sean · asked for a one-page scanned test like the engraved one, to find issues without a whole-movement re-gather · ROADMAP 1.6 (quick scan test on the two count pages, scored against the reference encoding for those bars); the overnight re-gather stays the confirmation
- 2026-09-30 · Sean · *"we can have a small regather and a full regather. fulls happen overnight and the small happens during the day while we are working"* · working rule in CLAUDE.md §6b: small re-gather (1.6, count pages) by day; full re-gather (both movements) overnight, and only the full one feeds the acceptance numbers
- 2026-09-30 · Sean, on three eighth rests between two staves on Brahms p1 (`glyph/1/0/2/5/{0,3,10}` = `glyph/1/0/3/5/{1,0,2}`, bar 5; both staves refused them `rest_outside_its_staff`, so all three were lost) · *"They belong to the lower staff. I was able to determine that based on the amount of voices in each of the staffs. The one above has 2 voices and both the voices are accounted for. The one below has a voice that crosses as they both jump up higher. If the 8th note rests didn't belong to the lower staff then it would be missing a voice."* · CONVENTION: a rest far from both staves belongs to the staff whose VOICE would otherwise be missing at that time; a staff whose voices are already complete there cannot own it. Never refuse such a rest on both staves · ROADMAP 2.45
- 2026-09-30 · Sean · *"the notes underneath those are the ones that are most important when you get further away from the staff. The way a human generally reads the ledger lines ... we look to see how many lines that don't have notes on it between the staff and where the note is to determine pitch and then we see if it looks like it's on a line or a space so it's not the individual line that is important as much as the context of the other lines"* · CONVENTION (how a reader places a far note): COUNT the clean ledgers (no note on them) between the staff and the note, then decide line or space from the note's relation to the LAST clean ledger (near edge touching it = the space beyond; about half a space off = on the next ledger, hidden under the head). Never depend on reading the ledger through the head · ROADMAP 2.44 reader redesign; tested first in the geometry-vs-print measurement (option 1)
- 2026-09-30 · Sean, on a crop with the ledgers drawn where they are PRINTED beside each chord · *"The first chord is D and F and the second chord is C and E"* · Litolff p3 \`glyph/3/0/0/2/4\`+\`/9\` = F6/D6; \`glyph/3/0/0/2/1\`+\`/3\` = **E6/C6** (its printed ledgers 396.6/413.3/433.2 sit ~5 px higher than its neighbour's and pass through each head's middle). Plain geometry gets BOTH chords wrong (F6/E6 and F6/D6). Supersedes the earlier F6/D6 confirmation for the second chord. Lesson: never show Sean a ruler built by extrapolation
- 2026-09-30 · manager review of ROADMAP 1.6's first version (ff8afcb8) · "gathering only the count page loses the meter/key carry from earlier pages" · the small re-gather (1.6) must gather from the movement's FIRST PAGE through the count page, never the count page alone — proved against the committed whole-movement records (Litolff: 0 held bars in isolation vs 58 in full context on the same page); a lone page's local bar numbering restarts at 1 while a gather from the movement's start makes it equal the reference's own bar number, so no offset is guessed
- 2026-09-30 · Sean · *"I don't want to chase down where it is getting lost before we refine what we are reading in the first 2 stages"* · PRIORITY: work on what GATHER and ADJUDICATE read and decide comes BEFORE tracing downstream losses (held bars, export grouping). The small re-gather (1.6) defaults to GATHER+ADJUDICATE only; `--full` adds the later stages and the reference score as a second view
- 2026-09-30 · Sean · *"our overnight runs should progressively add stages also. Tonight it should be full regather but only of the first 2 stages"* · the overnight full re-gather takes `THROUGH` (default `adjudicate`); stages are added night by night as the earlier ones are refined. Tonight (tag 20261001): both movements, GATHER+ADJUDICATE only -- acceptance's current.json is NOT updated from it
- 2026-09-30 · Sean · *"That is correct"* -- a meter change is printed on EVERY staff of the system at one bar, like a key change · confirms ROADMAP 2.46's digit-witness quorum (0.8 cross-staff coverage), which the lane had marked CONVENTION ASSUMED
- 2026-09-30 · Sean · chose option B for a note OUTSIDE the staff: where his count-the-clean-ledgers rule and `measure_ledger_rungs` (tools/omr/annotate/ledger_grid.py) AGREE on the position, that position is used -- even where geometry is confident (his second flute chord, `/2/1`, reads F6 by geometry at 0.38 from the boundary but prints E6); where they disagree or either cannot read, geometry stands and the note is counted · supersedes the geometry-first-only rule for far notes · ROADMAP 2.44 rebuilt on this
- 2026-09-30 · Sean · *"In the past we have got to this point and go with reads like this and make decisions based upon it, but I'd like to double check our work and see what we can do to refine what we have to get it to work before we give up"* · the 2.44 option-B build changed `glyph/3/0/0/4/8` C6 -> B5 with BOTH readers agreeing (the reference: flutes E-flat6/C6 in bar 53) -- not merged; instead ROADMAP 2.44c builds a reference-backed truth set of every far notehead on the count pages (measurement only), scores geometry and both readers, and refines the readers in logged iterations before any switch-on decision. General lesson: when a read looks decisive, check it against the reference before deciding
- 2026-09-30 · Sean, looking at the staff under the two flute chords · *"there seem to be a place where the staff changed height ... if the staff measurements are set once and then for some reason the staff changes location it would put everything off"* · measured: Litolff p3 staff/3/0/0's top line wanders 447-454 px across the system (7 px) and its height 60.5-64 px (~5% spacing); `gather._cell_grid` takes one flat (top_y, half_step) per BAR, so a 2-4 px tilt within a bar and the spacing error grow with distance from the staff · ROADMAP 2.44c adds a 'local staff geometry' reading (staff lines fitted at the head's own x) to the reference-scored comparison
- 2026-09-30 · Sean · agreed: switch NO far-note pitch rule on yet · reference-backed truth set (2.44c, branch `worktree-agent-ac053ee5c8a371951` `e4c43164`, unmerged because it carries 2.44's option-B wiring): Litolff p3 far notes n=47 -- geometry 31 right, measure_ledger_rungs 36, two readers agreeing 4/0 (43 no answer), Sean's clean-count rule 5/12; Brahms n=11 all methods right; staff drift at the heads is sub-pixel and explains 0 of 12 misses; top/middle/nearest-line anchors identical; local fit + ink centre 30/39 vs geometry 27/39 on the same heads, ink centre alone worse -- all inside small-sample noise · NEXT: fix the measure partition (2.47) so the truth set can score whole movements, then decide on numbers that hold
- 2026-09-30 · Sean, on a crop of Litolff p2 system 0 with our kept barlines drawn · *"There is a real barline between 19 and 20"* · the measure partition DROPPED a printed barline at page x≈870 inside our cell 2, merging printed bars 19+20; everything after on that system is one bar behind (reference-content alignment agrees). ROADMAP 2.47 finds the rule that dropped it and how often it recurs
- 2026-09-30 · Sean, on crops of the 11 notes measure_ledger_rungs gets wrong · *"The blue boxes are not centered around the notes they're supposed to be reading ... the note is partially boxed incorrectly, and therefore leaving it open to being read as the other note"* · a HEAD-SIZED but OFF-CENTRE detector box (2.39b's open issue -- 2.39b re-centres slivers only) puts a correct head on the wrong side of a ledger; 2.44c tests reader 2 with the box re-centred on the head's own ink, then with the overhang test
- 2026-09-30 · Sean authorised a scoped A/B of the barline dedup rule (ROADMAP 2.47): the global per-staff pass keeps the LEFTMOST of two close candidates and lost Litolff p2's real barline to a stem; test `prefer=tallest` (narrowed to staff-spanning if a control fails) on every page with verified bar counts or printed bar numbers, at GATHER+ADJUDICATE, before any merge
- 2026-09-30 · Sean · *"the green staff lines are not lined up with the staff lines"* (on the manager's crops) · the crop drew the staff-WIDE `Q.STAFF_LINES` (a manager error), but checking it found a real effect: at Sean's D6 (`glyph/3/0/0/2/9`) position vs the PRINTED lines at the head is -5.42 (D6, right) while the pipeline's per-bar grid gives -5.56 (E6, wrong) -- ~1 px of grid offset decides a near-boundary head; at bar 55 the cell grid equals the staff-wide lines, ~2.5 px off the print. 2.44c decomposes every failure into box offset vs grid offset. Lesson: crops draw lines measured AT the subject, never a staff-wide value
- 2026-09-30 · Sean · *"It stands to reason that scans will shift the geometry, and therefore anything that uses geometry compared to the staff needs to be measuring locally instead of globally on the staff"* · RULE (CLAUDE.md §10): every staff-relative measurement reads the staff lines at the subject's own x · ROADMAP 2.48: audit every consumer that measures against the staff (staff-wide `Q.STAFF_LINES`, the per-cell flat grid `_cell_grid`, or local), then give them one local staff-line model
- 2026-09-30 · Sean · *"As it works currently a straight line is aligned with the 5 staff lines. Once the straight lines are laid out can it be measured against the ink and where they begin to differ the straight line starts to change direction to match what the ink is doing?"* · 2.48's first attempt (five lines traced independently) was measured against the reference and NOT merged: 134 right->wrong vs 11 wrong->right -- a lone line wanders onto note/stem/beam ink. Second attempt = Sean's design: start from the rigid five-line comb and walk it along the staff, bending only where most lines agree and smoothly, holding course where ink covers a line
- 2026-09-30 · Sean, looking at the bending comb against the ink · *"The green is much closer to the ink but it moves every time it runs into a symbol that crosses the staff and when the ink collects at a bar line... right now the green line is on the ink but towards the top of the ink"* · two fixes for 2.48's comb: (1) a line's position is the CENTRE of its ink (midpoint of top and bottom edge), not its top -- a systematic ~1 px offset would push near-boundary heads one way; (2) the comb learns only from CLEAN columns (ink about one line-thickness tall, no stem/barline/head crossing) and otherwise holds course, with more smoothing
- 2026-09-30 · Sean, on 2.48's comb scoring worse (an A/A control showed 0 run-to-run noise; the comb's own moves broke 39 right heads and fixed 1) · *"The geometry should be more predictable with the staff lines following the actual ink. If it is making it worse, I don't think it is the staff - there is most likely another explanation."* · hypothesis under test: COMPENSATING BIASES -- today's per-bar lines sit toward the top of the printed line AND detector box centres sit above the head's ink centre, so relative position comes out right; correcting only the lines exposes the box bias. Measure both biases on clean single heads; if confirmed, score lines-through-ink-centre + head-ink-centre together
- 2026-09-30 · Sean · *"That feels too simplistic. It feels more like a reading or processing issue - something happening later"* · supersedes the compensating-bias test as the FIRST step: trace 12 flipped heads stage by stage (gather position -> clef/owner/event -> pitch -> export -> the judge's pairing) and name the first stage where base and arm diverge; check whether the comb's grid reaches other consumers (clef, key, ownership) that would move many heads at once
- 2026-09-30 · Sean · *"I want all our tests for now to just be the first 2 stages. I want to focus on the gather and identification."* · the 2.48 comb was scored through EVALUATE/EXPORT (`--full`) -- withdrawn; re-score at GATHER+ADJUDICATE by comparing `Q.NOTEHEAD_STAFF_POSITION` (rounded) with the reference pitch converted to a staff position via ADJUDICATE's decided clef. Every test until further notice is first-two-stages only, including reference scoring (position, not pitch)
- 2026-10-01 · Sean, on the whole-rest stray-ink sample (Litolff 20261001 record: 113 staff-bars hold a whole rest AND a kept notehead; of 5 cropped, 2 were real second voices, 1 a printed tempo equation "𝅝. = 𝅗𝅥" kept as a head on the top staff, 2 dense-ink fragments; branch `lane-whole-rest-stray-ink` `b5d71f30`) · *"Leave the whole rest alone - those rules are too simple and will rule out too much."* · NO rule that refuses a notehead because a whole rest sits in its bar, and no "far note with no ledger is not a note" refusal built on it; `notehead_is_not_a_notehead` stays as it is
- 2026-10-01 · manager, on 2.48's one-head check (branch `lane-2.48-onehead` `48b6d045`, Litolff p3 `glyph/3/0/8/0/3`, bar 49) · the comb's +0.78-step flip is NOT a staff tilt: `_trace_cell_local_lines` never commits in that bar (six stems and a beam at its left edge) and returns shift 0, i.e. the raw unshifted lines, while the per-bar `_cell_line_offset` had found the real +6 px. Measured by pixel rows on the crop: per-bar grid 1-6 px off the printed lines, comb ~20 px (crop scale). "Could not tell" was being used as an answer (rule 8). The earlier "the staff tilts" reading of the 14 flips (`81f8c94d`) is withdrawn: its crops drew an illustrative comb, not production's
- 2026-10-01 · Sean · *"let's use the current process to start where the comb starts - so the green line should take a cue from the orange lines so it can't get lost and then it should tilt with the ink as it does"* · 2.48 comb redesign: in each bar the comb STARTS from today's per-bar grid (`_cell_line_offset`'s shift), not from the raw staff lines at shift 0, then bends with the ink where most lines agree; where it cannot commit it stays on today's grid, never on the raw lines
- 2026-10-01 · Sean, on the seeded comb's crops (both right->wrong heads are rounding-boundary coin-flips, 0.13 and 0.03 step apart) · *"Currently I feel like the comb changes too much. Can it be more gradual? Like pinned at the ends and a few points in between a system?"* · 2.48 comb redesign #3: per staff, per system, a SMOOTH line model pinned at both ends of the system and at a few points between (measured on clean columns around each pin), interpolated between pins -- no bar-by-bar wiggle; a pin that cannot be measured is dropped, never defaulted; with no measurable pins the staff keeps today's per-bar grid
- 2026-10-01 · Sean · *"For the note heads the boxes are a bit more forgiving of ink blobs than the trace - is there another option? Can the boxes be centered based on the staff lines or spaces?"* · agreed plan (queued behind the boundary-distance check): snapping a box to a line/space IS the rounding decision, so it cannot be evidence; instead, for a head near a rounding boundary only, place an ideal head (2.39's standard size from the local spacing) on each of the two candidate steps against the comb's lines and take the one the ink covers clearly better; where both fit alike (merged blob, touching heads) today's reading stands and is counted. Dispatched only if the boundary check shows enough near-boundary heads to matter; else proven on Brahms or the far notes
- 2026-10-01 · Sean, on 12 crops of 2.42's `stacked_head_duplicate` refusals · *"I don't see any real notes being erased. I see double boxes and the other 2 are tremolo slashes"* · 2.42's refusals are sound; a tremolo slash boxed as a notehead is a separate fault -- and the keep-choice can keep the slash over the open head it crosses (`glyph/13/1/8/13/5`)
- 2026-10-01 · Sean · *"a single notehead can't extend on either side of the stem. A beam can but it must be connected to another stem and must be at the end of the stem. Any time a stem has a diagonal ink slash (that could be confused with a notehead) it must land on one side of the stem"* · CONVENTION: a notehead's ink lies on ONE side of its stem; a stroke crossing a stem (ink on both sides) that is not joined to another stem at the stem's end is a TREMOLO slash, never a notehead or beam -- refuse it as a notehead and keep it as a tremolo witness. Checked the tree: NOT built before (09-27's 'a tremolo as head' crop was never turned into a rule; the detector has never produced a tremolo box) · ROADMAP 2.49
- 2026-10-01 · Sean, on a contact sheet of 15 Litolff p3 heads (`lane-2.48-recipe` `out/print/2.48/recipe/clean_heads_sheet.png`: detector box, record staff lines extended at staff spacing, step ruler) · *"The boxes look very centered. Only occasionally on the hollow heads do the center look a bit high - but barely. The hollow heads should have a center in the white of the head. The big issue is obvious. The green lines for ledger lines do not line up at all."* · the detector boxes are NOT the problem (the ~4 px dy scatter was the ink-centroid instrument lumping chord-mates/stems into one component); the failing head-fit/ink-centre controls used far heads judged against the staff spacing EXTRAPOLATED past the staff, which does not land on the printed ledgers (cf. 2026-09-30, ledgers 18/13/20 vs 15.75). A far head's steps must come from the PRINTED ledgers. Minor: a hollow head's centre is in its white; boxes sit barely high on some hollow heads
- 2026-10-01 · manager, render-recipe check (`lane-2.48-recipe` `925fa9f3`) · the measurement scripts' fresh render matches the gather's frame exactly (`detect_staves(render_page(...))` reproduces the record's staff lines to the integer pixel; the scripts' second `deskew` is a no-op); no number from 10-01 is invalidated by the frame
- 2026-10-01 · Sean · *"We need to treat ledger lines entirely different from the staff lines. They need to be done as a separate process, entirely locally. Most of them on these old scores were done by hand so they are not even necessarily even or predictable by geometry. It can only be an ink read for the lines. When there is a ledger line that goes through a notehead it can sometimes be hard to see but generally it should have a line that extends on either side of the notehead."* · RULE: a head outside the staff is placed ONLY by an ink read of its own printed ledgers, beside the head, never by extending the staff spacing (no staff-line model, comb or grid reaches past the outer line); counting the rungs (`measure_ledger_rungs`, the best reader on 2.44c's truth set) is the base; a ledger through a head is read from the stubs that extend on BOTH sides of the head. The 2.48 comb is for the five staff lines only
- 2026-10-01 · Sean, on the ledger rung sheet (`lane-ledger-sheet`, `out/print/ledgers/rungs_sheet.png`: same 15 Litolff p3 heads, `measure_ledger_rungs` rungs drawn from the ink, staff lines never extended) · *"It looks like it is getting the ledger lines right! ... overall I am very happy with how that seems to be working"* · the ink rung read is the basis for far-head position (per the 10-01 ledger rule); noted by Sean: tile 1 (`glyph/3/0/0/0/15`) has a second head above the boxed one -- sample choice or a missed head, to check
- 2026-10-01 · Sean, on rung sheet tile `glyph/3/0/0/1/2` (geometry -7.98, rungs -5) · *"missed the ledger line that it is on. There is a larger space between the lower ledger lines and the one right underneath the note"* · the rung reader stopped at an unusually wide gap and missed the ledger under the head (hand-drawn ledgers are unevenly spaced): the walk outward from the staff must not stop at a wide gap while the head is still farther out
- 2026-10-01 · Sean, on tile `glyph/3/0/1/2/0` (reader marked a rung through the head) · *"there is no ledger line. It is the first space above the staff and should probably be treated as a note on the staff not as one that should be a part of ledger lines"* · RULE: a head in the first space just outside the staff (touching the outer line, no ledger) is an ON-STAFF note -- placed against the staff lines like any other, with no ledger read; the ledger reader starts beyond it
- 2026-10-01 · Sean, on Brahms p0 system 0 still deciding 8 bars after the 2.47b+2.47c merge (`deaa4fbc`; 10 of 14 staves read a signature-only tail, 4 have no `timeSig` box -- the detector boxed the printed 9/8 there as whole heads/ledgers) · *"if most of the bars confirm the time signature then it should run on all of the staves"* · 2.47b's every-staff requirement becomes a MAJORITY: when more than half the system's staves read their trailing cell as signature-only, the trailing cell is not a bar on every staff of that system (CLAUDE.md §10: a meter change is printed on every staff at one bar)
- 2026-10-01 · Sean, on the ledger rung lane (`lane-ledger-rungs` `6d25b314`: wide-gap walk, first space outside the staff is on-staff, both-side stubs) · *"Our new ledger work is much better than what we did yesterday"* · the ink rung read stays the far-head path; open faults: a below-the-staff rung count converts to an in-staff position (Brahms `glyph/1/1/8/5/0` geom +11.92 / rungs +2), and ledgers merged into a Litolff chord blob are missed (`glyph/3/0/0/2/9`)
- 2026-10-01 · Sean · *"For 2.48 let's park but not forget about. It is possible that later on the difference it makes could be helpful."* · ROADMAP 2.48 PARKED, branches kept
- 2026-10-01 · Sean · *"have a lane work on making sure we know where the center of a hollow head is and that it is labeled well. Small difference"* · a hollow (open) head's centre is the centre of its WHITE interior, not the detector box centre (boxes sit barely high on some hollow heads)
- 2026-10-01 · Sean, on the 2.50 hollow-head sheet (`lane-2.50-hollow-centre` `out/print/2.50/hollow_head_centre_sheet.png`: box centre vs the white-interior centre) · *"The red is almost always right and better"* · the detector BOX centre stays the position of a hollow head; 2.50's hole-centre reader is dropped, branch kept unmerged
- 2026-10-01 · Sean, on 2.49's refusals (`lane-2.49-tremolo`, ~25% of Litolff p3 heads would fire; manager crop `glyph/3/0/8/6/12` is a plain head) · *"it should first be recognized as a thick diagonal line that crosses both sides of the stem significantly. Some of the current firing looks like a notehead and a ledger line. Those are at the end of a stem - a trem slash wouldn't be and they primarily are on one side of the stem with a tiny bleed. Not to mention that it is round not a diagonal thick line"* · CONVENTION: a tremolo slash is (1) a THICK DIAGONAL stroke (elongated and slanted, not round), (2) crossing the stem with SIGNIFICANT ink on BOTH sides, (3) on the stem's SHAFT, not at the stem's end where the head sits. A head is round, at the stem's end, mostly on one side with a tiny bleed; a ledger is a thin horizontal line. Shape first, then crossing, then position along the stem
- 2026-10-01 · Sean, on ledger round-2 crops (`lane-ledger-rungs` `d592c59e`, `out/print/ledgers/review2/`) · on his C6 (`glyph/3/0/0/2/3`, both ledgers found, last one through the head, written -5): *"Fix the one line change that allowed the code to step further out"* -- a head whose last found rung passes through it is ON that rung · on `glyph/3/0/9/2/0` (ref 11; geometry 12, rungs 12): *"there are 2 notes below the staff both in spaces and there is a clear ledger line running in between the notes. The red box is around the lower of the 2 notes and an orange line runs through the middle of it but there is not a ledger line that runs through that note"* -- the reference is right; the reader invented a rung out of the head's own widest row and missed the real ledger between the two heads
- 2026-10-01 · Sean, on the 2.49 shape-rule sheet (`lane-2.49-tremolo` `ef5c6d74`, every firing on Litolff pp.1-3 = 6 boxes incl. one double box, plus his two named page-13 cases, plus one real head as control) · *"All of them are slashes except the last one. There is one (6) where the slash doesn't extend as far as it should on the left side but it is a slash"* · 7 of 7 firings are real tremolo slashes, the control head correctly does not fire: the shape -> crossing -> position rule is print-verified (the lane's two "ambiguous" tiles, `glyph/3/0/9/6/6` and `glyph/3/0/10/3/5`, are real slashes)
- 2026-10-01 · lane-2.49-tremolo, real-data check (Litolff small re-gather, pages 1-3 through the count page, + a direct page-13 single-page gather for the two fixed glyphs) · the tremolo-slash rule (`Q.NOTEHEAD_STEM_CROSS_INK` + `notehead_precision._tremolo_slash_crosses_stem`) refuses BOTH fixed cases correctly, confirmed by crop (`glyph/13/1/10/2/0` and the stacked pair at `cell/13/1/8/13`, where the real open head survives once its slash co-occupant is dropped from 2.42's group) — but on the count page alone it ALSO refuses 121-132 of 481 notehead-classed glyphs (~25%). 10 crops under `out/print/2.49/` are all dense beamed runs or chords on this MERGING plate, not slashes; excluding `Q.BEAM_STROKE` ink from the split (the convention's own named exception) only moved 132->121, so a wide beam box is not the dominant contamination. MEASURED NET NEGATIVE, HELD BACK: `TREMOLO_SLASH_SHIPS = False` (same shape as `UNLADDERED_SHIPS`), signal computed and recorded, never refuses by default. Open question for a future session: attribution — telling a slash's own ink apart from the next note's stem/body bleeding across the split line on ink this dense — not the floor
- 2026-10-01 · Sean · *"Switch it on"* · 2.49 `TREMOLO_SLASH_SHIPS = True`, merged: a box that passes shape -> crossing -> position is refused as a notehead (`tremolo_slash_crosses_stem`) and kept on the record as a tremolo witness. Supersedes the lane's own 'held back' line above. Reaches the records only at the next re-gather (`Q.NOTEHEAD_STEM_CROSS_INK` is a GATHER quantity)
- 2026-10-01 · Sean, on the both-wrong ledger sheet (`lane-ledger-rungs` `8a1f7c85`, `out/print/ledgers/both_wrong_sheet.png`), tile `glyph/1/0/10/14/1` (reference -1; geometry -2; rungs -2) · *"it is on the first line above the staff"* · the head is -2 (first ledger); the REFERENCE pairing is wrong for this head, both readers are right -- the truth set's pairing is not evidence on its own (rule 7). Manager's reading of the other 10: every geometry miss is ONE STEP FARTHER from the staff than the reference (never nearer) -- a systematic outward bias, cause not yet measured (ledgers drawn tighter than the staff spacing, or boxes sitting on the outer part of merged blobs)
- 2026-10-01 · measured (`lane-ledger-rungs` `fd13f955`, `outward_bias.csv`) and Sean agreed to build on it · on Litolff's far heads that geometry misses (all one step OUTWARD), the printed first ledger sits a median 1.19 staff spaces from the staff (controls 0.98); the box is not the cause (-0.4 vs +1.2 px). Hand-drawn ledgers are spaced wider than the staff, so dividing by the staff spacing overshoots. Stepping on the MEASURED ledger gaps fixes 7 of 10. Build: a far head's position is geometry measured against the printed ledger rows beside it; no readable ledgers -> plain geometry, counted
- 2026-10-01 · Sean, on the ledger-measured crops (`lane-ledger-rungs` `af181d87`, 13 heads made wrong; the ladder took heads' own rows as ledgers and missed ledgers) · *"I'm not ready to give up on this. There is either something too specific or not specific enough that we can fix."* Three faults in the rung read, as additions to the rung process: (1) a CLEAN ledger (nothing on it) between a lower note on a ledger and another note on/next to a ledger above it is missed; (2) *"it also seems to miss ledger lines when the notes sit between them because they don't always extend on both sides of the note head but when the line goes through the note it always extends on both sides"* -- RULE: the both-sides stub test applies ONLY to a line THROUGH a head; a ledger beside a head in a space may extend on one side only; (3) *"there also seem to be some drift horizontally of the ledger lines that are a part of the same collection vertically"* -- the rungs of one stack are not aligned in x; each rung must be searched where IT is, not in one fixed column window
- 2026-10-01 · Sean, on 2.12g (`lane-2.12g-twins` `682b61b7`: 496 same-ink OnLine/InSpace twin pairs on the Litolff movement, 197 surviving ADJUDICATE as two kept notes after 2.30/2.42/2.47c; Litolff count page kept 347 -> 344, all 12 traced boxes twins of the same ink) · *"Sounds good, merge"* · merged: the detector keeps the higher-confidence twin and records the other's class (`detector_role`); the ROADMAP gate "notehead count must not fall" is read as "no real note lost" -- the 3-box fall is duplicates removed, crop-checked. Reaches records at the next re-gather
- 2026-10-01 · Sean, on round-5 ledger crops (`lane-ledger-rungs-r5` `7ec94862`: his flute chords still miss the ledger hidden in the merged blob between two stacked heads) · *"when there are multiple note heads stacked in thirds and neither of them has a line through them then there must be a line between them and to go looking for it"* · CONVENTION: outside the staff, two heads of one chord stacked a third apart (one staff space), neither with a ledger through it, are both in spaces -> a ledger NECESSARILY runs between them. The reader goes looking for it at the midpoint (stubs beyond the blob on either side refine its y); found or not, the step between them is counted as a ledger (the convention forces it), recorded as implied-by-third when no ink confirms it
- 2026-10-01 · Sean, after the unboxed-ink sheet (`lane-2.51-unboxed-ink` `78d05d85`: ~3 of the 20 largest unboxed blobs on Litolff p3 look like whole rests) · *"If a bar has no notes it should expect to find a whole note rest and look in the middle of the bar first. If it finds it then the bar is complete."* · RULE: a staff's bar with no notehead is EXPECTED to hold a whole (measure) rest; the reader looks for it by ink in the middle of the bar, hanging from the 4th line (the standard whole-rest place), before anything else; found -> the bar is a whole-bar rest, complete. Not found -> the bar stays unread and counted, never silence (rule 8)
- 2026-10-01 · Sean, on the round-6 chord-pair crops (`lane-ledger-rungs-r5` `out/print/ledgers/r6_sheet.png`) · `/2/4`+`/2/9`: *"2 note heads a 3rd apart but there is a weird ink blotch in between them. The ledger line it is missing only goes out under one side of the note. It is clear to a human eye because the thin horizontal line is clearly there"* -- a ONE-SIDED ledger is real (round 5's "no real cases" is wrong): a thin flat horizontal run on one side of the head counts · `/2/1`+`/2/3`: *"looks correct"* · `/6/1`+`/6/2`: *"has 2 orange lines both on the edges of the same ledger line"* -- the top and bottom edge of ONE thick ledger were counted as two rungs; rungs closer than a ledger's thickness are one ledger, at their centre
- 2026-10-01 · manager, Brahms frame check (`lane-brahms-frame`) · the render frame is correct on Brahms too; the rung reader fed the staff-WIDE `Q.STAFF_LINES` fit in as the line position at each head (CLAUDE.md §10 violation) -- Brahms p1 is skewed, ~10-13 px off at the heads. Fixed by reusing `local_staff_lines`; 3 of the 4 Brahms crops Sean saw become right
- 2026-10-01 · Sean · *"It would never leave one out. It may leave more room between lines or notes but it would not make sense to leave out the lines"* · CONVENTION CONFIRMED: a note outside the staff has a ledger at EVERY line position between the staff and the note -- none is ever skipped (spacing may vary, the count never). So a far head's position = the number of ledgers from the staff to it + whether one runs through it (through -> on that ledger; not through -> the space beyond the last one). The found ladder must be CONTIGUOUS from the staff: a gap of ~two spacings means a missed ledger in the middle (look for it; count it either way); a rung that does not fit the contiguous ladder is suspect. Generalises the stacked-thirds rule
- 2026-10-01 · Sean, correcting the line above · *"The gap doesn't require a ledger line but in between notes a 3rd apart does."* · a wide GAP between found rungs is NOT evidence of a missed ledger (hand-drawn spacing can be wide) -- nothing is implied from spacing alone; a ledger is implied only BETWEEN two heads a third apart (the stacked-thirds rule). Supersedes the "gap of ~two spacings implies a ledger" half of the previous line
- 2026-10-01 · Sean, refining the two lines above · *"A gap should have a ledger line but it is possible for it not to be there due to hand drawn spacing"* · RULE (final): a wide gap between found rungs is a place to LOOK for a missed ledger (relaxed search there: a thin one-sided line is enough); found -> count it; not found -> imply nothing (wide hand-drawn spacing is possible). Only between two heads a third apart is a ledger counted even when no ink is found
- 2026-10-01 · Sean · 2.52 *"Merge"* -- merged (check 245 -> 248: three named producer/wiring gaps, the found rest is not yet read after ADJUDICATE, on purpose under the first-two-stages rule). The red boxes on its Litolff p3 sheet are bars FULL of notes the detector never boxed (oboe bar 1, a horn bar of tied halves, a bassoon chord) -- *"let's figure out those bars that clearly have notes"*
- 2026-10-01 · Sean, looking at ties on the 2.52 sheet · *"whenever there are 2 notes of the same pitch next to each other in a bar or across barlines and there is an arched line between them it is a tie. The notes have to be next to each other regardless of measures/barlines and they have to have the same pitch"* · CONVENTION: an arc joining two ADJACENT heads (consecutive in that voice/staff, nothing between them, across a barline or not) at the SAME staff position is a TIE; not adjacent, or different positions -> not a tie
- 2026-10-01 · Sean, on 2.53 (`lane-2.53-unboxed-bars` `ad41435b`: Litolff p3 29 boxless bars full of notes; the detector ran — other classes boxed — but noteheads/rests fell under conf 0.25; at 0.10, 24 of 29 recover, mostly hollow heads crossed by ties/slurs/ledgers) · *"Yes"* to: a bar with no note and no whole rest found looks AGAIN at a lower confidence (notehead/rest classes only, that bar only); every rescued box passes the usual checks and is crop-checked before anything ships
- 2026-10-01 · Sean · *"combine that way"* · far-head position combines the two readers: geometry and rung count AGREE -> take it; DISAGREE -> rungs where the head's own ledgers are uneven, geometry where they are even; neither can tell -> unread, counted. Wired into the far-head position path with nothing switched on until Sean has seen the crops
- 2026-10-01 · Sean, refining the 2.55 rescue · *"Every measure should have notes or rests. If the bar shows ties then there are notes; if there are stems then there are notes and the note heads will be connected to the stems. If there are ties the notes will be close to the end of the ties. If there are accidentals then there are notes."* · RULE: the rescue is GUIDED by witnesses already on the record, each predicting WHERE a head must be: a STEM -> a head attached at one end of it (stem up -> head at the bottom, right side; down -> top, left); a TIE/arc -> a head just beyond each end of the arc, at the same staff position at both ends; an ACCIDENTAL -> a head immediately to its right at the same staff position. A rescued head is accepted where a witness predicts it; a bar with such witnesses and no head is our failure, never an empty bar
- 2026-10-01 · Sean, reading the 8 far heads neither geometry nor rungs gets right (`lane-farhead-combined` `out/print/ledgers/neither_right_sheet.png`, all Litolff) · four causes: (A) BOX: *"found the correct ledger line but the box is small and only covers the top of the half note"*; half notes whose oval does not close (Litolff) are hard to box and evaluate; (B) MISSED HEAD in a blob: *"there should be plenty of shape to see 2 oval shapes with lines emerging from both sides of the note heads"*; (C) ACCIDENTAL INK beside a head on a ledger is read as two rungs, one each side of the head, while *"the obvious ledger line through the notehead"* is missed; (D) DECISION: one ledger found correctly, the head just beyond it (*"slightly low but should read as underneath that ledger line"*) -- the head is in the SPACE beyond that ledger, not on a further hidden one. Rule from (D) with his 10-01 rule (a line through a head always shows on both sides): a head is ON a ledger only if a line shows on BOTH sides of the head at its middle; otherwise it is in the space beyond the last ledger found
- 2026-10-01 · Sean · *"Do it all"* -- 2.55 guided low-confidence rescue switched ON and merged (`RESCUE_SHIPS = True`) after his look at every rescued head on Litolff pp.1-3 (24 rescued, 16 kept, 8 the same head boxed twice; 0 pre-existing verdicts changed). Reaches records at the next re-gather; not yet scored against the reference
- 2026-10-01 · Sean, on the redrawn 2.54 tie sheet (`out/print/2.54/litolff_review.png`) · *"the ties look right"* -- 2.54 merged (adjacency across barlines; `spans_a_whole_bar` refuses only an arc whose bar holds no head; `not_adjacent` with the chord-onset exemption) · and on the 2.55 rescue sheet, tiles 11, 13, 14, 20: *"a few of the boxes look very tall and enclose 2 notes a 3rd away from each other"* -- a rescued box spanning a dyad must not be kept as one head (fix in flight on `lane-farhead-box-ab`: split into the two ovals found in its ink, or keep neither)
- 2026-10-01 · Sean · *"all of those are notes connected to ties"* -- the tall rescued boxes are tied DYADS: each tie end is a witness for one head at its own position, so two tie ends on one tall box = two heads
