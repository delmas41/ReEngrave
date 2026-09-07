# Four faults in `page_normalise`, and the controls that had to hold

2026-09-06. Branch `claude/page-normalise-fixes-2026-09-06`, off `687d1c4e`.
**Nothing here changes a default, and `works.json` was NOT written** — see §6,
which is the one requirement of the commission I declined and why.

```bash
python3 -m pytest tools/omr/tests/test_scan_eval_structural.py       # 17 tests
python3 benchmarks/omr-page-normalise-fixes-2026-09/probe_derived_truth_unmoved.py
python3 benchmarks/omr-page-normalise-fixes-2026-09/probe_merge_unblocked.py
python3 benchmarks/omr-page-normalise-fixes-2026-09/probe_coverage_after.py
python3 benchmarks/omr-page-normalise-fixes-2026-09/controls.py      # ~40 min
python3 benchmarks/omr-headline-validity-2026-09/probe_engraved_normalise_noop.py
```

The faults were diagnosed, with the exact reproducing bar, by
`benchmarks/omr-staves-map-completion-2026-09/FINDINGS.md` §4, which patched
them in a probe-only module and left the shipped one alone. This is the fix.

⚠️ **The letters A and B are swapped between that benchmark's FINDINGS and its
own `normalise_patched.py`** (the module calls the `_tokens` fault B and the
`_voice_merge` fault A). This document uses the FINDINGS' lettering throughout:
**A is `_tokens`, B is `_voice_merge`.**

---

## 1. What each fault was

`page_normalise` builds a DERIVED GROUND TRUTH, so its failure modes are not
symmetric: a crash is the *good* kind, because it is visible. Three of these
four crash. The fourth does not, and it is the one worth reading.

Two blocked a merge (A and B, named as the commission names them); the other
two are latent in any edition that condenses PERCUSSION, and both are fixed
here because the same change covers them — with the caveat, recorded below,
that nothing in the corpus can price either.

### FAULT A — `_tokens` sorted a heterogeneous key (crash)

```python
        if isinstance(el, note.Rest):
            body: Any = "R"                     # a str …
        elif isinstance(el, chord.Chord):
            body = tuple(sorted(...))           # … next to a tuple
    return tuple(sorted(out))                   # TypeError when (off,dur) ties
```

The key is `(offset, duration, body)` and it is **sorted**, so two events that
share an offset and a duration fall through to comparing their bodies —
`TypeError: '<' not supported between instances of 'str' and 'tuple'`.

It needs both kinds in ONE measure, which takes a source part whose bar already
carries two `Voice`s with one resting where the other sounds. Mahler 5's `Vier
Trompeten in B.` writes exactly that: **p3 mm 12 and 14, p4 mm 17-19**. No
already-mapped row contains the shape, which is why the fifteen rows that
already carry a map never found it.

**Fix:** a rest's body is `("R",)`. Every body is now a tuple of strings.
⚠️ It reorders nothing that previously sorted — a `str` and a `tuple` never
compared successfully — and it shifts every measure's key identically, so
`classify`'s equality tests are unmoved. That is the argument for why the fix
cannot move an existing row, and §3 measures it rather than trusting it.

### FAULT B — `_voice_merge` inserted a copy still pointing at its old parent (crash)

```python
            v.insert(el.getOffsetInHierarchy(m), copy.deepcopy(el))
