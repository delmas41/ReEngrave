# The information lifecycle — stages 4–7 and the ownership decisions

**Agent I, round 1.** Commissioned 2026-09-07 off Sean's words: *"a systematic
process that follows and analyzes each gathered piece of information and asks if
there is more information that should or could be gathered."*

**Slice, per the round-1 brief:** `yolo_detector.py`, `line_detection.py`,
`pitch_resolver.py`, `rhythm.py`, `voicing.py`, and in `transcribe.py` the
per-cell detection loop, `_drop_clipped_notehead_fragments`,
`_drop_unladdered_noteheads`, `_dedupe_cross_staff_detections`.

⚠️ **TREE STATE.** I began on a worktree 28 commits behind main. The coordinator
rebased mid-task. **Every `file:line` below was re-anchored against `61eefe21`
after the rebase** and the drift was real — `_dedupe`'s category gate moved
2711 → 2715, `_stacked_bar_count`'s median 392 → 379, `detect_beams`' fabricated
bar y 534 → 546. §3 is checked against the **1,629-line** map (post `fbbd09c1`
and `94c46e80`), not the 1,303-line copy my brief pointed at.

**No pipeline behaviour was changed.** Source read at `61eefe21`, plus two
committed read-only probes and a consumer census (method §2.0).

⚠️ **This is not a second architecture map.** Where this file repeats one of
[`docs/architecture-decision-map.md`](../../docs/architecture-decision-map.md)'s
rows it says so and cites it. The value claimed is three things it does not do:

1. **consumer verdicts re-derived, per zone** — §3 lists three places the
   standing documents are wrong or now internally inconsistent;
2. **the never-gathered register** (§5) — the quantity that was in scope and no
   line of code forms, kept apart from the computed-then-discarded list;
3. **four new measurements** over committed artefacts (§4).

⚠️ **I have taken `fbbd09c1`'s lesson as binding: a name grep is not a
consumption graph.** Every `NOBODY` / `probe` verdict below was settled by
*reading the consuming expression*, not by counting hits — which is how §3.3
found the map's own two halves now disagreeing, and how S16's single
"production reader" turned out to be a `pop()`.

---

## 0. The one-line answer for this slice

> The map's finding for this region is that **detection confidence dies here**.
> True, and it understates the case in two directions.
>
> **(a) The one tier the ownership decision trusts above the coin flip is built
> from the lowest-confidence class on the page** — `ledgerLine`, median 0.337
> and 0.344 across two scanned editions, 70–72% of it under 0.40 — and neither
> of its two consuming sites reads a confidence at all.
>
> **(b) 9.6% of contested pairs are two readings of one piece of ink that
> disagree about WHAT IT IS** (436 of 4,521: `beam` vs `tie` ×118,
> `flag8thUp` vs `flag16thUp` ×18, `dynamicF` vs `dynamicP` ×22). The pipeline
> gates a pair on `category` equality, never compares `class`, and settles 434
> of those 436 by distance to a staff band.

Both are free to record and neither has a consumer today. Per
[`benchmarks/omr-additive-vs-gated-2026-09/FINDINGS.md`](../omr-additive-vs-gated-2026-09/FINDINGS.md)
§1.5, that is the correct state to ship them in.

---

## 1. The schema, and what I changed

The brief supplied ten fields. I argue for **thirteen**: three additions, no
deletions, each justified by a case in this slice where the ten fields give the
same answer for two signals that should be ranked apart.

| # | field | why |
|---|---|---|
| 1 | **signal + producer `file:line`** | as briefed |
| 2 | **what it measures · unit · range** | as briefed |
| 3 | **fidelity + DESTRUCTION SITE `file:line`** | ⚠️ **changed.** "Is it stored at the precision it was computed" is a yes/no; what a patch needs is the *expression* where precision is lost. Naming the line is what turns "record the refusal" from a design task into a mechanical diff. Every row below carries one. |
| 4 | **provenance tier + independence** | as briefed (map §0.2 vocabulary) |
| 5 | **consumers, by zone, read not grepped** | as briefed. Zones: `prod_omr` = `tools/omr/**` less `tests/`, `annotate/`, `training/` · `prod_tooling` · `backend` · `frontend` · `testbench`. |
| 6 | **who *should* read it** | as briefed |
| 7 | **cost to gather** | as briefed |
| 8 | **cost to consume** | as briefed |
| 9 | **provenance risk / shared ancestor** | as briefed |
| 10 | **the ONE settling measurement + can a harness SEE it** | as briefed |
| 11 | **VOLUME — times formed per document** | ➕ **added.** `imgsz_for_cell` fires ~10⁴–10⁵ times a document; `LocatedClef.symmetry` ~10². Volume sets both the recording cost and the reach, and the probability-gates handoff §4 is explicit that **reach is measured before precision**. Without it, "record the refusal" reads as one uniform recommendation when it is two — a few hundred bytes for a clef trace, and a *schema* decision for anything per-detection. |
| 12 | **FAILURE DIRECTION — does absence under- or over-claim, and is the failure visible?** | ➕ **added**, from additive-vs-gated §1.4. Not implied by A–E: `_drop_unladdered_noteheads` and `_drop_clipped_notehead_fragments` are both hard geometric deletions, but one sits on a documented empty gap and one deletes a 0.95 detection in silence. |
| 13 | **ARITY — 1-of-2, 1-of-N, or a count** | ➕ **added.** A binary refusal and an argmax over five readers are both "Class D" and want different records: the binary wants a margin, the argmax wants the losing list. ⚠️ **Nowhere in this slice is a losing-candidate list kept** — `pitch_candidates` is the sole exception, and §2.3 S16 shows its one production "reader" deletes it. |

**Not added, deliberately:** a priority column. Ranking belongs in §6 against the
standing shortlist; a per-row priority invites a second ranking that drifts.

---

## 2. The signal table

### 2.0 Census method, and its limit

Per-zone WRITE/READ counts from a script over every `.py`/`.ts`/`.tsx` in the
tree. Write pattern `"k":` | `["k"] =` | `.k =`; read pattern `.get("k")` |
`"k" in` | `["k"](?!\s*=[^=])` | `.pop("k")` | `.k` not followed by `=`.
**The map's documented regex trap is guarded** — naive `\["k"\][^=]`
false-positives on `st["k"] = {` because `[^=]` eats the space.

