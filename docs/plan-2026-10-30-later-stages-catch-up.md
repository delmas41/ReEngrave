# Plan: let the later stages catch up with the new GATHER (review, 2026-10-30)

Independent Opus review at Sean's request ("have it research where we are, what I am worried about, and suggest a way forward rather than just taking my rule"). Read-only, checked against tree 275d2bacd; `staged.check` = 198. NOT yet adopted -- a proposal for Sean.

Sean's concern (2026-10-30): the later stages were tuned for the old early stages; we are rewriting GATHER (claims, stroke map, cell map), so duplicate work should go, later stages should simplify to match, and a GATHER test should above all show the ink captured and designated.

## Where we are
New in GATHER (STAGED): stroke map (`Q.STROKE` 2.195) and box-to-stroke links (`Q.GLYPH_STROKES` 2.198); claim register `Q.CLAIMED_AREA` (clef, leading column, meter, key, page-wide words/brackets `gather_page_claims`, arcs `gather_arc_claim`, barlines, whole rests); page-wide barline pass; head fill from ink (`Q.HEAD_INK`); stem-end head reader; master cell map (2.231, not yet the test default).
Still old in GATHER: heads, rests, accidentals, dots, flags, ledgers are per-cell detector boxes on PADDED cells; the stroke map is per cell on the erased raster, so one page ink can sit in two cells' maps and "claimed once" cannot be counted at page level; staff lines erased not claimed; hairpins unclaimed; arcs never boxed are never read; 2.204 stems and 2.217 ledgers parked; ink-map steps 9 (slim basis) and 10 (retire) not started.
Later stages still tuned to the old GATHER:
1. Two ownership systems run side by side: `adjudicate_stroke_owner` (2.205, ON) decides one owner per stroke, but no precision decision reads it; the old pair rules still decide; parity 47% (Litolff) / 27% (Brahms).
2. Duplicate head-ink measurements: `notehead_precision` reads at least eight separate GATHER head-ink quantities (NOTEHEAD_INK, STACKED_HEAD_FIT, HEAD_INK, HEAD_OVAL, HEAD_LINE_CUT, NOTEHEAD_STEM_CROSS_INK, NOTEHEAD_LETTER_INK, LETTER_LOOK_COVER); 26 ink/stroke quantities in the record.
3. Workaround rules whose cause has landed are all live: 18 rows "retires with 2.205" (3,058 / 5,259 fires), 6 rows "retires with 2.206" (695 / 3,759). None re-measured; docs/ink-rules.md fires are from 20261022-night, before the eraser fix and every claim.
4. Readers that ignore claims: tip readers (2.233: 97 of 164 Brahms `beam_discounted_uncertain` heads have a claimed dot/slur end in the tip window); dot role (2.234: abstained "dots" mostly slur/hairpin tips); `voicing.group_chords_in_measure` groups by x alone (51 / 54 heads).
5. Record payload is later-stage: duration, voices, stem_value verdict bodies 13.7 of 19.6 GB (Brahms).

## Is the worry right (ranked costs)
Yes. The costliest part is not old rules being wrong; it is that they decide on old measurements while the new ones are computed and ignored.
| # | where | cost | measured / inferred |
|---|---|---|---|
| 1 | tip readers treat claimed ink as occupied | Brahms 164 + Litolff 47 heads unwritten on the sample (~20 / ~6 per page) | measured (12/12 bare stems) |
| 2 | two ownership systems disagree, old pair rules win | 53-73% of old refusals unmatched by ownership; ownership would refuse 85 heads + 43 rests (L), 75 + 92 (B) that main keeps | counts measured; who is right not judged beyond 12 tiles |
| 3 | `stacked_head_duplicate` picks on near-ties | 470 Litolff refusals, 41% on an ink gap < 0.02; one real note lost (Sean 10-30) | measured |
| 4 | padded-cell double detection makes owner contests | neighbour staff's padded crop 1,535 / 3,484 fires; nearest-staff tiebreak 4,799 / 18,005; `count_does_not_fit` empties 44 / 24 bars | fires measured (10-22); notes lost inferred |
| 5 | record bloat -> swap | Brahms 224 -> 352 min, CPU +10-13% | CPU measured, swap inferred |
| 6 | rankings mis-aimed by unit errors | 2.233 rests counted as heads; 2.234 abstentions as dots; 6 judged "right->gone" were key shifts | measured |
The whole-rest story (fixed 10-29) is the pattern in miniature: GATHER saw the ink; three later owners threw it away.

