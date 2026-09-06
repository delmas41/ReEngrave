# Handoff — continuing the "Project progress dashboard" session

**Written 2026-09-06.** The session titled *Project progress dashboard*
(`local_1fe01edd-849e-4cfd-a3e3-8790a0c42729`, branch
`claude/project-progress-dashboard-3fb8e2`, model Fable 5) was **archived** after
its PR merged, which is why it disappeared from the session list. Its transcript
is intact but its process is stopped, so **the subagents it spawned are gone** —
they were in-process children, not peer sessions, and no handle to them survives.

Nothing is in flight. This file carries what that session knew.

---

## 1. Its work is all on main

Head of main is `7ea27a4b`. Four agent branches landed:

| branch | what it did |
|---|---|
| `claude/movement-reference-2026-09` | a page belongs to its MOVEMENT's orchestra, not the volume's |
| `claude/absent-instrument-veto-2026-09` | refuse a name the movement's lineup cannot contain |
| `claude/spans-veto-composition-2026-09` | the 2×2 that priced the two together |
| `claude/label-ladder-2026-09` | the free label rungs run as documented |

All four verified `IN MAIN`. `docs/progress-dashboard.html` regenerates clean —
`python3 -m tools.dashboard.generate --check` reports **OK: dashboard is current**.

**Three flags were flipped default-ON**, on Sean's explicit delegation of the call:

- `OMR_MOVEMENT_REFERENCE` + `OMR_ABSENT_INSTRUMENT_VETO` (`e3422c71`) — **together;
  the pairing is the decision, neither is right alone**
- `OMR_LABEL_MERGE_QUALITY` (`7ea27a4b`)

### The headline number

Whole work, Beethoven 5 / Litolff, 88 pages, 1616 staff records, 807 judgeable:

| | impossible | correct | wrong | unnamed |
|---|--:|--:|--:|--:|
| spans off / veto off | **91** | 750 | 57 | 0 |
| spans off / veto on | 0 | 750 | 50 | 7 refused |
| **spans on / veto off** | **0** | **756** | 51 | **0** |
| spans on / veto on | 0 | 756 | 51 | 0 |

Spans remove all 91 **by naming**, not by refusing. The veto adds nothing on top
*on this work* — but on a **truncated page set** spans alone go 44 → 57 impossible
(nine correct string names become Trombone), because a span lacking its movement's
opening page has no fully-labelled system and its unlabelled string slots land on
the document's Trombone slots by position. The veto cleans that up. **Which fix
carries the load depends on whether the run contains its movement's opening page,
and the case where spans fail is created by spans.** That is why they ship together.

⚠️ **n = 1 work.** Neither standing benchmark can price either flag, provably: all
20 scan-gate rows and every `orchestral_eval` excerpt are single-page, so the veto
is inert (attestation distance always 0) and spans take no boundary. **A second
whole work disagreeing is the evidence that would reverse the call**, and it does
not exist yet.

---

## 2. Open threads — TRIAGED 2026-09-06, and half the original list was wrong

⚠️ **This section was rewritten after every item was checked against the tree.**
Of the six threads first listed here, **three sent a session after work that is
already done, after a "fix" that would REGRESS a real work, or after a bug that
is not a bug** — and a fourth stated a pruning rule that is unsafe. The wrong
ones are kept below with what closed them, because *why a wrong thread looked
right* is the part that stops it being re-opened. CLAUDE.md's own name for this
failure shape is **fixed-then-kept-open-in-prose**, the documentation dual of
detected-then-dropped, and this section had four instances of it at once.

**The rule the triage ran on: check the TREE, not the ledger.** Every claim
below is `git merge-base --is-ancestor`, a `lookup()` call, a named test, or a
measured run. Nothing is carried on the strength of having been written down.

### Genuinely open

