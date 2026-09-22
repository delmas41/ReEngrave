# WHICH PRINTING THIS IS — gathered, measured, and read by the key signature

**Sean, 2026-09-22:** *"if a page is engraved or a scan along with the
publisher info and year — whatever we have — should be gathered in the first
stage — then we need to make sure that the key signature is determined based
on that info."*

Work order: [docs/NEXT-2026-09-22-identity-conditions-the-key-signature.md](../../docs/NEXT-2026-09-22-identity-conditions-the-key-signature.md).
Everything here is reproducible with `run_all.sh`; the committed artefacts
under `out/` are what every figure below is read off.

⚠️ **AND EVERY FIGURE IS RE-DERIVED BY A SCRIPT, because the prose is the
thing that drifts**: `verify_findings.py` asserts each headline below against
the JSON it came from and **needs no weights, no score library and no PDF**.
It exits non-zero naming any figure that no longer matches.

---

## 1. ⚠️⚠️ SEAN'S OWN GUESS IS RIGHT AND THE BRIEF'S WARNING IS REFUTED

The brief says of the catalog's scan-type label: *"`image_type` IS IMSLP'S
LABEL, NOT A MEASUREMENT, AND IT IS ALMOST CERTAINLY WRONG ABOUT THE ENGRAVED
POPULATION … Seven. A key-signature decision keyed on it would be keyed on a
crowd-sourced string."* Sean's own reaction was the other one: *"Or maybe they
are all scans because they came from IMSLP..."*

**Measured over all 289 committed editions, every PDF on disk, 16 s**
(`classify_library.py`, `out/library-domains.json` — no weights, no gather):

| IMSLP `image_type` | MEASURED verdict | n |
|---|---|--:|
| `Normal Scan` | scanned | **272** |
| `Typeset` | engraved | **7** |
| *(absent)* | scanned | 7 |
| *(absent)* | engraved | 3 |

**Wherever the label exists the two agree 279 of 279 — 272/272 and 7/7, zero
disagreements.** The label's failing is **ABSENCE, not error**: the only ten
editions it cannot speak about are the ones carrying no label, which the
measurement splits 7 / 3.

⚠️ And the engraved ten are exactly what *Typeset* means on IMSLP — **modern
re-engravings** (Snortum 2024, Renioult 2025, Shaw 2024, NielsenComplete 1998,
Wolfson, Chang 2019, a 2016 *Boléro*) — plus **three local files** that are
not IMSLP downloads at all (two Handel *Messiah* reductions and a Kirchhoff).
**Every historical plate this project actually reads is a scan, because it
came from IMSLP.**

> **So the reason to key on the measurement is NOT that the label lies.
> Section 2 is the reason, and it is a stronger one.**

---

## 2. ⚠️⚠️ THE CATALOG IS STRUCTURALLY SILENT EXACTLY WHERE THE FIX IS PROVEN

The engraved fixture the whole key-signature failure is measured on
(`benchmarks/omr-staged-engraved-2026-09`) is a **Verovio render** — a build
product under `benchmarks/`, in no catalog. So `edition_for_pdf` returns `{}`
and `gather_document_identity` **ABSTAINS `not_in_catalog`** on it, while the
container reader answers `engraved` on all three pages (raster coverage
**0.000**, **1188–1655** drawings).

Read off the real record this lane gathered (`out/engraved-p0p2-identity.record.json`):

```
Q.INPUT_DOMAIN       observed 1  abstained 0  value ['engraved']
Q.DOCUMENT_IDENTITY  observed 0  abstained 1  ['not_in_catalog']
```

**A domain filed as a FIELD of the catalog row would have had a reach of ZERO
on the one input where the rule it conditions is proven.** That is why they
are two quantities, and it is a measurement rather than a taxonomy preference.
`test_the_catalog_is_SILENT_where_the_container_ANSWERS` is that argument in
one assertion.

