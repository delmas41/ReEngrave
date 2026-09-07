# Does more label evidence make staff identity WORSE?

**No. The label evidence moves ZERO records. The two passes were not comparable
in the first place: one was a transcription and the other was a clef-blind
replay, and the clefs are worth 51 records.**

2026-09-07. Settles D0/D2 of
[docs/backlog-2026-09-07-open-items.md](../../docs/backlog-2026-09-07-open-items.md)
and §2 of
[benchmarks/omr-identity-harness-2026-09/FINDINGS.md](../omr-identity-harness-2026-09/FINDINGS.md).

⚠️ **Naming.** The harness's §2 calls the good pass "A" and the bad one "B";
its own `out/diff-readpass.txt` calls them the other way round. This file never
uses the letters. The two artefacts are:

| here | artefact | how it was made | labels | identity |
|---|---|---|--:|--:|
| **TRANSCRIBE** | `omr-absent-instrument-veto-2026-09/out/whole-report2` | `tools.omr.transcribe`, 88 pages | 962 | 0.9913 |
| **REPLAY** | `omr-slot-alignment-2026-09/out/-map-spans-on.json` | `compose.py`, cached read pass | 973 | 0.9368 |

---

# 1. The verdict, in one table

Every row is Beethoven 5 / Litolff, whole work, 807 judgeable records, scored by
the **unmodified** phase-0 scorer (`omr-identity-harness-2026-09/probe/load.py`
+ `score.py`). Rows 4-11 are new here; rows 1-3 are committed artefacts.

| arm | commit | labels | clefs | correct | rate | contra | human |
|---|---|--:|---|--:|--:|--:|--:|
| TRANSCRIBE (recorded) | pass-A era | 962 | **real** | 800 | 0.9913 | 17 | 108 |
| REPLAY, same session, same day | pass-A era | 962 | none | 750 | **0.9294** | 108 | 199 |
| REPLAY (recorded, the §2 "worse" pass) | slot-align era | 973 | none | 756 | 0.9368 | 110 | 110 |
| replay `arm-full973` | **HEAD** | 973 | none | 756 | 0.9368 | 110 | 110 |
| replay `arm-minus11-962` | **HEAD** | **962** | none | 756 | **0.9368** | 108 | 108 |
| replay `arm-full973-structure-only` | HEAD | 973 | none (control) | 756 | 0.9368 | 110 | 110 |
| replay `arm-full973-clefs` | **HEAD** | 973 | **injected** | 807 | **1.0000** | 17 | 17 |
| replay `arm-minus11-962-clefs` | **HEAD** | **962** | **injected** | 807 | **1.0000** | 17 | 17 |
| replay, readers-only clefs | HEAD | 973 | injected (control) | 807 | 1.0000 | 17 | 17 |
| replay `7ea27a4b` | 7ea27a4b | 962 | none | 756 | 0.9368 | 108 | 108 |
| replay `7ea27a4b` | 7ea27a4b | 962 | **injected** | 807 | **1.0000** | 17 | 17 |

Read down the two `HEAD` pairs:

* **973 → 962 labels, clefs off: 0.9368 → 0.9368.** Zero.
* **973 → 962 labels, clefs on: 1.0000 → 1.0000.** Zero.
* **clefs off → on, at either label count: 0.9368 → 1.0000. +51 records.**

`out/report.txt` is that table as printed; `out/*.json` are the arms.

---

# 2. The experiment the harness asked for, and what it returned

> *"one ~26-minute whole-work read pass at ONE commit, serving both label sets
> off one cache."* — `omr-identity-harness-2026-09/FINDINGS.md` §2

Done, and cheaper than that: the read pass is the slot-alignment session's
**committed cache** (88 pages, `cache-beet5`), so every arm here is ~5 seconds
and no page is re-read. `probe/run_labelsets.py` patches
`contextual._labels_for_page` from that cache and **refuses on a cache miss** —
an arm that silently re-read a page would put the recorded Surya
nondeterminism back into a comparison whose whole content is a handful of names.

Three input assertions, all checked rather than assumed:

1. **The cache IS the 973-label set** — `probe/inspect_cache.py` counts 1013
   labels, 975 matched, **973** admissible under `slots.MIN_LABEL_CONFIDENCE`,
   which is the REPLAY artefact's `labelled_staves` exactly.
