# Code audit and cleaning run — 2026-10-07

Branch `lane-audit-2026-10-07`, off `main` 894ce442. Readers: four Sonnet
agents (staged pipeline; legacy and shared tools; backend and frontend; tests
and repo hygiene), each read-only and fact-only. Every claim below that a
reader made was re-checked against the tree before it was acted on or written
here. Analysis and decisions: Fable.

Nothing in GATHER or ADJUDICATE moved. Every derived-check count is identical
before and after, except `mutation_batteries_live`, which went to zero on
purpose (ROADMAP 0.4d).

## 1. The numbers

| control | before | after |
|---|---|---|
| `python3 -m tools.omr.staged.check` TOTAL | 247 | **192** |
| … inventory / wiring / gather_coverage / capture / reach / brakes / trace | 9 / 70 / 15 / 18 / 22 / 9 / 3 | same |
| … source_text_tests / mutation_batteries_live | 46 / 55 | 46 / **0** |
| `pytest tools/omr/tests -m "not slow"` | 4,580 passed, 0 failed, 17 skipped, 2 xfailed | **4,580 passed, 0 failed**, 17 skipped, 2 xfailed |
| `ruff check --select F` (pyflakes class), tools + backend, tests excluded | 231 findings | 13 (all unused locals, listed in §3B) |
| `backend/tests` | 116 tests | 119 passed, 3 failed: the two `test_export_module` failures the roadmap already records against the correction-patching stub (0.2b line), and one that needs the `lilypond` binary the container lacks; this run touched only imports under `backend/` |

A note on the container: it lacked `cv2`, `scipy`, `skimage`, `fitz`, the
backend requirements and `greenlet`, so the first `check` run reported eight
checks BROKEN and the fast tier stopped at collection. Those were installed;
none of the findings above is an environment artefact. The clone is also
SHALLOW (121 commits from 2026-10-01), which is now a line in CLAUDE.md §5a.

## 2. What this run changed (all zero-behaviour)

- [x] **`adjudicators/rhythm.py` `_corroborate`**: a dead block computed a
  `whole_rests` set over `ev.rows(Q.REST, …)` and three counters, used none
  of them, then returned. One record scan per meter candidate per system,
  gone. Verdicts cannot change: nothing read the results.
- [x] **`export.py`**: `RELOCATE_AT_EXPORT_ENV`, `RELOCATE_COLLISION_SPACES`
  and `relocate_at_export_enabled()` were defined twice, verbatim and
  adjacent (a merge artefact of 2.58). One copy kept.
- [x] **Three functions with no caller anywhere in the repo removed**:
  `header._template_fit` (its docstring names a design; the design lives at
  the call sites it describes), `review/human_evidence._verdict_subject`,
  `staged/legacy.group_index_for_reference` (its module docstring now says
  it was removed and where `git log -S` finds it).
- [x] **86 unused imports and placeholder-less f-strings** removed by `ruff
  --fix` across 43 files in `staged/`, `backend/` (non-test), `tools/library`,
  `annotate/`, `training/`, `tools/dashboard`. **Not touched:** the frozen
  legacy modules and their satellites (`tools/omr/*.py`, 11 findings; frozen
  means frozen) and every test file (pytest fixture imports read as unused
  to a linter and are load-bearing).
- [x] **Three annotation-only undefined names** given their import:
  `inventory.Sequence`, `pipeline.Verdict`, `annotate/ledger_grid.Callable`.
  Harmless at runtime under `from __future__ import annotations`; a
  `get_type_hints` call would have raised.
- [x] **ROADMAP 0.4d**: 55 mutation-battery scripts moved to
  `benchmarks/_archive/<same relative path>` with a README. Found by the same
  rule `check.py` uses; referenced by no test (three test docstrings mention
  them historically).
- [x] `benchmarks/omr-labeling-hollow2-2026-09-breitkopf-brahms1/batch_config.stale-9slot.bak` removed (the only tracked backup file).
- [x] **CLAUDE.md §4c** typed "28 adjudicators" and listed them; the tree has
  51 (`adjudicate.ORDER`). The passage now derives the count and names the
  six adjudicator files the list omitted. **§5a** gains the shallow-clone
  fact. 5,835 words, under the 6,000 cap.
- [x] **`docs/flags-2026-09.md`**: the `OMR_OWNER_FROM_STAVES` row said
  default ON in one column and "OFF until Sean has seen …" in the verdict
  column. The code is default ON (Sean, DECISIONS 2026-10-06); the verdict
  column now agrees.
