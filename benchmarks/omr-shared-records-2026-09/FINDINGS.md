# The second publisher exists — a shared staged record for Breitkopf Brahms 1

2026-09-15. **Infrastructure, not a repair.** Three separate jobs stopped at the
same missing artefact on 2026-09-15 — the arc grammar, the note-where-silence
cuts, and the `OMR_METER_CARRY` blocking objection — each because
`library/_shared-records/` held only the Litolff Beethoven record. This builds
the one they all wanted, and **inventories it honestly** so the next session can
size its own question from the repo rather than by re-gathering 444 MB.

⚠️ **NOTHING HERE WAS FIXED, AND NOTHING WAS TUNED.** No constant moved, no flag
flipped, no file under `tools/` touched. The gather ran at the defaults plus the
two label rungs. Where it exposed a defect — and the meter is a bad one — the
defect is recorded with its evidence and **left standing**.

⚠️ **NO ACCURACY CLAIM IS MADE ANYWHERE IN THIS DOCUMENT.** Every figure is a
REACH figure — how much of a population the record holds. Not one glyph was
checked against the print.

---

## 0. THE RECEIPT

| | |
|---|---|
| path | `library/_shared-records/brahms1-breitkopf-p0-p3.record.json` |
| md5 | `52b98f1cdfee3b39f10e56c592828ea4` |
| size | **443,702,431 bytes (443.7 MB)** — 3.3x the Beethoven record's 132.7 MB |
| wall clock | **20:27:39 → 22:11:53 = 1 h 44 min** |
| provenance | `{"commit": "e282ae0c02a346db6f248d2c0c7ead69de8a84c6", "dirty": false}` |
| document | Breitkopf & Härtel, Brahms Symphony 1 mvt 1, IMSLP `317803` |
| pdf pages | **0-3**, the hand-verified `works.json` window (reference mm **1-58**) |
| weights | `deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt` (scan production) |
| readers | `--surya --ocr`, both live; the resident llama-server was ATTACHED, never killed |

**THE TREE WAS CLEAN.** `dirty: false`, at a commit that is an ancestor of this
branch. That is the thing a shared artefact is FOR, and it is why the recipe was
committed *before* the run rather than written up afterwards: the stamp is taken
at the END, so a single untracked file under `benchmarks/` written during those
104 minutes would have made it `dirty: true`.

⚠️ **The Beethoven record it sits beside is `dirty: true`** (commit `9d4ccc85`).
So of the two shared records, only this one can name the tree that produced it.
That is not a criticism of the earlier artefact — it is a fact a consumer
comparing the two must know.

**Reproduce it:** `make_breitkopf_brahms1.sh`. **Re-read it:**
`inventory_probe.py` and `reach.py`, both committed here, both exiting non-zero
if they measured nothing.

---

## 1. ⚠️ REACH FIRST — the label rungs worked, 97 of 97

**This is the number that says whether the record is useful at all**, and it is
the reason the run was made with `--surya --ocr` rather than at the defaults.

| page | system | staves | labels | |
|--:|--:|--:|--:|---|
| 0 | 0 | 14 | **14** | `2 Flöten`, `2 Oboen`, `2 Klarinetten in B`, `2 Fagotte`, `Kontrafagott`, … `Kontrabaß` |
| 1 | 0 | 14 | **14** | `Fl.` `Ob.` `Klar. (B)` `Fag.` `K-Fag.` … `K-B.` |
| 1 | 1 | 13 | **13** | (no `Trpt.` — the suppressed staff, and the reader SEES that) |
| 2 | 0 | 14 | **14** | |
| 2 | 1 | 14 | **14** | |
| 3 | 0 | 14 | **14** | |
| 3 | 1 | 14 | **14** | |
| | | **97** | **97** | **100%** |

⚠️⚠️ **CONTRAST, AND IT IS THE WHOLE POINT OF DOING THIS ONE WITH THE READERS
ON.** The committed Beethoven shared record reads **0 labels over 75 staves**,
with `margin_label` abstaining `not_implemented` 75 times — it predates the
`run_staged` `pdf_path` forward. Downstream of that, its `instrument` abstains
`no_evidence` **75 of 75**, `slot_index` falls to the staff ordinal, and
`name_part` fires zero times.

**Here `instrument` DECIDES 91 of 97** and `name_part` fires **91**. Six staves
abstain `not_in_lexicon`, and every one of the six is an OCR-mangled HORN label
— `in C 1 2`, `Horner 4 | : |`, `(C)`, `(Es)`, `| | Hr.` — the brace this
edition draws across its two horn staves being read as text. Recorded, not
fixed: it is a lexicon/reader question and out of this job's lane.

⚠️ **This record therefore REFUTES, for this document, a premise written into
`KNOWN_GAPS`**: *"the range test needs the INSTRUMENT, which abstains
`no_evidence` on 22 of 22 and 27 of 27 staves of the two scanned pages — so it
would reach NONE of the population it was filed to fix."* That was measured on
records gathered WITHOUT the label rungs. With them the instrument is known on
91 of 97 staves here, so the population is no longer empty. **Deliberately not
repaired** — it is a docstring under `tools/`, and whether the range check is
worth wiring is a different job with its own measurement. It is flagged so
nobody quotes the stale premise.

