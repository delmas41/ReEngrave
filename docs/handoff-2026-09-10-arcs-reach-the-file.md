# Handoff — arcs reach the file, a dotted rest is dotted, and what a one-verdict control is worth

Landed on `main` as `253174b3` (fast-forward from `ac482198`). This session took
the two items the 2026-09-10 handoffs ranked and parked: the **arc export** from
the notations thread, and the **dotted REST** from
`docs/handoff-2026-09-10-the-duration-reader.md` §5.1 (now marked CLOSED in
place, because that entry ends by asking whoever takes it to say so first).

⚠️ **Read this beside its two predecessors, not instead of them.** Neither the
meter arc nor the duration reader is superseded by anything here.

---

## 1. WHAT LANDED

| | |
|---|---|
| `Q.CELL_BOX` | each measure cell's own page rectangle, **gathered** (a GATHER change — see §5) |
| `staged/export.py` | `_place_arcs`, `_pair_arcs`, `_arcs_by_kind`, `_flatten_part`, `_page_box_of`, `_corners_to_wh` |
| `staged/adjudicators/rhythm.py` | `_attached_dots` scores `noteheads + rests` as ONE pool; `_rest_ruling` reads its dots the way the notehead branch does |
| the merge | `_merge_arcs_across_barlines` / `_noteheads_under` / `_number_spans` **imported and called**, never ported |
| benchmarks | `omr-staged-arc-export-2026-09/`, `omr-staged-dotted-rest-2026-09/` |

Suite **3565 passed / 11 skipped**; `health --check` and `inventory --check`
green. **Three stubs remain and are untouched**: `articulation_owner`,
`wedge_anchor`, `direction` — only the last is input-starved.

---

## 2. THE ARC RESULT

`staged/export.py` read `Q.ARC_KIND` and emitted **zero** `<slur>` — 199 arcs a
page deciding with no route to a file, one day after the same
*value-existed-and-nothing-read-it* shape was found and fixed for the dynamics,
**inside the architecture built to stop it.**

Litolff Beethoven 5, pdf pages 1-3, 12 parts, one gather exported twice:

| | OFF | ON |
|---|--:|--:|
| `<slur>` / `<tied>` | 0 / 0 | **46 / 98** |
| slurs / ties written | 0 / 0 | **23 / 49** |
| notes / rests | 1075 / 432 | 1075 / 432 |

**Controls**: byte-identical outside the arc elements; balance holds; music21
reads back 12 parts and **exactly 23 Slur objects**. The partition is exact —
514 arc rows → 476 merged groups (**38 arcs, 7.4%, are one half of a
cross-barline pair**) → 23 + 49 + 361 + 43 = 476.

⚠️ **NO OMR-NED FIGURE IS CLAIMED AND THE MERGE LANDED WITH THE EMISSION FOR
THE SAME REASON.** The metric is symmetric, so emitting more symbols is
rewarded: the legacy slur work's first cut LOWERED pooled OMR-NED while RAISING
the edit count. Emitting each half of a cross-barline arc as its own `<slur>`
would have scored *better* and been wrong. The control here is a
byte-comparison plus a partition, deliberately.

---

## 3. ⚠️⚠️ WHAT IS *NOT* ESTABLISHED — read before quoting §2

1. **76% of merged arcs (361 of 476) bind fewer than two noteheads and are
   REFUSED.** One end would leave an unpaired `<slur type="start">` and an
   INVALID file. On a scan the usual cause is that the notes under the arc were
   never detected. **So "23 slurs" is not a recovery rate** — the exporter
   recovers all the arcs that had two notes to bind, and **the remaining three
   quarters are the DETECTOR's**, the same shape this repo already records for
   hairpins on scans.
2. **n = 1 document, 1 publisher, 3 pages.** No engraved arm was run.
3. **The dotted-rest change gains nothing measurable** — see §4.
4. Nothing here touches `arc_kind`'s classification. `OMR_ARC_RECLASS`'s
   position grammar was measured on both families and REFUSED (scan +130
   edits); that refusal is **inherited, not re-litigated**.

---

## 4. THE DOTTED REST — and ⚠️ a control whose whole range is ONE verdict

`_rest_ruling` did `ev.rows(Q.AUG_DOT)` on the REST's own glyph subject — the
exact fault fixed for noteheads the day before, in the same function, one
branch over.

⚠️ **It was a DIVERGENCE, not a narrower reading.**
`rhythm._pair_dots_to_targets` has always built `dot_targets = noteheads +
rests` under the SAME two constants (*"dots after rests are rarer but real"*).
That settles the open question of whether a rest wants its own window with n=1
to calibrate on: **it does not.**

