# Handoff — the staged pipeline, and why grading stops being the goal

⚠️⚠️ **STATUS, 2026-09-09: THE THREE RANKED TASKS OF §4 ARE DONE.** Do not
re-do them. What doing them found — and **four claims of this file they
correct** — is in CLAUDE.md, section *The staged pipeline: an inventory, an
exporter, and a health report*, with the measurements in
`benchmarks/omr-staged-inventory-2026-09/` and
`benchmarks/omr-staged-export-2026-09/`. In brief:

* **§3's "there is no exporter" is closed for MusicXML.**
  `tools/omr/staged/export.py`, wired as `--musicxml` on the staged CLI. Four
  scan pages export and parse under music21.
* **§2's `tuplet_ratio` question: it is THE PAGE**, with a positive control
  (Beethoven 5 / Litolff `984073` `--pages 2` reads 1 marker, decides 1
  ratio). The SILENCE is still a hole and is not tuplet-specific.
* **§2's redundancy control page is off by one** — `--pages 1` of `984073` is
  the ONE-system row; `works.json` says the two-system page is
  `pdf_page_index` 2. On the right page the layer works. ⚠️ Brahms p2 is two
  systems and still checks nothing, for a different and structural reason.
* **§4's "153 tests" is 226**, and **§3's "everything else is a stub that can
  be filled incrementally" is true of one of the six** — five are starved of
  input one stage earlier, in GATHER.
* **§6's open defect is fixed** and pinned by four tests that run RED without
  it.
* ⚠️ **§7's "suite 3,081 passed" was already stale**: two
  `test_works_json_staff_lineup.py` tests fail on a clean archive of
  `b2494cbc`. Fixed in `62eb59cd`.

⚠️ **§1's redirect is untouched and remains the governing instruction.**

**THE NEXT WORK IS IN GATHER.** Rests have no quantity at all (838 detected
over four pages, nothing declares the absence), and `arc_box`,
`articulation_mark`, `wedge_box` and `dynamic_letter` are observed by nothing —
so **2,541 detected glyphs cannot reach a file**, and no adjudicator or
exporter work changes that.

---


⚠️ **READ THIS FIRST.** It replaces `docs/handoff-2026-09-08-big-picture.md` as
the entry point. That file is still worth reading for the four-causes and
rest-fix history, but **two of its claims are now false and are corrected in
§5 below** — do not act on its ranked list.

Written at the close of 2026-09-08. Everything described here is **on `main`**
(`09073260` and its two predecessors); nothing is waiting on a branch.

---

## 1. THE REDIRECT, IN SEAN'S WORDS

> *"I am not deep enough into the grading to really care about the numbers
> shifting in meaning yet. honestly they dont feel like they have represented
> much that has been helpful and since we are redesigning the pipeline to
> stages - I just want to get everything accounted for and figure out our
> system. The tests currently may help us with if our tools and stages are
> working but I am not worried about it looking better or worse."*

**This retires the metric as the organising goal.** OMR-NED, the scan gate, the
page-normalised era, `check 3` — all of that is GRADING. It is banked, it is
correct, and it is no longer the top item. Do not open a session by running a
benchmark.

⚠️ **And there is a structural reason the redirect is right, not merely a
preference.** OMR-NED compares two FILES AT THE FAR END. It can say *that*
something is wrong; it can never say *which decision* went wrong. Every
attribution attempt of the last week hit that same wall — the category buckets
do not attribute (amplification varies 6x-2x by error kind), `wrong pitch` is
structurally unreachable under `AllObjects`, and a 1,251-error rest correction
scored EXACTLY ZERO on both families. The number was not broken. It was being
asked a question it cannot answer.

**The staged pipeline is the answer to that question**, which makes it the
replacement for the metric rather than a refactor of the reader. Its own design
says so: ADJUDICATE *"returns a value AND a record of what it saw — including
when it abstained."* A score gives a total; the record gives the decision, the
subject and the evidence. That is "everything accounted for" as an
ARCHITECTURAL PROPERTY instead of a document somebody has to keep rewriting.

It also structurally kills the highest-yield bug class of the week — *the value
existed, was correct, and nothing read it* — because here a decision that does
not record is not a decision.

---

## 2. THE ACCOUNTING, MEASURED — not from any document

One real run, one real conductor's page, on the current tree:

```bash
OMR_SURYA_KEEP_ALIVE=0 python3 -m tools.omr.staged \
  "library/editions/mahler/symphony-5/mahler--symphony-5--unidentified-scan-2016--local.pdf" \
  --pages 1 --weights omr-weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt \
  --out /tmp/staged-mahler-p2.json
```