---

## 2. STAFF COUNTS AGAINST THE PRINT — exact on all four pages

|  | p0 | p1 | p2 | p3 |
|---|--:|--:|--:|--:|
| printed (hand-read, `works.json`) | 14 | 27 | 28 | 28 |
| **read by this gather** | **14** | **27** | **28** | **28** |

Exact, and per SYSTEM as well as per page (14 / 14+13 / 14+14 / 14+14) — the
13 being page 1 system 2's suppressed `Trpt.` staff, which `works.json` records
as verified against the print. `measure_count_across_staves` is **unanimous on
all 7 systems with 97 witnesses and 0 disagreements**.

So the segmentation half of this document is sound, and a job reading this
record does not have to defend it.

---

## 3. ⚠️⚠️ THE METER IS WRONG ON 6 OF 7 SYSTEMS — reproduced, not repaired

The movement prints **`6/8`**, one bar of **`9/8`** at m8, then `6/8`. What the
record holds:

| system | opening meter | reason | what is wrong |
|---|---|---|---|
| p0 s0 | `6/8` | `voted` | correct — **the only one** |
| p1 s0 | **`9/4`** | `voted` | the printed `9/8` misread, exactly as CLAUDE.md records |
| p1 s1 | `4/4` | `change_only` | spurious, 1 staff, support 3.0 |
| p2 s0 | `4/4` | `change_only` | spurious, 2 staves, support 6.0 |
| p2 s1 | `4/4` | `change_only` | spurious, 2 staves, support 4.5 |
| p3 s0 | `4/4` | `change_only` | spurious, 4 staves, support 11.5 |
| p3 s1 | `4/4` | `change_only` | spurious, 3 staves, support 7.0 |

**Every one of the six carries `bars_fit: 0`** — not a single bar of any system
corroborates the meter that system was given. That is the recorded hazard *the
bars are not an independent umpire over a bad reading*, standing in the record
in its own numbers: the arbiter is silent exactly where it is needed.

⚠️ **The cautionary machinery is working correctly on the same page**, which is
what makes the failure attributable. p0 s0 records a **cautionary `9/8` at
`from_cell: 7`, support 26.5, read on 9 staves** — the courtesy signature
printed after the final barline that `works.json` uses to close p.1's window —
and it is filed as `cautionary`, governing no bar, rather than proposed as a
change. The reading is there; the next system still votes `9/4`.

**So this record is the arm `OMR_METER_CARRY` has been blocked on.** Its
standing objection is that the flag cannot be priced on a document whose meter
reading is CORRECT, because the carry is then never handed a wrong candidate to
weigh. Here the candidate is wrong on six systems out of seven, and a carry from
p1 s0 would propagate `9/4` forward across three pages. That cost is now
measurable. **This job did not measure it** — that is the meter job's, and it
must be run as a controlled arm.

---

## 4. WHAT THE RECORD CONTAINS — and four exact reproductions

`out/inventory-probe.txt`, `out/reach.txt`, `out/inventory-run.txt`,
`out/gather_coverage.txt`, `out/health.txt` are committed beside this file.

⚠️⚠️ **FOUR FIGURES REPRODUCE CLAUDE.md's INDEPENDENTLY-RECORDED NUMBERS FOR
THIS DOCUMENT TO THE UNIT**, and taken together they are a real control that
this record IS the document the repo has been describing — not a different
window, a different edition, or a different rasterisation:

| | this record | CLAUDE.md, recorded earlier and elsewhere |
|---|--:|--:|
| `flag` rows | **371** | *"Breitkopf fires **371** and 656"* |
| `aug_dot` rows | **656** | *(same sentence)* |
| tie arcs | **1658** | *"Brahms 1 `317803` p0-3 **1658** → 1227 merged"* |
| `wedge_box` rows | **47** | *"**47** on Breitkopf Brahms 1 p0-3 (46 `cv_hairpins`, 1 `detector`)"* |

`wedge_anchor` decides 46 and abstains 1 `no_page_frame` — also exactly as
recorded, the one detector row with no box.

### The three waiting jobs, sized