**On Litolff p1-3, NOTHING MOVED** — 1863 subjects, zero verdicts, dotted rests
0 → 0, dotted notes 1 → 1.

⚠️⚠️ **THE ZERO IS ABOUT REACH, AND ITS CONTROL IS WEAKER THAN THE WORD
"CONTROL" SUGGESTS.** The document holds **20 `aug_dot` rows over three pages**,
8 near a rest. The positive control (all dots off) moves **exactly ONE
verdict** — *that is the probe's entire dynamic range there*. It rules out a
probe comparing a file with itself and **cannot detect a regression smaller
than one verdict**, which is every regression this change could plausibly
cause. Reading "instrument LIVE" as a clean bill of health would be the same
mistake as reading the zero as a result, one step further back.

⚠️ **So the honest claim is CONSISTENCY, NOT PAYOFF** — of 848 `aug_dot` rows
across three documents, 752 attach to a notehead and **exactly ONE** to a rest.
Never quote it as a reading improvement. ⚠️ **And the COST is unmeasured**:
widening the pool can take a dot from a notehead, and this page has too few
dots to show it.

---

## 5. ⚠️⚠️ THE CONSTRAINT MOST LIKELY TO BE FORGOTTEN

**`Q.CELL_BOX` is a GATHER change, so `readjudicate` is STRUCTURALLY BLIND to
the arc path.** It rebuilds a `Log` from a SAVED record, so a new quantity never
enters and `--control` would pass whatever the change did. **Any future A/B on
arcs needs two full re-gathers**, not a re-adjudication.

`export_arc_arm.py` refuses a record predating `Q.CELL_BOX` outright rather than
reporting the zero that follows — and **it fired in this session**, on the first
record fed to it. A record gathered before the quantity existed carries no cell
boxes, every bar reports `arc_bar_has_no_geometry`, and the ON arm writes
nothing while looking like it ran.

⚠️ The `readjudicate` blind spot does **not** apply to the dotted rest, which is
adjudicate-only. That is why the two were measured with different instruments,
and it is worth checking which case you are in before reaching for either.

---

## 6. ⚠️ FOUR ACCOUNTING HOLES, THREE OF THEM IN THIS SESSION'S OWN CODE

Each was a place an arc vanished with no number attached. All four are counted,
and `test_every_placed_arc_is_written_or_counted` asserts the **partition**
rather than any one of them — which is the check that would catch a fifth.