⚠️ **The census is a candidate generator, not a verdict.** `fbbd09c1`'s E1 is
the standing counter-example: `nominal_line_spacing_px` reads as unconsumed and
is returned by a *property* with 15 readers. So every verdict below was settled
by opening the consuming expression — which is why S16 reads "1 production hit,
and it is a `pop`" rather than "1 consumer", and why §3.3 exists.

### 2.1 Stage 4 — `yolo_detector.py`

| # | signal (producer) | measures / unit | fidelity — destroyed at | consumers (read, not grepped) | should read it | gather | volume | fail dir. | arity | settling measurement |
|---|---|---|---|---|---|---|---|---|---|---|
| S1 | **detection `confidence`** (`yolo_detector.py:387`) | model posterior 0–1 | kept to the JSON at 3dp (`transcribe.py:1980`); dies at every consumer | prod_omr, **4 decisions**: `transcribe.py:1244`, `:1495`, `:1604` (three argmax) · `:3098` (the one threshold). `export.py` reads it **0 times** — `[V1]` re-verified, `grep -c` = 1, line 1003, prose | ownership (`:2645`), the ladder (`:2519`), export, `voicing`'s duration vote | paid | ~10⁴–10⁵ | absence over-claims (a 0.26 box exports as certainly true), invisible | continuous | already scoped: additive-vs-gated §5.4 item 4 |
| S2 | **class id → vocabulary block** (`:372-374`) | int 0–207 | destroyed at `:374`; only the NAME enters `SymbolDetection` | none | `class_aliases.unaccounted()`, which map D17 shows is never called at load | paid | as S1 | absence is silent (`category="unknown"`) | 1-of-208 | count `unknown`-category detections per checkpoint |
| S3 | **per-cell `imgsz`** (`imgsz_for_cell:253`, used `:342`) | inference scale, px | ⚠️ a **local variable inside `detect()`** — never returned, never recorded. `out["imgsz"]` (`transcribe.py:4108`) stores the *argument*, `None` on the production default | none | any post-hoc reading of a confidence distribution | paid | ~10⁴ | absence makes a class of analysis impossible after the fact | continuous | ⚠️ **MEASURED, §4.3**: of 28 committed transcriptions carrying the field, **6 read `None`** |
| S4 | **NMS-suppressed boxes** (`predict(iou=0.7, agnostic_nms=False)`, `:345-353`) | count + suppressed classes | never formed | — | §4.1's question from the detector's side | paid inside ultralytics | as S1 | absence is total | count | class (iii), §5.3 |
| S5 | **the 208-way class score vector** | per-box posterior | never formed — ultralytics returns argmax post-NMS | — | "how close was the runner-up class" | **new read** (model hook) | as S1 | — | 1-of-208 | class (iii), §5.3 |

### 2.2 Stage 5 — `line_detection.py`

| # | signal | measures / unit | fidelity — destroyed at | consumers | should read it | gather | volume | fail dir. | settling measurement |
|---|---|---|---|---|---|---|---|---|---|
| S6 | **`LineDetection.confidence`** (`:59`, set `:329`, `:549`) | — | **no probability is ever formed**; the dataclass comment says *"conf is arbitrary"* | **exactly one**, `rhythm.py:752`, and §3.1 shows that sort is inert for the case it was written for | — | — | 10³ | — | map Class A, already recorded |
| S7 | **component `area`** (`stats[i]`, `:309` stems, `:524` beams) | px² | consumed as a floor only; **the FILL RATIO `area/(w·h)` is never formed** | none | `detect_beams`' shape filters, which separate a beam from a slur only by demanding two stem ends | paid — already unpacked | 10³–10⁴ | under-claims | ⚠️ **the module publishes the separation itself**: `_stacked_bar_count`'s docstring measures *"sloped beams fill only 43-46% of their box against 95% for a level one"*. §5.2 N5b |
| S8 | **per-column bar-run counts** (`_stacked_bar_count`, `:374-379`) | ints per sampled column | `np.median(counts)` at `:379` — the **spread** dies there | none | the meter reconciliation, which exists to arbitrate this | paid | 10³ | over-claims: 1/3/2 and 2/2/2 are indistinguishable | map row confirms |
| S9 | **the bars' ACTUAL y positions** (`cols & ~above`, `:374-376`) | px | ⚠️ computed as a boolean mask and never read as positions; `detect_beams:546` then **fabricates** them as `y + k·(h/n_bars)`, evenly spaced | — | `rhythm._beams_attached_to_stem`, which **clusters beam y-centres to decide the duration** | paid | 10³ | over-claims — the clustering runs on synthesised coordinates | ⚠️ §5.2 N4, and §6 item 3 |
| S10 | **`_attached_stem_count` result** (`:433`) | count | `if attached < min_attached_stems: continue` — 2 and 9 stop identically | none | the beam's own reliability | paid | 10³ | under-claims, visibly | record beside the beam |
| S11 | **anchor-excluded stems** (`detect_beams:518-521`) | count | never formed | none | "this beam had 5 candidate stems, 4 too short" | paid | 10³ | under-claims, invisibly | record the count |

### 2.3 Stage 6 — `pitch_resolver.py` and the cell loop

