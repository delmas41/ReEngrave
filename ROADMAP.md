# ROADMAP — from here to a finished score

The phases and gates are defined in
[docs/plan-2026-09-22-from-here-to-a-finished-score.md](docs/plan-2026-09-22-from-here-to-a-finished-score.md).
This file is the STATUS of each item and nothing else. A session that takes
an item puts its branch beside it; a session that finishes one changes its
status and names the commit. Nobody writes a handoff — the line here and the
benchmark `FINDINGS.md` are the record.

Status words: `todo` · `in flight (branch)` · `done (sha)` · `blocked (why)`
· `dropped (why, DECISIONS line)`.

**Definition of done for the product** (plan §4): one command, a whole
movement, MusicXML + LilyPond PDF, unread bars marked never invented, every
staff named or held out, and a cleanup count Sean would rather pay than
re-enter.

---

## Phase 0 — Stop and consolidate

| item | what | status |
|---|---|---|
| 0.1 | Staged is the product path; legacy frozen | done (DECISIONS 2026-09-22) |
| 0.2 | Flag triage table, ≤ 15 product flags | done — table with a verdict on all 60 (`docs/flags-2026-09.md`) |
| 0.2b | Enforce the triage: remove the `promote — now` flags, delete `OMR_ADJUDICATE`, add `OMR_RESEARCH`, a derived test that staged reads no frozen flag and every `OMR_*` read has a row | todo |
| 0.3a | Archive CLAUDE.md → `docs/chronicle-2026-09.md` | done (2b441cb3) |
| 0.3b | New CLAUDE.md spec ≤ 6,000 words | done (2b441cb3; 4,700 words) |
| 0.3c | `docs/DECISIONS.md`, `ROADMAP.md` | done |
| 0.4a | Shared staged test fixture module; delete the four `_log` copies | todo |
| 0.4b | One `python3 -m tools.omr.staged.check` with `open-findings.json` | done — **baseline 250 open findings on 2026-09-22** (wiring 66, reach 26, gather_coverage 19, capture 18, inventory 11, brakes 8, trace 3, source-text tests 47 files, live mutation batteries 52) |
| 0.4c | Fast / slow test tiers derived from measured durations | done — full suite 4,806 passed / 20 skipped in 700 s; fast tier 2,695 tests in 75 s wall (`pytest -m "not slow"`); threshold derived from `tools/omr/tests/durations.json` |
| 0.4d | Archive the 52 mutation batteries under `benchmarks/_archive/`; no new ones | todo — `check` counts live ones meanwhile |
| 0.4e | No new source-text tests; `check` counts them | done — 47 files counted, allowlist of 2 |
| 0.5 | Lane discipline: brief from the tree, phase item, gate, print check | done (plan §6, rules 1–10) |

Gate: spec < 6,000 words; `check` writes `open-findings.json`; flag table
has a verdict on every flag; fast tier under two minutes.

## Phase 1 — The acceptance harness

| item | what | status |
|---|---|---|
| 1.1 | Whole-movement staged records for the three acceptance documents, ink SUMMARY persisted not rows (< 20 MB/page) | todo |
| 1.2 | Run-time budget; `OMR_DIRECTION_TEXT_SCAN_GATE` on for acceptance; movement in < 1 h unattended | todo |
| 1.3 | `python3 -m tools.omr.acceptance` → `benchmarks/acceptance/current.json`, side-by-sides, nightly | todo |
| 1.4 | First cleanup count on the three fixed pages (DECISIONS 2026-09-22) — Sean | todo |

Gate: `current.json` for all three; a baseline count committed.

## Phase 2 — Close the foundation, in funnel order

| item | what | status |
|---|---|---|
| 2.1 | Identity is PLACEMENT (which slot a staff is), never naming — every part is already named on both shared records; gate `staff_not_identified` 783 → < 100, zero grafts against print | measured, gate NOT met: 783 → 141 was won by `OMR_SLOT_FAMILY_BLOCK` on 09-21; the constraint channels of `claude/instrument-identification-channels-8dcaa2` (2acb3fcf, a0a5aeac, 73d7ffbe, f934ae7c) move 13 placements from INFER to ADJUDICATE and the count by 0. **The whole residual is five `Violoncello e Basso` staves narrowed to [Cello, Contrabass]** (141 notes) — a condensed staff is two parts and a slot is one. Placing it on the first of its two slots takes 141 → 0 as a CONDENSATION, not a graft, and changes what a placed staff means: **blocked (Sean's call — see DECISIONS request 2026-09-22)** |
| 2.2 | Key-signature precedence, engraved-only one-sided; gate 20/20 engraved, Litolff ≥ 44/75 | **landed** `claude/identity-conditions-key-signature-b510b3` (`beba5c64` is the default flip; `291677b5` the rule). Engraved gate **exceeded**: 47 of 50 right, 3 wrong, and the template is 67/67 wherever it speaks. ⚠️ **The Litolff half of the gate is NOT measured** — the rule is one-sided and proved a no-op on a real scan gather, so it cannot have moved 44/75, but *cannot have moved it* is not *measured at ≥ 44/75*. ⚠️ n = 1 engraved document, 1 renderer, no print consulted; a second engraved document is the ranked next step and the 10 held candidates are named in `benchmarks/omr-document-identity-2026-09/out/library-domains.json` |
| 2.3 | INFER duration rules against the print (17 + 41 crops) → default decision | todo |
| 2.4a | Notehead precision on staged: port the two legacy filters; width floor as an ADJUDICATE refusal | todo |
| 2.4b | Detector recall on hollow noteheads and hairpins: one labeling round + head surgery | todo |
| 2.4c | Unread-mark subject: zero-coverage mark-sized ink at a corroborated column → marked bar, never a note | todo |
| 2.5 | Arcs — re-measure after 2.4 | blocked (2.4) |

Gate: > 80% of gathered noteheads reach the file on both scans; all parts
named; second count lower than the first.

## Phase 3 — The staged pipeline becomes the product

| item | what | status |
|---|---|---|
| 3.1 | LilyPond exporter for staged, reusing the `_lily_*` renderers | todo |
| 3.2 | Port the legacy-only list deliberately (weight routing first) | todo |
| 3.3 | Web app `omr_engine=staged`; page cap → job budget; default flips on acceptance parity | todo |
| 3.4 | Corrections as human evidence in the record; re-export; auto-accept over recorded verdicts | todo |

Gate: a whole movement through the web app on staged to MusicXML + PDF; an
accepted correction changes the re-export and the record names the decider.

## Phase 4 — Import from IMSLP

| item | what | status |
|---|---|---|
| 4.1 | `reengrave import <work>`: rank, one browser click at the gate, ingest, run, export, render | todo |
| 4.2 | `Kind.MOVEMENT`; a whole work exports one file per movement | todo |
| 4.3 | Budget printed before the run; unattended mode owns its processes | todo |

Gate: Beethoven 5, four movements, four MusicXML + four PDFs, page ranges right.

## Phase 5 — Clean (ongoing)

Cleanup count every two weeks on the fixed pages; corrections filed as
evidence; auto-accept rules from recorded verdicts. Done for a publisher when
Sean would rather fix than re-enter.