⚠️ The two are still kept apart as **two witnesses** — `image_type` is filed
beside the measurement and neither overwrites the other, the discipline
`Q.INK` uses for `ink_detector_coverage`. §1 is why that costs nothing here:
they do not disagree.

---

## 3. WHAT WAS ALREADY THERE — and one duplicate the derived checks caught

⚠️⚠️ **`Q.INPUT_DOMAIN` HAS BEEN DECLARED SINCE BEFORE THIS SESSION**, at
`record.py` under *"scan vs engraved, for weights"*, classified
`CLAIM.EXTERNAL` with a docstring reasoning that it *"reads the PDF's own
object graph … a fact about the FILE, and like the other externals it does not
degrade with the print"* — **produced by nothing, read by nothing**, and
reported as a GHOST by `reach --check` on every run. `OMR_WEIGHT_ROUTING` has
classified every document since 2026-09-03 and the staged path never wrote the
answer down.

**This session independently reached the same design and then declared the
quantity a second time.** `reach --check` and `capture --check` caught the
duplicate; it was removed and the documentation moved onto the original. The
brief's §2 table listed four existing pieces and missed this one — *"roughly
half of it already exists"* was true of more than it named, and `ls
benchmarks/` is not enough: **`grep Q\\.` the vocabulary too.**

---

## 4. WHAT IS NEW

| piece | state |
|---|---|
| `gather_document_identity` carries `publisher_year`, `plate`, `has_text_layer` | **NEW** — Sean asked for the year by name |
| `OMR_DOCUMENT_IDENTITY` | **DEFAULT ON**, deny-list (was default OFF, allow-list) |
| `gather_input_domain` → `Q.INPUT_DOMAIN` | **NEW producer**, `source_kind: "container"`, `READERS.CONTAINER` |
| `ABSTAIN.NO_DOMAIN_SIGNAL` | **NEW word** — neither raster-dominant nor drawing-rich |
| `adjudicate_key_signature`'s engraved tier | **NEW**, `OMR_ENGRAVED_KEYSIG`, **default OFF**, allow-list |
| `positional_store._edition_projection` | **unified** — two lookups had hand-listed one tuple twice |

**`source_kind: "container"` is a FOURTH kind and is named deliberately.** Not
`catalog` (no external authority speaks), not `encoding`, and emphatically not
`page` — which means *an OMR output of the same raster* and is refused as a
second witness because it falls silent exactly when the reading it would
arbitrate does. This counts vector drawing operations against full-page raster
coverage: **a bad scan is still unambiguously a raster**, so it has `catalog`'s
independence from print quality without `catalog`'s dependence on somebody
having catalogued the file.

Read off the real Litolff scan record (`out/litolff-p1-identity.record.json`):

```
Q.INPUT_DOMAIN       'scanned'   max_raster_coverage 1.0   pages_probed [1]
Q.DOCUMENT_IDENTITY  publisher "Henry Litolff's Verlag, Braunschweig, 1870,
                      plate 2769"   publisher_year '1870'   plate '2769'
                      image_type 'Normal Scan'   has_text_layer False
