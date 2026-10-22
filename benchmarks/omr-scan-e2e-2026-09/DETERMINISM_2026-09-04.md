# Is the scan-e2e harness deterministic? Yes — bit-exact, noise floor 0.0000

2026-09-04, on `b8b10514` (tip of `claude/scan-weights-round4-continue-074940` at
the time), in a fresh worktree (`claude/scan-e2e-determinism`) with the two
mandatory venv links (`OMRNED_PYTHON` + the `.venv-omrned` / `.venv-surya`
symlinks — note `scan_eval.py`'s own trimmer resolves `ROOT/.venv-omrned`
directly, so the env var alone is NOT enough; without the symlink the run
refuses before transcribing anything).

**Verdict: the harness is fully deterministic run-to-run — the measured noise
floor is exactly 0.0000 pooled and 0.0000 on every row — so the round-5
candidate delta (0.7517 → 0.7493, 22 edits) is a real, reproducible property of
the weights, not harness jitter. It clears the noise floor by definition;
"clears the noise" and "is musically meaningful at 22 edits of ~7900" remain
different questions, which is what the three-axis gate is for.**

## The runs

Replicating `gate_round5.sh`'s axis-2 invocation exactly (weights pinned via
`OMR_SCAN_EVAL_WEIGHTS`, protocol from `works.json`: dpi 600, conf 0.25,
imgsz null, direction text at pipeline default = ON, no dossier; the bach row
self-skips as unverified, 5 verified rows run):

| run | weights | tag | pooled OMR-NED (full precision) | edits | pred |
|---|---|---|---|--:|--:|
| recorded prodbase (`aa9bcfde`, other worktree, days earlier) | hollow-ft-2026-09-03 (production) | prodbase | 0.751737929720979 | 7894 | 4350 |
| **Run A** (this tree) | production | det-a | **0.751737929720979** | 7894 | 4350 |
| **Run B** (this tree, back-to-back repeat) | production | det-b | **0.751737929720979** | 7894 | 4350 |
| recorded gate (`4049eb0a`-era, other worktree) | round5-merged/d25e0_graftprod_shift0.9 | shift0.9 | 0.7492861222158766 | 7872 | 4355 |
| **Run C** (this tree) | d25e0_graftprod_shift0.9 | det-c | **0.7492861222158766** | 7872 | 4355 |

Per-row, A vs B: every |Δ OMR-NED| = 0.0000000000, every Δedits = 0. Run C
matches the recorded gate on every row to full float precision (beet5-984073
0.715239/1286, beet5-575951 0.762598/1362, dvorak 0.430582/673, brahms
0.919165/3434, mahler 0.688232/1117).

## Byte-level localization

- **All five `.omr.musicxml` are byte-identical between A and B**, and — the
  stronger fact — byte-identical to the OTHER worktree's fixtures produced
  days earlier: det-a ≡ prodbase (all 5 rows), det-c ≡ shift0.9 (all 5 rows).
  Transcription + export, including both OCR rungs, is bit-reproducible
  across runs, sessions, and worktrees.
- **The `.omr.json` pairs differ ONLY in wall-clock fields**:
  `_scan_eval_seconds` and `runtime.{phase1,yolo,contextual,direction_text,total}_s`.
  Every musical field — detections, confidences, margin labels, direction
  text — is identical. (Verified by full flattened-JSON diff on two rows.)
- **The Surya nondeterminism lead does not manifest here.** The margin-label
  reader ran (it read `Yiolino II.` on the Dvořák row and dropped it at the
  lexicon, same in every run) and the direction reader ran
  (`runtime.direction_text_s` present); their outputs were byte-stable across
  four runs on two checkpoints. No OCR-off arm was needed — the task's trigger
  ("if A ≠ B anywhere") never fired.
- **Truth files are NOT byte-reproducible across trees but are score-inert**:
  re-trimming in a fresh worktree regenerates music21's random
  `<score-instrument>`/`<midi-instrument>` ids and nothing else; the scores
  came out edit-identical anyway. Within one worktree they are cached after
  the first run, so A/B/C scored against the same truth bytes by construction.

## Two provenance facts worth keeping