## How we test GATHER now and what is missing
- lane_report: exported file OFF vs ON by place, 12 tiles, judged moves; a GATHER flag needs a re-gather; by Sean's 10-29 ruling a weak measure for a claim. Its sample/docstring still name 20261020-night (lane_report.py:19, :140).
- judged scorer: answers, not capture. hand_truth.score: boxes per family at GATHER+ADJUDICATE on one page (Brahms p0) -- right shape, scores detector boxes not claims. check / gather_coverage / capture.py: vocabulary and wiring, not ink. `Q.INK` unread_mark: a narrow slice.
- MISSING: one command saying, per page and coarse kind, which ink is claimed once, contested, claimed twice or unclaimed, and whether a claim's kind matches Sean's labels (the arc and word lanes each built one-off scripts).
- A GATHER lane's test: capture first (that readout + "what is this ink?" tiles), the exported file second as a VETO only. A later-stage lane keeps today's three measures.
- When a GATHER gain causes a right->wrong, trace the deciding rule; if it picks below its own noise or is a rule-page workaround, the cure is that rule abstaining (blue/red), not reverting the capture. Nothing wrong is ever written plain.
- A GATHER + stroke-owner-only run is practical (stroke_owner ~1.5 s/page, reads GATHER rows only; master cells; `readout.match_glyphs` already matches truth boxes).

## Way forward (sequenced, at most 3-4 lanes)
Week 1:
1. Capture readout (Sonnet): `python3 -m tools.omr.staged.claim_readout REC --pages` -- per page ink area by state (one owner / contested / unclaimed) and owner kind, strokes de-duplicated across padded cells in page pixels; against Brahms p0 truth (each truth box's strokes -> right kind / wrong kind / split / nothing); a tile sampler for unclaimed and contested ink; controls that fail (`OMR_ARC_CLAIM=0` drops arc coverage from 136/153; a planted double claim shows). Run on 20261029-night slices: GATHER's to-do list ranked by unclaimed ink.
2. Rule-page refresh (Sonnet, read-only): re-count fires on the 20261029-night sample; for each "retires with 2.205/2.206" row: still fires? parity with stroke_owner? share of decisions on near-tie margins? Three lists: dead (delete), full parity (delete after a byte-identical file), disagreeing (tiles). Nothing deleted on principle.
3. 2.232 and 2.223 continue (2.232 makes a near-tie abstain: a rule-8 fix, not tuning).
4. Slim the record (ink-map step 9): file byte-identical, record smaller, Brahms swap gone.
Week 2:
5. Readers honour claims (connect, not tuning): tip readers, dot role, beam reader consult `Q.STROKE_OWNER` / `Q.CLAIMED_AREA`. Biggest measured cost (#1).
6. One owner decides: for each disagreeing pair rule, Sean's tiles on the disagreements pick the winner; the loser is deleted.
7. Next GATHER item from the readout (stroke page identity, claiming staff lines, hairpins, arcs not seeded by boxes).
8. Chord grouping by shared stem (EXPORT), after step 5.
Freeze new cut-offs, collapses and INFER rules; allow changes that only make an old rule abstain, or make a reader consult claims.
Rule or tool: no new CLAUDE rule needed -- Sean's 10-29 line ("a claim is proven by what it captures") already is the rule. Missing: the tool (step 1) and two lines in measuring.md §0: a GATHER lane reports capture first, the file as a veto; the cure for a right->wrong traced to an old near-tie or workaround rule is that rule abstaining, never reverting the capture.

## What to ask Sean (one at a time)
1. "When a gather improvement makes an old later rule guess wrong, may we fix it by having that old rule mark the note blue or red, rather than undo the gather change?"
2. With capture tiles: "What is this ink?"
3. Later, per disagreeing rule: "Which box is the note?"
4. Optional: "Could you hand-label one Litolff page, arcs and heads only?" (no Litolff hand truth today)

## Risks
Deleting too early (parity 27-47%: junk heads written plain). A self-referential capture score (only Sean's labels and tiles count; one labelled page, Brahms only). A capture-only test misses harm to the file (keep the veto). More abstention raises cleanup (report blue/red counts every change). Moving baselines (place-match, cell map). Shared LEGACY code (voicing.py, measure_extractor frozen; fixes live in STAGED).