- [x] **README.md** (last touched 2026-06-10) described the legacy CLI as
  the entry point and pointed at the frozen files as "where the work stands".
  Rewritten to point at CLAUDE.md, ROADMAP, DECISIONS and the staged CLI.
- [x] ROADMAP: 0.4d done, new row 0.6 for this audit, a START HERE block.

## 3. What was found and NOT changed, by priority

### 3A. Web app security — for Sean, before any public deployment

The web app is Phase 3 work and the legacy engine still drives it, so none
of this is on the roadmap and none of it was touched. It is listed first
because `docker-compose.prod.yml`, `scripts/deploy.sh` and Traefik with
Let's Encrypt exist, so it CAN be deployed as is. Each line names the file
and the fix; all are small.

- [ ] **Any authenticated user can list, read, delete and export every
  score.** `Score` has no owner column (`backend/database/models.py:45`);
  `main.py` filters nothing by user. Fix: `user_id` on `Score`, filter every
  `/api/scores*` route. Schema change, so the DB drops (CLAUDE.md §11).
- [ ] **`/uploads` is served with no auth** (`main.py:109`, `StaticFiles`).
  Every uploaded PDF, MusicXML and snippet is readable at its path. Fix: an
  authenticated file route, or a per-score token in the path.
- [ ] **Two upload routes join the client's filename into a path**
  (`main.py:901-914` Gradus, `main.py:999-1002` compare):
  `os.path.join(dir, file.filename)`. An absolute filename replaces the
  directory. Fix: `os.path.basename` plus an extension allowlist, as
  `file_import.py` already does for `/api/import`.
- [ ] **Forgot-password returns the reset token in the response**
  (`routers/auth.py:254-258`, "Remove in production"). Anyone who knows a
  registered email resets its password. Fix: drop `dev_token` and either
  send mail or log the token server-side.
- [ ] **The JWT secret has a working default** (`core/config.py:18`,
  `"changeme-please-…"`) and nothing refuses to start with it. Fix: refuse at
  startup when `secret_key` equals the default and the env is not dev.
- [ ] Refresh cookie `secure=False` (`auth.py:67-75`); `logout` blacklists
  neither token (`auth.py:208`); no upload size cap anywhere (`file.read()`
  whole-body; nginx has no `client_max_body_size`); rate limits only on
  register, login, forgot-password (refresh, reset-password, every upload,
  OMR and Vision route unlimited; key is the remote address with no
  proxy-header handling behind Traefik and nginx).
- [ ] `lilypond`, `musicxml2ly`, `rsvg-convert`, `inkscape` subprocesses
  have no timeout (`lilypond_engrave.py:51,81`, `claude_vision.py:407,422`).
  A hostile `.ly` hangs a worker.
- [ ] Dependency pins with published advisories: `python-multipart 0.0.9`
  (fixed 0.0.18), `python-jose 3.3.0` (fixed 3.4.0; app uses HS256 only, so
  exposure is uncertain), `requests 2.32.2` (fixed 2.32.4), `pillow 10.3.0`
  (several releases behind). `passlib 1.7.4` + `bcrypt 3.2.2` is an
  end-of-life pair. Frontend base image `node:20-alpine` is end-of-life
  (April 2026); its Dockerfile runs `npm install --legacy-peer-deps`
  despite a tracked lockfile. Backend Dockerfile has no `USER` (runs as
  root), copies `tests/` into the image, pins `alembic` but has no
  migrations directory.
- [ ] `admin_emails` default is a personal address baked into
  `core/config.py:22`.

### 3B. The staged pipeline — structural, each a lane

- [ ] **Nine flags whose table verdict is `promote` are still read**
  (`OMR_SLOT_FAMILY_BLOCK`, `OMR_CLEF_GAP`, `OMR_METER_CARRY`,
  `OMR_METER_FROM_BARS`, `OMR_SLOT_CONSTRAINTS` unconditionally;
  `OMR_WHOLE_REST_INK`, `OMR_ENGRAVED_KEYSIG`, `OMR_DOCUMENT_IDENTITY`
  "pending" a measurement; `OMR_DIRECTION_TEXT_SCAN_GATE` is "promote ON"
  but default OFF, so promoting it flips behaviour). ROADMAP 0.2b reads as
  done; a 0.2c for the first five is mechanical and Sean-free. The staged
  path reads 23 `OMR_*` names against a cap of 15 (CLAUDE.md §7).