| # | signal | measures / unit | fidelity — destroyed at | consumers | should read it | volume | fail dir. | settling measurement |
|---|---|---|---|---|---|---|---|---|
| S12 | ⚑ **staff-position residual `pos_float − pos`** (`pitch_resolver.py:180`) | half-steps 0–0.5 | `int(round(pos_float))` at `:181`, in the same expression; **and again, independently, at `:231`/`:232`** | none | **everything downstream of pitch**; the parity-flip line `OMR_CELL_LINE_TRACE` was priced on is exactly this quantity | 10⁴ | over-claims: a note dead on a line and one halfway between export identically | map §7.1 item 11 — **this slice adds the volume (the highest-volume free item in the pipeline) and the second destruction site** |
| S13 | **the SPREAD of a cell's four staff-line gaps** (`:172-174`) | px | `avg_gap = sum/len` at `:173` | none | the grid-reliability question; the direct measure of how well `_cell_line_offset`'s rigid comb fitted | 10⁴ | over-claims | ⚠️ **never formed** — §5.2 N1 |
| S14 | **notehead height ÷ staff spacing, at the pitch site** | staff spaces | never formed *here* | — | pitch. ⚠️ The identical expression IS formed at `transcribe.py:558` and used to **delete** | 10⁴ | over-claims | §5.2 N2 |
| S15 | **ink centroid inside the notehead box** | px | never formed — `y_center` is `y + h//2` (`template_matcher.py:109`) | — | pitch. ⚠️ This project measured box-centre vs blob-centre differing by **up to a full half-step** on the labeling side and moved the annotate snap to the blob; **the resolver never did** | 10⁴ | over-claims | class (iii), §5.3 N12 |
| S16 | **`pitch_candidates`** (emitted `transcribe.py:1987`) | (pitch, weight)×3 | kept | ⚠️ **production readers: ZERO.** The single `tools/omr` hit is `clef_correction.py:312`, `det.pop("pitch_candidates", None)` — a **delete**. Out of band: `tools/maestro_bridge/re-rank.ts` ×3, off by default | — | 10⁴ | — | map §7.3 item 15; verified by reading, per `fbbd09c1`'s lesson |
| S17 | **`_notehead_fill_ratio`** (`transcribe.py:406`, called `:475`) | ink fraction 0–1 | **destroyed at `:477-484`** in a two-branch comparison; no field, no provenance flag | none | the hollow-notehead thread, CLAUDE.md's largest recorded scan duration fault | 10⁴ | absence is total — a class is silently rewritten | §3.2, §5.2 N3 |
| S18 | **`best_clef_conf`** (`:1604-1607`) | 0–1 | computed, then not carried out of the loop; the losing readings are dropped with no `clef_candidates` list | none | the five-reader precedence ladder, which arbitrates on `clef_source is None` alone | 10²–10³ | over-claims | map Stage 6 row, unchanged here |
| S19 | **`_find_attached_stem`'s `best_dx`, and `has_stem`** (`:648-683`) | px / bool | `best_dx` dies at return; `has_stem` is computed at `:1829` for the fill correction and again at `:1841-1855` for direction, and **never emitted** | none | duration (a stemless black head is a reading fault), `voicing` | 10⁴ | over-claims | §5.2 N11 |
| S20 | **`_pair_accidentals_to_noteheads`' winning score** (`:927`) | composite | argmin, discarded; a second accidental can overwrite a claim with no conflict record | none | the accidental ladder | 10³ | over-claims | map Stage 6 row |

### 2.4 Stage 7 — `rhythm.py`, `voicing.py`

| # | signal | measures / unit | fidelity — destroyed at | consumers | should read it | volume | fail dir. | settling measurement |
|---|---|---|---|---|---|---|---|---|
| S21 | **beam-cluster gap sizes** (`_beams_attached_to_stem._count`, `:971`) | px | `if ys[i]-ys[i-1] > tol` — the gap dies in the comparison | none | `_reconcile_measure_to_meter`, which exists to arbitrate this and is handed only the integer `beam_levels` | 10⁴ | over-claims: a 0.34-vs-0.36 call and a 3× margin are identical | map row; **volume added** |
| S22 | **the LOSING stem end's beam count** (`:975`) | int | dies in the `max(_count(top_ys), _count(bot_ys))` | none | beams at BOTH ends of a stem is physically impossible — a free, loud signal that the stem pairing failed | 10⁴ | over-claims, silently | ⚠️ **not in the map** — §5.1 N7 |
| S23 | **`_deduplicate_beams`' confidence sort** (`:752`) | 0–1 | live for YOLO-vs-YOLO; **inert for CV-vs-YOLO** | — | — | 10³ | — | ⚠️ **CORRECTS the map's still-live D23** — §3.1 |
| S24 | **`_pair_dots_to_targets`' score** (`:1137`) | `dx + 2·|dy|`, px | argmin, discarded; no floor; **a second dot silently double-dots the same target** (`result[id(best)] = result.get(...) + 1`, `:1142`) | none | the dot rule, whose own docstring names the double-stop hazard | 10³ | over-claims: a triple dot is accepted in silence | §5.1; free |
| S25 | **`_flag_for_notehead`'s `best_dist`, and the beam↔flag contradiction** (`:1038`; the gate at `:1589`) | px / bool | `best_dist` dies at return; the flag is consulted **only when the beam count is exactly 0**, so a 1-beam note beside a `flag16thDown` never has the contradiction formed | none | duration | 10³ | over-claims | map row; ⚠️ §4.1 gives it a measured population — **39 contested flag-VALUE disagreements** |
| S26 | **`_tuplet_groups`' refusal reason** (`:1336`) | — | `continue`, no record | none | the quarter-plus-eighth triplet the docstring names as real and unhandled | 10¹–10² | under-claims, invisibly | §5.1 N8; free, and small enough to eyeball |
| S27 | **`voicing`'s chord duration-vote count** (`voicing.py:204`) | int | ⚠️ literally `(best…), _ = durations.most_common(1)[0]` — **bound to `_`**; a 1–1 tie breaks on `Counter` insertion order | none | `beam_levels`, the REASON two members disagree, is on both notes and unread | 10³ | over-claims | map §7.1 item 8 — this row supplies the exact expression |
| S28 | **`voicing`'s stem-direction vote count** (`:210`) | int | dies in `.most_common(1)[0][0]` | none | as above | 10³ | over-claims | free |

### 2.5 The ownership decisions — `transcribe.py`

