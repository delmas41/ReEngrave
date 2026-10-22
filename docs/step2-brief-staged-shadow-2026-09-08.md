# Step 2 brief — test the staged pipeline, with the ledger as the instrument

Written 2026-09-08 by the cloud session that closed Step 1, for a session
running **on Sean's machine**. Step 2 cannot be done anywhere else: it needs
weights, fixtures, `.venv-omrned` and `library/`.

Read first: `docs/handoff-2026-09-08-next-steps.md` §2, §3 Step 2, §5, §6, then
`tools/omr/staged/ASSUMPTIONS.md` including its refusals table.

---

## What Step 2 is, and what it is NOT

**Not a headline score.** A **divergence list ranked by how many staves each
disagreement touches**, each traceable to the decision that caused it.
`Verdict.basis` carries the ancestor closure, so *"this note is B"* traces back
through the clef, the key and the notehead position.

⚠️ **Score it with the LEDGER, not OMR-NED.** Handoff §2 measured that
musicdiff amplification differs 6×–2× by error kind and that one changed
`<type>` scores ZERO on 10 of 20 files. **Direction** (did an A/B help) is still
sound; **attribution** (what kind of error is this) is void. Do not switch the
benchmark's detail level in response — that silently redefines every historical
scan figure.

⚠️ **Expect the staged pipeline to lose on some rows.** Standing rule A00: *a
worse score does not condemn the mechanism.* Order of enquiry: comparison
validity → is the metric charging for something other than correctness → is
there a downstream consumer → only then the mechanism.

---

## What already exists — do not rebuild it

`git log --all -S "<thing>" -- tools/omr/` before building anything.

- `OMR_ADJUDICATE=shadow` — **both paths, ONE gather, ONE process.** Read
  `tools/omr/staged/pipeline.py`'s docstring on why that is not a convenience:
  it removes the cached A/B (no second arm to cache), detector jitter (both
  paths consume the same detections, so jitter cancels exactly) and the
  worktree venv traps (the divergence table needs no venv and no scorer).
- `python3 -m tools.omr.staged score.pdf --pages 0-2 --weights <f>.pt --against legacy.omr.json`
  — the CLI already takes a legacy result.
- `pipeline.divergence(log, legacy)` — returns `{"counts", "rows"}` over
  `AGREE / DIFFER / NEW_ABSTENTION / NEW_DECISION / LEGACY_ONLY`.
- `benchmarks/omr-symbol-ledger-2026-09/run_ledger.py` and its siblings.

## ⚠️ CORRECTION (2026-09-08, same day): the legacy extractor DOES exist

**An earlier revision of this brief said `divergence()`'s `legacy` argument had
no caller and that writing it was most of Step 2. That was wrong** — found by
reading `tools/omr/staged/__main__.py` rather than trusting the earlier read.
`tools/omr/staged/legacy.py` (102 lines) implements `extract()` / `load()`, and
the CLI already calls it. It is careful: it mirrors `gather._system_local`
because the `staff_index` FIELD is page-wide and using it as a subject
coordinate would misfile every row of every system after the first, and it
deliberately excludes `group_index` because that field reaches the serialised
staff dict and **no reader in `export.py` consumes it** — delivered-and-unread,
a different failure from stranded-in-process, available as
`group_index_for_reference()` so the distinction is unmissable.

**The tree outranks this document. It outranked it within hours.**

## What actually needs doing

### 1. FIX FIRST — the CLI gathers TWICE, which breaks the instrument

`pipeline.run_staged` does prepare → gather → adjudicate. Then `__main__`, under
`--against`, calls `prepare_pages` → `gather` → `adjudicate` **a second time**
and computes the divergence table from THAT log. So `result["adjudication"]` and
`result["divergence"]` come from two independent passes.

⚠️ **This contradicts the design property the shadow docstring claims**: *"both
paths consume the same detections and jitter cancels exactly."* Detector jitter
is documented and real in this repo — a from-scratch rebuild of the hairpin fix
reproduced the categorical result and not the edit count, the same four boxes'
confidences moving between runs on byte-identical code. Two gathers reintroduce
exactly that. It also doubles the runtime.

