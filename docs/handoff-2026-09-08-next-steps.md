# Handoff — 2026-09-08: where the work stands and what to do next

Written at the close of the 2026-09-07 session. **Everything described here is
merged to `main` and pushed.** Read this before starting; then read the files it
points at, because **the tree outranks this document.**

---

## 1. What exists now that did not exist on the morning of 2026-09-07

### The staged pipeline — built, never scored

`tools/omr/staged/`, behind `OMR_ADJUDICATE` (`0` default / `shadow` / `1`).
**Four stages: GATHER → ADJUDICATE → GROUPS → EVALUATE.** 15 of 21 decisions
wired, 6 declared stubs that abstain with `NOT_IMPLEMENTED`; 5 of 6
consequences; **197 tests, ~5 s, no venv**. **No pre-existing pipeline file is
modified** — verified by diffing the branch's own commits against the merge
base, not by assertion.

Built on Sean's directive — *"Let's wire everything up the way we imagine it
will work best. Then test it."* **The testing half has not happened.** That is
deliberate, and it is the largest open item here.

⚠️ **Read `tools/omr/staged/ASSUMPTIONS.md` first.** It opens with STATE OF THE
BUILD, declares that it outranks the reader's memory, and carries an
**eleven-entry refusals table** — each entry cost someone a measurement.

### The symbol ledger — built, and it overturned how we read our own metric

`tools/omr/symbol_ledger.py` + `benchmarks/omr-symbol-ledger-2026-09/`.
Every truth symbol and every predicted symbol gets a row, addressed
**part / bar / beat**. Correspondence is proposed by four keys (`ord` — which
**abstains** rather than pairing i↔i across unequal counts — `onset`, `pitch`,
`joint`) and adjudicated; ⚠️ **an attribute is reported ONLY from a pairing
established by a key blind to it**. `uncorresponded` and `not_assessable` are
first-class outcomes that are **counted**, never absorbed.

```bash
python3 benchmarks/omr-symbol-ledger-2026-09/run_ledger.py        # the ledger
python3 benchmarks/omr-symbol-ledger-2026-09/mutation_matrix.py   # inject a known error
python3 benchmarks/omr-symbol-ledger-2026-09/compare_to_omrned.py # ledger vs musicdiff
python3 benchmarks/omr-symbol-ledger-2026-09/lookup.py            # one address
```

---

## 2. ⚠️ What changed about how to read every number in this repo

**Measured, not argued** — mutation matrix over 20 truth files, injecting a
*known* error and asking both instruments what it was:

| injected | ledger | musicdiff |
|---|--:|--:|
| one note's pitch | 1 | **4–12 (median 6)**, never named a pitch error |
| one written `<type>`, duration untouched | 1 | **ZERO on 10 of 20 files** |
| two parts swapped | 4–174 | **34–590**, mostly `wrong note` |

⚠️ **Amplification differs 6× to 2× by ERROR KIND, so musicdiff bucket totals
are not comparable to each other and cannot rank work.** Not "unreliable" —
invalid. ⚠️ **And musicdiff can score ZERO for a real duration error**: blind,
not merely imprecise.

**The mechanism**, measured separately
(`benchmarks/omr-wrongnote-decomposition-2026-09/FINDINGS.md`): without
`Voicing`, musicdiff pairs notes **by pitch** — it establishes *which note
corresponds to which* using the quantity under measurement. A wrong pitch
therefore destroys the correspondence and cannot be reported as a wrong pitch.
**This is circular in exactly the way this codebase refuses at three sites**
(`clef_correction.py:396` / `:566`, `dossier.py:434`, `score_layouts.py:682`).

On the real gate the **unnamed share is 80–96% on every one of 20 rows**,
including rows where the ledger corresponds 100% of symbols. **That mass is a
property of the metric, not of how badly the page was read.**

### The split to carry