**A. The strings → Trombone residue on REDUCED systems.** *(Owned as of
2026-09-06 by the `sad-austin-7e16e7` session.)* The 7 residual errors on the
88-page run are **mis-slotting, not mis-naming**, which is the whole of where to
look. Scored 800/807: `Violin → Trombone` ×4, `Viola → Trombone` ×2,
`Timpani → Trombone` ×1 — **all on 12-staff systems, while the 17-staff finale
systems are 663/663**. Every wrong staff carries `instrument_source: label`: the
strings land on slots 9/10/11, the finale's trombone slots, and inherit the name
those slots were correctly given by the finale's own labels, because a name is
stamped per SLOT and written onto every staff of that slot on every page. The
tail is anchored right (Cello 15, Contrabass 16), so it is an **off-by-three in
the monotone DP over a reduced system**: 12 staves against a 17-slot reference
needs five deletions and it deleted 12/13/14 instead of 9/10/11. That is
`slots.align` / `assign_slots` — **not** `OMR_MOVEMENT_REFERENCE` and **not** the
absent-instrument veto, neither of which is in play in that artefact. Recorded in
`4858594e` so the diagnosis is not re-derived.

**B. The reader/window truncation that eats a label's leading characters.**
*(Owned by another agent as of 2026-09-06.)* `'larinetti in B.'` (Clarinetti),
`'mpani in C-G'` (Timpani), `'orni in F I II'` (Corni) — on LilyPond pages whose
text layer contains the names in full, with `'Flauto.'` and `'Oboi.'` reading
cleanly on the *same page*. ⚠️ **This is a reader/window fault and must not be
answered in the lexicon** — see the closed thread D below, which is where it was
mis-filed. Source:
[`benchmarks/omr-corpus-widening-2026-09/FINDINGS.md`](../benchmarks/omr-corpus-widening-2026-09/FINDINGS.md) §6.

**C. The veto's 18 refusals under spans are a pure unpriced cost.** *(Owned by
another agent as of 2026-09-06.)* Unpriced, **not** disproven — reduced systems
carry no full-lineup truth to adjudicate them against. Unchanged from the
original list; it is the one thread that survived triage intact.

### Claimed, and essentially done

**`Tp.` → Trumpet where it means Timpani.** Landed on
`claude/agitated-bassi-e3a0ab` as `5d6e76a8`, by the session that already owned
it (`local_52073ef5`, still running out of `project-progress-dashboard-3fb8e2`).
**Not yet in main** — coordinate before touching `contextual.py` around it.

⚠️ **The lexicon was never at fault, and that is the transferable part.**
`lookup('Tp.')` returns **Timpani at coverage 1.0** and always did. `Tp.` is
declared ambiguous, so the slot goes to `score_layouts.resolve_ambiguous_label`,
where the canonical layout puts the timpani AFTER the trombones while Litolff
prints it BETWEEN the trumpets and the trombones; the aligner is monotone, so
staff 8 took the second trumpet slot. The fix is entirely in
`contextual._resolve_ambiguous_labels`: **the prior may not move a staff onto an
instrument that a different alias on the same system already names** — `Tr.`
stands four staves up, and an engraver does not name one section with two
abbreviations on one system. Asymmetric by design: it refuses an OVERTURN and
never removes the lexicon's own answer, because `Tr. Bas.` on p.48 has BOTH its
candidates separately named on its system and a symmetric rule would have
nothing left to choose.

⚠️⚠️ **ITS HEADLINE FIGURE IS A NARROW-PAGE-SET CLAIM — do not quote it as a
whole-work number.** `24/29 → 26/29` and the finale system's `16/17 → 17/17` are
a same-tree A/B on `--pages 23,44`. The committed 88-page artefact
(`benchmarks/omr-absent-instrument-veto-2026-09/out/whole-report2.extract.json`)
**already** has slot 8 = Timpani and `ambiguous_labels_resolved = 1`: with a
whole work's worth of systems voting, the layout fit proposes Timpani or
abstains and the new guard is a **no-op there**. Recorded by its own author in
`4858594e`, which qualifies `5d6e76a8` one commit later. **This is the third time
page-set size has flipped an identity result** — the whole-work session measured
`--pages 0-2` collapsing 11/12 → 4/12, reproducible with `OMR_MAX_PAGES=5` — so
score any identity change on BOTH a narrow set and the 88-page extract.