| # | signal | measures / unit | fidelity — destroyed at | consumers | volume | fail dir. | settling measurement |
|---|---|---|---|---|---|---|---|
| S29 | **`_ledger_ladder`'s `(complete, rungs)`** (`:2519-2556`) | ints | ⚠️ **each call site reads one half and neither reads both.** `_dedupe:2737` reads `[0]` and drops the count; `_drop_unladdered_noteheads:3105-3110` computes `n_expected`, then reads `[1] == 0` and drops `n_expected` | none | 10³ | over-claims both ways | ⚠️ **not in the map as a pair** — §5.1 N6 |
| S30 | **`ledgerLine` detection confidence** (`_ledger_rows:2510`) | 0–1 | **never read** — the filter is `det.get("class") != "ledgerLine"`, then the bbox is taken | none | 10³ | over-claims | ⚠️ **MEASURED, §4.2 — the headline** |
| S31 | **the pair's IoU** (`_bbox_iou_xywh`, used `:2717`) | 0–1 | `if iou <= threshold: continue` — 0.31 and 0.95 proceed identically | none | 10³–10⁴ | over-claims | map row |
| S32 | **the two band distances and their MARGIN** (`:2763-2766`) | px | computed inside a ternary; **neither value nor the margin survives** — and `OMR_CONTEST_DUMP` records confidences and the tier but *not* the distances | none | 10³–10⁴ | over-claims; documented as a coin flip at 5–62 px | additive-vs-gated §5.3 already shortlists recording it |
| S33 | **the two readings' CLASS agreement** (`class_i` vs `class_j`) | bool | ⚠️ **never formed.** The pair gate is `category` equality only (`:2715`) | none | 10³–10⁴ | over-claims | ⚠️ **MEASURED, §4.1** |
| S34 | **the three drop counters** | ints | kept | **prod 0 · backend 0 · frontend 0 · `probe` for all three** | 1/page or /run | — | §3.3 |
| S35 | **per-deletion reason** (any of the three drops) | — | never formed — only the count | — | 10²–10³ | absence is total | class (ii) |

---

## 3. Where I disagree with the standing documents

**The tree outranks the ledger**, including this file. Each row was read at
`61eefe21`.

### 3.1 ⚠️ D23 is right that a fifth confidence site exists and wrong about which way it decides

Still live in the current map at `:693` (the Stage-7 row) and `:1286` (D23
itself), which describes `_deduplicate_beams` as *"a lower-confidence CV stroke
loses to a higher-confidence YOLO box."*

**That direction is unreachable on the production path.** Two facts, both inside
`resolve_rhythms_for_cell`:

- `rhythm.py:1523-1525` builds the list as
  `list(cv_beams) + [y for y in beams if not _overlaps_any_in_x(y, cv_beams)]`
  — a YOLO beam survives **only if it overlaps no CV beam in x**;
- `_deduplicate_beams:769` requires x-overlap ≥ 0.6 of the candidate's own width
  before it will call two beams duplicates.

A CV/YOLO pair therefore **cannot both be in the list and overlap enough to be
compared**. The sort is live only within the YOLO subset (a column the CV
detector was silent in, or `extra_lines` absent) and within the CV subset, where
every value is 1.0 by fiat and the sort degenerates to `detect_beams`' emission
order.

The count of five stands; the mechanism does not. `_deduplicate_beams`' own
docstring (*"CV + YOLO both fired on the same stroke"*) describes a case the
merge above it already removed — the same shape as D13.

**Consequence:** there is nothing to fix here. The behaviour D23 implies should
be built (make the CV stroke win) is already the behaviour.

### 3.2 `_notehead_fill_ratio` is a ONE-WAY ratchet, and no document says so

Map D12 correctly reports that the docstring's three fill bands are two branches
in code. One line short of the more consequential fact —
`transcribe.py:472` is

```python
    if "black" not in lname:
        return
```

so the correction runs **only on heads the detector called black**. A hollow
class on a *solid* head — `noteheadHalf` where the ink says `noteheadBlack` — is
never tested and never corrected. The rewrite is a one-way ratchet toward
hollow, and its input float is discarded either way (S17).

⚠️ It points *into* the pipeline's known scan fault. CLAUDE.md records half notes
read as something shorter as the dominant scan duration error, and records
"reclassifying by ink fill" as **tried and refused** — a refusal made about the
*missing-detection* case ("nothing to reclassify"), not about this rewrite. The
two have been conflated since.

### 3.3 ⚠️ The map's §5 and §6.1 now disagree with each other about the three drop counters

`fbbd09c1` corrected §5's Stage-4/5 rows to `probe`, with exact probe file:line
for `_drop_clipped_notehead_fragments` and `_drop_unladdered_noteheads`.
**§6.1's verdict table was not updated** and still files all three under
SERIALISED-ONLY (`:1057`).

Read: `probe` is right for **all three**, including
`n_cross_staff_duplicates_removed`, which §5 has no row for at all —
`omr-additive-vs-gated-2026-09/probe/dump_contests.py:92`,
`probe/probe_gate_reach.py:79`, and now this audit's own
`probe/probe_ownership_reach.py:23`. Production, backend and frontend read none.

⚠️ **And one asymmetry inside them nothing records.** Two are written per page
*and* per run; `n_clipped_notehead_fragments_dropped` is written **only at run
level** (`transcribe.py:4119`, `:4543`), so unlike its siblings it cannot be
localised to a page. If any of the three becomes evidence, that one needs a
schema change first.

### 3.4 Two of the map's claims I re-verified and confirm

- **`[V1]`** — `grep -c '\bconfidence\b' tools/omr/export.py` → **1**, line
  1003, inside a prose paragraph about fermatas. Holds exactly.
- **The four confidence decision sites** — present at `transcribe.py:1244`,
  `:1495`, `:1604`, `:3098`. Three argmax, one threshold, as documented.

### 3.5 ⚠️ Thirteen decision points in this slice have no §5 row — and one of them DELETES

Per the coordinator's note that *"what is MISSING outranks what is wrong"*, and
`fbbd09c1`'s finding of 185 uncatalogued points. Enumerated from code in my slice
alone, against the current 176-row §5:

| uncatalogued decision | where | note |
|---|---|---|
| **the spurious-rest filter** | `rhythm.py:1424-1480` | ⚠️ **three deletion branches** (off-staff above, off-staff below, duplicate-of-notehead, duplicate-of-earlier-rest), every one a bare `continue` — **no count, no reason, no record.** The pipeline's fourth silent deletion rule and the only one with no §5 row and no counter at all |
| `_filter_stems_overlapping_tremolo` | `transcribe.py:612` | a 0.3 overlap gate; symmetric deletion, no record |
| `_find_attached_stem` | `transcribe.py:648` | argmin on `best_dx`, ties by iteration order |
| `_stem_direction` | `transcribe.py:685` | decides voice membership downstream |
| `_pair_ties_in_cell` / `_pair_ties_in_staff` | `transcribe.py:2227` / `:2038` | the coordinator's note counts 25 tie-pairing points; §5 has zero |
| `_attach_articulations_in_cell` | `transcribe.py:2170` | 21 of 218 marks left unattached, unrecorded |
| `_spans_the_whole_cell` / `YOLO_BEAM_MAX_CELL_FRACTION` | `rhythm.py:805` | a measured empty gap (0.5–0.7), correctly gated, uncatalogued |
| `_beamed_groups`' pad and identical-member collapse | `rhythm.py:1226` | the fault that cost 464 edits on Mozart 41 |
| `voicing._directions_conflict` and `chord_x_tolerance` | `voicing.py:167`, `:147-152` | what makes two notes one chord |
| `detect_beams`' anchor filter | `line_detection.py:518-521` | S11 |