| | verdict |
|---|---|
| **direction** — did a change help? | ⚠️ **STILL SOUND.** Both A/B arms are scored identically. Every historical A/B stands. |
| **attribution** — what kind of error is this? | ⚠️ **VOID.** And this is what has chosen the work. |

⚠️ **Do NOT switch the benchmark's detail level in response.** That silently
redefines every historical scan figure; the era-boundary rule applies. Use the
ledger as the second instrument instead.

---

## 3. The next several steps, in order, with why

### Step 1 — the tenth export gap, and the hole in the check built to catch them

**Cheapest and most certain thing on this list.**

⚠️ **`export_coverage.compare()` iterates a hand-written 19-name `VISIBLE` dict**
(`export_coverage.py:181`, used at `:279` and `:464`), so an element in **neither
`VISIBLE` nor `KNOWN_GAPS` fails nothing.** Found:

| element | truth (engraved / scan) | ours | detected? |
|---|--:|--:|---|
| `<ornaments>` | 12 / **131** | **0** | yes — `ornamentTrill` ×12, `ornamentMordent` ×1 |
| `tremolo` | 12 / **123** | **0** | — |
| `transpose` | — | **0** | — |

`grep -c ornaments tools/omr/export.py` is **0**. This is the same shape as the
nine forensic "detected then dropped" bugs.

⚠️ **Fix the CHECK as well as the gap.** A curated allow-list reintroduces
precisely the blindness the check exists to remove. **Derive the element set
from the truth files** and let `KNOWN_GAPS` carry the deliberate exclusions with
their reasons — that is the existing, working pattern, and
`test_the_inventory_has_no_stale_entries` already enforces the discipline.

### Step 2 — TEST the staged pipeline, with the ledger as the instrument

**The strategic step, and the reason the two builds were run in parallel: they
compose.** Shadow mode, both pipelines, one gather.

⚠️ **NOT a headline score.** A **divergence list ranked by how many staves each
disagreement touches**, each traceable to the decision that caused it —
`Verdict.basis` carries the ancestor closure, so *"this note is B"* traces back
through the clef, the key and the notehead position. ⚠️ **Score it with the
LEDGER, not with OMR-NED** — §2 is exactly why: a structural improvement can
raise OMR-NED while being correct, and OMR-NED cannot say which kind of thing
changed.

**Expect the staged pipeline to lose on some rows.** Standing rule A00: *a worse
score does not condemn the mechanism.* Order of enquiry: comparison validity →
is the metric charging for something other than correctness → is there a
downstream consumer → only then the mechanism.

### Step 3 — rests

⚠️⚠️ **476 rests carry a wrong duration against 235 notes — 55% of the duration
mass, and every duration analysis in this repo is note-level and therefore blind
to the larger half.** Nobody has looked. Unknown difficulty, genuinely new
territory, and the ledger can now attribute it.

### Step 4 — `entire staff` is three problems wearing one name

**8 of 20 rows have NO part correspondence — 51% of symbols.** Larger than
everything about notes, and upstream of all of it. The three causes, filed as
one bucket today:

1. `_stitch_slots` refusing (3 rows)
2. one-line percussion staves the detector never finds (3 rows)
3. a `works.json` arity convention where one lineup entry covers two printed
   staves (bach)

⚠️ **Any structural fix priced against that bucket is priced against a
mixture.** Separate the causes before attempting any of them. Related and
already measured: `OMR_SLOT_STITCH` and `OMR_CONDENSED_PARTS` (both default-off,
oracle ceiling −4,557 scan edits, and **the condensed COUNT cannot come from the
page** — it is a property of the encoding, proved).

### Step 5 — finish the staged stubs

Six remain. **Deliberately last**: breadth without a self-check is more
decisions nobody can verify. Steps 2–4 will also change what the stubs should
do.

---

## 4. What NOT to do

- ⚠️ **No probabilities on candidate members.** **Measured**: an uncalibrated
  probability is *worse* than none — it launders a guess into something that
  reads as evidence, and the estimator failed worst exactly where a consumer
  would set its bar (ECE 0.1277; top bin promised 0.989, delivered 0.692).
  Ordered relative support is enough.
