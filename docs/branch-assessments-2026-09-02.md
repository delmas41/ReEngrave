# Branch assessments — 2026-09-02

Handoff item #14 (`PROJECT_STATUS.md`'s ranked list / `docs/next-steps-omr-2026-09-01.md`):
assess `claude/omr-dossier-verification-layer-eaf6d0`, "the last branch with a capability
`main` lacks," then the two March web-app branches. All three inspected read-only —
`git log` / `git show` / `git diff` / `git merge-tree --write-tree <base> <branch>` (the
two-arg form; the deprecated three-arg form reports false clean merges, per the method
note this repo already carries from the `clef-phase0-eval` audit) — from the
`transcription-overnight-progress-426c90` worktree. No branch checked out, nothing merged.
`main` is `3aee540` throughout. This file is the only write.

---

## 1. `claude/omr-dossier-verification-layer-eaf6d0`

### What it is

Four commits, all dated 2026-07-11, forked from `8113244` (the design brief,
`docs/dossier-verification-plan.md`) — which is also the branch's merge-base with today's
`main`, i.e. nothing from the seven weeks since has ever been rebased in.

| commit | title | touches |
|---|---|---|
| `3a30247` | slice 1 — meter back-fill + column notation-math | `dossier.py` (new, v2 loader), `rhythm.py`, `transcribe.py` |
| `f2a9080` | Phase 2 — clef seed + range-fit | + `pitch_resolver.py` |
| `27953dd` | Phase 3 — structure verification + alignment guard | `transcribe.py` |
| `aa28dcb` | Phase 4 — dossier-steered re-segmentation | `measure_extractor.py` |

`git diff main...claude/omr-dossier-verification-layer-eaf6d0 --stat`: 13 files,
+2131/-26, including a hand-typed data model at `tools/omr/dossiers/*.json` — two files,
`ravel-bolero.json` (meter + a partial instrumentation seed) and `bach-wtc1-prelude1.json`
(adds a hand-typed per-page `pages[]` layout). `git log --all --oneline -- tools/omr/dossiers/`
returns only this branch's three commits: that directory has never existed on `main`, at
any point, on any branch that landed.

### Each claimed capability, checked against today's `main`, not July's

`PROJECT_STATUS.md`'s branch-audit table (dated 2026-09-01) reads: *"Slice 1 ... is
superseded, but Phase 2/3 and dossier-steered re-segmentation — acting on a known bar
count — have no equivalent on `main`."* That undercounts what happened in the seven weeks
between the branch's fork and the audit itself. Three of the four phases were
independently rebuilt by August's dossier/contextual-analysis/system-grouping work, and
the fourth was **literally cherry-picked, credited by hash, with only its data source
swapped**. Checked one phase at a time:

**Slice 1 (meter back-fill + column notation-math) — superseded twice over.**
The column-aggregated rhythm-sum verifier was ported **verbatim**:
`tools/omr/transcribe.py:2801` (`_annotate_column_rhythm_warnings`) carries the comment
*"Ported verbatim from the dossier-verification track so the column rhythm verifier is
implemented ONCE"* and the merge that did it, `c70d6d0` (2026-07-12, "Merge
column-aggregated rhythm-sum verifier (check c) onto the internal path"), is one day after
the branch itself. Main's copy is **stronger**: it runs unconditionally for every page
(`transcribe.py:4094`), not only "on the dossier path" as the branch had it — so it also
covers pages whose meter came from detection, beat-sum inference, or the header reader,
none of which the branch's gate could reach.
The meter back-fill half is superseded by something stronger still: `apply_meter`
(`tools/omr/dossier.py:229`) doesn't only fill a missing meter, it *replaces* a
detected-but-wrong one with the dossier's — a misread, not a disagreement, per CLAUDE.md's
"Meter → rhythm feedback" section — and `tools/omr/time_signature_locator.py` reads the
meter from the header geometrically and needs no dossier at all.