### Closed — do NOT re-open (and what each one would have cost)

**D. `Basso.` → "Bass voice" — SETTLED DOWNSTREAM, and the implied lexicon fix
would REGRESS Handel.** This was listed as "a lexicon fault of the `Tr. Alt.` →
Alto family. Unfixed." It is **neither unfixed nor a lexicon fault**.

- It is settled by POSITION, in **`c0a80ae7`, which is in main**. The ambiguity
  is declared in `instruments.AMBIGUOUS_ALIASES`
  (`basso: ("Bass voice", "Contrabass")`), the slot is withheld from the roster
  refill, and `score_layouts.resolve_ambiguous_label` overturns it to Contrabass
  from score order. Verified reaching the consumer on an orchestral bottom staff:
  on `--pages 23,44` `ambiguous_labels_resolved` goes 2 → 1 and **the survivor is
  the `Basso.` → Contrabass overturn** — slot 16, `instrument_source:
  score_order_ambiguity`, on all three systems.
- ⚠️ **Why it still LOOKS broken, and this is the trap:** `lookup('Basso.')`
  returns `Bass voice` at coverage 1.0, and it is *supposed to*. The first entry
  in the ambiguity table is deliberately the lexicon's own answer, so that
  **nothing moves when the score-order prior has no opinion**. Reading the
  lexicon in isolation cannot tell you the fault is fixed; the fix is one layer
  down. `test_instruments.py::test_basso_is_ambiguous_rather_than_decided`
  asserts `lookup("Basso").instrument.name == "Bass voice"` **on purpose**.
- ⚠️⚠️ **Making Contrabass the first answer for `basso` inverts a real work.**
  In the margin-label corpus (`benchmarks/omr-lexicon-2026-09/labels.json`),
  `handel-messiah-leadsheet` prints **both words on ONE page, on ADJACENT
  staves**: `page_index` 254 has staff 8 `BASSO` directly above staff 9 `Bassi`,
  and 159 has the same pair at staves 10 and 11 — read there by *both* the text
  layer and Surya, so it is not an OCR artefact. Two different words on two
  different staves must name two different things, and the current first-answers
  (`basso → Bass voice`, `bassi → Contrabass`) are the only pairing that keeps
  them apart. **Collapsing `basso` onto Contrabass makes both staves of each of
  those pairs read Contrabass** — and it does so at exactly the place the
  score-order prior cannot help, since on a vocal score the singer legitimately
  sits above the basses.
- **Three tests would go red**, which is how this was meant to be caught:
  `test_instruments.py::test_basso_is_ambiguous_rather_than_decided`,
  `test_contextual_roster_ambiguity.py::test_the_ambiguity_is_in_the_lexicon_not_the_reading`
  (whose failure message reads *"`Basso` is no longer ambiguous in the lexicon"*),
  and `test_score_layouts.py`'s four `candidates_for_alias("basso")` cases.

**E. "Harvested lexicon gaps, concrete and unclaimed" — WRONG ON ALL FOUR.**
Not one of the four was a lexicon gap that wanted filling.

- `'in Es 3 4'` — **abstaining is the RIGHT answer, and two tests pin it.**
  Breitkopf prints the noun `Hörner` **once**, braced across the pair of horn
  staves, so the second staff's margin genuinely holds only a key and a number.
  Recovering it needs a contextual rule about what a brace means — a staff
  inheriting the noun from its brace-mate, with its own multi-edition
  measurement — not a wider lexicon.
  [`benchmarks/omr-lexicon-2026-09/FINDINGS.md`](../benchmarks/omr-lexicon-2026-09/FINDINGS.md):137
  says so; `test_staff_labels_surya.py:543` and
  `test_library_edition_instrumentation.py:105` both assert
  `lookup("in Es 3 4") is None`. **Adding it fails the suite.**
- `'orni in F I II'`, `'larinetti in A'`, `'mpani in C-G'` — **not lexicon gaps
  at all**, but the leading-character truncation now filed as open thread **B**
  above. `benchmarks/omr-corpus-widening-2026-09/FINDINGS.md`:619 says it in
  terms: *"That is a reader/window fault, not a lexicon one, and the two should
  not be confused: adding `larinetti` as an alias would paper over it."*