- ⚠️ **Never erase staff lines for the detector.** Measured: 7–13 pooled reading
  points, noteheads to 0.774 on Mozart 41, and it *manufactures* beam confusion
  (YOLO beams 46 → 105, precision 0.783 → 0.343). **Erase for the CV consumer,
  bound the search for everyone else.**
- **Do not re-try beam union or replace-outright** — both measured, both
  recorded with numbers.
- **Do not retrofit every staged decision to emit candidate sets.** Only those
  natively set-shaped.
- **Do not change the benchmark's detail level** (§2).

---

## 5. Operational traps that cost time this session

- ⚠️ **`git diff origin/main..HEAD` LIES when main moves under you.** A branch
  appeared to have deleted 4,874 lines it never touched. **Diff against the
  merge base.** This caught two different agents hours apart, and the
  coordinator once.
- ⚠️ **A ZERO IS A SUSPECT, NOT A RESULT.** Three instances in one day,
  including `pgrep -c` (no such flag on macOS) printing an all-zero
  "no stray jobs" table. **Print a positive control beside every count.**
- ⚠️ **`scan_eval` CACHES BY DEFAULT** — two arms sharing a fixtures dir with an
  empty `--tag` reuse the first arm's transcriptions and the second never runs.
  It reports "identical on every bucket", which reads exactly like a clean
  no-regression result. **The tell is wall time, not the numbers.** Give every
  arm its own `--tag=` (it needs the `=`).
- ⚠️ **A fresh worktree has NEITHER venv, and the failures are ASYMMETRIC** —
  `orchestral_eval` can run clean while `scan_eval` dies or, worse, runs
  degraded with the Surya rung silently self-disabled. **Four** links are
  needed:

```bash
export OMRNED_PYTHON=/Users/seanjohnson/Desktop/ReEngrave/.venv-omrned/bin/python
ln -sfn /Users/seanjohnson/Desktop/ReEngrave/.venv-omrned .venv-omrned   # scan_eval IGNORES the env var
ln -sfn /Users/seanjohnson/Desktop/ReEngrave/.venv-surya  .venv-surya    # else it SELF-DISABLES
ln -sfn /Users/seanjohnson/Desktop/ReEngrave/tools/omr/training/data/weights \
        tools/omr/training/data/weights
```

- ⚠️ **NEVER `pkill -f llama-server`.** One machine has one shared Surya daemon;
  killing it has already destroyed another agent's multi-hour run. For
  unattended work use `OMR_SURYA_KEEP_ALIVE=0` so the run owns its own process.
- **`test_direction_text.py::TestReaderSelection::test_the_env_var_restricts_the_rungs`**
  passes in the main checkout and **fails in a worktree without `.venv-surya`**.
  Pre-existing, environment-dependent; not a main breakage, but it makes an
  agent think it broke something it did not.
- **The full suite takes ~8m36s** (2,900 passed, 8 skipped). Slow, not stuck.
  `-k staged` is ~5 s.

---

## 6. The standing rules, in one place

- **A worse score does not condemn the mechanism.** Enquire in this order:
  comparison validity → metric charging for non-correctness → downstream
  consumer → mechanism.
- **The tree outranks the ledger**, including this document.
  `git log --all -S "<thing>" -- tools/omr/` before building anything you
  suspect exists.
- **Two signals sharing an ancestor are ONE signal, not corroboration.** Now
  mechanically checkable via `Verdict.basis`.
- **A failed check is certain about the GROUP and silent about the MEMBER.** A
  violated constraint raises every member's suspicion; it does not convict the
  cheapest one to change.
- **Run a test RED before believing it is green.** Several tests this week were
  pinning the wrong rule and passing.
- **Fix only what corrupts the thing being built; park the rest** — and ⚠️ **the
  systematic version of a fix is a park even when the instance is a fix-now.**
  Keep the observation; park the fix.
