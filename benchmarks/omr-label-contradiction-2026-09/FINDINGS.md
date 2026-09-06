# A staff that contradicts its own label

**2026-09-06.** A staff whose OWN margin label the reader read on THAT page, and
which the file names something else. Free — no detection, no reading, no second
pass — and the only identity check in the project that needs **no truth file**:
it asks the document to agree with itself.

Characterised here over every committed contextual artefact (80 of them, two
whole works), **every one of the 158 firings on the two whole-work runs
hand-adjudicated against the printed page**, and wired into
`tools/omr/contextual.py` behind no flag.

---

## 1. The headline

| | |
|---|--:|
| firings, Beethoven 5 / Litolff, 88 pages | **110 of 973** labelled staff records (11.3%) |
| firings, Brahms 1 / Breitkopf, 86 pages | **48 of 1713** (2.8%) |
| adjudicated **`export_wrong`** — the file names an instrument the page does not print | **138 of 158 (0.873)** |
| adjudicated **`label_wrong`** — the reader misread; the exported name is right | **20 of 158 (0.127)** |
| adjudicated **both right** (the structural false positive) | **0 of 158** |

**Every firing marked a real fault.** That is close to true by construction — a
contradiction is a disagreement, so one side must be wrong — which is exactly
why the number that matters is the last row: the case where BOTH names are right
did not occur, and §5 says which corpus would produce it.

**What it cannot tell you is WHICH side.** Three cheap side-signals were measured
against the adjudication and all three fail (§4). So this is **additive evidence,
not a gate**: it renames nothing and refuses nothing.

---

## 2. It detected a 149-staff regression it was never told about

`OMR_SPAN_REFERENCE_FIT` landed today because spans-on without it named **149**
Brahms staves an instrument the work has not got yet. Scoring that arm needs a
notion of "impossible", which needs the work's roster. The contradiction count
needs nothing, and it ranks the arms the same way:

| `OMR_SPAN_REFERENCE_FIT` | spans | impossible names (needs a roster) | **contradictions (free)** |
|---|---|--:|--:|
| `off` | off | 36 | 44 |
| `off` | **on** | **149** | **167** |
| `refuse` | on | 36 | 44 |
| **`search`** (shipped) | on | **0** | **48** |

The impossible column is quoted from
[`../omr-span-composition-2026-09/FINDINGS.md`](../omr-span-composition-2026-09/FINDINGS.md);
the contradiction column is this session's `probe/scan_artefacts.py`, and it
**reproduces that session's own `self-contradicting` column exactly** (its
`probe/score_brahms.py` computes the same quantity independently and prints
44 / 167 / 48). Two implementations, one number.

⚠️ **`impossible` can only ever fall**, so it scores a categorically-wrong name
traded for an ordinarily-wrong one as free. The contradiction count does not: it
is why `search` reads 48 against `refuse`'s 44 while `impossible` reads 0 against
36 — `search` fixes 149 names and creates six new wrong ones on pages 33–35, and
only one of the two columns can see that.

⚠️ **On Beethoven the count does not move across any of those arms** (110 on all
six). Correct: Beethoven's spans pick the same reference either way. A flat
column is coverage of a work the change does not reach, not evidence the change
is safe.

---

## 3. What it actually caught — the adjudication

Every row of the two whole-work runs, settled by opening the printed page
(`probe/render_margin.py`), counting the printed staves where the detected count
was in doubt (`probe/count_staves.py`), and reading the work's roster out of
`data/score-library/catalog.json` where an instrument's existence was the
question. Verdicts and their evidence: `out/adjudication.json`.

### Beethoven 5 / Litolff — 110 rows

| read → exported | n | verdict | what the page prints |
|---|--:|---|---|
| `Timpani → Trumpet` | 93 | **export_wrong** | `Tp.` / `Timp.` on p37, p50, p64. Slot 7 already carries a label-agreeing Trumpet on the same system, so the file names two trumpets and no timpani. |
| `Flute → Piccolo` | 8 | label_wrong | `Fl. pic.` set on two lines; the reader keeps `Fl.` and drops the qualifier. Slot 0 = Piccolo is right. |
| `Trumpet → Trombone` | 5 | label_wrong | `Tr. Bas.` / `Tr. Ten.`; the reader falls back to the bare `tr` → Trumpet. Slots 9–11 = Trombone are right. |
| `Bass voice → Contrabass` | 3 | label_wrong | `Basso.` at the foot of the strings — `c0a80ae7`'s score-order overturn, working. |
| `Contrabass → Oboe` | 1 | label_wrong | p37 prints `Ob.`, clipped at the left edge of this scan. |

⚠️ **The 93 are the `Tp.` defect**, diagnosed on `claude/agitated-bassi-e3a0ab`
(`5d6e76a8`) and **not in main**. It is the largest single identity fault in the
corpus and it costs 93 wrong `<part-name>` elements on one document. Nothing
standing sees it: musicdiff does not score `<part-name>`, `export_coverage` asks
about element KINDS, and the absent-instrument veto exempts a staff that speaks
for itself — so all 93 are exempt by that rule.

