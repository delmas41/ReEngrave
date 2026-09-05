# Export gaps, September round: the accents "gap", and the tie/slur veto

**Date:** 2026-09-04 · **Branch:** `claude/export-accents-arcs` (base `0487be1f`)
· **Charter:** close the accents export gap (KNOWN_GAPS' recorded open item)
and build the tie/slur impossible-configuration veto from
`docs/position-grammar-confusables-2026-09-04.md` R3, both measured on both
benchmark families before anything defaults on.

**Duplication check first (mandatory, both hairpin branches inspected):**
`claude/friendly-pike-395b8e`'s tip IS its merge-base with main — zero unique
commits. `claude/mystifying-curran-613606` carries one commit (`53e6f233`,
hairpins: `<wedge>` export + staff attribution); its diff touches accents only
as CLAUDE.md prose — and *propagates the stale claim* this document refutes
("The one open item now is **accents** … nothing consumes them"). Neither
branch closed accents; neither needed to. Hairpins were left entirely alone.

---

## 1. Task A verdict: THE ACCENTS GAP WAS ALREADY CLOSED — two days before the work order

The premise came from CLAUDE.md's OMR-NED section: *"Two open items are
recorded there now: **accents** (Mahler's truth has 6, the detector finds
exactly 6, nothing consumes them)"* — and the design doc's §5 row repeating it
("consumed **0** — a pure export gap wearing a confusable costume"). Both were
stale on the day they were read, and the second inherited the first.

**What the tree actually says, verified live on `0487be1f`:**

| link in the chain | where | state |
|---|---|---|
| the class | `articAccentAbove` / `articAccentBelow` (Mahler: 1 + 5 — the original KNOWN_GAPS entry itself said so) | detected |
| attachment | `transcribe._attach_articulations_in_cell` — "accent" is in `_ARTICULATION_KINDS`, side-aware, 0.75-notehead-width gate | wired; pinned by `test_transcribe_helpers.py` (`articAccentAbove → ("accent", True)`, attach tests) |
| MusicXML | `export._MXL_ARTICULATION["accent"] = "accent"` | wired; pinned by `test_export.py::TestArticulations` |
| LilyPond | `export._LILY_ARTICULATION["accent"] = "->"` | wired; **was unpinned** — test added this round |
| the file | `to_musicxml(mahler.omr.json)` on this tree | **6 `<accent>` against the truth's 6**; `to_lilypond` emits 6 `->` |
| KNOWN_GAPS | the `"accent"` entry ("EIGHTH GAP, open and cheap … This is the next one to close") | **already removed** — left at `6d40e95e`, the same day `df29e9b2` wrote it |

The timeline: `df29e9b2` created `export_coverage.py` with accents as the
eighth gap on 2026-09-01; the articulations work (`0eb1271`, that evening)
closed it — all ten `artic*` classes attached and exported, accents among
them — and the entry was removed; the merge landed on main as `bdda54d`
2026-09-02. CLAUDE.md's articulation section was updated; the sentence in its
OMR-NED section was not, and the 2026-09-04 design doc copied the stale
sentence into its opportunity table, from which this task was cut.

**So there is nothing to wire, and no A/B to run — before equals after by
construction.** The 11-work baseline run of this round (§4's OFF arm) is the
verification run: its Mahler export carries the 6 accents, and
`export_coverage --all` over it reports no `accent` gap. Redoing the wiring
was explicitly declined; what this round contributes instead:

- **CLAUDE.md corrected** (the OMR-NED section's KNOWN_GAPS sentence now names
  hairpins as the one open item and records how the accents copy went stale);
- **the design doc's §5 accents row corrected in place**, dated, so the third
  session to read it does not cut the same work order;
- **`test_lilypond_accent` added** — the one genuinely unpinned half-link
  (MusicXML accent emission was tested; LilyPond `->` was not, for any test
  naming accent).

The shape of the failure is worth the entry it now has in CLAUDE.md: the
project's recurring bug is "detected, then dropped on the way out", and this
is its documentation dual — **fixed, then kept open in the prose**. A stale
"open" claim costs a session the way a stale figure does, which is exactly
why the OMR-NED figure lives in one generated block. Gap ordinals already
live in one place (`export_coverage.py`, numbered, with closing commits);
what failed here is the two prose restatements outside it.

## 2. Task B: the tie/slur impossible-configuration veto (`OMR_ARC_RECLASS`, default OFF)

A tie and a slur are the same drawn arc; the notes under its ends tell them
apart (`docs/position-grammar-confusables-2026-09-04.md` §2 ARC). The veto,
R3-shaped — veto the impossible, reclass only when decisive, abstain
otherwise — lives entirely at EXPORT time in `export._pair_slurs_in_run`,
behind `OMR_ARC_RECLASS` (env, default off):

- **slur → tie**: a merged slur arc covering **exactly two heads, adjacent
  events of one voice, one pitch** becomes a tie (flags set on the pair; the
  merge matters — the canonical tie crosses a barline and arrives as two
  fragments). Adjacency counts REST events (a tie cannot cross a rest), so a
  same-pitch pair with a rest between abstains. Chords defend themselves:
  a covered chord member drags its mates into the covered set (same x) and
  the count passes two.
- **tie → slur**: a tie arc is refuted by its own configuration. Its pair is
  re-derived by `_tie_flank_pair` — a mirror of
  `transcribe._pair_ties_in_staff`'s pairing relation, pinned against the
  original by test — and vetoed where the pair's **pitches differ** or a
  **third event of the pair's voice sits under the arc's span**. An arc that
  never paired (no exported tie today) is reclassed only where decisively
  slur-shaped: >2 events of one voice under its span, or exactly two heads of
  different pitches. A vetoed arc joins the slur pool — **widened to the
  flanked centres and split at cell boundaries**, because a tie arc spans the
  GAP between its heads and slur coverage asks what sits under the ink;
  moved unchanged it covers nothing and "corrected to a slur" silently
  degrades to a bare deletion (found on the first smoke run: Mahler's two
  vetoed ties produced zero slurs until the widening).
- **bookkeeping**: every flag the pass adds or removes is recorded
  (`arc_reclass_added` / `arc_reclass_removed`) and the next annotate pass
  restores the transcription's own state before re-deriving — so one result
  dict exports identically under either flag in either order, and re-export
  is idempotent. Firings are counted per rule in `export.ARC_RECLASS_STATS`.

What it deliberately does NOT do: create ties the pairing never made (a
same-pitch pair under an unpaired tie arc abstains — pairing-by-coverage
would be a new pathway, not a veto); touch flags beyond the vetoed arc's own
mirror pair (chained ties share heads); veto a flagged same-pitch pair with a
rest between (the task's two impossible configurations only — span and
pitch).

Unit tests: `test_export.py::TestArcReclassOff / TestSlurToTie / TestTieToSlur
/ TestArcReclassBookkeeping` — both veto directions, the abstain cases
(different pitch, three heads, rest between, legal tie, arc over nothing),
flag-off inertness, restore, idempotency, and the flank-pair mirror agreement.

## 3. Flag OFF is byte-identical

Verified three ways: (a) unit tests pin the off-path on the veto-triggering
fixtures; (b) exports of the stored 3-work-era transcriptions under this
tree's flag-off code are byte-equal to the base commit's exports (MusicXML
and LilyPond, checked before any benchmark ran); (c) §4's A/B asserts, per
work and per scan row, that the flag-off re-export is byte-equal to the
`.omr.musicxml` the baseline eval itself wrote.

## 4. Engraved 11-work A/B

*(pending — filled from `ab_engraved.json`)*

## 5. Scan 10-row A/B

*(pending — filled from `scan-arc-off.json` / `scan-arc-on.json` /
`ab_scan_elements.json`)*