**Phase 2 (clef seed + range-fit) — superseded, and generalized past what Phase 2 itself
could reach.**
Dossier-based clef+key seeding exists on main: `tools/omr/dossier.py:389`
(`join_parts_to_slots`) plus the seeding call sites at `transcribe.py:3726-3746,3903`. It
replaces Phase 2's binary gate ("trust only if staff count == `largest_system_staves`")
with a monotone, margin-label-**pinned** alignment that resolves *condensed* systems
(staff count != part count) — precisely the case Phase 2's own findings.md flagged as its
open limitation ("Boléro/Mahler/La Mer are condensed (the join can't be trusted)").
The register self-diagnosis (Phase 2's `_clef_range_disagreement`) is superseded by
`tools/omr/clef_correction.py` (introduced `5a146e7`, 2026-08-28), which needs **no
dossier at all** — it reads `instrument.written_range` off the contextual pass's
instrument labels (text layer / Tesseract / Surya / Vision), checks four candidate clefs
instead of one, and — via `correct_clefs_from_instruments` — reports a disagreement with
`applied: False` when a clef *was* read, the same "surface it, don't overwrite it" design
Phase 2 specified.

**Phase 3 (structure verification against a declared page layout) — the literal mechanism
cannot be ported; its purpose is covered by a different, more general check.**
Phase 3's `Dossier.page_layout(page_index)` needs a `pages[]: {systems,
measures_per_system}` fact **per printed edition** — a page break is the engraver's
choice, not a fact about the work, so it cannot be generated from MusicXML. Confirmed on
main's schema: `data/dossiers/beethoven-sym5-mvt1.json` is `schema_version: 3` and carries
only work-level facts (`total_measures`, `starting_meter`, `meter_changes`, `parts`, …) —
no `pages` field, in any of the 97 generated files.
What shipped instead, the **same day** as the branch (2026-07-11, `05b5b63`):
`transcribe.py:2893` (`_flag_measure_count_inconsistency`) — an always-on,
zero-external-input check that flags a staff whose measure count disagrees with a strict
majority of its system's siblings, direction-aware exactly like Phase 3 (too few = missed
barline, too many = spurious split). It goes further than Phase 3 by separating a
genuinely fused measure from a condensed multi-measure rest using note content — a
false-positive class Phase 3's own findings.md never mentions handling.
The whole-work half of Phase 3 — explicitly deferred in the branch's own findings.md
("`total_measures` ... needs full-piece processing or a page-range→measure mapping —
parked") — shipped as `tools/omr/dossier.py:584` (`check_total_measures`), introduced with
the generated-dossier system itself (`d0563a6`, 2026-08-29).

**Phase 4 (dossier-steered re-segmentation) — cherry-picked outright, then measured to fix
nothing on the current corpus.**
`886ac23` (2026-08-29, "omr: steer re-segmentation with the bar count the system's own
staves agree on") says in its own message: *"Cherry-picked from
`claude/omr-dossier-verification-layer-eaf6d0` (aa28dcb, July, unmerged) ... That logic is
taken as written; it is careful and it is well tested."* `resegment_fused_measures(...,
expected_bars_by_system=...)` on main (`measure_extractor.py:1128`) keeps the branch's
exact constants — `RESEGMENT_MIN_PIECE_FRAC = 0.5`, `RESEGMENT_MAX_PIECE_FRAC = 1.75`,
`RESEGMENT_STEER_WIDTH_FACTOR = 1.5` — and the same safety properties (no barline ink, no
split; never overshoot; sliver floor always kept).
Only the data **source** changed. `majority_bars_by_system` (`measure_extractor.py:1042`)
computes the target from cross-staff majority vote instead of a hand-typed page layout,
and the commit explains why in one line: *"MusicXML page and system breaks describe the
engraver's own edition — the right bar counts for the wrong page."* That is the same wall
Phase 3's per-page layout runs into.
**Measured, and it changes nothing on any page in the repository.**
`benchmarks/omr-majority-steering-2026-08/findings.md`: 27 systems across 12 real scan
pages (Bach WTC, Beethoven 5, Boléro, La Mer, Mahler 5, Kirchhoff) — **0 systems where a
staff disagrees with its own system's majority, 0 systems steered, 0 bars added.** *"The
conservative pass has already done the work; there is no shortfall left to steer."* (The
same probe run is also the origin of the one-line-staff `resegment_fused_measures` crash
recorded in `PROJECT_STATUS.md`'s August 30 entry — La Mer p.25, a percussion staff of
span 0, a 1×0 OpenCV kernel; fixed the same day, 3 of 13 one-line-staff pages had been
uncrashable before that.)

### Is dossier-steered re-segmentation still needed at all? No.

Two independent lines of evidence, both post-dating the branch, both pointing the same
way:

1. **The root causes it was compensating for were fixed directly, not steered around.**
   Barline detection got a Theil-Sen geometric refit (CLAUDE.md, 2026-08-31) that took the
   real Beethoven 5 p.1 scan from "4 of 17 barlines missed" to "17/17, 0 false, 16
   measures of 16" — the barline itself was found, not papered over with a forced split.
   System grouping got the left-edge split (cue A, default on) that fixed 27 over-merged
   symphony pages with 1 mild residual. Beethoven's engraved orchestral benchmark reads
   8/8 measures exact, note recall/precision 1.000.
2. **The general mechanism is already in place, is a strict superset of what a
   dossier-sourced version could trigger, and was measured inert.** A hand-typed,
   per-edition dossier could in principle catch a system where *every* staff uniformly
   under-counts the same way (cross-staff majority can't see that, by construction) — but
   nothing in the current corpus exhibits that failure, and `majority_bars_by_system`
   found zero disagreement of any kind across 27 systems on six real scores.

### Mergeability (checked, not attempted)

`git merge-tree --write-tree main claude/omr-dossier-verification-layer-eaf6d0`:

```
CONFLICT (add/add): tools/omr/dossier.py
CONFLICT (content): tools/omr/measure_extractor.py
CONFLICT (content): tools/omr/rhythm.py
CONFLICT (add/add): tools/omr/tests/test_dossier.py
CONFLICT (content): tools/omr/tests/test_measure_extractor.py
CONFLICT (content): tools/omr/transcribe.py
```

Two of the six are **add/add**: main independently created `tools/omr/dossier.py` (642
lines, generated-dossier checks) and `tools/omr/tests/test_dossier.py` (40 tests, against
main's own `dossier.py`) at the identical paths the branch used for a different module (a
642-line v3 loader vs. the branch's v2 loader; a 40-test suite vs. the branch's
37-test suite for a different `Dossier` class entirely). Not a close call in any of the
six files.

### Recommendation: close, do not port, do not merge

Every capability the branch adds either already exists on `main` in a more general form
(Slice 1, Phase 2, Phase 4's mechanism) or targets a data shape the current dossier system
deliberately cannot supply (Phase 3/4's *per-edition* page layout — the whole point of
moving to a generated dossier, per CLAUDE.md's central-library section, was scaling past
hand-typing: 2 hand-typed works here vs. 97 generated ones on `main`). Phase 4's specific
idea was already taken, credited by commit hash, and re-measured on `main`, and found to
have nothing to fix on any page in the repository. There is no remaining capability gap to
port.

**Correction worth carrying back to `PROJECT_STATUS.md`.** Its table row is technically
defensible under a narrow reading (no *dossier-sourced* equivalent exists) but reads as
"no equivalent capability at all," which is not accurate as of `5a146e7` / `d0563a6` /
`886ac23` — all three landed 2026-08-28/29, before the audit's own 2026-09-01 date. The
audit's stated method (`git cherry` + comparing file contents) is exactly the kind of
check that misses this: `git cherry` compares patch IDs, and `886ac23` is deliberately
**not** patch-identical to `aa28dcb` (the data source was swapped), so it correctly does
not show up as "already applied" even though the commit message says outright that it is
the same logic. Flagged separately rather than fixed here, since this doc is the only file
this assessment writes.

---

## 2. `claude/magical-bhabha` — measure-level MusicXML patching

One commit, `cbebafd` (2026-03-26), forked from `2b3955f`. Replaces the stub
`apply_corrections_to_musicxml` in `backend/modules/export_module.py` (which only copies
the file and injects an XML *comment* listing the accepted diffs) with real per-measure
patching: locate the `<part>` by instrument name (exact → substring → first-part
fallback), locate the `<measure>` by number, and apply one of three edit shapes depending
on `human_edit_value` — a full `<measure>` replacement, a single-element replacement/append
(`<note>`, `<clef>`, …), or several elements grouped by tag — all namespace-aware
(detects, strips, and re-applies the document namespace to inserted fragments).

**Still applies.** `main` has changed `export_module.py` by 86 lines since the fork point
(`+79/-7`, `git diff 2b3955f main -- backend/modules/export_module.py`), but every changed
line is the unrelated OMR-JSON-direct-to-LilyPond path added in May (`export_as_lilypond`
/ `export_as_pdf` gaining a `tools.omr.export.to_lilypond` branch that skips the
`musicxml2ly` hop when `Score.metadata_json['omr_json_path']` exists). The diff's context
lines show it stops exactly at `apply_corrections_to_musicxml`'s signature —
that function and its one caller (`export_as_musicxml`, `export_module.py:109`) are
byte-identical to March. The `FlaggedDifference` fields the patcher reads
(`measure_number`, `instrument`, `difference_type`, `description`, `human_decision`,
`human_edit_value`) are all still present and unrenamed in `backend/database/models.py`.
`git merge-tree --write-tree main claude/magical-bhabha` shows exactly one conflicting
file — `export_module.py`, content conflict, not add/add — which is expected, since both
sides touch the same function region from different bases.

**Surprising finding: `main` already carries a test spec for this feature, and 2 of 5
tests currently fail against the shipped stub.** `backend/tests/test_export_module.py`
(added by `1bde868`, "Add docker-compose, fix frontend renderers, and add 79 backend
tests" — a *different*, later commit than `cbebafd`; the file is byte-identical between
the two) asserts real per-measure patching: `test_edit_with_xml_fragment_replaces_measure`
expects a note swapped from `C` to `G`, `test_edit_with_plain_text_adds_comment` expects a
free-text edit to appear verbatim in the output. Ran `python3 -m pytest
backend/tests/test_export_module.py -q` against current `main`:

```
FAILED tests/test_export_module.py::test_edit_with_xml_fragment_replaces_measure
  AssertionError: assert 'C' == 'G'