```

⚠️ **The offset was never the problem, and the diagnosis matters for the fix.**
`getOffsetInHierarchy(m)` is measured against the source MEASURE and the new
`Voice` goes in at 0.0 of the new measure, so a nested-voice event keeps the
position it had on the page — asserted directly by the regression test.

What is wrong is the COPY. Instrumented on the reproducing bar
(Mahler 5 p3 `Sechs Hörner in F.` m15):

```
m15 <music21.note.Note E>            copy.activeSite=None                       -> fine
m15 <music21.chord.Chord E4 G#4 B4>  copy.activeSite=<Measure 15>  sites={None}  -> KeyError
```

`copy.deepcopy` of a **Chord** returns an object whose `activeSite` still points
at the source measure while its own `sites` dict does not hold it. `Stream.insert`
runs an is-this-still-sorted check that calls `sortTuple()`, which does
`self.sites.siteDict[id(self.activeSite)]` — and raises a bare `KeyError: <id>`.
A `Note` copy comes back with `activeSite` None and never fires, which is why
the fault looked intermittent: p5 m31 is the same musical shape and does not
raise.

**Fix:** `_detached(el)` — deepcopy, then clear the stale pointer; `insert` sets
the real one immediately afterwards. Used at both copy sites in `_voice_merge`.
The whole-measure copies elsewhere in the module were checked and are NOT
affected: a deepcopied `Measure` comes back with its site present
(`copy has site? True`), so they were left alone.

### FAULTS C and D — an `Unpitched` note is neither `Note` nor `Chord` (one crash, one silence)

`notesAndRests` also yields `music21.note.Unpitched`, which is what every
one-line percussion part parses to.

* **C** — `_tokens`'s `else` branch reached for `el.pitch`, which an `Unpitched`
  does not have.
* **D** — `_is_silent` tested `isinstance(el, (note.Note, chord.Chord))`, so a
  bar of percussion notes read as SILENT. A condensed percussion staff would
  take the `silent_all` branch and **discard a player's notes without a word**.

⚠️ **D is the dangerous one and it is the quiet one.** It does not raise, it does
not warn, and what it produces is a smaller truth — which is the exact shape of
the two bugs this module has already been bitten by (dropped spanners; a dropped
part), both of which made the score BETTER.

**Fix:** `_is_silent` tests `note.NotRest` (which is `Note`, `Chord` and
`Unpitched` and not `Rest`); `_tokens` gives an `Unpitched` the staff position
it is DRAWN at as its body; and — the third piece, without which fixing D would
have created a NEW silent loss — a bar carrying an `Unpitched` takes the VOICE
path rather than the chord path, because a `Chord` holds `Pitch`es and the
"add what the other part plays" loop would add nothing at all
(`Unpitched.pitches` is `()`). The voice path copies whole events and is
lossless.

⚠️ **Both are unmeasurable today, and that is stated rather than papered over.**
Censused over all 20 scan-gate truths: 17 rows carry no `Unpitched` at all; the
three that do (Mahler p3/p4/p5 — `Becken`, `Grosse Trommel`, `Kleine Trommel`,
`Tamtam`) carry it only on parts that stand ALONE on their own printed staff, so
`classify` is never called on them. Two of the candidate maps DO fold percussion
parts onto a condensed staff (p3 folds 22, 25 and 26 onto `Tuba`; p4 folds 26
onto `Pauken`) — and those parts are tacet in the window, i.e. rests only, so the
`Unpitched` branch is still not reached. **The fix therefore has no price and
no benchmark can guard it; `test_a_condensed_percussion_staff_keeps_both_players`
is the only thing that does.**

---

## 2. The tests, verified RED

`tools/omr/tests/test_scan_eval_structural.py`,
`TestPageNormaliseOnOrchestralShapesTheGateHadNotSeen`. Every fixture is
**written to MusicXML and re-parsed**, not merged in memory — built in memory,
Fault B does not fire at all (the copies come back with no `activeSite`), so a
convenient in-memory fixture would have been a test that passes either way.

Run with `benchmarks/omr-scan-e2e-2026-09/page_normalise.py` stashed:

| test | fails with |
|---|---|
| `test_a_rest_and_a_note_at_one_offset_do_not_raise` | `TypeError: '<' not supported between instances of 'str' and 'tuple'` |
| `test_every_token_body_is_a_tuple_so_the_key_can_always_sort` | `assert False` |
| `test_unaligned_divisi_becomes_stacked_voices_and_keeps_every_event` | `KeyError: 4428515312` |
| `test_a_condensed_percussion_staff_keeps_both_players` | `assert 1 is None` — the bar was classed `silent_all` |

4 failed. With the fix, the file is 17 passed.

---

## 3. The controls — the ones that CANNOT improve

⚠️ **A bug in this module does not make a number worse; it makes every number
better while being wrong.** So the fix is judged by arms whose only acceptable
answer is zero.

### 3a. The strongest one: the derived truth did not move, byte for byte

`probe_derived_truth_unmoved.py` loads the PRE-FIX module straight out of git
(no stash, no branch switch — both revisions live in one process) and has both
write a page-normalised truth for every row that carries a map today.

**20 rows: 18 identical, 2 NEWLY POSSIBLE (Mahler p3 and p4 — the two that
previously raised), 0 moved.** Including all three Dvořák rows, all eight
Beethoven rows, all four Brahms rows, Mahler p2, Mahler p5 and Bach.

A score can only move if the file it is scored against moved, so this is a
stronger statement than an edit count — and it has no noise floor, where the
20-row gate has one of roughly ±6 edits.

⚠️ **THE SELF-CONTROL FIRED, AND WITHOUT IT THIS PROBE WOULD HAVE REPORTED A
CATASTROPHE.** music21's MusicXML writer mints a **fresh random
`<score-instrument id="I…">` on every write**, so the fixed module writing
Dvořák p5 twice differs from itself on 92 lines. The first run of this probe
reported all 20 rows MOVED. The ids are canonicalised away and the
fixed-vs-fixed arm must come back identical before the cross arm is read at all;
it is recorded per row as `writer_is_deterministic`.

### 3b. The engraved pool is an exact no-op

`benchmarks/omr-headline-validity-2026-09/probe_engraved_normalise_noop.py`,
identity map, same predictions scored against both truths:

| work | raw ed | norm ed | delta |
|---|--:|--:|--:|
| beethoven-sym5-mvt1 | 54 | 54 | +0 |
| brahms-sym1-mvt1 | 518 | 518 | +0 |
| mahler-sym5-mvt1 | 40 | 40 | +0 |
| mozart-sym40-mvt1 | 218 | 218 | +0 |
| mozart-sym41-mvt1 | 315 | 315 | +0 |
| beethoven-sym3-mvt1 | 230 | 230 | +0 |
| brahms-sym4-mvt1 | 401 | 401 | +0 |
| dvorak-sym9-mvt4 | 239 | 239 | +0 |
| tchaikovsky-sym4-mvt2 | 60 | 60 | +0 |
| tchaikovsky-sym6-mvt2 | 266 | 266 | +0 |
| bruckner-sym5-mvt1 | 191 | 191 | +0 |

**11 of 11, 0 edits moved. NO-OP.**

### 3c. Dvořák, and every already-mapped scan row, scored end to end

`controls.py`, one musicdiff batch, one tree, the canonical run's own
predictions (`.reconciliation`, the artefacts behind pooled 0.8444). Nothing is
re-transcribed, so this measures the TRANSFORM and only the transform.
`d ES` is `entire staff insert/delete`.

```
row                                 raw ed  norm ed    d ed    d ES  arm
------------------------------------------------------------------------
dvorak-sym9-mvt1-405834-p5             661      661      +0      +0  identity control
dvorak-sym9-mvt1-405834-p6            2586     2586      +0      +0  identity control
dvorak-sym9-mvt1-405834-p7            5698     5698      +0      +0  identity control
beethoven-sym5-mvt1-575951-p1         1358      700    -658    -513  already-mapped
beethoven-sym5-mvt1-575951-p2         4407     1941   -2466   -1551  already-mapped
beethoven-sym5-mvt1-575951-p3         3172     1763   -1409    +440  already-mapped
beethoven-sym5-mvt1-575951-p4         4714     2579   -2135   -1377  already-mapped
beethoven-sym5-mvt1-984073-p1         1283      658    -625    -513  already-mapped
beethoven-sym5-mvt1-984073-p2         4341     2386   -1955   -1551  already-mapped
beethoven-sym5-mvt1-984073-p3         3034     1903   -1131    +397  already-mapped
beethoven-sym5-mvt1-984073-p4         4679     2706   -1973   -1377  already-mapped
brahms-sym1-mvt1-317803-p1            3431     1737   -1694   -1001  already-mapped
brahms-sym1-mvt1-317803-p2            6562     5529   -1033    +507  already-mapped
brahms-sym1-mvt1-317803-p3            4573     2953   -1620   -1292  already-mapped
brahms-sym1-mvt1-317803-p4            7012     3842   -3170   -1860  already-mapped
mahler-sym5-mvt1-local-p2             1118      702    -416    -549  candidate map
mahler-sym5-mvt1-local-p3             3075     2159    -916   -1467  candidate map
mahler-sym5-mvt1-local-p4             4149     3209    -940   -1403  candidate map
mahler-sym5-mvt1-local-p5             2967     2300    -667    -716  candidate map
bach-brandenburg3-mvt1-468678-p1      6148     6148      +0      +0  candidate map
```

**CONTROL: all three Dvořák rows move by exactly 0**, and so does Bach — 15
parts into 15 printed staves, and 11 into 11, so the transform is asked to
change nothing and does not.

**And the four Mahler rows reproduce the completion benchmark's own priced
figures TO THE EDIT** — 702 / 2159 / 3209 / 2300 against the probe-only
monkeypatch's 702 / 2159 / 3209 / 2300. The fix in the module and the patch
beside it are the same transform, so that benchmark's pricing carries over
unchanged and does not need re-running.

⚠️ The `already-mapped` rows are not controls — they condense, so their delta is
supposed to be large — and they are here because §3a has already shown their
derived truth is byte-identical across the fix, which makes these numbers a
property of the map rather than of anything that changed today. ⚠️ Three of them
show `entire staff` going UP while total edits go down. That is NOT MEASURED
HERE and the op lists were not opened; the reading consistent with the recorded
corollary — the bucket names the staves the alignment SHED, never the staves
that were missed — is that merging reference parts can make the truth shorter
than the prediction, at which point the alignment sheds OUR parts instead of the
truth's. It predates this fix either way: §3a shows those three rows' derived
truths are byte-identical across it.

---

## 4. The merge is unblocked

`probe_merge_unblocked.py` asks the reviewed tool — `merge_additions.check_row`,
unmodified — with a SIMULATED `done` additions row per candidate, and writes
nothing:

```
  OK   mahler-sym5-mvt1-local-p2           21 entries,  38 parts named  38 -> 21
  OK   mahler-sym5-mvt1-local-p3           15 entries,  38 parts named  38 -> 15
  OK   mahler-sym5-mvt1-local-p4           21 entries,  38 parts named  38 -> 21
  OK   mahler-sym5-mvt1-local-p5           21 entries,  38 parts named  38 -> 21
  OK   bach-brandenburg3-mvt1-468678-p1    11 entries,  11 parts named  11 -> 11
