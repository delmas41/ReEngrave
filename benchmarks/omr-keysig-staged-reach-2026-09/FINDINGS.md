# The key signature's declared corroboration cannot be wired — and the thing that could be, was

**2026-09-21.** No flag. `tools/omr/staged/adjudicators/header.py`.
Item **2** of the 2026-09-20 handoff's ranked list: *"`key_signature_
corroboration` on the staged path — CLAUDE.md says shipped; the staged path
does not import it."*

**The import claim is true. The repair it implies is not.**

| | |
|---|---|
| the declaration | *"a key CHANGE is printed on every staff at the same bar (key_signature_corroboration — CONSUMED, default-ON)"* |
| non-test imports of that module | **exactly one, `transcribe.py` — the LEGACY path** |
| **mid-staff key changes the staged path can express** | **ZERO, structurally** |
| ⇒ wiring the import would produce | **a pass over an empty domain** |
| what WAS wireable, and is now wired | `Q.KEYSIG_MARKER` — declared in `wants` AND `composed_from`, read by nothing |
| what that repaired | **`no_evidence` reported on staves that carry key-accidental ink: 7 of 17 and 9 of 20** |

---

## Ask-first block

**CONVENTION.** Sean's, via registry entry `[C24]`: a key change is printed on
every staff at the same bar. Nothing here disputes it — the finding is that
this path cannot yet hold a key change for it to govern.

**NOT CONFIRMED WITH SEAN.** Whether a mid-staff key reader should be built at
all (§3 measures its reach at **21 and 2** detections and §3a says what the
legacy path paid for reading them naively), and whether `markers_without_a_run`
is the right name for the split.

**WHAT WOULD FALSIFY §2.** A staged record carrying a `key_signature` verdict
at any scope but `staff`, or a `keysig_marker` row at any frame but `cell:0`.
`probe_records.py` prints both counts first and they are the first thing to
re-check on a new document.

---

## 1. The import claim, verified

```
$ grep -rn 'key_signature_corroboration' tools/ --include='*.py' | grep -v tests/
tools/omr/transcribe.py:267:from .key_signature_corroboration import (      <- the ONLY import
tools/omr/staged/adjudicators/header.py:15: '... -- CONSUMED, default-ON)',  <- a docstring
… four more staged files, all prose
```

The staged path names it in five places and imports it in none. **That part of
the handoff is exactly right.**

---

## 2. ⚠️⚠️ AND IT CANNOT BE FIXED BY IMPORTING IT, BECAUSE THERE IS NO CHANGE TO CORROBORATE

The guard reverts *a mid-staff key change that no other staff corroborates*.
On this path a mid-staff key change **cannot exist**:

| | where it is decided |
|---|---|
| `adjudicate_key_signature` | `scope=Kind.STAFF` — one key per staff, full stop |
| `_gather_keysig_markers` | reads `R.cell(p, s, i, 0)` — **cell 0 and nothing else** |
| `Q.KEYSIG_RUN_POSITION`, `Q.KEYSIG_TEMPLATE_FIT` | the HEADER WINDOW |
| `staged/export.py` | `run.fifths`, **one int per staff-run** |

Measured on the two shared records, with no pipeline code
(`probe_records.py`):

| | Litolff Beethoven 5 p1-p4 | Breitkopf Brahms 1 p0-p3 |
|---|--:|--:|
| `key_signature` verdicts | 75 | 97 |
| …of them at a scope other than `staff` | **0** | **0** |
| `keysig_marker` rows | 105 | 146 |
| …of them at a frame other than `cell:0` | **0** | **0** |

⚠️ **THE CONTRAST WITH THE METER IS THE WHOLE ARCHITECTURE OF IT.** `Q.METER`
carries `segments`, `record.meter_at` reads a bar's meter, and
`OMR_METER_SEGMENTS` made the exporter read the meter in force at each BAR —
that family solved exactly this problem and shipped it. The key signature has
no equivalent: **no segments, no `key_at`, one value per run.** So this is not
a missing import, it is a missing QUANTITY SHAPE, and the two repairs are not
the same size.

---

## 3. What is out of reach, measured — because someone will propose building it

Key-accidental detections (`keySharp` / `keyFlat` / `keyNatural`) standing in
cells OTHER than cell 0. The detector fires on them; GATHER never looks:

| | Litolff | Breitkopf |
|---|--:|--:|
| in cell 0 (gathered) | 105 | 146 |
| **in later cells (gathered by nothing)** | **21** | **2** |

### 3a. ⚠️⚠️ AND THE LEGACY PATH IS THE WARNING ABOUT READING THEM

`key_signature_corroboration.py` records what happened when the legacy path
DID read later-cell markers: across 11 scanned pages it sees **15** of them,
**7 CHANGED THE KEY, AND ALL SEVEN WERE WRONG** — every one landing on exactly
one accidental, because where the slot fit abstains
`_detect_key_sig_from_cell` falls back to COUNTING markers. The guard this
item is named after exists to undo that.

**So a mid-staff key reader must arrive WITH its corroboration, not before
it** — and that is the one thing the staged path can do better than the legacy
one, because here the guard would be designed in rather than bolted on. It is
ranked work, not this change.

---

## 4. What WAS wireable: `Q.KEYSIG_MARKER`, and a reason word that was wrong

`Q.KEYSIG_MARKER` is declared in `wants` **and** in `composed_from`, filed 105
and 146 times, and was read by nothing — confirmed by the convention audit's
own derived tool (`declared_vs_read.py`: *"DECLARED IN wants AND NEVER
REACHED: dossier_fact, keysig_marker"*).

⚠️⚠️ **THE STATED REASON FOR LEAVING IT UNREAD WAS FALSE, WHICH IS WHY IT
SURVIVED TWO GAP LISTS.** Both `inventory.KNOWN_GAPS` and `reach.KNOWN_GAPS`
excused it identically — *"the decision reads `keysig_clef_fit`, which the
markers already feed in GATHER"*. They do not:

* `Q.KEYSIG_CLEF_FIT` is filed from `locate_key_signature(crop, candidate,
  occupied_boxes=...)` — a **CV reader on the header crop**;
* the one place detections enter that call is `_occupied_boxes`, whose body
  filters on `_NOTEHEAD_PREFIX` — **noteheads only**;
* `_gather_keysig_markers` **returns nothing at all**; it only logs.

**The markers feed nothing.** A gap list holds reasons a gap EXISTS, never
reasons one is acceptable — and this one held a reason that was not true.
Both entries are removed.

### 4a. The repair is a REASON, never a value

Where the run reader could not speak but the detector saw key accidentals, the
abstention now says **`markers_without_a_run`** instead of `no_evidence`, and
every abstaining path records `keysig_marker_ink` / `_state` / `_classes`.

| abstention reason | with marker ink / total (Litolff) | (Breitkopf) |
|---|--:|--:|
| **`no_evidence`** | **7 / 17** | **9 / 20** |
| `run_fits_no_slot_table` | 3 / 4 | 1 / 1 |
| `needs_clef` | 2 / 5 | — |

⚠️ *No evidence* was wrong on **41%** and **45%** of the staves it named. That
is the ABSENT/DECLINED collapse this record exists to prevent, and it sends
the next person to the wrong module: **nothing was printed** wants a reader,
**we could not fit what was printed** wants a fitter. The `direction` family
split `NO_INK` from `NO_READING` for exactly this reason — *folding the two
hides which rung is the limit*.

⚠️⚠️ **IT MAY NEVER BECOME A VALUE, AND THE RECORD AGREES FROM ITS OWN SIDE.**
Over the staves this path DECIDES, the marker COUNT equals the settled
`|fifths|` on **19 of 49 (39%)** and **39 of 76 (51%)**. A reading that
disagrees with the settled answer about half the time is not a value; it is
evidence that ink was there. Four mutation arms and four unit tests pin that
it never decides, never overturns a fit, and says so in its own key name
(`keysig_marker_count_is_not_a_reading`).

---

## 5. Controls

**NO DECIDED KEY MOVED — RUN, AND PASSED.** Litolff
(`out/beethoven5-p1-p4-ink-identity.json`): **75 key verdicts rebuilt of 75,
49 decided, MOVED 0, absent 0**, and the abstention split is
`no_evidence -> markers_without_a_run` ×**7** — ⚠️ **the exact number
`probe_records.py` predicted from the record's JSON with no pipeline code at
all.** Two instruments, two routes, one number.

Breitkopf: **97 of 97 rebuilt, 76 decided, MOVED 0, absent 0**, split
×**9** — again the probe's own number. **Both arms exit 0**
(`out/control-arm.txt`).

⚠️ **ONE NUMBER LOOKED TOO GOOD AND WAS CHECKED: `DETAIL` reads `{carries the
detail: 21, and ink was there: 10}` IDENTICALLY on both documents.** This
repo's own diagnostic is *"is this number suspiciously EXACTLY some other
number"*, so it was decomposed rather than admired — and it is a genuine
coincidence built from **different components**: Litolff is 17 `no_evidence` +
4 `run_fits_no_slot_table` = 21 carrying the detail (its 5 `needs_clef` return
before it) with 7 + 3 = 10 carrying ink; Breitkopf is 20 + 1 = 21 with
9 + 1 = 10.

`check_arm.py` re-adjudicates each shared record through the SHIPPED
decision. ⚠️ The control is sharper than *"nothing
moved"*, because something IS meant to move: every DECIDED verdict must be
identical in value and reason, **only** `no_evidence -> markers_without_a_run`
is a permitted abstention movement, and any other is a failure.

**POSITIVE.** The split must actually have happened, or *"no decided key
moved"* is also exactly what a change that never ran looks like.

**TWO INSTRUMENTS.** `probe_records.py` asks §2 and §3 with **no pipeline code
at all** and deliberately RESTATES `_KEYSIG_CLASSES` rather than importing it;
`check_arm.py` imports the real tuple and **refuses to run if the two have
drifted**, so the independence cannot quietly become a disagreement about
which population is being measured.

**THE DERIVED TOOLS CAUGHT THE CLOSURE THEMSELVES — TWO OF THEM, AGAIN.**
Wiring the quantity turned `test_staged_inventory` and `test_staged_reach` RED
on exactly one stale entry each, and **not** `dossier_fact`, which is still
genuinely unread.

**`dossier_fact` IS DELIBERATELY LEFT ALONE, and its reason was re-checked
rather than inherited.** `staged/__main__.py` refuses to supply a dossier in
terms — *"a dossier is generated from the same MusicXML the benchmarks score
against, so the scan gate is dossier-free BY PROTOCOL and a `--dossier` flag
would put a truth file inside a measurement path"*. That reason is still true,
so the gap stays and its entry stays with it.

### 5a. ⚠️ THE BATTERY'S FIRST RUN: 8 RED, **6 SURVIVORS**, and five of them were the INSTRUMENTS

`out/mutation-battery-run1.txt`. One survivor was a real gap in the code's
tests and **five were the arm's and the probe's own controls**, which no suite
imported — a benchmark arm is a script, so every battery arm against one is
free unless something drives it. Closed by tests that run each `main()` over a
synthetic record.

⚠️ **THE CODE SURVIVOR IS THIS REPAIR'S OWN LESSON ONE LEVEL DOWN.** Deleting
`keysig_marker_state` from the no-ink branch left every assertion green: the
tests checked the COUNT was zero and never that the record could still say
WHICH zero — *the detector filed no row* against *it filed a row saying it saw
nothing*. That is the ABSENT/DECLINED collapse this whole change repairs,
reappearing inside the repair.

⚠️ **AND THREE OF THE SIX CLOSING TESTS WERE WRONG ON THEIR FIRST RUN, ALL
THREE FIXTURE FAULTS OF MINE**: a clef glyph row with no `score` (so the
rebuild abstained `needs_clef` and the test silently exercised a different
branch); a record with NO observation on the staff at all (so no verdict was
filed and *"absent from the rebuild"* was being read as the illegal-move it
was named for); and an import-machinery monkeypatch, replaced by inducing the
drift from the arm's own side. *A fixture that does not reach the branch tests
the fixture.*

**MUTATION BATTERY, RE-RUN AFTER CLOSING THEM.** 14 arms. See `out/`.

⚠️⚠️ **AND THE FIRST CONTROL-ARM RUN WAS DISCARDED, DELIBERATELY, 18 MINUTES
IN.** The battery mutates `header.py`; the arm had imported it. An
already-imported module keeps its code, so the arm was almost certainly
isolated — but *almost certainly* is not a control, and this repo's own rule
(written one day earlier, by this session) is that **a mutation battery is a
concurrent writer and it is one you started yourself**. The arm was killed and
re-run alone rather than reasoned about.

⚠️⚠️ **AND KILLING IT DID NOT KILL IT. THE ARM RUNS BOTH RECORDS IN A SHELL
`for` LOOP, so killing the python process killed ONE ITERATION and the loop
moved straight on to the second record** — where it ran for a further 31
minutes, overlapping the battery it had just been removed from, and racing the
clean re-run for the same `--tag` output file. Found by counting processes,
not by anything in either run's output: **both would have written a plausible
result.** The stale loop was killed by PID (never by name — this repo has paid
for a blanket `pkill` before) and its output discarded.

> **Killing a long job means killing the LOOP, not the iteration** — and a
> `--tag` that two runs share is a race whose loser is silent.

---

### 5b. ⚠️⚠️ A UNIT TEST OVERWROTE THIS BENCHMARK'S OWN COMMITTED ARTEFACT

The tests added to close §5a's instrument survivors drive each instrument's
`main()` — and both write their results under `HERE/"out"`, which is a
COMMITTED measurement. The first version **silently replaced
`out/probe-records.json` with the synthetic one-staff fixture's numbers**, and
nothing failed: the file still parsed, still had the right shape, and still
looked like a measurement. It was caught by a later command reading it and
finding `rec.json` named inside.

**An instrument that destroys its own artefact when exercised is worse than
one with no test at all**, because the artefact goes on looking like evidence.
`HERE` is redirected to a temp directory now — ⚠️ with the sibling `.py` files
COPIED in, because `check_arm` loads `probe_records.py` from `HERE` for the
constant-drift check, and redirecting alone broke that check instead of
exercising it. A test asserts the committed `out/` is untouched after both
instruments run.

---

## 6. WHAT IS NOT ESTABLISHED

* **No print was consulted.** The 7-of-17 and 9-of-20 are our detector
  disagreeing with our CV reader; **neither is truth**, and this does not say
  the ink is a key signature — only that the detector called it one.
* **Nothing is repaired about the READING.** 26 and 21 staves still abstain.
  This changes what the record SAYS about them and not one exported note; no
  file moves and **no OMR-NED figure is claimed**.
* **The out-of-reach population is 2 on one publisher**, so §3's number is not
  a rate — it says the ceiling is low on these pages, not on every page.
* **n = 2 documents, 2 publishers, 8 pages, both scans.** The engraved family
  is untouched, and it is the family CLAUDE.md records as printing **ZERO**
  later-cell key markers — so it cannot exercise §3 at all.
* **`markers_without_a_run` is never produced on a page with no detector**, and
  no fixture here has one.

---

## 7. Running it

```bash
B=benchmarks/omr-keysig-staged-reach-2026-09
R=library/_shared-records

python3 $B/probe_records.py $R/*.record.json     # seconds, no pipeline code
python3 $B/check_arm.py $R/beethoven5-p1-p4-ink-identity.record.json --tag litolff
python3 $B/mutate.py
python3 -m pytest tools/omr/tests/test_keysig_marker_ink.py
```

⚠️ `check_arm.py` re-adjudicates a whole record and takes **tens of minutes**
per document. `probe_records.py` answers §2 and §3 in under a second.