1. a bar whose geometry is missing (the merge's `continue` skips its arcs whole);
2. an arc binding fewer than two notes;
3. a span past the slur-number ceiling;
4. ⚠️⚠️ **a span whose ends land in the SAME CHORD — found on a real page, not
   by review.** The report said **55 slurs where the file held 23**.
   `voicing._chord_span_states` discards a span whose start and stop share a
   chord ("a slur from a note to itself is a curve to nowhere"), and
   `_paired_spans` cannot catch those: it refuses two ends on one DETECTION,
   while a chord is several detections at one x. **32 of 55 marked spans.**

⚠️ **The fix for (4) is WHERE THE COUNTER LIVES, not what it counts.** It
incremented where the mark was SET; it now increments where the ELEMENT is
written. That is the `FAMILIES` table's own rule arriving from a new direction —
*a verdict says what was DECIDED, only the counter says what reached the FILE* —
and a counter at the mark measures the first while reporting it as the second.

⚠️ **Arc drops are kept OUT of the note balance**, deliberately: that control
counts noteheads and rests, and folding a different family into one side would
make `to_musicxml` raise `Unbalanced` for a reason unrelated to notes — a
control reporting a defect it was not built to see.

---

## 7. ⚠️ WHAT THE MUTATION BATTERY FOUND THAT THE TESTS DID NOT

Nine arms on the arc path, five on the rest path. **Two survived the first run,
and both were the shape the duration handoff names: *a test named for a hazard
it does not reach*.**

* **CORNERS read as WIDTH** — `[x0,y0,x1,y1]` vs `[x,y,w,h]` — turned a 140px
  arc into a 1190px one and **every assertion still passed**, because a wider
  arc still yields one span with one start and one stop. ⚠️ **Counting spans
  cannot see a frame error; only naming the NOTES can.** The fixtures sit at
  page x 1000 for the same reason: **at the origin the two spellings agree in
  every coordinate.**
* **Marking every chord member** rather than the first — every fixture used
  single notes.

⚠️ **One arm is an EQUIVALENT MUTANT, not a coverage gap**: marking bar 0 a
system break changes nothing, because at index 0 `pending` is empty and
`at_break` is read only inside `if pending and resumes`. Recorded so nobody
chases it.

⚠️ **A fixture bug looked like a code bug and was not.** The first cross-system
test asserted two halves merge; they did not, because a resuming fragment must
END ON the first note of its system (`_resumes_after_system_break`) and mine
overshot it. **The rule was right and the fixture was wrong** — check that
before "fixing" the merge.

---

## 8. THE NEXT WORK, RANKED

### 1. ✅ CLOSED 2026-09-10 — the 361 is split, and both repairs it invited are REFUSED

**Done by the next session**, marked here rather than left standing.
`benchmarks/omr-staged-arc-split-2026-09/`. It needed nothing but the record —
no truth file, no second document, no re-gather — because the staged export
passes `voice_of={}`, so every refusal is the two-note minimum.

**170 (47.1%) A** no head anywhere in the arc's own bars · **109 (30.2%) B**
bars hold heads, none under the span · **82 (22.7%) C** exactly one head.
`170+109+82+115 = 476` and `115−43 = 72 = 23+49`, closed both ways.

⚠️ **So "the remaining three quarters are the DETECTOR's" — the sentence this
entry replaces — is about half right.** At most 47% is *nothing was read
there*, and that is an UPPER bound because a wrong-staff arc lands in A too.

⚠️⚠️ **Both obvious repairs are refused by their own controls.** `arc_owner`:
a sibling staff plays under the arc's x for 95.9% of A — against a **base rate
of 92.2%** among the arcs that DID pair, so it is a base-rate artefact, not a
signal. And **widening `_SLUR_ARC_PAD_NOTEHEADS` is refused**: B decays
smoothly to 3 notehead widths with **no plateau**, so the gap that constant was
read off on an ENGRAVED page does not exist on this scan and widening just
reaches further with nothing to stop at.

**The bucket is therefore bounded and parked, not next work.** What is left is
~279 detector/geometry against 82 one-ended, with no cheap constant available.

The original entry, kept because the correction is the point:

> The export half is done; this is the DETECTOR. Before writing anything,
> **split that 361**: arcs over notes that exist but were not detected, vs arcs
> whose notes are there and the pad/geometry missed. Those need different
> repairs and the number does not currently distinguish them.

### 2. Breitkopf Brahms 1 — ONE fixture, THREE open questions

It is the second publisher that (a) the dotted rest's COST wants (371 flags /
656 dots against Litolff's 49 / 35), (b) the meter floors have been waiting on,
and (c) would give the arc work its second document. ⚠️ Its page 1-3
transcription is already committed and cloud-reproducible.

### 3. The remaining stubs

`articulation_owner` and `wedge_anchor` are **one repair each** (write the
adjudicator; inputs are gathered). `direction` is still two — `Q.DIRECTION_WORD`
is the only starved input on the record.

### 4. Unchanged from the predecessors

The scan-side meter READING (`_meter_from_digits`, `time_signature_locator`) —
the meter handoff's own #1, still blocked on a corpus. `A-DUR-5`'s unclassified
ink, Sean's standing request, still needing a RASTER pass in GATHER.

⚠️⚠️ **A HUMAN STILL OWES A DECISION ON `A-DUR-8` §5.2** — whether better bar
sums re-open `OMR_METER_CARRY` / `OMR_METER_FROM_BARS`. **This session did not
touch those floors and neither did the last two.** Do not tune them as a side
effect of anything above.

---

## 9. OPERATIONAL

* Four symlinks in a worktree: `library`, `tools/omr/training/data/weights`,
  `.venv-surya`, `.venv-omrned`. The staged pipeline needs only the weights.
* A staged gather of 3 scanned Litolff pages is **~8 min**; one `readjudicate`
  arm on that record is **~6 min**, so a 3-arm probe is ~19 min of CPU and
  longer under load. The full suite is **~9.5 min**.
* ⚠️ **The staged CLI does no weight routing** — scans want the hollow graft.
* `export_arc_arm.py <staged.json>` and
  `rest_dot_arm.py <staged.json> --positive-control` reproduce §2 and §4. Both
  print what the document can SHOW before they print any arm.
* ⚠️ The committed `rest_dot_arm` output says *"instrument LIVE"*; the probe was
  **reworded after that run** to report its range instead. A re-run prints a
  longer line — the artefact is the record of what was read, not a stale file.

```bash
OMR_SURYA_KEEP_ALIVE=0 python3 -u -m tools.omr.staged <pdf> --pages 1-3 \
    --weights tools/omr/training/data/weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt \
    --out staged.json
python3 benchmarks/omr-staged-arc-export-2026-09/export_arc_arm.py staged.json
python3 benchmarks/omr-staged-dotted-rest-2026-09/rest_dot_arm.py staged.json --positive-control
```