⚠️⚠️ **AND ITS SOURCE IS `score_order_ambiguity`** — the same source as the three
correct `Basso.` overturns. The handoff that commissioned this work reports a
2-source table on an older artefact (`whole-report2.extract.json`, 962 label
records: 14 `label` + 3 `score_order_ambiguity`) in which all three
`score_order_ambiguity` rows are correct overturns, and warns that a consumer
which does not exclude that source "reports our own fixes as defects". On the
CURRENT artefacts (973 label records) that source holds **96 rows, 93 of them the
live `Tp.` defect**. **Report the split; never filter on it.** Pinned by
`test_every_source_is_in_scope_and_reported`.

### Brahms 1 / Breitkopf — 48 rows

| where | n | verdict | mechanism |
|---|--:|---|---|
| p33–35, six systems | 18 | **export_wrong** | The system prints one horn staff; the aligner consumes slot 6 (the second Horn) instead of deleting it, so `Trpt.` / `Pk.` / `Viol. Solo` export as Horn / Trumpet / Timpani. Read off the page: p33 prints Fl, Ob, Klar(A), Fag, Hr(E), Trpt(E), Pk, Viol.Solo, 1.Viol, 2.Viol, Br, Vcl, K.-B. |
| p60, p67 | 16 | **export_wrong** | Both pages print TWO systems (14+13 and 14+14, counted off the page) that phase 1 merged into one; the 16-slot reference lands on the last 16 staves and every name below the join is wrong. |
| p85 | 6 | **export_wrong** | The page prints 16 staves (`count_staves.py`) and phase 1 found 17; the slots land one staff too high. |
| `* → Tuba` | 8 | **export_wrong** | **Brahms 1 has no tuba.** `catalog.json` `InstrDetail`: `2, 2, 2, 2+1 - 4, 2, 3, 0, timp, strs` — the fourth brass number is zero, `source_kind: catalog`, independent of every encoding. Slot 9 is a score-order invention; the page prints `Pos.` there. (4 of these fall on the merged/short pages above and are counted in those rows.) |
| p36 | 1 | label_wrong | A movement-opening ROSTER block printing `4 Hörner in Es / in H basso`; `basso` there is a horn key, read as a Bass voice. |
| p63 | 1 | label_wrong | `Ob.` scanned so the O reads as a C → Contrabass. |
| p72 | 1 | label_wrong | `Hr. (C)`; the key qualifier read as a Clarinet. |

Full per-system context (every staff of every contradicting system, with what was
read and what was exported): `out/detail-brahms1.txt`, `out/detail-beet5.txt`.

⚠️ **The fault is not always where the `source` points.** On p33–35 seven rows
carry `source: roster`, and the roster's name for slot 6 (Horn) is *correct* —
verified on p68/75/81/82, where a staff reading `Horn` sits at slot 6 and agrees.
What is wrong there is the SLOT ASSIGNMENT. **A contradiction is evidence against
the chain `staff → slot → name` as a whole; the source names the link that
supplied the name, not the link that broke.**

---

## 4. Nothing on the record says which side is wrong

Three side-signals, each computable from the same block, scored against the
adjudication (`probe/refinements.py`, `out/refinements.txt`):

| signal | Beethoven | Brahms |
|---|---|---|
| **`read_dup`** — the READ name is already carried, with agreement, by another staff of this system | True → **13/13 label_wrong** | True → **11/13 export_wrong** |
| **`duplicate`** — the EXPORTED name is | True → 86/91 export_wrong | True → 7/8 export_wrong, but False → 38/40 export_wrong too |
| **`run`** — another contradiction within 2 staves | True → 1/2 export_wrong | True → 38/39 export_wrong |

`read_dup` looks like a clean discriminator on Beethoven and **inverts** on
Brahms. `duplicate` and `run` do not beat the 0.873 base rate on both works at
once. This is the project's oldest lesson about tuning on one edition, arriving
again — and it is the measured reason the check is additive rather than a gate.

**So the recommendation is Sean's principle applied literally**
(`docs/scope-identity-upstream-2026-09-06.md` §8b — *"I don't want a stain from
disagreement — I want additive information to build probability"*): emit the
contradiction as a negative evidence term on the (staff, name) pair, and let a
consumer that has other evidence — a roster, a clef register, a written range —
combine it. Do not veto on it, and do not overturn on it.

⚠️ **One narrower thing IS actionable and is already claimed.**
`name_already_on_system` is exactly the premise of `5d6e76a8`'s guard (*an
engraver does not name one section with two abbreviations on one system*), and 93
of the 99 rows carrying it are the `Tp.` defect. That guard is written and
unmerged; this measurement supports it and adds nothing to it. It is recorded on
every row as context and **used to decide nothing here**.

---

## 5. What this corpus cannot show