- **The one genuine lexicon gap in that harvest is already fixed.** It was
  `'Oboes'`, an English plural, deferred at the time because a new label changes
  the part–staff join and so needed its own measured run. `d59c35a8` (in main)
  closed it along with `'Cellos'`:
  `python3 -c "from tools.omr.instruments import lookup; print(lookup('Oboes'))"`
  → Oboe, coverage 1.0. ⚠️ `lookup` returns a `Match`, not an `Instrument` — it
  has no `.name`; print the whole object or reach `.instrument.name`.

**F. The "pre-existing test failure" is a WORKTREE SETUP FAULT, and the
diagnosis in this file was wrong in both halves.** It was recorded as *"a
cross-test env leak. Passes alone."*

- **It does not pass alone.** `pytest tools/omr/tests/test_direction_text.py`
  on its own gives `1 failed, 71 passed` in 1.3 s. So there is no leak to hunt:
  neither `pytest-randomly` nor `pytest-xdist` is installed, ordering is
  deterministic file order, and there is no seed.
- **The cause is the missing `.venv-surya` symlink** — the documented worktree
  trap in §3 below, in its third variant. `test_the_env_var_restricts_the_rungs`
  sets `OMR_DIRECTION_READERS=surya` and asserts `default_readers() == ["surya"]`,
  but `direction_text.default_readers` appends the Surya rung only if
  `staff_labels_surya.available()`, and `staff_labels_surya.VENV_DIR` is computed
  **worktree-relative from the module's own location**. No symlink → `available()`
  is False → the list is empty → the assertion fails.
- **Proven by A/B in one worktree, the symlink the only thing changed:**

  | | `test_direction_text.py` | full `tools/omr/tests` |
  |---|---|---|
  | no `.venv-surya` | **1 failed**, 71 passed | **1 failed**, 2343 passed, 16 skipped |
  | `ln -sfn …/ReEngrave/.venv-surya .venv-surya` | **72 passed**, 4 skipped | **0 failed, 2346 passed, 14 skipped** |

  Two tests move from skipped to passed and the failure goes, which is the
  signature of a capability arriving rather than of flakiness.
- ⚠️ **The residual skip gap is the OTHER symlinks, and it is worth naming
  because it is the same trap once more.** Even repaired, this tree reports
  **14 skipped against the 8** that `5d6e76a8` reports from a fully linked
  checkout — the run above still has no `tools/omr/training/data/weights` and no
  `.venv-omrned`. **A worktree missing its links runs a visibly smaller suite and
  says nothing about it**, so a green suite in a worktree is weaker evidence than
  a green suite in the main checkout. Compare skip counts, not just pass counts.
- ⚠️ **The residue worth fixing is small and real, and it is not what was
  described:** unlike its neighbours in the same file, this test carries no
  `@pytest.mark.skipif` guard, so it hard-asserts a *host capability*. It will
  fail on any machine with no Surya install, not only in a worktree. That is a
  one-line test-robustness fix, not an env-leak investigation.

**G. The worktree-pruning RULE stated here is unsafe — see §5.** *"Pruning ones
whose branches are already in main is safe"* is **false as written**, and the
survey that falsified it is now §5 of this file. Short version: six worktrees
whose branches are **fully merged into main** hold **8,556 hand-cut cell PNGs
between them** that exist nowhere else — `weight-generalization-publishers-548504`
alone holds 4,862, and the main checkout's `benchmarks/omr-labeling-grace1-2026-09/`
has no `cells/` directory at all. Merge state answers a question about COMMITS.
It says nothing about gitignored, non-regenerable work sitting beside them.

---

## 3. Traps this session paid for — read before running a benchmark