| job | population here | Litolff p1-3 |
|---|--:|--:|
| **arc grammar** — `arc_box` | **2,207** | 779 |
| … `Q.STEM` | 2,305 | 1,920 |
| … noteheads | 3,337 | 2,347 |
| … arc kinds | tie 1,658 / slur 549 | — |
| **note-where-silence** — `rest` rows | **1,028** | — |
| … `restWhole` (the cut population) | **398** | 395 |
| … `rest8th` / `restQuarter` | 380 / 238 | — |
| **meter carry** — `meter_glyph` | 197 | — |
| … systems whose opening meter is not the printed `6/8` | **6 of 7** | 0 of 7 (Litolff's one read meter is correct) |

⚠️ **`restWhole` 398 against Litolff's 395 is the single most useful line here
for the note-where-silence job**: its two cuts sit on a plateau one step wide,
derived from one document's 395 whole rests, and this record offers an almost
identically-sized independent population to re-measure them on. **That is a
statement about the DENOMINATOR, not about the answer.**

### ⚠️ WHAT THIS RECORD CANNOT ANSWER

| quantity | here | Litolff p1-3 |
|---|--:|--:|
| `fermata_mark` | **0** | 67 |
| `ornament_mark` | 7 | 6 |
| `direction_word` | 10 | 6 |
| `wedge_box` | **47** | **0** |
| `dynamic_letter` | 531 | 485 |

**`fermata_owner` and `tuplet_ratio` write NO ROW OF ANY KIND** — `inventory
--run` names both — because these bars print no fermata and no tuplet digit.
That is a property of the PAGE, and a clean zero that means nothing must not be
read as a result. **A fermata question cannot be asked of this record at all.**

Symmetrically, and in this record's favour: **hairpins exist here and do not
exist on Litolff at all** (47 against 0). Any wedge work whose only fixture was
Brahms now has that fixture inside a shared, clean-tree artefact.

### Stage health

`gather_coverage` and `health --check` both exit 0 on this tree.
`adjudicate.stubs()` is `()` — **0 declared decision stubs**, 1 consequence stub
(`join_parts`). `inventory --run` reports **14 problems, 0 of them off
`KNOWN_GAPS`**. EVALUATE fired 5,728 consequences (`restate_pitch` 3,428,
`respell_accidental` 671, `move_glyph` 1,491, `name_part` 91,
`size_measure_rest` 105, `reconcile_duration` 33).

---

## 5. ⚠️ THREE THINGS THE GATHER EXPOSED AND THIS JOB DELIBERATELY DID NOT FIX

1. **The meter, section 3.** Six systems of seven. The largest defect this
   record holds, and the reason the record is worth having.
2. **Six horn labels abstain `not_in_lexicon`**, all of them the brace this
   edition draws across its two horn staves being OCR'd as text
   (`Horner 4 | : |`, `| | Hr.`, `(C)`, `(Es)`, `in C 1 2`, and one `F1.` for
   `Fl.`). Every other staff of all seven systems reads.
3. **`key_signature_across_systems` disagrees on 10 of 27 facts** (4 `split`, 6
   `majority`) against `clef_across_systems`' 2 — and `key_signature` abstains
   `no_evidence` on 20 staves. The key-signature reader is the weaker of the two
   on this document. Recorded; the key-signature thread owns it.

None of the three was touched. ⚠️ Each is a candidate for *"a result that holds
on both documents"*, which is exactly what this artefact was built to make
possible.

---

## 6. ⚠️ THE STANDING WARNING THIS RECORD EXISTS TO ANSWER

**Everything ReEngrave measured on 2026-09-15 is n = 1 document, 1 publisher,
4 pages, on the low-res bitonal Litolff `984073` — which CLAUDE.md itself calls
the pessimistic end of the corpus.**

The two documents differ in ways already measured and now reproduced here: 371
flags against 49, 656 dots against 35, 2,207 arcs against 779, 47 hairpins
against 0, 0 fermatas against 67, and a meter that is wrong on six systems
against one that is right. **So a result that holds on BOTH is a result; one
that holds only on Litolff is a property of that scan.** Say which you have.

⚠️ And this record is n = 1 too. Two publishers is not a corpus.

---

## 7. Operational notes, each of which cost somebody a session

- **The machine was busy** (load 8-18 throughout: four `rest_sizing_arm`
  processes and, from 20:30, a sibling Beethoven gather). Nothing was killed.
  The run was niced only by `OMP_NUM_THREADS=4`.
- **`pkill -f llama-server` was NOT run.** `staff_labels_surya --check` found a
  resident server on port 55208 and the run ATTACHED to it
  (`OMR_SURYA_KEEP_ALIVE=1`). That is also why GATHER took **5.5 minutes** here
  against the 33 minutes a comparable Litolff gather cost with a cold Surya —
  the model was already loaded, by somebody else.
- **The time went where the budget did not predict.** GATHER (including both OCR
  rungs) was 5.5 min; **ADJUDICATE was ~98 min, and `arc_owner` ALONE was ~70 of
  them** — 2,207 arcs each asked of every staff of a 28-staff system, against
  Litolff's 779 arcs over 12. Budget a second-publisher gather by ARCS x STAVES,
  not by pages.
- **A parent at 0% CPU is not a wedge.** Mid-run the shell wrapper read 0.0%
  while its python child read 100% and 10.7 GB RSS. CLAUDE.md records this; it
  came up again, on schedule.
- **No `--musicxml`.** The exporter is imported after the gather, so a 104-minute
  run would have died at the export step on whatever `export.py` said at that
  moment. Export from the record, separately.
- **The recipe was committed BEFORE the run** so the provenance stamp — taken at
  the END — could be clean. This is the cheap move that makes a shared artefact
  worth more than a private one.