- [ ] **One flag, two readers**: `OMR_OWNER_FROM_STAVES` has its own
  constant and reader in both `gather.py:1383` and `ownership.py:294`;
  `OMR_DIRECTION_TEXT` is read in `pipeline.py:111` and `gather.py:7961`.
  One function each, or a typo in one place diverges the stages.
- [ ] **55 `except Exception` handlers in `staged/`, none logs** (no
  `import logging` in the package). Sixteen abstain visibly on the record,
  which is the right shape. About twenty convert a crash into a default
  (`header_cells = {}` at `gather.py:6282, 6627, 6838`; `stems = []` at
  `:554`; `facts = {}` at `:8242`; `return None` in `groups.py:484`,
  `meaning.py:505`, `readout.py:1229`). Rule 8 says a fallback never turns
  "cannot tell" into an answer; an empty header dict reads downstream as
  "no header printed". A lane: every handler in GATHER files an abstention
  with the exception class as its reason word.
- [ ] **Duplicated helpers across the derived checks**: `_gap_key`,
  `stale_gaps`, `unaccounted`, `_quantities`, `_q_name`, `_attr_tail` are
  defined in two to five of `capture`, `inventory`, `trace`, `wiring`,
  `gather_coverage`, `health`. Also `_cell_staff_space` and `_glyph_box_row`
  identical in `family_precision.py` and `notehead_precision.py`; four IoU
  functions (`gather._iou`, `readout._iou`, `export._box_iou`,
  `geometry.box_iou`); `_movement_spans` twice (`header.py:619`,
  `rhythm.py:4296`, different lengths, worth a diff).
- [ ] **Six functions referenced only by tests** (`adjudicate.by_checkability`,
  `notehead_precision._notehead_same_side_second_refusal`,
  `ownership._ink_overridden_rungs`, `rhythm._to_canonical`,
  `gather_coverage.q_covering`, `infer.inferred_in_basis`) and one retired
  rule kept for its docstring trail (`ownership._ink_refutes_side`, 2.37
  elimination). Delete or wire; Sean's call on the elimination rule.
- [ ] Size: `gather.py` 8,735 lines, `rhythm.py` 6,390, `export.py` 5,922,
  `ownership.py` 3,667; `to_musicxml` is 562 lines, `_place_notes` 507,
  `adjudicate_duration` 465. Not a cleanup; a Phase 3 fact.
- [ ] Remaining pyflakes findings, all unused locals, left for the owner of
  each line: `rhythm.py:1024 dot_w`, `:3461` loop variable shadows the
  `tally` import, `gather.py:5668 prev_positions`, `:6063 lx0`, `:6281 exc`,
  `:7491 h`, `wiring.py:1333 src`, `ledger_grid.py:3392 r0`,
  `port_user_verdicts.py:84 rows`, `draft_windows.py:167 base_index`.
- [ ] Coupling: staged imports ~25 private `_mxl_*`/`_lily_*` renderers and a
  dozen tuning constants from the frozen `export.py`/`transcribe.py`
  (`export.py:58`, `lilypond.py:54`, `ownership.py:21`,
  `notehead_precision.py:89`, `rhythm.py:33`). Allowed by §3; it means a
  "bug fix" in legacy can move a staged verdict. Worth a test that pins the
  constants' values.

### 3C. Legacy and shared tools

- The freeze holds as far as this clone can see: `transcribe.py`,
  `export.py`, `contextual.py` are byte-identical from 2026-10-01 to HEAD.
  Earlier history needs an unshallowed clone.
- No module is unreferenced, but `run_pipeline.py` ("older Phase-1-only
  CLI"), `score_translation.py`, `_phase1_diagnostic.py` (docstring
  mentions only), `condensed_parts.py`, `bracket_reader.py`,
  `vertical_runs_page.py` are referenced by no product code, only benchmarks
  or one test each. Frozen satellites, so left; candidates for `delete` rows.
- Two annotation-only undefined names in frozen files
  (`transcribe.py:3065 Sequence`, `contextual.py:1052 Assist`), harmless.
- Hard-coded `/Users/seanjohnson/…` paths in seven training and annotate
  scripts (`training/orchestral_eval.py:60`, `end_to_end_eval.py:48`,
  `build_dossiers.py:37`, `annotate/select_cells.py:65`, three evals) and
  two tests (`test_pipeline.py:44`, `test_stage_review_real_record.py:21`).
  Machine-local by nature; an env var with that default would let a second
  machine run them.
