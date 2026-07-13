# OMR internal-consistency checks — reference & lessons learned

**What this is.** A deterministic, zero-external-input "does this OMR output even
make sense?" safety net that verifies the `transcribe()` JSON **against itself**
and flags where it is internally contradictory. It works on *any* score with no
hand input, and sits **beneath** the (separate) dossier-guided verification layer
— when a dossier of known facts is available, that layer can *resolve* which
staff is right; this layer can only *surface* that something disagrees.

Built 2026-07-11/12 from `docs/followup-prompts-deterministic-and-training.md`
(Prompt A). All checks are pure **additive post-passes** over the built
`page_dict` in `tools/omr/transcribe.py`; none touch detection / pitch / rhythm
code.

---

## The checks

| id | flag key | invariant it tests | merge |
|----|----------|--------------------|-------|
| **(d)** | `measure_count_warning` | barlines run through a whole system → every staff shares one measure count | `76f0bfe` |
| **(c)** | `rhythm_sum_warning` | each measure-column sums to its meter | `c70d6d0` |
| **(b)** | `key_signature_warning` | one concert key explains all staves (via transposition) | `551666b` |
| **(a)** | `clef_register_warning` | staves run high→low; a lower staff shouldn't resolve above an upper one | `0fde067` |
| **(e)** | `time_signature_disagreement` | all staves of a system share one meter | `c07432c` |

Each is defined by a `_flag_*` function near the bottom of `transcribe.py` and
wired into the per-page post-pass (search `Cross-staff consistency checks`).
Unit tests: `tools/omr/tests/test_{transcribe_helpers,column_rhythm,key_signature,clef_register,time_sig_agreement}.py`.

---

## Design principles (shared by all five)

1. **Zero external input.** Only the transcribe JSON + fixed music theory
   (transposition offsets, clef registers). No hand input, no model.
2. **Additive & byte-identical on clean output.** A warning key is written
   **only** on a genuine anomaly, so a consistent page serialises identically
   before/after. This is the primary regression guard (proven on bach-wtc,
   ravel-bolero, beethoven-5). *Exception:* check (c) deliberately reshapes the
   shipped `rhythm_sum_warning` (a precision upgrade, not additive) — see below.
3. **Abstain rather than guess.** With no external anchor a check can say "these
   disagree, at most one is right" but usually **not which**. So each requires a
   **strict majority** (`mode_k*2 > total`) before pointing at the minority, and
   stays silent on near-even splits (a 2-2 piano disagreement, a 3-3 tie).
4. **Graded confidence, honest labels.** `confidence_label ∈
   {advisory, low, medium, high}`, driven by consensus strength
   (`_CONSENSUS_HIGH = 0.8`, `_CONSENSUS_MED = 2/3`, shared across checks) plus
   check-specific corroboration. "advisory" is a distinct tier meaning "heuristic
   hint, verify" (used by the clef/register check).
5. **Point at the anomaly, don't assert the cause.** A flag names the staff /
   pair / column and *why* it looks wrong; it never claims certainty.

---

## Per-check detail

### (d) Cross-staff measure count — the strongest
Barlines are engraved through every staff, and `resegment_fused_measures`
renumbers `measure_index` 0..N-1 per system, so every staff must have the same
`n_measures`. A deviating staff localises a **missed barline** (too few → a
fused cell) or a **spurious** one (too many). Pure integer invariant.

**Multi-measure-rest trap (the dominant orchestral false positive).** A tacet
instrument prints a condensed multi-measure rest — one wide bar spanning many
measures — so its staff is short *and* its wide cell trips `phase1_warning`,
looking exactly like a missed barline. We separate the two by **note content**
(`_measure_has_notehead`): a fused pair of real measures is note-dense (9–27
noteheads on real fused cells), a multi-measure rest is a wide, **note-empty**
cell (a real Beethoven-5 tacet cell measured 2.2×-wide with **zero** detections).
So a short staff is promoted to `high` only when its wide cell contains
noteheads; a note-empty wide gap is flagged `likely_multimeasure_rest` and
down-weighted to `low`, never high.