⚠️ **And two bare pixel constants**, in a codebase that scales everything by
staff spacing: `rhythm.py:1444` `else 30` (the notehead-width fallback that sizes
the rest filter's x tolerance) and `voicing.py:152` `chord_x_tolerance = 30.0
# fallback`. Both are canonical-coordinate constants with no measurement behind
them — the same shape as the map's `measure_extractor:1060` 10-px finding.

### 3.6 Orphan producers in and beside this slice

Per the coordinator's instruction. **Within the slice's five files: none** —
every producer has a call site. Adjacent, and already catalogued: the two CV
rungs that parallel `line_detection` are both orphans —
`hairpin_detection.py` (344 lines, map D21) and `bracket_reader.py` (390 lines,
map `:889`, `:1182`). ⚠️ Worth stating for this slice specifically: the dataclass
my whole slice passes around, `SymbolDetection`, lives in
`template_matcher.py`, **a module whose own detector is dead** — including
`y_center` at `:109`, the expression S15/N12 is about.

---

## 4. New measurements

All read-only over committed artefacts. Probes committed under `probe/`.

### 4.1 ⚠️ 9.6% of contested pairs are two readings that disagree about WHAT the ink is

`probe/probe_contest_class_disagreement.py`, over the 20 committed
`OMR_CONTEST_DUMP` files of the 20-row scan gate.

`_dedupe_cross_staff_detections` gates a pair on **`category` equality**
(`transcribe.py:2715`) and never compares `class`. A `beam`-classed copy and a
`tie`-classed copy of one arc are deduplicated exactly like two agreeing copies,
and the fact that the pipeline's own two reads contradicted each other is not
formed, not recorded, not available.

**436 of 4,521 pairs = 0.0964.** By tier, **434 of them are decided by DISTANCE.**

| category | tier | n | class-disagreeing | rate |
|---|---|--:|--:|--:|
| structural | distance | 2197 | 295 | 0.134 |
| dynamic | distance | 869 | 38 | 0.044 |
| notehead | distance | 550 | 16 | 0.029 |
| notehead | **ladder** | 266 | **2** | **0.008** |
| accidental | distance | 198 | 31 | 0.157 |
| **flag** | distance | **102** | **47** | **0.461** |
| ornament / rest / clef / time-sig / stem | distance | 339 | 7 | 0.021 |

What they disagree about:

| the two readings | n | what that decides |
|---|--:|---|
| `beam` / `tie` | 118 | duration, or an arc |
| `slur` / `tie` | 74 | the arc's kind — the family `OMR_ARC_RECLASS` was built for |
| `beam` / `slur` | 71 | duration, or an arc |
| `dynamicF` / `dynamicP` | 22 | **opposite dynamics** |
| `flag16thUp`/`flag8thUp` · `flag16thDown`/`flag32ndDown` · `flag16thUp`/`flag32ndUp` | 18+12+9 | **the note's duration**, on an unbeamed note |
| `accidentalFlat` / `accidentalNatural` | 15 | **the pitch** |
| `noteheadBlackInSpace` / `noteheadBlackOnLine` | 13 | a diatonic step |

**47 of 102 contested flags (46.1%) disagree about the flag's value**, every one
settled by distance — and `rhythm._flag_for_notehead` → `_flag_duration` makes
that class *the note's duration* whenever the beam count is zero (S25).

**Confidence has more to say on exactly this subpopulation.** Median |Δconf|:

| | n | median &#124;Δconf&#124; |
|---|--:|--:|
| the two readings AGREE about the class | 4085 | **0.059** |
| the two readings DISAGREE | 436 | **0.137** |

⚠️ **Controlled for category**, because flags and structural dominate the
disagreeing set: the gap survives *within* every category with n ≥ 18 —
structural 0.084 → 0.155, dynamic 0.050 → 0.107, notehead 0.031 → 0.074,
accidental 0.041 → 0.133, flag 0.073 → 0.102. Not a mix artefact.

⚠️ **What this does NOT show.** A larger margin means the quantity has more to
say, not that the higher-confidence side is *right* — no corpus records which
class a contested glyph really is, so additive-vs-gated's **T5 fails** here too.
What it does establish is that the pipeline settles these 436 by *distance to a
staff band*, a quantity about ownership and uncorrelated with class correctness
by construction.

⚠️ **SHARED SUBSTRATE.** These are the same dumps
`benchmarks/omr-additive-vs-gated-2026-09` measured its 0.617 ladder-agreement
figure on. A different column of one table — **not independent corroboration**.

### 4.2 ⚠️ The one trusted ownership tier is built from the page's weakest class

`probe/probe_confidence_by_class.py`, two committed scan transcriptions, two
editions, two weight files.

The map establishes ~29.7% of a scanned page's detections under 0.40. That pool
is not uniform:

| | beet5-p02 (Litolff, graft weights) | brahms1 (Breitkopf, imgsz2048-ft) |
|---|---|---|
| all detections | n=2797, median 0.515, **33.0%** < 0.40 | n=10523, median 0.497, **35.3%** < 0.40 |
| notehead | median 0.710, 17.9% | median 0.550, 28.3% |
| dynamic | median 0.794, 5.5% | median 0.732, 14.3% |
| clef | median 0.846, 9.8% | median 0.734, 12.6% |
| **structural** | **median 0.400, 50.0%** | **median 0.399, 50.2%** |

Inside `structural`:

| class | beet5-p02 | brahms1 | what it feeds |
|---|---|---|---|
| **`ledgerLine`** | n=633, **median 0.337, 71.6% < 0.40** | n=768, **median 0.344, 69.9% < 0.40** | **the ladder tier** and `_drop_unladdered_noteheads` |
| `tie` | n=111, median 0.366, 61.3% | n=828, median 0.359, 62.7% | export |
| `beam` | n=176, median 0.487, 34.1% | n=945, median 0.453, 41.8% | duration, where CV is silent |
| `augmentationDot` | n=13, median 0.550 | n=465, median 0.718 | dots |

**So:** the ladder is the *only* evidence `_dedupe` ranks above distance on a
dossier-free scan — the code calls it *"the strongest evidence in the
function"* — and `_ledger_rows:2510` assembles it from the class with the lowest
median confidence on the page, **with no floor at either consuming site**. The
same class then licenses `_drop_unladdered_noteheads` to **delete a real note**
on `found == 0`.

⚠️ **A00 applies and I am observing it.** This is **not** a claim that the ladder
is unreliable — it fired on 266 pairs and this project uses it as an internal
gold standard. The claim is narrower and it is about information: **the number
that would let anyone ask is on the same dict and no line reads it.** Whether a
floor helps is UNMEASURED; §6 item 5 names the reach probe that must come first
and states the two ways it could fail for reasons unrelated to the mechanism.

⚠️ n = 2 pages. They agree, and they differ in publisher and in weights — the
axis that has burned this project before (Simrock 45/45 vs Litolff 2/50). Two is
still two.

### 4.3 The actual inference scale is unrecoverable on every modern run

Across all committed transcriptions carrying an `imgsz` field (**n = 28**):
`1280` ×17, `640` ×5, **`None` ×6**. `None` is what `out["imgsz"]`
(`transcribe.py:4108`) stores when the argument is unset — the production
default, where `imgsz_for_cell` computes a *different* value for every cell and
holds it in a local at `yolo_detector.py:342`. The module docstring is explicit
that this number decides whether the model recognises a notehead; it is computed
~10⁴ times a document and written down zero times.

### 4.4 Every contested notehead is a pitch coin flip

`pitch_i == pitch_j` on **0 of 816** contested notehead pairs. Trivially true —
different clefs, different anchors — but it converts an ownership statistic into
a pitch statistic: **816 contested noteheads on the 20-row gate are 816 pitch
decisions, 550 of them made by distance.**

---

## 5. THE NEVER-GATHERED REGISTER

Three classes, kept apart because they cost different amounts.

### 5.1 Class (i) — computed and discarded

The map covers this exhaustively (§7.1–§7.3) and I do not re-derive it. Rows
S12, S18, S20, S21, S24, S25, S27, S28, S31, S32 are its rows with a
destruction-site `file:line` and a volume added. **Four are new:**

| | the discard | where | why it matters |
|---|---|---|---|
| **N5** | **the rank-0 APPLICATION ORDER.** `sorted(verdicts, key=lambda v: -v[0])` sorts on rank only. Python's sort is stable, so within rank 0 — **94.1% of all pairs** — the order is append order, i.e. y-bucket iteration order. `if loser in doomed or winner in doomed: continue` then lets that order decide which verdicts are *skipped* in an overlapping chain | `transcribe.py:2812-2816` | the natural key inside a rank is the DISTANCE MARGIN, computed at `:2763-2766` and destroyed there (S32). An ordering exists for free and is not used |
| **N6** | **`_ledger_ladder` returns `(complete, rungs)` and neither call site reads both** | `:2737` reads `[0]`; `:3105-3110` computes `n_expected` and reads only `[1] == 0` | a note 4 spaces out with 1 rung survives identically to one with 4, and a *broken but long* ladder is worth nothing to the deduper. One function, two consumers, two different halves |
| **N7** | **the losing stem end's beam count**, dying in a `max` | `rhythm.py:975` | beams at both ends of one stem is physically impossible; a free, loud signal that the stem pairing failed |
| **N8** | **`_tuplet_groups`' refusal reason** | `rhythm.py:1336` | "a `tuplet3` was read and refused because the group holds 4 notes" is the quarter-plus-eighth triplet the docstring names as real and unhandled |

### 5.2 Class (ii) — available and never computed

⚠️ **The register's core.** Every input is in hand; **no line of code forms the
quantity.** None appears in the map, and `git log --all -S` over `tools/omr/`
finds zero commits for any of them (`imgsz_used`, `fill_ratio"`, `pos_residual`,
`staff_position_residual`, `class_disagree`, `band_distance`).

| | the quantity nobody forms | inputs already in hand | the decision blind to it | cost |
|---|---|---|---|---|
| **N1** | **the SPREAD of a cell's four staff-line gaps** | `cell.staff_line_ys_canonical`, read at `pitch_resolver.py:172`, `line_detection.py:96`, `rhythm.py:717` — ⚠️ **three modules independently reduce the same five numbers to one mean and none keeps the residual** | pitch (S12/S13); and it is the direct measure of how well `_cell_line_offset`'s rigid comb fitted, which `OMR_CELL_LINE_TRACE` was priced on | one subtraction |
| **N2** | **notehead height ÷ staff spacing, at the pitch site** | both, at `pitch_resolver.py:157-183` | pitch. ⚠️ The identical expression IS formed at `transcribe.py:558` and used to **delete**. A 1.4-space blob — a merged chord, a print-merged rung — resolves to one confident pitch and nothing asks | one division |
| **N3** | **the fill ratio as a KEPT number, and the reverse test** | `_notehead_fill_ratio` already returns it | S17 / §3.2. The ratchet is one-way and its input is thrown away, so nobody can ask how many heads sat near 0.75 | one field |
| **N4** | ⚠️ **a multi-bar beam component's ACTUAL bar positions.** `_stacked_bar_count` computes the per-column run-START mask (`cols & ~above`, `line_detection.py:374-376`) — those rows *are* the bar positions — reduces it to a median count, and `detect_beams:546` **fabricates** the positions as `y + k·(h/n_bars)`, evenly spaced | the label mask, already computed | ⚠️ `rhythm._beams_attached_to_stem` **clusters beam y-centres to decide the duration.** Whenever `n_bars > 1` it clusters synthesised coordinates — and the module's own docstring says a sloped beam's box is far taller than its bar, so even spacing is exactly wrong there | a row-mean per run |
| **N5b** | **the beam component's FILL RATIO** `area/(w·h)` | `stats[i]` unpacks `area` at `line_detection.py:524` and uses it only as a floor | `detect_beams`' shape filters, which separate a beam from a slur only by demanding two stem ends. ⚠️ **The module publishes the separation itself**: *"sloped beams fill only 43-46% of their box against 95% for a level one"* — measured, in the docstring, never computed | one division |
| **N9** | **the CLASS-agreement of a contested pair** | `di["class"]`, `dj["class"]`, both in scope at `transcribe.py:2715` | ownership — §4.1 measures the population at **436 pairs, 9.6%** | one comparison |
| **N10** | **how many staves claimed one glyph** | the pairwise loop sees each pair; a 3-staff contest becomes 3 pairs | ownership. A glyph two staves want and one three staves want are the same to the rule. ⚠️ **UNMEASURED** — the dump carries no detection ids | a counter |
| **N11** | **`has_stem`, as an emitted fact** | computed at `transcribe.py:1829` and again at `:1841-1855` | a black notehead with no stem is a reading fault the exporter never learns about; and `voicing.split_events_into_voices` silently collapses to one voice on a page with no CV stems, which **enables** `_reconcile_measure_to_meter` on every measure | one bool |
| **N16** | **the spurious-rest filter's deletion count and reasons** | the three `continue` branches at `rhythm.py:1424-1480` | ⚠️ the only silent deletion rule in the pipeline with **no counter at all** — its three siblings each write one (S34) | a counter and a reason string |

### 5.3 Class (iii) — obtainable only with a new read

Priced, so the difference from (ii) is visible.

| | quantity | what must be re-read | rough cost | worth it? |
|---|---|---|---|---|
| **N12** | **the ink centroid inside a notehead box** (S15) | one crop of `cell.image_no_staff` per notehead + a first moment | ~10⁴ crops of ~50×50 px per document — the same order as `_notehead_fill_ratio`, which the pipeline **already pays for every notehead**, so the marginal cost is near zero | ⚠️ **the strongest (iii) candidate.** The labeling side measured box-centre vs blob-centre differing by up to a half-step and moved to the blob; the resolver never did. ⚠️ And a documented failure mode transfers directly — a print-merged ledger rung drags the centroid, which is exactly why the labeling audit's own box-relative fix did **not** generalise. Measure, do not assume |
| **N13** | **the 208-way class score vector** (S5) | an ultralytics hook before NMS | large — 208 floats × 10⁴ boxes, plus a schema decision | ⚠️ **the runner-up class alone** (2 floats) would answer §4.1's question from the detector's side rather than from a cross-staff accident. Scope that sub-case separately |
| **N14** | **NMS-suppressed boxes and their classes** (S4) | a results hook, or a second pass at a lower IoU | one extra tensor read per cell | the same information as N13 at a fraction of the volume |
| **N15** | **per-line staff residual at the notehead's own x** | re-probing the cell image at the note's x-column | one column read per notehead | ⚠️ **partly REFUSED already** — `OMR_CELL_LINE_TRACE` measured per-line tracing as ALIASING and shipped a rigid comb. What is *not* refused is recording the comb's residual (N1), which is (ii) and free. Do N1; do not re-open N15 without reading `WIDENED_PRICING_2026-09-04.md` |

---

## 6. Ranked conclusions for this slice

Cheapest first. **Nothing re-recommends anything additive-vs-gated measured and
refused**, and items 1–2 sit *under* its shortlist item 1 (*record the
refusals*) rather than beside it.

### 1 · Record the class-disagreement and the band distances in `_dedupe` — free, byte-identical

**What:** at `transcribe.py:2715` form `class_i != class_j`; at `:2763-2766`
keep both `_distance_to_band` values instead of consuming them in a ternary.
Write both onto the existing `OMR_CONTEST_DUMP` record, which is already
documented verdict-neutral and already carries the confidences.
**Payoff:** it makes item 4 decidable **from disk** — exactly as the survey's
item 1 made `measure_dynamics` decidable from disk while `_dedupe` needed a
re-run. The population is 436 pairs, 9.6% (§4.1), and the survey's §5.3 already
asks for the distances.
**Risk:** none — no consumer, output byte-identical.
**Settling measurement:** the flag-off byte-identity assertion the project
already uses, plus `probe_contest_class_disagreement.py` re-running against the
richer dump. **Harness: none.**

### 2 · Record the seven free numbers that die in their own expression — free, byte-identical

`pitch_resolver`'s residual (S12, the pipeline's highest-volume free item) · the
staff-gap spread (N1) · the fill ratio (N3) · the beam-cluster gap sizes (S21) ·
the losing stem end's count (N7) · the tuplet refusal reason (N8) · **the
spurious-rest filter's deletion count (N16)**.
**Payoff:** five of the seven are direct inputs to flags this project has already
priced (`OMR_CELL_LINE_TRACE`, `_reconcile_measure_to_meter`, the hollow thread),
and none can be re-derived from a stored JSON today. N16 gives the pipeline's one
uncounted deletion rule the counter its three siblings have.
**Risk:** near zero. ⚠️ But the per-detection ones are a **schema** decision at
10⁴ rows per document — S12 and N3 want a per-cell summary (a histogram, or the
count past a band), not a field per notehead. That is why field 11 (VOLUME) is in
the schema.
**Settling measurement:** byte-identical MusicXML on both families.
**Harness: none.**