⚠️ **`scan_eval` CACHES, and a cached A/B fails SAFE-LOOKING.**
`run_pipeline` opens with `if pred.is_file() and raw.is_file() and not force:
return`, so two arms sharing a fixtures dir with an empty `--tag` reuse the first
arm's transcriptions and **the second arm never runs**. It reports *"identical on
every bucket and every row"* — exactly the clean no-regression result a
flag-guarded change hopes for. **The tell was wall time, minutes vs hours, not the
output.** Give every arm its own `--tag` (needs `=`, as `--tag=-myarm`) or its own
work-dir. Contrapositive: arms returning *different* numbers did both genuinely run.

⚠️ **A worktree needs FOUR symlinks, and three fail on the scan side only** — so a
worktree that runs `orchestral_eval` cleanly proves nothing about `scan_eval`.
`scan_eval` ignores `OMRNED_PYTHON` and resolves `.venv-omrned` worktree-relative.

⚠️ **The Surya keep-alive server is SHARED.** `pkill -f llama-server` destroyed
another agent's multi-hour run (`395e2193`, committed against itself). Use
`--stop`, or `OMR_SURYA_KEEP_ALIVE=0` for an unattended run.

⚠️ **Establish a null at three levels before believing it.** The label-ladder arms
came back flat on both pools and the agent proved the flag had *run* (transcriptions
differ 20/20 and 11/11), that exports differ on 5 files, and that the entire export
difference is `<part-name>` — which musicdiff does not score. **The pools are blind
to the channel, not to the change.** Measured on that channel directly: engraved
part names **67 → 71 correct, placeholders 2 → 0, 4 of 4 better, 0 worse**.

---

## 4. The correction worth carrying

A PDF text layer is **not** more reliable than OCR — on a scan it *is* OCR,
someone else's, run once, years ago, with no ability to reconsider. Beethoven 5 p.1
staff 8 prints `Violino II.`; the text layer encodes `Yiolino II.`; the lexicon
rescues it via the `Y`→`V` fold, which is tagged `low` **by construction**; and
`slots.MIN_LABEL_CONFIDENCE` and `roster.py:219` both drop `low`. **Read correctly,
carried correctly, discarded at the join** — while the reader that would have got it
right was never asked, because a cost control meant for the *paid* rung was gating a
*free* one, against that module's own documented promise.

---

## 5. The worktrees — surveyed 2026-09-06, and NOTHING was removed

Full table, per-row evidence and method:
[`docs/worktree-prune-survey-2026-09-06.md`](worktree-prune-survey-2026-09-06.md).

**108 linked worktrees, not ~25.** Verdicts: **4 IN USE, 24 NEEDS A LOOK,
80 SAFE.**

⚠️⚠️ **The rule §2 originally stated — "pruning ones whose branches are already
in main is safe" — is FALSE, and following it would have destroyed 8,556
hand-cut cell PNGs.** Six worktrees are fully merged into main *and* hold
`benchmarks/**/cells/` images that exist in no other tree on this machine;
`weight-generalization-publishers-548504` alone holds **4,862**, and
`benchmarks/omr-labeling-grace1-2026-09/` in the main checkout has **no `cells/`
directory at all** — while that batch's `cells.json`, `detections/` and
`verdicts/` are all correctly committed, which is exactly why the branch reads as
merged.

**Merge state is a fact about COMMITS.** `cells/` is gitignored by design, so it
is invisible to every merge check, and a green `git branch --merged` says nothing
about it. `recut_cells.py` *may* recover them, but it aborts on a frame mismatch
and phase 1 has drifted — of v8's 122 source PNGs, 11 survived. **Copy or re-cut
`cells/` out before removing any of those six, and verify the re-cut rather than
assuming it.**

⚠️ **Three worktrees hold a `git worktree` lock owned by a pid that `ps`
confirmed ALIVE** (61864 — sibling agents), and a fourth,
`project-progress-dashboard-3fb8e2`, is held by the running `Tp.` session and
carries two commits not in main. ⚠️ And `git status` **cannot** be run inside
another worktree from an isolated agent, so ordinary uncommitted edits are
UNVERIFIED on every row — check each one by hand before removing it.

**Sean decides what goes. Nothing in this survey removed anything, per
`395e2193`: an orphan you cannot identify is safer left alive.**