### (c) Column-aggregated rhythm-sum
The naive per-staff `_measure_rhythm_sum_warning` over-fires: it flags every
resting/sparse staff that legitimately under-sums against a meter. The fix
(`_annotate_column_rhythm_warnings`) aggregates to the measure **column** and
flags only when the column's **fullest** voice mis-sums: **over-sum = high**
(extra beats → fused barline / over-detection, cross-refs `phase1_warning` via
`fused_suspected`), **under-sum = low** (only when even the fullest voice is
short — usually an under-detected rest). All-resting columns are skipped.
On real multi-staff systems this removed **27–32 %** of the naive flags
(ravel 52→38, beethoven 25→17). Meter comes from each measure's
`time_signature` (populated by inference back-fill here, or a dossier there) —
so the function is **meter-source-agnostic**, which is why it is shared with the
dossier track (see reconciliation, below).

### (b) Transposition-aware key signature
A naive "all staves share one key sig" check is useless on orchestra:
transposing instruments print **different** written key sigs for one concert
key. Modelled as a circle-of-fifths offset (`written = concert + offset`):

| instrument | offset | concert C is written as |
|---|---|---|
| C | 0 | C (0) |
| F (horn, cor anglais) | +1 | G (1♯) |
| B♭ (clarinet, trumpet) | +2 | D (2♯) |
| E♭ (alto sax, E♭ clar) | +3 | A (3♯) |
| A (clarinet in A) | −3 | E♭ (3♭) |

So for concert key `K` the consistent written set is `{K−3, K, K+1, K+2, K+3}`
(≈5 signatures). A staff is flagged only when **no** single concert key
reconciles it with the strict majority. Conservatism: a **no-key-signature
staff (0 accidentals) is a wildcard** — parts are routinely written without a
key sig (horns, trumpets, whole modern scores), so 0 never flags and never
constrains `K`. An outlier one fifth outside the set (e.g. a rarer D instrument
at −2) is capped below `high`. Real ravel sys0 (`0,0,1♯,1♯,1♭,1♭`) is correctly
read as **concert F** — a naive equality check would false-flag it.

### (a) Clef-from-pitch register inversion — advisory only
The weakest check. A wrong clef shifts every notehead by a constant offset, so a
**single staff gives zero evidence** (the mis-read pitches and the wrong clef
field shift together and stay self-consistent). The only internal signal is
relational: staves run roughly high→low, so a lower staff resolving an octave+
above the staff above it is a possible clef error — *or* a voice-crossing / a
high instrument. Calibration on the real scores: benign adjacent pairs reach a
p25(lower)-vs-p75(upper) separation of **+9 semitones** with no error present, so
a full **octave (12)** of robust separation is required to flag. Consequence:
**0 false positives / byte-identical**, but **low recall by construction** —
clef shifts that don't grossly invert are ambiguous with benign range overlap.
`confidence_label` is always `advisory`. Real reliability needs the dossier's
per-instrument range.

### (e) Cross-staff time-signature agreement
All staves of a system share one meter, so genuinely-**detected** meters that
disagree are a hard mis-read. Only **source-less** (genuinely detected) staff
meters participate — back-filled / propagated meters are inference, not evidence.
Flags the minority under a strict majority, or all detected staves on a
near-even split.