FAILED tests/test_export_module.py::test_edit_with_plain_text_adds_comment
  AssertionError: assert 'add forte here' in '<?xml version=... <!-- ReEngrave corrections applied: ...'
2 failed, 3 passed in 0.44s
```

The test file was evidently written to spec exactly the feature this branch delivers, but
the branch's implementation itself never made it to `main` — only its target tests did,
some time between March and whenever `1bde868` landed. This is independent, pre-existing
evidence (not something this assessment introduced) that the gap is real and that a
correct port should turn both failures green.

**Recommendation: port.** This is the cheapest of the three branches to land — one function
region untouched by five months of drift, a model surface that hasn't changed, and an
existing failing-test suite that already specifies the target behavior. Redo it as a fresh
patch against current `export_module.py` (the file has moved even where the function
hasn't — imports, surrounding structure) rather than a literal merge, but the branch's own
logic (`_find_part_for_instrument`, `_find_measure`, `_apply_diff_to_xml`, the namespace
handling) can be carried close to as-written. Still a web-app-track item — per
`PROJECT_STATUS.md`'s Scope section, personal-use is the current priority and the web app
is not being actively extended — so this is worth doing opportunistically, not urgently,
but it is a small, well-specified, low-risk piece of work whenever picked up.

---

## 3. `claude/peaceful-kapitsa` — SQLite-backed job queue

One commit, `c65ee95` (2026-03-26, same day and author line as `magical-bhabha`, same
fork point `2b3955f`). Adds a `jobs` table (`Job` ORM model + `JobResponse` schema) and
`backend/modules/job_queue.py` (392 lines: `enqueue()`, `reset_stale_jobs()`,
`start_worker()`, handlers for `omr` / `compare` / `download` job types with progress
updates at key milestones), then rewires three `main.py` endpoints from
`BackgroundTasks.add_task(...)` to `job_queue.enqueue(...)` so an in-flight OMR or Vision
comparison job survives a server restart (pending/in-progress jobs reset to pending on
startup, retried up to 3 times).

**The gap is still real.** `backend/main.py` today still calls `BackgroundTasks` at the
same two sites the branch replaced — `background_tasks.add_task(_run_omr)` at the
`/process/omr` handler and `background_tasks.add_task(_run_compare)` at `/process/compare`
— confirmed by grep against current `main.py`. `PROJECT_STATUS.md`'s Known Limitations
entry for this is current, not stale.

**But the port is not cheap, and part of the branch's surface no longer exists.**
`main.py` has grown from 694 to 971 lines since the fork point, and **400 of the current
971 lines were inserted (123 deleted) since `2b3955f`** (`git diff 2b3955f main --numstat
-- backend/main.py`) — auth, payments, the Gradus library, and comparison-session routes
were all built into this same file after the branch forked (23 routes at the fork point,
26 today; the route *count* barely moved but the churn inside existing routes is heavy).
`backend/database/models.py` gained 78 lines (1 deleted) over the same window — new tables
(`ScoreAccess`, `PasswordResetToken`, `TokenBlacklist`, `ComparisonSession`, `GradusScore`,
per CLAUDE.md's model list) that didn't exist when the branch's `Job` model was written.
`git merge-tree --write-tree main claude/peaceful-kapitsa` shows content conflicts (not
add/add) in both `main.py` and `models.py` — both files existed at the fork and have
diverged in overlapping regions. One of the branch's three job types, `download` (wired to
an `/imslp/download` route), has **no matching route on `main` at all** today — confirmed
by grep; the September IMSLP ingest work (`tools/library/ingest imslp`) is a host-side CLI
tool, not a web-app endpoint, so that third of the branch's wiring is now dead weight.

**Recommendation: re-implement fresh rather than port.** The worker/queue *design* (SQLite
`jobs` table, startup requeue-with-retry, a progress-callback shape) is sound and worth
keeping as a reference, but `main.py`'s route surface has moved too much for the branch's
diff to apply usefully — reconciling two 400+/78+-line divergences in files this central
would cost more than re-wiring `job_queue.enqueue` into today's `/process/omr` and
`/process/compare` handlers directly and dropping the stale `download` job type. Lower
priority than `magical-bhabha`: `PROJECT_STATUS.md`'s Scope section has explicitly
deprioritized multi-user/production robustness ("the Stripe payment gate and multi-user
infra are already built but no longer the optimization target ... design decisions should
minimize complexity and ongoing cost, not maximize generality"), and for a single-user
Docker Compose session, losing an in-flight job on a restart Sean initiated himself is a
smaller cost than the same failure would be in a production deployment.

---

## Summary

| branch | capability | still needed? | port cost | recommendation |
|---|---|---|---|---|
| `omr-dossier-verification-layer-eaf6d0` | dossier verification, 4 phases | no — all four already have a shipped `main` equivalent, three general-purpose, one measured inert | n/a | close, archive |
| `magical-bhabha` | measure-level MusicXML patching | yes — still a stub; still the #1 web-app TODO; 2 existing tests fail without it | low — one untouched function, unchanged model fields, an existing test spec to turn green | port |
| `peaceful-kapitsa` | SQLite job queue | yes — still bare `BackgroundTasks` | high — `main.py` +400/-123, `models.py` +78/-1 since the fork, one job type's route is gone | re-implement fresh against today's routes; lower priority |