```

⚠️ **Catalog coverage, so nobody sizes work off a field that is mostly
absent:** `publisher` 285 / 289, **`publisher_year` 195**, **`plate` 177**,
`image_type` 279, **`has_text_layer` 289** — the only field present on every
edition, and 54 of the 279 scans do carry a text layer.

---

## 5. THE RESULT — one gather, adjudicated twice

`keysig_domain_arm.py`, over `out/engraved-p0p2-identity.record.json`
(3 pages, 18 parts, **54 staff-systems, 50 decided**). The canonical
`readjudicate.py --control` reproduces **688 of 688** duration verdicts
exactly on this record first.

| | right | wrong |
|---|--:|--:|
| **OFF** — the shipped precedence | **26** | **24** |
| **ON** — the engraved tier | **47** | **3** |

⚠️⚠️ **IT REPRODUCES THE BRIEF'S OWN TABLE FROM A FRESH GATHER, A DIFFERENT
TREE AND A DIFFERENT SCORER.** Split by reason, the OFF arm reads
`fitted_by_template` **20 right / 0 wrong** and `fitted` **6 right / 24
wrong** — the brief's §1 figures to the unit, arrived at independently.

**The template is 67 of 67 right wherever it speaks**, across both arms
(20 + 47), and it over-counts **nowhere**.

⚠️ **The three that remain wrong are template SILENCES, not template errors** —
all three read reason `fitted`, i.e. the template produced no fit for that
staff's settled clef and the tier fell through to the locator. They are
Violin 1 on systems 1 and 2 and Violin 2 on system 2.

⚠️ **It is not "always answer −3":** the transposing parts are right in BOTH
arms — B♭ clarinets at −1 and E♭ horns at 0 — so the tier is reading the ink,
not a constant.

**In the file** (both arms exported through the committed `export_record.py`):

| | OFF | ON | truth |
|---|--:|--:|--:|
| bars exact (bars 1-20, 18 parts) | **313** | **322** | 360 |
| `<alter>` | 44 | **67** | 100 |
| `<fifths> -3` | 6 | **14** | **14** |
| `<fifths> -1` | 10 | 4 | 2 |
| `<note>` | 676 | 676 | — |

**Per part: 4 better, 0 worse** (Violin 2 +6, Violin 1 +1, Flute 1 +1, Oboe 1
+1). One-sided in the file as well as in the record.

**CONTROL — the zero.** Of **29 quantities** in the record exactly **2** move:
`key_signature` and its downstream `accidental`. Nothing else in the pipeline
notices.

---

## 6. THE CONSUMER IS ONE-SIDED, AND FOUR INPUTS FALL THROUGH

> **Prefer the template ONLY where the document is PROVED engraved. A scan, a
> classifier abstention, a record with no identity row, and the flag off all
> leave the precedence exactly as it ships.**

That is not tidiness. The template's 20/0 is an **engraved** figure; on a scan
the staff-line erasure works **FOR** the locator (accidental-sized clusters
5 → 11 on the Litolff plate, because there the lines merge glyphs and erasing
separates them), and the template's over-counting risk is exactly what the
shipped refusal was written about — **a side that is not measured for
accuracy**. Each of the four fall-throughs has its own test, and each is
paired with the engraved case as a positive control, because a battery of
fall-through tests passes by falling through always.

⚠️ **THE TWO FLAGS INTERACT, AND IN THE SAFE DIRECTION.** The domain row is
written by `OMR_DOCUMENT_IDENTITY`, so setting that OFF while
`OMR_ENGRAVED_KEYSIG` is ON leaves the tier with no row to read and it falls
through to the shipped precedence — silently, and correctly. There is no
combination in which the tier acts on a domain nobody measured, because
`_proved_engraved` requires a positive `engraved` row and an absent row is
not one. `test_NO_IDENTITY_ROW_is_UNCHANGED` pins it.

⚠️ **`Scope.SELF_AND_ANCESTORS` is not optional.** `Q.INPUT_DOMAIN` is filed
on the DOCUMENT and this decision is `Kind.STAFF`; a bare `ev.rows(...)`
returns nothing on every page forever and **fails silent**, reading exactly
like an honest document with no identity — the fault `adjudicate_instrument`
records against `Q.ROSTER_ENTRY` in the same words. Pinned by a test that
asserts the default EXACT scope finds nothing.

---

### What was REUSED, and the one scorer that was not

The brief says *"`locator_vs_template.py` already prints the per-staff table
this job is scored on. Reuse it; do not write a second scorer."* **Reused**:
`readjudicate.rebuild` (imported from the canonical harness, not copied, so
this arm cannot drift from the instrument every other ADJUDICATE arm in the
repo is measured with), `export_record.py`, and `note_accuracy.py` unchanged.

⚠️ **`locator_vs_template.py` was NOT reused, because it answers a different
question.** It re-prepares the page and re-runs both READERS on the ink —
*what did each reader see?* This arm compares two ADJUDICATE passes over one
fixed gather — *what did the decision do with what the readers already said?*
Its numbers are on the record; there is nothing for a re-read to add, and a
second raster pass would introduce exactly the detector jitter the
gather-once-adjudicate-twice design exists to exclude. **That its OFF arm
reproduces `locator_vs_template`'s published 20/0 and 6/24 to the unit is the
check that the two agree.**

## 5b. THE RESIDUE — it reconciles with the brief's 91%, and names the next job

`note_accuracy.py` buckets every disagreement, and the OFF arm reproduces the
09-22 handoff's *"91% of all note errors on 20 bars of 18 parts are this one
fault"* **exactly**: `same count, differs ONLY by an accidental` is **43 of
47** disagreements (91.5%). The tier takes it **43 → 34**, leaving the other
two buckets (2 and 2) untouched.

⚠️⚠️ **SO THE RESIDUE IS STILL ACCIDENTALS — AND IT IS MOSTLY NOT THE KEY.**
Of the 38 bars still not exact, only **8** are on the two parts that still
carry a wrong key; **30 are on the 16 parts whose key is now CORRECT.** The
worst offenders are `Bassoon 1` (12 of 20) and `Bassoon 2` (14 of 20), whose
key is `-3` and right in BOTH arms and whose bar counts **do not move at all**.

**That is the IN-BAR accidental, which reaches no quantity at all** — the
separate job the brief's §8 names, scoped in
`docs/symbol-dossiers/accidentals-keys.md` and blocked on a record-shape
decision (*the record has nowhere to put a span*) that is Sean's. `<alter>`
ends at **67 of a truth 100**, and the 33 missing alterations are the same
population.

⚠️ **So this fix reaches the KEY-borne alterations and nothing else, by
construction, and the numbers say how far that goes**: it is the whole of the
9-bar gain and it cannot touch the remaining 30.

---

## 5c. THE ALTERNATIVE SHAPE — measured for REACH, and NOT taken

The brief's §5 names a second shape and does not rule it out: *"leave the
precedence alone and lower `min_height_spaces` for engraved input instead,
since the mechanism is measured (flats at 0.94-1.22 after erasure against a
1.10 floor)."*

**Not taken, and the reason is reach against cost rather than a measurement
of it.** That route is a **GATHER** change — it moves a constant inside
`key_signature_locator`, so `readjudicate` is structurally blind to it and
every arm costs a full re-gather; this one moves no constant at all and is
priced by re-adjudicating a fixed gather. Its ceiling is also visibly higher
(it could reach the 3 staves the template is silent on, which this cannot),
so **it is worth measuring and this lane did not measure it.** ⚠️ Whoever
does: the floor is shared with the SCAN path, where the erasure is what makes
the locator work at all, so it needs the same one-sided gating and an
engraved-only arm — which is now cheap, because the domain is on the record.

---

## 6b. THE SCAN IS UNTOUCHED — with a control proving the comparison has teeth

`scan_is_untouched.py`, over a **real 1-page Litolff scan gather**
(`out/litolff-p1-identity.record.json`, which carries `input_domain: scanned`
at raster coverage 1.0 and the full catalog row — publisher, **year 1870**,
**plate 2769**, `image_type: Normal Scan`, `has_text_layer: False`):

```
OFF == ON                      True      ✅ the scan is untouched
CONTROL (forced `engraved`)    DIFFERS   ✅ the comparison has teeth
control changed 12 of 12 verdicts, reasons {'fitted_by_template_engraved': 12}
```

⚠️⚠️ **THE CONTROL IS THE INTERESTING HALF, AND IT STRENGTHENS THE ONE-SIDED
RULE RATHER THAN DECORATING IT.** Rewriting that record's own domain row to
`engraved` moves **all 12** key-signature verdicts. So the tier is a no-op on
that page **because the domain gate stops it**, not because the template is
silent there — the template speaks on all 12 staves and the gate is the only
thing standing between it and the file. **Whether it would be RIGHT on those
12 is exactly what is not measured**, which is the whole reason the rule is
one-sided.

⚠️ The instrument returns non-zero unless **both** conditions hold: a run
where the scan is untouched and the control is vacuous is a pass-shaped
nothing.

---

## 7. INSTRUMENT DEFECTS FOUND IN THIS SESSION'S OWN TOOLS

1. ⚠️⚠️ **THE ACCURACY TABLE REPORTED A CLEAN 0 RIGHT / 0 WRONG ON BOTH
   ARMS.** `str(Outcome.DECIDED)` is `'Outcome.DECIDED'` on this Python, so an
   `== "decided"` test could never be true. A believable zero from a
   comparison that cannot fire. Repaired to `.value`, **and the scorer now
   REFUSES a run in which it scored nothing** rather than printing a table.
2. ⚠️⚠️ **THE CONTROL LOOP MEASURED THE SHELL.** `for t in "staged.capture
   --check"; do python3 -m tools.omr.$t` — **zsh does not word-split an
   unquoted parameter**, so every check ran as a module name containing a
   space and returned 1, on BOTH trees. It read as *eight derived checks
   failing identically on base and on mine*, which is the exact shape of a
   legitimate "pre-existing" control. `${=t}` gives the truth: **all eight
   pass on both trees.** CLAUDE.md already records this trap for `env $3`.