- **Device:** the axis-2 scan-e2e runs never set `OMR_DEVICE` (only axis 1's
  `gate_all.py` forces CPU, and nothing in the transcribe path reads
  `OMR_DEVICE` at this commit anyway — `YoloDetector` is `device="auto"`).
  On this machine ultralytics `select_device('')` resolves to **cpu** (torch
  2.8.0; MPS available but not auto-picked), so all recorded gate numbers and
  these runs are CPU numbers regardless.
- **The 0.7517 baseline and the 0.7493 gate were measured on trees that
  differ by the `OMR_CELL_LINE_TRACE` addition to `measure_extractor.py`**
  (+183 lines, aa9bcfde → 4049eb0a). Run A proves that change inert for
  transcription: same production weights on the later tree reproduce
  0.751737929720979 to the byte. The earlier cross-tree pair sometimes read as
  noise — "0.7517, reproducing 0.7512" in `aa9bcfde`'s commit message — is not
  run jitter either: 0.7512 is CLOUD_2048_RESULTS.md's production figure from
  a different tree/era, i.e. a tree difference, not variance.

## What the noise floor does and does not cover

Zero observed variance over a same-tree pair plus two cross-day, cross-worktree
reproductions bounds **run-to-run and session-to-session noise at 0** for this
harness on this machine. It says nothing about sensitivity to environment
changes (torch/ultralytics versions, another machine, dpi or page-box
differences across editions), and it does not make a 0.0024 delta *important* —
the metric is symmetric and flatters under-prediction (ROUND5_METHOD §3b's
shift-1.5 warning). It does mean nobody needs to re-run an arm to trust its
third decimal, and that any future scan-e2e delta ≠ 0 between two runs of the
same configuration is a real change (tree, weights, env), never jitter.

## Candidate re-measurement, and the element counts round 5 never quoted

`d25e0_graftprod_shift0.9.pt` re-measures at **pooled 0.7493 / 7872 edits /
4355 predicted** — identical to its recorded gate number. Element counts across
the 5 pages (same counting as ROUND5_METHOD §3: `<tie>` tags counted
start+stop, `<rest>` any):

| element | truth | production | graft no floor (recorded §3) | **shift0.9 candidate** |
|---|--:|--:|--:|--:|
| tie | 271 | 60 | 106 | **97** |
| rest | 972 | 577 | — | **589** |
| note | 1894 | 1478 | 1490 | **1451** |
| slur (start+stop) | 204 | 160 | 170 | **170** |
| beam | 563 | 358 | 368 | **370** |
| time | 110 | 57 | 69 | **60** |

So the bias shift keeps most of the graft's tie recovery (60 → 97 of the
unshifted 106) and the slur/beam gains, while pulling note emission *below*
production (1478 → 1451) — consistent with §3b's mechanism: the floor works by
believing fewer noteheads. Rests barely move (577 → 589 of 972); the rest hole
is not this candidate's business.

## Reproduction

```bash
git worktree add <dir> -b <branch> b8b10514 && cd <dir>
ln -sfn /Users/seanjohnson/Desktop/ReEngrave/.venv-omrned .venv-omrned
ln -sfn /Users/seanjohnson/Desktop/ReEngrave/.venv-surya .venv-surya
export OMRNED_PYTHON=/Users/seanjohnson/Desktop/ReEngrave/.venv-omrned/bin/python
OMR_SCAN_EVAL_WEIGHTS=/Users/seanjohnson/Desktop/ReEngrave/omr-weights/deepscoresv2-yolov8l-hollow-ft-2026-09-03.pt \
  python3 benchmarks/omr-scan-e2e-2026-09/scan_eval.py --tag det-a \
  --out benchmarks/omr-scan-e2e-2026-09/results-det-a.json
# repeat with --tag det-b; then the candidate with
# OMR_SCAN_EVAL_WEIGHTS=.../omr-weights/round5-merged/d25e0_graftprod_shift0.9.pt --tag det-c
```

Result JSONs beside this file: `results-det-a.json`, `results-det-b.json`,
`results-det-c.json`. (`--wait-for-cpu` was also passed here; it only delays
start, it cannot change a computation.)