**Dropped from (e): cross-system clef continuity.** A post-pass that
majority-votes each role's *final* clef across same-sized systems is unreliable —
on reduction/condensed scores same-sized systems aren't the same instruments (it
false-fired on bach's three single-staff systems), and majority-clef ≠
correct-clef so it can flag the *right* staff (beethoven). The sound signal ("a
detected clef overrode the inherited one") is only visible inside
`_ClefContinuity` during transcription, or from the dossier's expected per-role
clef. Deferred there.

---

## Lessons learned

- **The wall is a synthetic→real domain gap, not a threshold.** The detector is
  often *blind* on dense orchestral pages (the conf-0.10 probe recovered zero
  real time-sig digits, mostly-treble clefs — see
  `benchmarks/omr-detection-probe-2026-07/findings.md`). So these checks, like
  the shipped time-sig layer, correctly **abstain** where detection can't see its
  inputs. They are a free floor, not a fix for detection.

- **No in-repo PDF triggers the checks naturally.** The `benchmarks/.../output/`
  PDFs (bach-wtc, ravel-bolero, beethoven-5) are re-engraved **reductions**:
  their dense/fused content segments onto **single-staff** systems (no sibling to
  cross-check), so every multi-staff system is internally consistent → the checks
  correctly stay silent. The genuinely dense originals (Boléro/Mahler/Debussy
  scans) are gitignored/absent. **The dramatic wins land on dense multi-staff
  orchestral pages that aren't in the repo.**

- **So verification is: byte-identical on the real reductions + fire on
  injections into real geometry + exhaustive unit tests.** For every check we
  proved (1) it adds nothing to the clean real output, and (2) it fires correctly
  when a single realistic error is injected into a *real* system (a missed
  barline fused into ravel sys4; a +14-semitone clef mis-read; a 6♯ key sig).
  Unit tests carry the behavioural proof.

- **"Same-sized systems = same instruments" is FALSE on reductions.** This broke
  the clef-continuity idea and is why (a)/(b)/(c)/(d)/(e) are all *within-system*
  or *note-content* based rather than *cross-system role* based.

- **Majority ≠ correct.** Cross-referencing the majority is only safe for
  invariants where the majority is *definitionally* right (measure count, shared
  meter). For clef, the majority can be the wrong reading — so we don't majority-
  vote clefs.

- **Build the shared verifier once.** The column rhythm-sum verifier already
  existed on the dossier branch; rather than write a second one it was ported
  **verbatim** to main and parameterised by meter-source. (Reconciliation recipe
  below.)

---

## Reconciling the dossier branch (`claude/omr-dossier-verification-layer-eaf6d0`)

Porting `_annotate_column_rhythm_warnings` to main created a duplicate with the
dossier branch. When that branch is brought up to date with main, **exactly one
file conflicts** — `tools/omr/transcribe.py` (everything else auto-merges).
Merge base is `8113244`. Resolution recipe (do it in the dossier worktree, then
run `pytest tools/omr/tests` — incl. `test_dossier.py`, 66 tests — to verify):

1. **`_annotate_column_rhythm_warnings` / `_measure_rhythm_sum_warning`**:
   identical on both sides — keep one copy (git auto-merges the bodies; only a
   preceding comment conflicts — keep either).
2. **`_staff_notehead_midis`**: both branches added it (main via `_pitch_to_midi`,
   dossier via `note_name_to_midi`). They are functionally identical — **keep
   one**. Keeping the dossier's version needs its `.dossier` import (already
   present); keeping main's leaves `note_name_to_midi` used nowhere else. Either
   works for both callers (`_flag_clef_register_inversion` and the dossier's
   range-fit, which passes an already-computed `pitches_midi`).
3. **Union the rest**: keep main's `_CONSENSUS_*`, `_measure_has_notehead`, and
   the five `_flag_*` checks + pitch helpers **and** the dossier's
   `_RANGE_FIT_CLEFS`, `_clef_range_disagreement`, `_verify_page_structure`.
4. **Wiring** (the post-pass block): use `backfill_page_time_signatures(page_dict,
   dossier_meter=dossier_meter)`, then call `_annotate_column_rhythm_warnings`
   **unconditionally** (drop the dossier branch's `if dossier: … else:
   per-measure` — the column verifier handles both meter sources), then main's
   per-system `_flag_*` loop, then the dossier's `if dossier is not None:
   verify-structure` block.
5. Keep the dossier branch's `dossier` param on `transcribe()` and its `.dossier`
   imports (auto-merged in).

**Verified (2026-07-13).** This exact resolution was carried out in a throwaway
branch off the dossier tip (`note_name_to_midi` confirmed identical to
`_pitch_to_midi`: C4=60, and a strict superset — handles unicode ♯/♭) and the
**full suite passed (569, same pre-existing 4 fails + 14 errors)** — the dossier
branch's own 66 `test_dossier.py` tests included. So the recipe is proven to
produce a green tree. It was **not** applied to the live dossier branch (it's
another session's active WIP), but a land-time application is a mechanical,
verified 3-hunk merge.

---

## Open items

- Execute the dossier-branch reconciliation (recipe above) when that branch is
  ready to sync.
- Give the clef checks (a) + the deferred clef-continuity real teeth via the
  dossier's per-instrument register/clef facts.
- The four pre-existing test failures (`test_pipeline.py` cell-count drift 28≠32;
  `test_annotate_server.py` missing gitignored `deepscoresv2_208_classes.json`)
  are environmental and unrelated to this layer.