### 3 · Make `_stacked_bar_count` return the bars it measured instead of the count (N4)

⚠️ **The one item here that is not free, and the only one I would call a defect
rather than a gap.** A multi-bar beam component's bar positions are fabricated by
even division, and `rhythm._beams_attached_to_stem` clusters those fabricated
y-centres to decide the duration.
**Payoff:** unknown, possibly zero — a level beam's box is nearly its bar, so
even division is nearly right there; the exposure is *sloped* multi-bar
components, which the module measures at 43–46% box fill.
**Risk:** this changes behaviour. It is not a record-the-refusal item.
**Settling measurement:** ⚠️ `benchmarks/omr-phase4-lines` **cannot price it** —
its LilyPond truth knows the bar COUNT, not the bar positions, and the count is
unchanged by construction. The arm is `orchestral_eval --omr-ned` duration rate
on the works with sloped sixteenth beaming (`mozart-sym41-mvt1`, Brahms 1's
Violin 2 — both are the worked examples already in the docstrings), A/B on one
tree, `--tag=` per arm. **Harness: the engraved benchmark, and it CAN see this**
(duration rate is a reported column).

### 4 · A confidence tier under rank 0 in `_dedupe`, restricted to class-DISAGREEING pairs

⚠️ **Explicitly NOT the survey's item 4 and must not be conflated with it.** That
item thresholds |Δconf| > 0.30 over all 4,233 distance-decided pairs — 143 swaps,
priced as a bet the size of the range veto's 52. **This is a different
population**: the 434 distance-decided pairs whose two readings disagree about
the *class*, where §4.1 measures median |Δconf| at 0.137 against 0.059
elsewhere, with a within-category control.
**Payoff:** the largest group is the arc/beam confusable family (263 of 436) —
the family CLAUDE.md records as the biggest engraved reading gap and the one
`OMR_ARC_RECLASS` was built for and refused on scans.
**Risk:** real. A behaviour change on a signal with no calibration corpus
(**T5 fails**, as for the survey's item 4).
**Settling measurement:** scan-gate **note recall per row**, not pooled OMR-NED
— the ±6-edit noise floor swamps a change this size, `wrong note` is 29.6% of the
pool, and the metric rewards emitting more symbols. ⚠️ Give each arm its own
`--tag=` and **check the wall clock**: a cached `scan_eval` A/B reports
"identical on every bucket", which is exactly the result this hopes to see.
⚠️ **Do item 1 first** — with the record in place this is priceable from disk.

### 5 · A confidence floor on `ledgerLine`, in both ladder consumers

⚠️ **Ranked last on purpose, and the finding I would most want a second opinion
on.** §4.2 establishes the *information* fact and establishes nothing about
whether a floor helps.

**§A00's order of enquiry, applied before anyone builds it:**
1. **Comparison valid?** Yes if same tree, `--tag=` per arm.
2. ⚠️ **Is the metric charging for something else?** Yes, and dangerously —
   `_drop_unladdered_noteheads` DELETES notes, and OMR-NED's symmetric reward for
   under-prediction means a floor that deletes *fewer* notes can score worse
   while being right.
3. ⚠️ **Can a downstream consumer use it at all?** **This is what could kill it
   outright.** The ladder decided 266 of 4,521 pairs (5.9%), so a floor's whole
   reachable population is those 266 plus whatever `_drop_unladdered_noteheads`
   fires on — and a floor at 0.40 would silence ~70% of the rungs, which may
   simply convert ladder decisions into *distance* decisions. That would be
   worse, for a reason with nothing to do with the mechanism.
4. Only then, is the mechanism wrong.

**Settling measurement, in order:** first a **reach probe** (free, off the same
dumps plus one instrumented run): how many of the 266 ladder verdicts survive a
0.40 rung floor, and how many `_drop_unladdered_noteheads` deletions change.
**Only if the reach is non-trivial**, a scan-gate note-recall A/B.
**Harness: the reach half needs none.**

---

## 7. What I did NOT cover, and what is UNMEASURED

### Not covered in round 1

- **`_pair_ties_in_staff` / `_pair_ties_in_cell` / `_attach_articulations_in_cell`** — in the slice, and §3.5 shows they have zero §5 rows (the coordinator counts 25 tie-pairing decision points). I ran out of round-1 budget after the ownership functions. Same shape as `_pair_dots_to_targets` (S24); I expect the same finding and did not verify it.
- **`_correct_notehead_class_by_fill`'s effect size.** §3.2 establishes the ratchet is one-way; **how often it fires, and in which direction the errors run, is UNMEASURED.**
- **`rhythm.py`'s meter half** (`parse_time_signature`, the votes, `_reconcile_measure_to_meter`'s internals). In the slice by file; it is stage 8c's decision and the map covers it, and I judged the ownership functions the better use of the round.
- **`voicing._chord_span_states`** and the slur/wedge ride-up — export-adjacent.
- **Agent II's angle on `_dedupe`** — deliberately not written.