- `sys.path.insert` in `backend/modules/{export_module,local_omr,staged_omr}.py`
  and four tools: the backend reaches `tools.omr` by path, not by package.
- 44 `OMR_*` names read in legacy/shared; every one has a row in the flags
  table. No `shell=True`, no `os.system`, no `pkill` anywhere.

### 3D. Tests

- 299 test files, 6,310 test functions, 106,511 lines. Ten files over
  1,000 lines (`test_export.py` 3,206; `test_staged_export.py` 2,725).
- **The slow-by-text rule caught 56 files, 52 of them slow by text ONLY**
  (a `.pdf"` string in 47); 7 matched only in a comment or docstring, 32 were
  measured fast on 2026-09-22 and slow by text alone. **Fixed the same day
  (Sean: "move on the .pdf issues")**: a measured duration now decides for a
  measured file, the text rule judges only unmeasured files, and it ignores
  comments and docstrings (`tools/omr/tests/conftest.py`, CLAUDE.md §6c).
  39 files moved to the fast tier; it found one test the slow tier had been
  failing since 10-06 (`test_cell_line_localization` pinned the comb-slide
  bound that ROADMAP 2.57 replaced; it now pins that path under its flag) and
  four that need `ijson`, which this container lacked. 168 files still have
  no recorded duration; re-measuring `durations.json` on Sean's machine is
  the remaining step.
- 46 source-text test files remain (policy: no new ones, counted).
- **ROADMAP 0.4a** (shared fixture module): the four two-line `_log` copies
  are in `test_staged_c_clef.py:33`, `test_staged_clef.py:19`,
  `test_staged_clef_human_box.py:56`, `test_staged_clef_offstaff.py:58`;
  there are 24 `_log` and 8 `_record` definitions in all. The inventory is
  the useful part; the item stays `todo`.
- `backend/tests/test_staged_accounting_3_3c.py` and
  `test_staged_job_budget.py` import fixtures from another test module (13
  redefinition warnings); a `conftest.py` fixture is the usual home.

### 3E. Repo weight and hygiene

- 20,081 tracked files; `.git` 506 MB; working tree 1.4 GB. By kind: PNG
  3,686 files / 855 MB; JSON 8,926 / 365 MB; `benchmarks/` 832 MB,
  `data/` 503 MB, `out/` 72 MB.
- **45 tracked files were matched by `.gitignore`** (`git ls-files -ci
  --exclude-standard`): 11 `*.omr.json` in `omr-clef-demo` (30 MB), 17
  files under `crops/`, 16 noise-floor outputs, 1 thumbnail. **Resolved the
  same day**: the thumbnail untracked; the other 44 are the raw data of
  documented results (the clef-demo results file cites the `.omr.json`; the
  noise-floor arms are behind the ±6-edit figure CLAUDE.md §6b quotes; the
  crops are print evidence) and are kept, with negation rules so the rules
  and the tree agree. The count is 0. The ~290-line `.gitignore` itself,
  with its ~20 per-roadmap-item blocks, was not consolidated: changing rule
  semantics is a separate decision.
- **11 `*.record.json` were tracked, 98.7 MB**, mostly
  `benchmarks/omr-staged-engraved-2026-09/out/`. **Triaged the same day**
  (a read-only survey of the 38 tracked dumps over 3 MB, 247.6 MB in all):
  ONE is an input — `engraved-p0p2-20260930b.record.json`, which
  `benchmarks/acceptance/manifest.json` names as the engraved acceptance
  document's record, the only one a cloud container needs; 28 (174 MB) are
  evidence a `FINDINGS.md`, a benchmark script or the acceptance tooling
  reads; 9 (62.8 MB) are uncited outputs. The six clear-cut ones were
  untracked (`engraved-p0p2-20260929b`, `engraved-p1`, `engraved-p2`, the
  `omr-no-ink-lie` repaired Litolff record, the `omr-owner-domain` Brahms
  dump, the two timestamped acceptance MusicXML files; ~39 MB off the
  checkout, history untouched) and the engraved benchmark's `out/*.record.json` is now ignored
  with the kept records negated by name. Three weak candidates stay tracked
  (`20260929`, the `2.3b` arm, `grid_brahms_0-26.json` from a two-day-old
  lane). Untracking never shrinks `.git`; only a history rewrite would, and
  none is proposed. Compressing the two `gather.json` dumps (32 MB) is the
  next size lever if wanted.