3. **The new test file skipped 5 of 18 assertions silently** — `REPO` was
   computed with three `dirname`s where the file is four levels down, so every
   path test `skipTest`ped. A skip is the one outcome that looks like a pass;
   the path is now asserted at import.
4. **A bad anchor, twice.** The catalog projection appears **twice** in
   `positional_store.py` (`edition_facts` by path, `edition_for_pdf` by
   basename) — the anchor-occurring-twice trap. Repaired by writing the
   projection ONCE, which is also why the new fields reach both lookups.
5. **A shared helper defeated a derived check.** Factoring the two template
   returns into one function taking the reason word as a PARAMETER made
   `brakes --check` report `['fitted_by_template', 'fitted_by_template_
   engraved']` UNRESOLVED. INFER refused exactly this trade when it wrote two
   flag predicates out separately; the lookup is shared and the two literal
   reasons stay at their call sites.

---

## 8. WHAT IS **NOT** ESTABLISHED

- ⚠️ **n = 1 engraved document, 1 renderer, 24 bars, 3 pages.** A render is
  not a scan, and this says nothing about an engraved page from a publisher.
- ⚠️ **NO PRINT WAS CONSULTED.** The truth is the encoding's
  `<key><fifths>`, joined ordinally to staves on a render where that join is
  true by construction. No crop was cut.
- ⚠️ **THE SCAN SIDE IS UNMEASURED FOR ACCURACY AND DELIBERATELY SO.** What
  is shown is only that the tier is a **no-op** there — which is the
  fall-through working, not evidence that the shipped precedence is right.
- ⚠️ **NOTHING READS `Q.DOCUMENT_IDENTITY` YET.** The publisher, year and
  plate are gathered and no decision consumes them; its `reach.KNOWN_GAPS`
  entry stays, corrected to say the flag is now ON and the READ is what is
  open.
- ⚠️ **No OMR-NED figure**, deliberately: the metric is symmetric and pairs
  by pitch, and a key signature moves pitches wholesale.
- ⚠️ **THE DEFAULT IS SEAN'S.** `OMR_ENGRAVED_KEYSIG` ships **OFF**. Flipping
  it is a behaviour change on a population of one document, and this lane
  recommends it only for engraved input, which is 10 of 289 held editions
  plus rendered fixtures.
- ⚠️ **The records were gathered from a DIRTY tree** (`provenance.dirty`
  true) — the working tree carried exactly this lane's change and nothing
  else. They are benchmark arms, not shared records.
