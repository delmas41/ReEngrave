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