`adjudicate.ORDER` holds **21 decisions**. On that page:

| | count | which |
|---|--:|---|
| DECIDED | 12 | system_membership, staff_group, measure_partition, staff_ordinal, system_staff_count, slot_index, part_partition, clef, key_signature, glyph_owner, duration, meter |
| DECLARED STUB | **6** | `arc_owner`, `arc_kind`, `articulation_owner`, `wedge_anchor`, `dynamic`, `direction` |
| abstained for real reasons | 2 | `instrument` (no_evidence x19), `group_symbol` (no_identity) |
| **never fired at all** | **1** | **`tuplet_ratio`** — in neither the decided nor the abstained table |

Consequence stubs: **1** — `join_parts(part_partition->part_name)`.
EVALUATE: **77 fired, 654 skipped**.

⚠️ **`tuplet_ratio` is the interesting one.** A stub ABSTAINS and says
`not_implemented`, which is the design working. `tuplet_ratio` produced no row
of any kind, so on this page it is not accounted for at all — the one place the
record has a hole rather than an entry. Find out whether that is the page (no
tuplet markers detected) or the wiring, and if it is the page, say so with a
positive control.

### The redundancy layer reports itself INERT, and the reason is the fixture

```
⚠️ witnessed_by_nobody : ['instrument_across_systems']
⚠️ checked_nothing     : ['clef_across_systems', 'instrument_across_systems',
                          'key_signature_across_systems', 'staff_group_across_systems']
⚠️ DISAGREEMENTS: 1 (each implicates its WHOLE group, not its dissenter)
```

Four of six groups "corroborated NOTHING, however busy it looks". ⚠️ **Do not
report that as a defect without the control**: this page is ONE system
(`system_membership: 1`), so an `across_systems` group has nothing to compare
and `single: 17` is the correct answer. **The judgement needs a MULTI-SYSTEM
page.** Beethoven 5 / Litolff p.2 (`--pages 1` of `984073`) is two systems and
is the obvious control.

That the pipeline says this about itself, unprompted, is the property worth
protecting.

---

## 3. ⚠️ THE ONE STRUCTURAL HOLE: THERE IS NO EXPORTER

Verified two ways, not quoted:

* no file in `tools/omr/staged/` mentions `musicxml` or `lilypond`;
* `grep -c staged tools/omr/export.py` is **0**.

So the staged pipeline **cannot produce a file**. It cannot be used on real
work, and it cannot be compared to the legacy path except through the
divergence table — which its own CLI calls *"a POPULATION, not a result"*.

The previous handoff said *"do not start one as a side quest."* Under the
redirect that advice inverts: an exporter is no longer a side quest, it is the
component that makes the staged path real. **It is the only missing COMPONENT;
everything else in there is a stub that can be filled incrementally.**

---

## 4. THE THREE TASKS, IN ORDER

**(1) A DERIVED inventory of the 21 decisions.** For each: what it consumes,
what it produces, which legacy module it replaces, stub or real.
⚠️ **Generate it from the code, do not type it.** Every hand-written inventory
in this repo has gone stale — including the one this file corrects in §5 — and
a decisions table is exactly the shape that rots. `adjudicate.ORDER`, the
adjudicator modules and the per-run record are the sources. Ship it as a script
plus its output, the way `export_coverage` works, so it can be re-run.

**(2) The exporter.** ⚠️ Read `tools/omr/export.py` first and take its
POSITIONS, not its structure: nine "detected then dropped on the way out" bugs
were paid for there, and each is a rule the new exporter must satisfy (whole
rest means the BAR; `_compute_divisions` is an LCM not a max; `<direction>` on
an eventless measure; slur pairing over the staff, not the cell). The staged
record is a better input than the legacy page dicts, so this is not a port.

**(3) Per-stage "is this working"** using the 153 tests already in
`tools/omr/tests/test_staged_*.py`. Sean's bar is *"if our tools and stages are
working"*, NOT better-or-worse. A stage's test should assert it decides what it
can, abstains when it cannot, and RECORDS both.

---

## 5. ⚠️ TWO CLAIMS IN THE PREVIOUS HANDOFF THAT ARE FALSE

Both were acted on today and cost real time. They are the same failure —
reading a written artefact as current state.

