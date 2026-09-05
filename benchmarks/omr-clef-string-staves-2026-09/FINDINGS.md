# Clef on string staves — verifying the `shift` diagnosis before touching code

2026-09-04, branch `claude/clef-string-staves` off `0487be1f`. Task: evaluate
the forensics' lever #3 — "clef on string staves, ~1,900–2,700 pooled edits,
constant-offset shifts" (`ERROR_FORENSICS_2026-09-04.md` §5/§6 on
`claude/scan-error-forensics`) — as a flag-gated, default-off candidate.
Baseline everything here is measured against: the widened-graft fixtures in
the `scan-rebaseline` worktree (`*.widened-graft.omr.json` /
`.omr.musicxml`), pooled **0.8387 / 29,082** on the 10-row pool.

**Status: diagnosis + mechanism map done (this file). Reachability count done
in draft, being finalized. No pipeline code touched yet.**

The brief's lever shape was: *when contextual NAMES a staff's instrument and
the staff's clef is only the POSITIONAL DEFAULT, default it from the
instrument's conventional clef.* The verification below says that shape, as
briefed, reaches almost none of the damage — the damage is real and
constant-offset as diagnosed, but its mechanisms are (a) detector
**misreads**, not absent reads, and (b) **mid-staff spurious clef changes**,
plus (c) staves whose margin label never resolved, where naming comes only
from score order — which prior art forbids using for clef correction
(contextual.py: "clef correction runs on identity that was READ, never on
identity the score-order prior deduced", measured on Beethoven 5 p.15).

---

## 1. Method

Two independent joins, neither trusting the other:

1. **Per-staff, per-measure shift classification**, rebuilt from scratch
   (scratchpad `shift_sites.py`, music21 under `.venv-omrned`): for every row
   with a `works.json` `staves` map, truth measure = multiset union of the
   mapped reference parts' diatonic indices, pred measure = the positional
   part's multiset; a measure is `shift k` when both sides have the same note
   count and every sorted pairwise difference is the same k ≠ 0. This
   reproduces the forensics' shift signatures independently (Viola +6,
   Vn2 −12, Vc −4/−5 all reappear, at the same rows).
2. **Provenance + naming dump** from the same fixtures' `.omr.json`: per
   staff, `clef`, `clef_source`, per-measure `clef` state, every
   `category == "clef"` detection with confidence, and contextual's
   `instrument` / `instrument_source` / `label_tiers` / `unresolved_labels`.

`works.json` note: the 575951 rows' `staves` is the literal string
`"same-as:beethoven-sym5-mvt1-984073-p1"` (resolve it; it is not a list).

## 2. The mechanism map — every named shift site, verified

Shift measures are numbered in the stitched prediction's measure order (sys1
then sys2 on the p2 rows).

| site (staff, row) | shift, where | mechanism (verified from detections) | staff `clef_source` | contextual naming |
|---|---|---|---|---|
| Viola s9, 575951-p1 | **+6 on 13 of 16 bars — whole staff** (22 truth notes; forensics ~108 edits) | **Header MISREAD**: the alto glyph detected as `clefG` conf 0.72 | `detector` (read, wrong) | **Viola via label** (text layer; 12 labels on this page) |
| Viola s9 (sys1), 575951-p2 | +5/+6/+7 on ~14 of 17 sys1 bars | **Header MISREAD**: `clefG` 0.34 (weak) | `detector` | Violin via **score_order** (margin unread) |
| Viola s20 (sys2), 575951-p2 | +6 continuing m18–m26 | Header **alto CORRECT** (`clefCAlto` 0.74), then **spurious mid-staff `clefG` 0.58 in the 2nd cell** flips the rest of the staff to treble | `detector` (correct at header!) | Violin via **score_order** |
| Violino II s8, 575951-p2 | **−12 m9–m15** (truth D4-family read F2-family) | Header `clefG` 0.94 correct; **spurious mid-staff `clefF` 0.68 at m7** | `detector` | Violin via **score_order** |
| Viola s9 (sys1), 984073-p2 | +5/+6/+8 scattered over sys1 | **Header-crop gap-fill MISREAD**: no clef detection in any measure; the `detector_header` pass read the header crop as treble | `detector_header` | Violin via **score_order** |
| Viola s20 (sys2), 984073-p2 | +6 (m24–25 etc.) | **The one genuine positional default** among all sites: zero clef detections, carried treble | absent (`None`) | Violin via **score_order** |
| Viola s9, 984073-p1 | **−6/−5 m7–m15** (header bars fine; forensics 38 edits) | Header **alto CORRECT** (`clefCAlto` 0.40 over `clefG` 0.34), then **spurious mid-staff `clefF` 0.59 at m4** flips m4+ to bass | `detector` (correct) | **Viola via label** (Surya; 12 labels) |
| 1. Violine s9, brahms-p1 | **−12 m3–m5** (16 truth notes; the clef-shaped core of brahms shift 359) | Header `clefG` 0.94 correct; **spurious mid-staff `clefF` 0.32 at m3** — 0.32, just above the 0.25 floor | `detector` (correct) | **Violin via label** |
| Violoncello s13, dvorak-p5 | **−4/−5 m0–m3** (12 truth notes; forensics 116 edits) | **Header ARBITRATION loss**: the plate prints TENOR (the −4 constant = tenor-read-as-bass, and `clefCTenor` 0.88 was detected); `clefF` 0.92 outscored it by 0.04 and bass won | absent — but a provenance ARTIFACT, see §3; the clef WAS detector-read | **Cello via label** |
| dvorak-p6 | one −1 bar | not clef-shaped (±1 = step errors, no clef pair is 1 apart) | — | page unlabeled (Tesseract read `\|`) |