### UNMEASURED, and said so

1. **Whether the inside-the-staff ladder inversion is reachable.** `_ledger_ladder` returns `(0, 0)` for a glyph *inside* a staff — the strongest possible ownership evidence — which is the same value it returns for *outside with a broken ladder*, the weakest. The comparison at `transcribe.py:2737` is `ladder_i[0] != ladder_j[0]`, so a glyph inside band *i* **loses** to a staff *j* holding a complete ladder to it. The docstring acknowledges the collapse (*"Both are 0 for a glyph inside the staff, which needs no ladder"*) without noting the rule above it can then invert. The committed dumps carry no band data. **Cheap to settle:** it needs item 1's band distances, then one grep of the enriched dump for a ladder verdict whose loser had distance 0.
2. **Whether the higher-confidence side of a class-disagreeing pair is the correct one** (§4.1). No corpus records it; T5 fails.
3. **Whether a `ledgerLine` floor helps** (§4.2, item 5). Reach unmeasured.
4. **N10** — how many staves claim one glyph. The dump carries no detection ids.
5. **N4's blast radius** — how many multi-bar beam components exist per page, and how many are sloped. One page-level probe would settle it; I did not run one.
6. **N12 and N13's cost** — priced by reasoning about volume, not by timing anything.
7. **§3.5's list is a floor, not a census.** Thirteen uncatalogued points found by reading my slice's five files; I did not enumerate systematically the way `fbbd09c1` did for its five scopes.

### Substrate cautions carried

- §4.1 shares its dumps with `benchmarks/omr-additive-vs-gated-2026-09`. Different column, same table — **not corroboration**.
- §4.2 is **n = 2 pages**, two publishers, two weight files. They agree; two is still two.
- §4.3 is over 28 committed transcriptions spanning months and several weight files. It measures the *recording*, not the pipeline.
- ⚠️ **I began on a tree 28 commits stale.** Every citation was re-anchored after the rebase (see the header) and three had drifted, but §2's tables were first drafted against the older tree; a reader finding a stale line number should treat it as my error, not the tree's.