```

Against the shipped module p3 refused with `KeyError` and p4 with `TypeError`
(`benchmarks/omr-staves-map-completion-2026-09/merge-path.json`). **Every
reference part is accounted for on every row** — 38 of 38, and 11 of 11 for
Bach — which is `merge_additions`' own check, not mine.

⚠️ **A worktree trap worth recording.** `merge_additions` resolves its imports
through `build_cache.MAIN`, a hard-coded path to the MAIN CHECKOUT — so a naive
run of it from a worktree proves the map against **main's** `page_normalise`,
not the one under test, and would have reported this fix as working (or not) on
the wrong file. The probe binds this tree's module first and asserts on
`page_normalise.__file__`.

---

## 5. The coverage split, before and after

`probe_coverage_after.py`, on the canonical `results-reconciliation.json`:

| | today | after the four Mahler rows |
|---|--:|--:|
| rows with a hand-read map | 15 of 20 | **19 of 20** |
| `entire staff`, attributable | 11,927 | **17,234** |
| `entire staff`, cause UNKNOWN | **5,593** | **286** |
| printed staves a human would read | 89 | 24 |

The 286 that remain are Bach's, and they are not a labelling gap: the reference
encodes the Cembalo as ONE part where the page prints a GRAND STAFF, so our 12
predicted parts meet 11 truth parts and the whole charge is one `delpart` on a
part we read correctly. The map idiom cannot express a split, so no `staves` map
reaches it (completion FINDINGS §6).

⚠️ **MERGING A MAP CHANGES NO HEADLINE FIGURE.** The pooled 20-row 0.8444 is
untouched by every row of this table; what changes is what can be SAID about it.
And any edits a normalised truth removes are **STRUCTURAL CHARGE REMOVED — the
metric ceasing to bill a printing convention — never the pipeline improving**;
a normalised figure is a different benchmark era and may not be differenced
against 0.8444 in either direction (`page_normalise` rule 5).

---

## 6. ⚠️ `works.json` WAS NOT WRITTEN, and that was deliberate

The commission asked for `merge_additions.py --write` on the four Mahler rows. I
did not run it, and this is the reasoning rather than an omission:

1. **The maps are not confirmed.** `works.staves-additions-completion.json` has
   all five rows at `status: "in_progress"`. `merge_additions.check_row` refuses
   anything that is not `done`, so the only way to write them today is to edit
   that status myself — which is recording a human confirmation that nobody
   made, into a file whose entire value is that it is hand-verified.
2. **A premature write would LOCK SEAN OUT of his own reading.**
   `merge_additions` refuses to overwrite a row that already carries a `staves`
   map — deliberately, "never overwrite someone else's hand reading". So if I
   write the transcribed map now and the 57-slot pass then corrects any slot,
   the corrected map cannot be merged by the reviewed tool at all. The cost of
   waiting is nothing; the cost of writing early is a blocked confirmation pass.

**The block this task was about is gone** (§4), which is what the confirmation
pass needed. After it marks the rows `done`:

```bash
python3 benchmarks/omr-staves-map-2026-09/merge_additions.py \
    --additions benchmarks/omr-scan-e2e-2026-09/works.staves-additions-completion.json