2. **The 11 extra rows are the whole difference**, and they are the ones the
   harness named: `(25,11) (28,3) (28,12) (43,8) (47,4) (50,8) (52,8) (60,4)
   (61,2) (63,8) (80,2)`, 962 shared rows agreeing, **0 contradictions, 0 rows
   only in the smaller set**. All eleven are `matched=True` at `confidence=high`
   — so **`MIN_LABEL_CONFIDENCE` is not quietly dropping them**, one of the
   candidate mechanisms, and the admissible count moves exactly 973 → 962 when
   they are withheld.
3. **The two passes' STAVES are identical** — `probe/compare_staves.py`, 88
   pages, **1616 of 1616** staff records, 0 differing systems. Phase 1 is not
   part of the drift, so the identity join was handed the same page both times.

**Result: withholding the 11 changes nothing.** 756/807 either way, the same
51 wrong records, the same slot 8. The harness's reproduction control also
holds: `arm-full973` at HEAD reproduces the recorded REPLAY artefact to the
record (756/807, 110 contradictions).

---

# 3. Code drift is not the cause either — and the proof was in the same session

`probe/bisect_code.sh` re-runs the arm with `tools/omr` checked out at eight
commits between the transcription's own era and HEAD, with the label set held
fixed. `out/bisect.txt`:

    913a1c5b  slot 8 = Trumpet     (the commit nearest the transcription's run)
    7ea27a4b  slot 8 = Trumpet
    5d6e76a8  slot 8 = Trumpet     "FIX: the timpani exported as a second trumpet"
    a827fa36  slot 8 = Trumpet     the group-map fix
    776f8e4f  slot 8 = Trumpet     the span-composition fix
    fd94b270  slot 8 = Trumpet
    b6233a9e  slot 8 = Trumpet
    HEAD      slot 8 = Trumpet

Flat. No commit in the window flips it.

⚠️⚠️ **And the decisive control was already on disk, unexamined, in the very
session that produced the transcription.** That session ALSO ran
`identity_only.py` over the same document 21 minutes later
(`whole-identity.json`, 2026-09-06 15:46 UTC vs the transcription's 15:25):

* same commit,
* **byte-identical label evidence** — 962 rows, same keys, **0 disagreements**
  against the transcription's (checked, not assumed),
* slot 8 = **Trumpet**, identity **750/807 = 0.9294**.

So at one commit, on one label set, the transcription scores 0.9913 and the
replay scores 0.9294. **The 50-record "read-pass floor" is not a read-pass
floor. It is the difference between a transcription and a replay.**

---

# 4. THE MECHANISM: an identity-only replay is CLEF-BLIND, and slot 8 is decided by the clefs

One sentence, and it is checkable by anyone:

> **`Tp.` means either Timpani or Trumpet, and the tie is broken by asking a
> layout model what sits at that position — a replay hands that model no clefs,
> so it answers "Trumpet"; a real run hands it the bass clef the timpani staff
> actually reads, and it stops answering "Trumpet".**

The long form, and every step is measured:

1. `contextual.py:1076` computes `clef_by_slot = _read_clefs_by_slot(pages, …)`,
   which walks `result["pages"][].systems[].staves[]` and keeps only staves with
   a `clef_source`. **A replay passes `pages` with empty `systems`, so this
   returns `{}`.** `identity_only.py`'s own docstring says so — *"With no staff
   dicts, `_read_clefs_by_slot` returns nothing … and so may the ambiguous-alias
   resolutions that depend on the fit"* — the limit was written down before
   anyone asked this question.
2. `fit = fit_layouts(len(reference), labels=fit_labels, clefs=clef_by_slot)`.
   Slot 8 is withheld from `fit_labels` on purpose (`_ambiguous_label_slots`),
   because it is named by an ambiguous alias and the fit exists to question it.
3. `_resolve_ambiguous_labels` asks `resolve_ambiguous_label(8, {Timpani,
   Trumpet}, fit)`, which returns whichever CANDIDATE the fit proposes at
   ordinal 8 — and then writes it to `instrument_by_slot[8]` **and to the
   reference itself**, document-wide.
4. `probe/fit_slot8.py` isolates exactly that call:

   | | fit proposes at ordinal 8 | ambiguous alias resolves to |
   |---|---|---|
   | clef-blind (a replay) | **`Trumpet`** | **`Trumpet`** — the label is overturned |
   | with the real run's clefs | `Trombone` | `None` — not a candidate, so the label stands |

5. The clef that does it is real ink. `probe/slot_clefs.py` over the
   transcription's own readings: **slot 8 votes bass 67, treble 16, tenor 2**,
   against slot 7 (the trumpets) at **treble 90, nothing else**. A timpani part
   is a bass-clef part.

**Two controls, because "non-empty pages" and "clefs" are not the same thing:**

* ⚠️ **`--structure-only`** builds the identical page/system/staff dicts and
  puts **no clef** in them: **0.9368**, unchanged. So it is the clef readings,
  not the presence of a page structure.
* ⚠️ **Circularity.** The injected clefs come from a run where `apply_clefs`
  was on, so a clef *derived from* an instrument name would make this
  self-fulfilling. It cannot: `_read_clefs_by_slot` admits a staff only if it
  carries `clef_source`, and `clef_correction.py` never writes that field
  (`grep`; it writes `clef` only where `clef_source` is absent). The 1369
  admitted rows are `detector` 1220, `detector_header` 96, `cv_locator` 52 —
  readers — plus **one** `slot_continuity`, which is contextual's own fill and
  therefore downstream of the join. Dropping that one row and re-running gives
  **1.0000** unchanged (`arm-full973-clefs-readers-only`).

`probe/diff_paths.py` on the clef pair: **B fixes 51, B breaks 0**, and all 51
are the same record — slot 8, `Trumpet` → `Timpani`, source
`score_order_ambiguity` → `label`.

---

# 5. What the candidate mechanisms turned out to be

The commission listed five. Four are falsified and the fifth is where it
happens, but driven by the wrong variable:

| candidate | verdict |
|---|---|
| the extra labels are on pages the slot's naming never consults | **partly true and irrelevant** — they change nothing, but neither would they if they were consulted; the arm with them and the arm without are identical |
| they are below `MIN_LABEL_CONFIDENCE` and dropped | **NO** — all 11 are `matched`, `confidence=high`; admissible count moves 973 → 962 exactly |
| they move which system wins `reference_view` / `build_reference` | **NO** — the 17-slot reference lineup is identical between the two label sets, in both clef conditions |
| they tip `fit_layouts` to a different layout | **the right function, the wrong evidence** — the fit's answer at slot 8 is decided by CLEFS, and is invariant to these labels |
| the ambiguity machinery treats a contested slot differently | **this is where the flip happens** (`_resolve_ambiguous_labels`), but its input is the fit, not the label count |

---

# 6. ⚠️ Two findings this leaves behind, neither of them the commission's question

## 6a. Every arm in the phase-0 identity harness except one is CLEF-BLIND

`arms.py` registers 59 arms (its prose says 78; `len(ARMS)` is 59). **58 are
`compose.py` replays**;
exactly one — `beet5/shipped` — is a transcription, and the file already says so
("the veto session's own whole-work run; the ONLY artefact in the 'staff'
shape"). That shape difference is documented and proven harmless. **The CLEF
difference travels with it and is not documented, and it is worth 51 records on
Beethoven — 8.5× the largest flag the harness grades (the group map, 6).**

Consequences, stated plainly:

* the harness's pooled shipped-defaults row mixes one clef-bearing arm with one
  clef-blind arm and pools them;
* every Brahms figure in it is clef-blind, including the 0.9699 the
  span-composition self-test asserts on;
* **an identity figure needs a CLEF REGIME stamp beside its page-set regime
  stamp**, and `arms.py` is the place for it.

⚠️ This does **not** invalidate the harness's flag A/Bs: within a
(work, regime) block both arms are the same kind of replay, so a difference
between them is still the flag. What it invalidates is comparing a replay row
to a transcription row — which is exactly what §2 did.

⚠️ It also does not mean the replays are useless. They are ~5 s against ~26 min
and they reproduce a transcription's LABEL-sourced names exactly. What they
cannot reproduce is anything the score-order prior decides, which is what
`identity_only.py` told its readers from the start.

## 6b. A per-SYSTEM refusal guards a document-WIDE write

Latent today, and worth writing down because it is the shape §8b's design cares
about. `_resolve_ambiguous_labels` refuses an overturn on a system that names
the proposed instrument under a different alias — a per-system test — but the
overturn it performs is `instrument_by_slot[slot] = chosen` plus a write into
`reference`, which is **document-wide**. `probe/tp_labels.py` counts the
population on this document: **80 `Tp.` labels, 73 on systems that also name
Trumpet (blocked), 7 that do not** (p11 sys0/sys1, p35 sys1, p42 sys1/sys2, p43
sys0, p63 sys2). Seven systems out of eighty carried the name for all 88 pages
and 51 judgeable records inherited it.

With clefs the overturn never fires, so this costs nothing today. It is a
standing hazard, not a bug report.

---

# 7. What it means for the scope

* **D2 comes off the backlog.** Non-monotonicity in label evidence is not
  demonstrated: the manipulation available moved 0 of 807 records, twice.
* **Phases 2 and 4 are unblocked.** The premise they rest on — that adding
  evidence does not make the answer worse — survives this test. It is not
  *proven* (see the limits below), but the one alleged counter-example is gone.
* **The evidence that mattered was additive and monotone in the right
  direction**: supplying clefs, an independent channel, took identity 0.9368 →
  1.0000 and human cost 0.0681 → 0.0105 per record. That is §8b working, on the
  same page that was said to falsify it.
* **Phase 1's evidence store should record the CLEF channel**, not only the
  label channel. On this document it is worth 51 records where labels are worth
  0, and it is the channel a replay silently drops.
* Beethoven 5 whole-work identity at HEAD, given a real run's clefs, is
  **807/807 with 0 impossible names and 17 contradictions**. The seven records
  the transcription still had wrong are fixed by the group-map and
  span-composition work (`probe/diff_paths.py`: fixes 7, breaks 0, impossible
  91 → 0), which is what those sessions claimed.

## ⚠️ Limits, so nobody over-reads this

* **n = 1 work, 1 edition, 1 manipulation.** This refutes the specific claim; it
  does not prove the identity join is monotone in label evidence generally. The
  only asymmetry available was 11 rows, and they were all `high`-confidence
  agreements.
* **The 1.0000 is clef-conditioned.** The injected clefs come from a
  2026-09-06-morning transcription; a HEAD transcription might read slightly
  different clefs. This is not a claim that a whole-work `transcribe` at HEAD
  scores 807/807 — it is a claim that the clef channel is worth 51 records on
  this document.
* **The group-map flag is inert at HEAD on this work** (`ordinal` and `map`
  score identically, both clef conditions) — the span-composition fix subsumed
  it. The harness's 6-record figure belongs to its own commit era, which is what
  a committed artefact is for.

---

## Reproduce

    # ~5 s an arm, off the committed read-pass cache; nothing is re-read
    bash benchmarks/omr-readpass-monotonicity-2026-09/probe/report.sh

    python3 probe/inspect_cache.py   CACHE_DIR              # what is in the cache
    python3 probe/compare_staves.py  TRANSCRIBE.json CACHE  # 1616/1616, 0 differ
    python3 probe/extract_clefs.py   FULL.json OUT.json     # the clef channel
    python3 probe/fit_slot8.py                              # the mechanism, one call
    python3 probe/slot_clefs.py      ARM.json CLEFS.json    # what each slot reads
    python3 probe/tp_labels.py       CACHE_DIR              # 80 `Tp.`, 73 blocked
    python3 probe/diff_paths.py      beet5 A.json B.json    # which records moved
    bash    probe/bisect_code.sh     SHA [SHA ...]          # code, label set fixed
    bash    probe/run_passA_era.sh   7ea27a4b               # one commit, clefs on/off

⚠️ `run_labelsets.py` reads a cache that lives in another worktree
(`agent-a28a9beefa2dbc9f7/.../cache-beet5`, 88 pages) and the 125 MB
transcription the clefs come from lives in a third
(`agent-a27ea6f49a3716925/.../whole-report2.json`). Both are gitignored session
outputs. `out/passA-clefs.json` (the clef channel, 1369 rows) is committed here
so the clef arms remain reproducible if that worktree goes away; the cache is
not, and without it the arms cannot be re-run.

⚠️ `bisect_code.sh` and `run_passA_era.sh` check `tools/omr` out at another
commit and restore it on exit, including on interrupt. They change no default
and touch no file outside `tools/omr` and this directory.