- `out/print/` is tracked by design (526 files, crops). `data/user-labeled*`
  tracks 1,781 PNGs (496 MB) — the hand labels, not regenerable (§9), so
  they stay.
- `benchmarks/`: 287 directories; **102 lack a `FINDINGS.md`** (40 of them
  last touched before September; 62 have some other `.md`). Rule 9 says
  findings go in `FINDINGS.md`. A rename pass, not a rewrite.
- `benchmarks/omr_ledger_extrapolation_shim.py` is a by-path loader for a
  hyphenated directory, imported by 8 probe scripts. Fine where it is.
- `docs/`: 115 files; 51 are handoff-style (`handoff-*` 38, `NEXT-*`,
  `RESUME-HERE*`, `next-*`), declared historical. The chronicle is 130,834
  words. No action; §"Read in this order" already fences them.

### 3F. Branches

The remote holds **423 branches**: 336 merged into `main`, **87 not**. Of
the 87, 47 are from October (`lane-*`, `rescue-*`, `worktree-agent-*`), most
of them the ledger rounds whose outcome DECISIONS 2026-10-04..06 records
("all nine retired, nothing merged") or whose accepted part landed under
another name. Four are from April–July. Deleting remote branches is
destructive and not done here; the list is in the hygiene reader's report
(this file's git history has the agent output if wanted). **Half done the
same day (Sean: "clean up of ... unmerged branches")**: the 67 unmerged
branches with no commit since 2026-10-04 each have a verified copy at
`archive/<name>` (the session proxy accepts pushes to `refs/heads/*` only,
so a bare `refs/archive/*` namespace was refused; a branch keeps every
commit reachable). **Deleting the 403 originals was blocked by the cloud
session's permission system** ("unverifiable deletion scope") and nothing
was deleted. The recipe needs only the remote's own state, so it can be run
from any checkout once Sean approves:

```bash
git fetch origin --prune
# 1. every branch fully merged into main (336 at the time of writing)
git branch -r --merged origin/main | sed 's#^ *origin/##' \
  | grep -vx main | grep -v '^archive/' > /tmp/merged.txt
# 2. every stale branch that already has its archive copy (67)
git ls-remote --heads origin 'archive/*' | sed 's#.*refs/heads/archive/##' > /tmp/stale.txt
# sanity: nothing active, nothing named main
grep -cx main /tmp/merged.txt /tmp/stale.txt      # both 0
# 3. delete, in batches of 30
cat /tmp/merged.txt /tmp/stale.txt | xargs -n 30 git push origin --delete
```

Every branch active since 2026-10-04 stays, including the ones other
sessions created during this run.

## 4. Proposed next lanes, in order

1. [ ] **Web app hardening** (§3A, first five bullets) — before any deploy;
   one PR; the owner column drops the DB.
2. [ ] **0.2c: promote the five unconditional `promote` flags** — removes
   five reads, no behaviour change, brings staged to 18 of the 15 cap.
3. [ ] **GATHER handlers abstain, never default** (§3B third bullet) —
   rule 8 made structural; `health` would see it.
4. [x] **Tighten the slow-by-text rule** — done the same day (§3D).
   [ ] Re-measure `durations.json` on Sean's machine so the 168 unmeasured
   files are judged by measurement too.
5. [ ] **Derived-check helper module** (`_gap_key`, `stale_gaps`,
   `unaccounted`, `_quantities`) — four copies to one.
6. [ ] **Record-dump triage** (§3E) — name the committed records that are
   inputs; `git rm --cached` the rest. (The 45 ignored-but-tracked files:
   done the same day.)
7. [~] **Branch prune** — archive copies made; the deletions wait on Sean's
   approval (§3F has the recipe).
8. [ ] 0.4a shared test fixture module (inventory in §3D).

## 5. The root files — ruled

The user preference for this account asks that `CLAUDE.md`, `PROJECT_BRIEF.md`
and `version_memory.md` be updated after every commit; CLAUDE.md (2026-09-22)
had declared the latter two frozen. **Sean, 2026-10-07: "Unfreeze and update
so that all docs are up to date."** Done (DECISIONS 2026-10-07): both are
un-frozen and current, `version_memory.md` carries one bridge entry for the
frozen window and per-commit entries from here on, CLAUDE.md §13 names them
in the session-end rule, and `PROJECT_STATUS.md` / `NOTES.md` stay frozen
with a refreshed banner.
