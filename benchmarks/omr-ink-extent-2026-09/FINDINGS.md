# The ink-extent test: my §7 prediction is NOT SUPPORTED, and the direction I tested it in was the wrong one

**2026-09-18.** Sean: *"can you run a quick compare ink extent test?"* — the
falsification test of
[docs/breakthrough-2026-09-18-the-unit-of-enquiry.md](../../docs/breakthrough-2026-09-18-the-unit-of-enquiry.md)
§7, which I had written hours earlier. **Read-only, one committed record, no
re-gather.**

⚠️ **THE HEADLINE IS AGAINST ME: the specific prediction §7 offered as its own
falsification test does NOT hold on this document.** Recorded at its site,
because a prediction that fails and is quietly dropped is worse than one never
made.

---

## 1. WHAT §7 PREDICTED, AND WHAT IT DID

§7: comparing ink extent against the detector's box should sort
already-adjudicated failures into distinct shapes — MERGE, BARLINE, CARVED
SUB-PART, SHATTERED — and *"if that table comes back undifferentiated, the
framing is wrong."*

Joined to the crop pass's **106 blind print verdicts** (Litolff), via its own
`id → subject` crop manifest:

| print verdict | n | median ink/box area | dominant shape |
|---|--:|--:|---|
| `cannot_tell` | 63 | 13.31 | MERGE_TALL 53 |
| `stem_printed_down` | 19 | 5.85 | MERGE_TALL 16 |
| **`not_a_notehead`** | **14** | **14.93** | **MERGE_TALL 12** |
| `stem_printed_up` | 8 | 19.67 | MERGE_TALL 6 |

**CONFIRMED NOTEHEADS `AGREES` = 0.074. CONFIRMED NON-NOTEHEADS `AGREES` =
0.143.** Both populations come back **MERGE_TALL**. ⚠️ **The table is
undifferentiated, which is the condition §7 named.**

⚠️ **There IS a ratio signal and it points the right way** — junk boxes sit at a
median ink/box area of **14.93** against real noteheads' **6.01**, ~2.5×. But it
is a **continuum, not the four-way sort predicted**, n is **14** on the junk
side, and **my shape cuts (3.0, 2.5, 1.5, ≥4 components) were invented rather
than measured.** Fitting them to 106 rows with 14 junk cases would be the
"constant read off a wish" this repo refuses.

⚠️ **WHY IT FAILS IS ITSELF THE EXPLANATION, AND IT WAS ALREADY ON RECORD:
Litolff MERGES.** A *real* notehead's ink component is >3× its box area and
>2.5× its height on **59%** of confirmed heads — because the head is fused to
its stem and its beam. **On a plate where nearly every component is a merge,
"is this a merge?" has no discriminating power.** The test's natural home is
the **SHATTERING** plate — and ⚠️ **the Breitkopf record predates `OMR_INK`, so
it cannot be run there at all.** That is a real limitation, not an excuse.

## 2. ⚠️⚠️ THE METHOD FINDING: I RAN IT BOX-FIRST, WHICH IS THE ARRANGEMENT THE FRAMING SAYS IS WRONG

Every row of §1 starts from a **box** and asks what ink is under it. That is the
subject space the breakthrough document argues against — **so the test inherited
the very defect it was meant to examine.** Asked the other way round, from the
ink, the same record is highly structured:

| ink-first, 7,093 ink rows | |
|---|--:|
| pieces of ink with **ZERO detections** overlapping them | **3,018 (42.5%)** |
| pieces the detector explains **<5%** of | **3,490 (49.2%)** |
| …their share of all ink **AREA** | **36.0%** |
| pieces claimed by **MORE THAN ONE** detection | **1,607 (22.7%)** |
| coverage distribution | **BIMODAL** — p25 = 0.000, median = 0.062, p75 = 0.804 |

⚠️ **The bimodality is the most interesting thing here**: the detector either
sees a piece of ink or it does not, with very little in between.

⚠️⚠️ **AND THESE NUMBERS DO NOT VALIDATE THE FRAMING — THEY QUANTIFY THE GAP.**
`Q.INK` filters **nothing** by design, so a large share of those 3,018
zero-detection pieces will be **specks and staff-line residue**, which are not
missed music. The **36% of ink AREA** figure is harder to dismiss on size alone,
but staff residue can be large in area too. **The shape/size split is not done
here, and until it is, none of §2 is evidence that the ink is a better
subject** — only that the two populations differ by a lot.

## 3. ⚠️ FOUR CONTROLS, AND THE FIRST RUN FAILED ONE

`probe_box_first.py` refuses to report unless all pass. Output in
`out/box-first-litolff.txt`.

1. all 106 adjudicated subjects present in this record — **106/106**
2. each one's class matches the crop manifest — **106/106**
3. ⚠️ **ink corners reproduce the row's own `width_spaces`** — median error
   **0.0000** spaces over 7,093 rows
4. notehead box median width **149 px** (~1.5 staff spaces, matching the width
   lane's independently measured 1.26–1.78)

⚠️⚠️ **THE FIRST RUN REPORTED `NO_INK_UNDER_BOX` ON 100 OF 106 — a clean,
believable zero, and entirely my bug.** The two populations use **OPPOSITE BOX
CONVENTIONS IN ONE RECORD**: `glyph_box.value` is `[name, x, y, w, h]` while
`ink.detail.ink_bbox_canonical` is `[x0, y0, x1, y1]`. Read the same way, a
notehead's width comes out **−108 px**. ⚠️ **This is the exact hazard CLAUDE.md
already records** (*"`Q.GLYPH_BOX` read as `[x,y,w,h]` when the name comes
first"*) and which the breakthrough document itself predicted would *"bite
immediately"* — it did, within one run. Control 3 exists so it cannot happen
silently again.

⚠️ **A SECOND, EARLIER REFUSAL WAS ALSO CORRECT AND IS WORTH KEEPING**: the
first draft joined the **Breitkopf** standoff verdicts to the **Litolff**
record and **11 of 26 subjects "matched"** — coincidental collisions, because a
subject's last coordinate is a positional index. The probe refused. **That
accidental cross-document join is itself the breakthrough's point arriving as a
bug.**

## 4. WHERE THIS LEAVES THE FRAMING

* **§7's test, as written, is not supported.** It should be marked so.
* **The framing is neither confirmed nor refuted.** What it needs is the
  ink-first question asked properly: split §2's population by **shape and
  size**, and join it to print truth — *which piece of unexplained ink is a
  mark, and which is residue.* That is the residue adjudicator the ink findings
  already rank as next work, and it is the honest version of this test.
* **It cannot be run on the shattering plate** until a Breitkopf record exists
  with `OMR_INK` on. **That is now the blocking artefact**, and it is one
  gather.

## 5. ⚠️ NOT ESTABLISHED

One document, one publisher, 4 pages, **106 print verdicts of which 14 are
confirmed non-noteheads and 63 are `cannot_tell`** — on a plate where ~60% of
noteheads cannot be adjudicated by eye at all. My shape cuts are invented. No
shape/size split of the unexplained ink. Nothing re-gathered, no file touched,
no OMR-NED. **The ink-first figures are a measurement of the GAP between two
populations and not a test of which one is the better subject.**