python3 benchmarks/omr-staves-map-2026-09/merge_additions.py \
    --additions benchmarks/omr-scan-e2e-2026-09/works.staves-additions-completion.json --write
python3 benchmarks/omr-headline-validity-2026-09/probe_map_coverage_cost.py
python3 benchmarks/omr-headline-validity-2026-09/normalised_arm.py
```

⚠️ Note the `--additions` flag: `merge_additions` defaults to
`works.staves-additions.json`, which is the FIRST pass's file and holds the five
rows already merged. Running it bare would report "already carries a map" on all
of them and touch nothing — a no-op that reads like a refusal.

---

## 7. What was verified, and what was not

**Verified.** Both crashes reproduced on the exact bars named by the completion
findings, and reproduced again on written-and-reparsed synthetic fixtures; all
four regression tests run RED with the module stashed and green with it;
the derived truth of every already-mappable row byte-identical across the fix,
with a self-control proving the comparison is meaningful; the engraved pool an
exact no-op on 11 of 11 works; the `Unpitched` census over all 20 scan-gate
truths and over every condensed entry of every candidate map; `merge_additions`
accepting all five rows through its own validation; the full suite.

**Not verified.** No pooled scan figure was re-measured and no default changed.
`works.json` is untouched, so §5's "after" column is a PROJECTION of an
accounting, not a measurement of a merged file — though the accounting is exact
arithmetic on the baseline's own per-row counts, and merging cannot move the
pooled figure at all. Faults C and D are guarded only by a unit test: no page in
the corpus condenses two sounding percussion parts, so nothing measurable prices
them. And the residual on the Mahler rows after a map is the one-line percussion
staves, which the pipeline drops at cell extraction by an explicit design
decision (completion findings §2) — that is a pipeline ceiling and this fix does
not touch it.