⚠️ **The structural false positive is a CONDENSED STAFF.** `Violoncello e Basso`
carries two instruments; its margin names one and its slot may name the other,
and both are right. The rate here is 0 of 158 — but Litolff's Beethoven and
Breitkopf's Brahms print `Vcl.` and `K.-B.` on separate staves, so that is a fact
about two editions and not about the check. A Mozart or Haydn edition with a
combined bass staff would produce it, and a consumer that wants to ACT on a
contradiction must ask the condensation question first. **Page-vs-encoding
condensation belongs to `benchmarks/omr-headline-validity-2026-09/`** — this
workstream flags the class and hands it over rather than solving it.

⚠️ **n = 2 works, 2 publishers, both 19th-century German orchestral scans.**
Both label nearly every staff, which is what makes them measurable at all — an
edition that labels only at movement starts has almost no population for this
check. The firing RATE (11.3% vs 2.8%) is a property of the edition and of the
run's faults, not a constant.

⚠️ **The count is page-set dependent, like every identity figure in this
project.** A live 2-page run of Brahms p33–34 fires 4 of 51 with a different mix
from the whole-work run, because 2 pages build a different reference. Score any
change on both a narrow set and a whole work — the third time page-set size has
flipped an identity result here.

⚠️ **Neither standing benchmark can price this.** All 20 scan-gate rows and every
`orchestral_eval` excerpt are single-page, and the accuracy metric cannot see a
wrong `<part-name>` at all (musicdiff does not score it — the same blindness that
let the roster ship on a measured 0 edits while exporting seven staves as a
singer). The tests in §6 are what guard this, not a pooled figure.

---

## 6. What was wired, and where

`tools/omr/label_contradiction.py` — the rule (pure), the summary, and a CLI:

```bash
python3 -m tools.omr.label_contradiction out.json                # any transcription
python3 -m tools.omr.label_contradiction benchmarks/**/*.json    # or any stored artefact
```

`tools/omr/contextual.py`, immediately after the absent-instrument veto,
**unconditionally — there is no flag, because there is no behaviour to gate**:

1. `summary["label_contradiction"]` — count, denominator, split by source, split
   by read→exported pair, and the rows. In the JSON of every run.
2. `staff["label_contradiction"]` — `{read, exported, source}` on each
   contradicting staff dict, for a downstream consumer. Built from
   `label_evidence`, **never** from `instrument_label`.
3. **`logger.warning` whenever it fires** — the channel `unresolved_labels`
   already uses, and for the same reason: a wrong name is otherwise
   indistinguishable from a right one anywhere downstream. Verified live on a
   two-page run.

**Controls.** The exported MusicXML and LilyPond are **byte-identical** with the
new field and without it (`probe/export_is_untouched.py`), and the full OMR suite
is green (2403 passed, 8 skipped).

**Anti-drift, and it is not vacuous.**
`tools/omr/tests/test_label_contradiction.py` asserts at source level that
`apply_contextual_analysis` calls `find_contradictions`, does so *outside* any
`if`, assigns the summary, writes the per-staff field *from
`_contradiction_by_key`*, and warns. `probe/mutate_wiring.py` removes each call
site in turn and checks the suite goes RED — all five do
(`out/mutate-wiring.txt`). It also asserts, by AST, that
`label_contradiction.py` never references `instrument_label` or
`raw_label_by_slot` in code.

⚠️ **One of these tests was vacuous when first written and the mutation run
caught it.** `test_the_summary_carries_the_report` matched any
`summary["label_contradiction"]` subscript — including the READS inside the
warning's own arguments — so deleting the write left it green. It now matches an
`ast.Assign` target. This repo has shipped a vacuous regression test before
(`benchmarks/omr-margin-labels-blob-2026-09`, which asserted on label LENGTH and
passed either way); **run the mutation script, do not assume.**

---

## 7. ⚠️ The obvious field is vacuous — do not build this on `instrument_label`

`contextual.py` does `raw_label_by_slot.setdefault(staff.slot_index, text)`:
**one raw text per SLOT**, from the first page in the run that labelled it,
stamped onto every staff of that slot on every page. `contextual.py` states the
consequence in its own comment — the carry *"makes a 'does the staff's own label
agree with its name' audit unable to disagree."* An audit on that field cannot
fail. The per-staff source is
`absent_instrument.label_evidence(page_indices, staff_labels_per_page)`, which is
confidence-filtered exactly as the alignment filters: a label too weak to align
on is too weak to attest with.

---

## Files

```
probe/scan_artefacts.py        every committed artefact -> out/scan.json, out/scan.txt
probe/detail.py                per-system context for one artefact
probe/adjudicate.py            the hand verdicts + their evidence -> out/adjudication.json
probe/refinements.py           do any side-signals separate the direction? (no)
probe/render_margin.py         the margin strip of a printed page, for the eye
probe/count_staves.py          how many staves the page actually prints
probe/export_is_untouched.py   control: the new field does not reach the file
probe/mutate_wiring.py         control: the anti-drift tests are not vacuous
probe/write_findings.py        this document
```
