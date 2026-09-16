# A measure is numbered by the DOCUMENT's bar sequence, not by its part's own count

**2026-09-15**, no flag. Item 3 of
[docs/handoff-2026-09-11-phase-2-opened.md](../../docs/handoff-2026-09-11-phase-2-opened.md)
§8 — the middle of three repairs to the part-join defect, and deliberately
**not** the loud one.

---

## 1. REACH, first

Litolff Beethoven 5 mvt 1, pdf p1-4, the shared record `beethoven5-p1-p4.record.json`
(md5 `d3620ba9…`, matched before either arm was read) — 12 parts, 7 printed
systems, 75 staff-systems, 1,183 measures.

| | |
|---|--:|
| parts whose numbering changes | **3** (P9, P10, P11) |
| `<measure>` elements renumbered | **90 of 1,183 (7.6%)**, every one by **+18** |
| printed systems carrying two number ranges | **2 of 7 → 0 of 7** |

The +18 is the width of **p3/s1**, the 8-stave system where the plate suppresses
Oboi, Trombe and Timpani. P9-P11 go `1…93` → `1…111 with 64-81 absent`; P1-P8
and P12 are untouched.

⚠️ **This is a RELABELLING, not a reordering, and the control says so**:
ordinal-for-ordinal the 1,183 measures are **identical, 0 different**.

## 2. The music is provably unmoved — and the control provably fails

One record, two trees, export-stage re-export, so the transcribe half carries no
detector jitter. The two files are **byte-identical outside `<measure number=…>`**
and all 19 element families are identical to the unit (note 2460, rest 842,
pitch 1618, tie/tied 179, slur 80, dynamics 174, articulations 47, fermata 41,
words 6, backup 24…).

**A byte-identity control is not a result on its own** — this repo has a recorded
case of one passing vacuously because the code under test never ran. So the arm
was mutation-tested:

| arm | result |
|---|---|
| drop a note | exit 1 (`note 2460→2459`) |
| alter a pitch | exit 1 |
| drop a slur | exit 1 (`slur 80→79`) |
| **the same file twice** | **exit 1 — "no measure number moved: the instrument is DEAD"** |
| the real pair | exit 0 |

That fourth arm is the guard against the vacuous case.

## 3. ⚠️⚠️ VEROVIO IS SILENT ON THE WHOLE FILE — the brief was wrong about the witness

The handoff records Verovio saying `Mismatching measure number 87` and cites it
as the thing that found the defect. **The whole-file render is silent in BOTH
arms — 0 such lines before, 0 after** (15 warnings either side, all pre-existing
*"ties left open"*), and the committed cleanup artefact renders clean too.

**The warning is not a property of the file. It is a property of an OPERATION on
it.** Verovio lays a full score out along each part's own measure *order* and
never reconciles two parts' numbers. Only `build_sidebyside.py`'s question —
*take one printed system's bars, BY NUMBER, from every part* — can see it.
Reproduced exactly: on the **before** file, requesting p4/s0 the way the
side-by-side does (`P1-P8 = 82:96`, `P9-P11 = 64:78`) gives **30
`[Error] Mismatching measure number` lines**; after the fix the same system needs
**one** window (`82:96`) for all 11 parts and Verovio is **silent**.

⚠️⚠️ **And the single-window route on the BEFORE file is the dangerous one: it
raises nothing and silently returns twelve bars of p4/s1 for P9-P11.** A reader
who simplified the workaround would have got a clean render of the wrong music.

music21 parses both; `last measure numbers [16, 93, 111] → [16, 111]`, notes 1127
in both.

## 4. Two further witnesses, already in the tree, neither built for this

- **`export_arm.py`'s map-vs-file control fired unprompted — 108 `(part, measure)`
  problems** — because the system map held a **second copy** of the numbering
  rule. It now calls `system_bar_starts` and reports `1183 pairs, all present
  exactly once`. *The value existed and a second consumer disagreed with it.*
- **`build_sheet.py`'s `out_of_sync`** (30 attention points per system, computed
  from `first_measure` alone): **2 of 7 → 0 of 7**.