1. ***"`page_normalise` is not imported by `scan_eval` — a decision plus
   wiring."*** **False, and it was never true.** `page_normalise.py` and the
   `scan_eval` wiring landed in the SAME commit (`1de175b7`, main, 2026-09-06);
   `scan_eval --page-normalised` has existed since, with the era warning in its
   own output. The two latent faults were fixed on main in `492f1e07`.

2. ***"5 rows unmapped, 89 printed staves for a human to read."*** Stale by
   hours. `map-coverage-cost.json` was generated at `eafca887` (17:27);
   `833afe9f` (23:04, same day) added maps for mahler p3/p4/p5 and bach. **Only
   Mahler p2 ever needed a confirmation pass.** Sean did p3 as well before this
   was noticed.

**The rule that catches both, and it is cheap: ask the TREE, not a committed
JSON.** `map-coverage-cost.json` is a measurement of a works.json that no longer
existed. The scan gate is now **20/20 mapped, 0 staves left to read**.

---

## 6. AN OPEN DEFECT, FILED AND NOT FIXED

⚠️ **The confirmation UI proposes a WORSE `parts` order than `works.json`
holds.** Sean's p3 pass matched works.json on 15 of 15 entries except entry 0
`Fag. 1/2`: his `[0..10]` against works.json's `[10, 0..9]`, printed part FIRST.

That is not cosmetic. `page_normalise` keeps `parts[0]` and merges the rest into
it, so a folded SILENT part sorted ahead of the printed one makes the silent
part's bar survive a `silent_all` measure — measured at **+8 edits** in
`833afe9f`. But `build_cache._research_proposal` sorts, because
`merge_additions.shape_problems` refuses unsorted `parts`. **Two conventions
that contradict each other, and nothing reconciles them.**
`test_staves_map_validation.py` already guards the EDITED path
(`sorted(set(patch.parts))` is banned in `server.py`); the initial PROPOSAL is
unguarded.

The only thing that stopped a regression on p3 was the unrelated
"works.json already has a map" refusal. **Luck, not a guard.** It will bite the
next row that has folds.

---

## 7. WHAT LANDED 2026-09-08 (all on main)

* `1c5f460b` — merged `claude/reengraved-step-4-step-3-105645` (17 commits,
  fast-forward) **and** `claude/rescue-midstaff-key-lilypond`, rescued work that
  existed on no branch and in no tree. The second CONFLICTED in
  `_lily_staff_block`'s single-voice loop — main's whole-rest fix against the
  branch's `\key` emission, orthogonal, both kept. Each half was mutated out and
  run RED to prove the resolution load-bearing. Suite 3,081 passed, 0 failed.
* `1cf44dbc` — Mahler p2's hand-confirmed `staves` map. **The scan gate is
  20/20 mapped**; "printed staves a human would have to read" is 0.
* `99f8d1dc` — the staves-map UI shows a printed staff the reference cannot
  represent, greyed and inert. Found by Sean counting the percussion on p2
  against the print: the page prints `Becken u. Gr.Trommel von einem geschlagen`
  between Grosse Trommel and Kleine Trommel and the list silently omitted it.
  The exclusion is right — the `.mxl` has five percussion parts against six
  printed percussion staves — but a silent omission is not.
* `09073260` — the normalised arm, 11 of 20 rows (nine lack a `..graft09`
  prediction on this machine). ⚠️ Its delta is STRUCTURAL CHARGE REMOVED, a
  different benchmark era, and per the redirect **it is not a goal to chase**.
  The control holds: Dvořák +0 on both rows.

---

## 8. OPERATIONAL

* `timeout` does not exist on this macOS. `| tail` **eats git exit codes** —
  verify a push by re-reading the remote ref, not by the push message.
* ⚠️ `git merge-tree <base> <a> <b>` reported **0 conflicts on a merge that
  genuinely conflicted** today. That three-arg form emits a diff, not conflict
  markers. Do not trust it; do the merge.
* `OMR_SURYA_KEEP_ALIVE=0` for unattended runs. **Never `pkill` the shared Surya
  daemon** — one machine has one server and `--serve` detaches to ppid 1.
* A fresh worktree needs four links (`.venv-omrned`, `.venv-surya`, the weights
  dir) plus `OMRNED_PYTHON`; three of the four failures are scan-side only.
  ⚠️ **None of that is needed for the staged pipeline** — it needs only the
  weights.
* `benchmarks/omr-hairpins-2026-09/score_export_arm.py` re-exports the 11 stored
  transcriptions without re-running the detector — the right tool if an export
  A/B is ever wanted again.