Unmapped rows, from provenance + the blocked proposals (no per-measure
classification possible — no `staves` map):

| site | evidence | naming |
|---|---|---|
| brahms-p2 s4 + s18 (Bassoon), s8 (Timpani) | all read **treble by the detector**; `clef_correction` PROPOSED bass on all three (register fits 1.0 vs current 0.926 / 0.571 / **0.000**) and was blocked by `clef_was_read` | all three **via label** |
| mahler-p2 s16 (Viola) | `clef=treble`, `clef_source` absent, no clef detections — a genuine default candidate; damage share unquantified (row unmapped) | **Viola via label** |
| brahms-p2 s11/s24 (Viola) | both read **alto correctly** — no damage | label |
| mahler-p3 s12 (Viola) | alto via `detector_header` — correct | label |

### The forensics' own signatures, sharpened

- "Viola +6 on both 575951 rows and 984073-p2, −6/−5 on 984073-p1 — the same
  plate at two rasters guessing two different wrong clefs" — confirmed, and
  now explained: **they are not the same mechanism.** 575951 guesses wrong at
  the HEADER (misread alto→treble); 984073-p1 reads the header RIGHT and is
  then flipped mid-staff by a spurious `clefF` 0.59. One is a wrong first
  decision; the other is a right first decision overturned four bars later.
- "Violino II −12 verified as treble-read-as-bass" — confirmed, and it is
  **mid-staff**, not a header default: `clefG` 0.94 read correctly at m0,
  spurious `clefF` 0.68 at m7, damage m9–15. A header-defaulting lever
  cannot reach it by construction.

## 3. A provenance bug found on the way (worth fixing regardless)

`staff["clef_source"]` is NOT a reliable "was this clef read" authority on
rows where the furniture-column dropper fired. `transcribe.py`'s
furniture-drop pass (≈ line 2831) refreshes `staff[field] = kept[0][field]`
for `clef`/`key_signature`/`time_signature` after dropping a leading
furniture column — but never refreshes `clef_source`, which still describes
the DROPPED first cell. dvorak-p5 shows the signature: every staff
`clef_source: None` with correct detector-read clefs (`clefG` 0.92–0.96,
`clefCAlto` 0.92/0.60, `clefF` 0.88–0.93 in the surviving first cells) and
`clef_final` echoing the staff clef. Verified by instrumented re-run: at
assembly time every staff was `first=treble, src=None`; the post-drop refresh
rewrote the clefs and left the provenance stale.

`clef_correction.clef_was_read()` is already robust to this — it ORs in a
scan for `category == "clef"` detections, exactly for "JSON produced before
clef_source existed" — so the existing gate behaves correctly on p5. But any
NEW code (and any human) reading `clef_source is None` as "positional
default" will be wrong on furniture-dropped rows. The mahler-p2 s16 default
candidacy above was therefore verified against the detections (zero clef
detections on the staff), not against `clef_source` alone.

## 4. What already exists (prior art in the tree, not in the docs)

`tools/omr/clef_correction.py` — wired into contextual since 2026-08-28 —
already implements the briefed lever *and more*: per-staff register fit of
candidate clefs against `instruments.py`'s `written_range`, led by
`instrument.default_clef` (the field the brief asked to investigate: it
exists), applied ONLY where `clef_was_read()` is False, recorded as
`clef_proposal` on the staff and `contextual.proposals` either way. On this
baseline it applied **zero** clefs anywhere in the pool and proposed five:

- 575951-p1 s9: **treble→alto, Viola, fit 1.00** — the exact fix for the
  largest label-named site, `applied: false` because the wrong clef was
  *detected*, not absent;
- brahms-p2 s4/s18/s8: treble→bass (Bassoon ×2, Timpani), fits 1.00 vs
  0.926 / 0.571 / 0.000 — all blocked the same way;
- brahms-p1 s12: tenor→bass, Cello, fit 1.00 vs 1.00 — **blocked, and
  correctly so**: the shift classifier finds NO shift on that staff, i.e.
  the detected tenor is RIGHT and the instrument-convention proposal is
  wrong. This staff is the standing proof that "override a detected clef
  with the instrument's default" is unsafe as a general rule.

## 5. Reachability — where the ~1,900–2,700 actually sits

Three mechanism families, three different levers, only some ownable here:

| family | sites | mapped edits at stake (forensics row shifts, apportioned by shifted bars) | reachable by what |
|---|---|---|---|
| **A. Header treble misread, label-named** | 575951-p1 s9 Viola; brahms-p2 s4/s18/s8 (unmapped); mahler-p2 s16 (unmapped, genuine default) | ~108 mapped + unmapped shares | a TREBLE-ONLY override tier: instrument label read from the margin + instrument default ≠ treble + register fit not worse. Treble-only is what keeps brahms-p1's correct cello TENOR safe, and matches the measured `score_layouts` asymmetry (`SCORE_TREBLE_CONFLICT` −0.3 vs −1.5: an all-treble read is the documented failure mode and weak evidence) |
| **B. Mid-staff spurious clef change, label-named** | 984073-p1 s9 Viola (`clefF` 0.59 at m4, ~38); brahms-p1 s9 1.Violine (`clefF` 0.32 at m3, the −12 core of its 359) | ~38 + a share of 359 | an instrument-conditioned mid-staff clef-change veto (a violin staff never changes clef; a viola staff never changes to bass) — a different lever from the brief's, same identity evidence |
| **C. Score-order-named staves + arbitration losses** | ALL FOUR damaged staves of the two beethoven p2 rows (s8/s9/s19/s20 — margin unread, named "Violin" by score order, wrongly for the violas); dvorak-p5 s13 (tenor lost to bass 0.88 vs 0.92, both detected) | the **bulk**: ~1,000 of the mapped 1,869 (477 + 523) + dvorak's 116 | **nothing safe in this lever family.** Score-order naming driving clef correction is measured-rejected (closes the loop on its own mistake); the dvorak arbitration needs better clef evidence, not identity — the instrument default (bass) AGREES with the wrong reading there. The p2 unlock is the MARGIN READER: Surya labeled 14 of 22 staves on each p2 row — the 7 wind/brass/timp slots in both systems — and zero string staves, with `unresolved_labels` empty (nothing read-and-dropped; the reader returned nothing usable there) |

**The honest headline so far**: the briefed gap-only lever reaches ~0 of the
mapped damage (the one genuinely-defaulted damaged staff is score-order-named;
every label-named damaged staff has a *detected* clef). A treble-only
override tier (A) + a mid-staff veto (B) — both gated on label-read identity —
reach roughly **150–350 mapped edits + the unmapped brahms-p2/mahler-p2
shares** (to be measured by A/B, expected order a few hundred), out of the
~1,900–2,700 stake. The remaining ~1,100+ is walled behind the margin reader
on continuation pages (family C), and that is a finding about *reader reach*,
not about clef logic.

## 6. Next (in order)

1. Finalize the reachability count: verify mahler-p2 s16 truth (does the
   viola sound in the window; is the truth clef alto), estimate the
   brahms-p2 bassoon/timpani stake, look at the p2 margin crops to say
   whether the string labels are printed-but-unread (reader-fixable) or not
   printed (nothing to read).
2. If A+B justify implementation: flag `OMR_INSTRUMENT_CLEF_DEFAULT`
   (default OFF, flag-off byte-identical), A/B on the 10-row pool with
   `OMR_SCAN_EVAL_WEIGHTS` pinned to
   `deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt`, engraved
   11-work benchmark firings counted, `eval_pipeline_clefs` 69/69 and 50/52
   held, unit tests for every abstain rule above (score-order gate,
   treble-only gate, tenor-protection, mid-staff veto instrument table).
3. Either way: record the `clef_source` provenance bug (§3) — candidate
   one-line fix in the furniture dropper, plus a seam test.