## 5. ⚠️⚠️ THE REFUTATION THAT OUTRANKS THE FIX: the legacy exporter already does this

`tools/omr/export.py` builds `starts[]` as a cumulative `max(len(measures))` per
system and takes `starts[sys_i]` per slot, with a comment at `export.py:3871`
stating the tacet case **verbatim**:

> *"A slot need not appear in every system (a suppressed tacet staff), so each
> staff takes ITS OWN system's measure start rather than the n-th one."*

**So this is not a new rule — it is the staged exporter re-converging on a
position the legacy one already paid for**, the `_rest_ruling` /
`_pair_dots_to_targets` shape again. Nothing in the legacy exporter needed
repair and none was made. The two cannot share code (page dicts against
`StaffRun`s), so the rule is RESTATED with cross-references — the `_meter_dict`
precedent — rather than duplicated silently.

## 6. ⚠️ A SELF-INFLICTED CORRECTION TO THIS REPO'S OWN OPERATIONAL RECORD

CLAUDE.md files *"a mutation battery `git checkout`s the files it mutates"* as a
**sibling-session** collision. **It is also SELF-destructive.** The battery was
run over an uncommitted change; arm 1's cleanup restored `export.py` from the
index and **the change under test vanished** — noticed only because every later
arm reported `anchor occurs 0 times`. `mutate.py` now **refuses to start on a
dirty tree, with no `--force`**. The re-applied change reproduces the identical
file (md5 `758d087f…` both times).

**Battery: 10 arms, all red, positive control green.** The first run had two
survivors and both were worth having — one an **equivalent mutant of the arm's
own writing** (replaced, not tested around), one a **real gap nothing else
found**: `width` is filled by walking the parts, so insertion order is `0, 2, 1`
whenever the *first* part is the suppressed one, and only the `sorted` saves it.
Closed by a test that asserts the fixture REACHES the hazard before asserting the
answer.

## 7. What is NOT established

- **Accuracy.** This says the numbers are CONSISTENT ACROSS PARTS; it does not
  say bar 82 is printed bar 82. No bar was checked against the print.
- **The join, which is the bigger defect**, still puts **12 of 75 staff-systems
  on the wrong instrument**. ⚠️ A correct join gives **111 / 93 / 78 / 31**, so
  **the eight parts reading 111 read 111 BECAUSE of the graft.**
- **Padding** — deliberately untouched. Padding first would have made the numbers
  line up while leaving the grafted notes in place, and a graft counted as a note
  error ranks the work into the wrong module.
- **OMR-NED** — musicdiff pairs by pitch and would not see a renumbering.
- Whether Verovio silently mis-aligns a full-score render of the before file.
- **n = 1 document, 1 publisher, 4 pages of ~16**, on the *low-res bitonal*
  pessimistic end of the corpus.

## 8. One item left for whoever owns the artefact

`build_sidebyside.py` still renumbers each slice `1..n`. That workaround is now
unnecessary **for the numbering defect**, but its own comment defends it on
separate ordinal-alignment grounds, so it was left alone.

## 9. Reproduce

```bash
PYTHONPATH=. python3 benchmarks/omr-measure-numbering-2026-09/numbering_arm.py
PYTHONPATH=. python3 benchmarks/omr-measure-numbering-2026-09/probe/content_identity.py
PYTHONPATH=. python3 benchmarks/omr-measure-numbering-2026-09/mutate.py   # clean tree required
PYTHONPATH=. python3 -m pytest tools/omr/tests/test_staged_export.py -q
```

Suite at the time of writing: **3,849 passed / 1 failed / 19 skipped**. The
failure is `test_direction_text::TestReaderSelection::test_the_env_var_restricts_the_rungs`
and is **environmental and pre-existing** — the documented worktree `.venv-surya`
trap, which CLAUDE.md records for `orchestral_eval` / `scan_eval` but **not as
something that turns a unit test red**. Proved both ways: symlink the venv in →
`2 passed`; remove it → `1 failed`. Neither file is in this diff.
`health --check`, `inventory --check`, `gather_coverage` and
`export_coverage --all` all exit 0.