Per the scope rule this is a **FIX NOW**, not a park: it corrupts the thing being
built. Reuse the single log.

### 2. A staged decision with NO legacy counterpart is INVISIBLE, not counted

`divergence()` iterates `legacy.items()`, so a quantity the old path never
concludes produces no row at all. `legacy.extract` covers **9** quantities —
`SYSTEM_STAFF_COUNT`, `SYSTEM_MEMBERSHIP`, `STAFF_ORDINAL`, `CLEF`,
`KEY_SIGNATURE`, `INSTRUMENT`, `SLOT_INDEX`, `MEASURE_PARTITION`, `METER` —
against **15 wired decisions**. The other six (`staff_group`, `group_symbol`,
`part_partition`, `glyph_owner`, `tuplet_ratio`, `duration`) are silently absent
from the table. The `LEGACY_ONLY` outcome covers the opposite direction only.
Decide deliberately: extend `extract`, or report the staged-only set separately
so it is *counted* rather than missing. **Do not let it stay invisible** — that
is the shape of every bug in this project's export-gap list.

### 3. Validate the join before trusting one row

`STAFF_ORDINAL` is the positive control: the staged path and the legacy path
must agree on it by construction, so a low AGREE rate there means the subject
keys do not line up and **every other row of the table is meaningless**. Print
it beside the counts.

### 4. Rank by staves touched

`divergence()` returns flat rows. The handoff asks for a list ordered by blast
radius, each row carrying its `Verdict.basis` ancestor closure.

---

## Read these columns before any score

⚠️ **`NEW_ABSTENTION` is a feature that scores as a loss.** musicdiff charges
an absent element, so a decision that correctly declines to guess makes the
pooled number worse. Precedent already in the tree: `OMR_SLOT_STITCH` is
structurally right, doubles its named bucket 715 → 1,632, and ships default-off
with the reason recorded.

⚠️ **`Verdict.basis` is what makes "two signals sharing an ancestor are ONE
signal" mechanically checkable.** Use it. A divergence corroborated by two
decisions that share an ancestor is corroborated by nothing.

⚠️ **A failed check is certain about the GROUP and silent about the MEMBER.**
Do not convict the cheapest member to change. `_reconcile_measure_to_meter` is
the tree's one correct implementation: it repairs only when the answer is
UNIQUE.

---

## Traps that have already cost this project time

- `git diff origin/main..HEAD` **lies** when main moves. Diff the merge base.
- **A ZERO IS A SUSPECT, NOT A RESULT.** Print a positive control beside every
  count. Step 1 hit this twice — a probe read `bbox_page` as `[x0,y0,x1,y1]`
  when it is `[x,y,w,h]`, so every median width was negative and nothing said
  so.
- **Run every new test RED before believing it green.** Step 1 had a test that
  passed under the exact mutation it was written to catch.
- `scan_eval` **caches by default**; give every arm its own `--tag=` (with the
  `=`). Shadow mode sidesteps this — one gather, no second arm.
- **NEVER `pkill -f`.** One machine has one shared Surya daemon and killing it
  has already destroyed another agent's multi-hour run. A `-f` pattern also
  matches your own shell. Use `OMR_SURYA_KEEP_ALIVE=0` for unattended work.
- The full suite is ~8m36s. Slow, not stuck. `-k staged` is ~5s.

## Scope rule

**FIX NOW** only if it corrupts the thing being built. **PARK** everything
else — and the systematic version of a fix is a PARK even when the instance is
a fix-now. A borderline case is a PARK, not a judgment call.

## Deliverable

`benchmarks/omr-staged-shadow-2026-09/FINDINGS.md`: the join and its positive
control, the ranked divergence list, the ledger comparison per family, every
RED-then-green demonstration, and — separately — the rows where the staged path
loses and why, with `NEW_ABSTENTION` reported apart from `DIFFER`.
