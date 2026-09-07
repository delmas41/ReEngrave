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

---
---

# ROUND 2 — stage 3, two settled hypotheses, and a census

**Written after the coordinator's round-2 brief and the verifier's report on
round 1.** Tree: `61eefe21` + the audit commits; every `file:line` anchored
there. Four new committed probes; **no benchmark was run and no behaviour
changed.**

## R0. Corrections to round 1, applied here rather than by rewriting it

Per the brief, round 1 stands as written except for errors. Two, both from the
verifier, plus one I am withdrawing myself.

| | round 1 said | correct |
|---|---|---|
| **R0-a** (verifier D2) | §3.5: the spurious-rest filter is *"the pipeline's only silent deletion rule with no counter at all"* | ⚠️ **FALSE as a universal.** There are at least four counterexamples, two in the same neighbourhood (`_spans_the_whole_cell` five lines above, `_deduplicate_beams` fifty below, plus `_drop_close_outliers` and `_reject_spacing_outliers`). **The observation survives and the CLASS is the finding**: §R3 replaces the singleton with a mechanical count — **18 drop sites in the seven slice files, 14 of them writing no count (0.778)**. `n of m` beats `the only`, and this project's verification passes keep finding their errors in universals. |
| **R0-b** (verifier D9) | §0/§4.2: `ledgerLine` is *"the lowest-confidence class on the page"* | **The lowest-confidence STRUCTURAL class.** `stem` (YOLO's own, unused) is lower. The ownership argument is unaffected — `ledgerLine` is still the substrate of the only tier ranked above distance — but the claim is now stated to its evidence. |
| **R0-c** (mine) | §6 item 5 proposed a `ledgerLine` confidence floor, ranked last with a reach probe named first | ⚠️ **The reach probe ran (§R2.2) and the answer is NO. Item 5 is REFUSED, measured.** A 0.40 floor destroys 42–58% of complete ladders. I am withdrawing my own recommendation. |

⚠️ **And an inference-discipline correction the coordinator relayed, which
changes how I phrase §4.1.** A 44.8% split at n = 4,521 is z ≈ −7: the effect is
**real but uninformative about correctness**, not "indistinguishable from
chance". Round 1's §4.1 already said the right thing in prose (*"a larger margin
means the quantity has more to say, not that the higher-confidence side is
right"*); the sharper phrasing is the one to quote.

**What the verifier confirmed and I am not repeating:** the D23 overturn
(re-derived independently, called airtight), all of §4.1's counts, and that
`additive-vs-gated/FINDINGS.md` contains no `436` anywhere — the column is
genuinely new, as round 1 cautiously framed it.

---

## R1. Stage 3 — `measure_extractor.py`

Taken first for the reason round 1 gave: 15 importers including the labeling
pipeline, and it feeds every function round 1 audited. It is also the freshest
code in the tree (+104 lines in the rebase, the one-line-percussion workstream).

### R1.1 ⚠️ THE HEADLINE: `Barline` has five fields and all five are coordinates

```python
@dataclass
class Barline:                    # types.py:108-115
    page_index: int
    x: int
    y_top: int
    y_bottom: int
    system_index: int
```

`detect_barlines` computes, for every accepted column: the **vote count**
(`n_votes`), the **inter-system connectivity** (a float per column), the
**span-test score** (`_spans_system`, a float), **which of four acceptance
prongs** fired (vote+connectivity, strong-connectivity rescue, small-system
vote, small-system span rescue), the per-staff x observations that let the
probe follow a leaning line, and — page-level — whether this system was judged
an **open score** (`barlines_cross_gaps`) and whether cue C **overrode** that
judgement.

**Every one of those dies at the `Barline(...)` constructor**
(`measure_extractor.py:685-691`). The dataclass has no evidence field.

This generalises the map's `_drop_close_outliers` row, which observes that that
function *"receives only integers"*. It is not one function's problem: **no
consumer of a barline anywhere in the pipeline can know anything about why it is
there.** The consumers are `_measure_x_boundaries` (which decides every cell's x
extent), `_drop_close_outliers`, `resegment_fused_measures`,
`majority_bars_by_system`, and — downstream — the measure count that
`_flag_measure_count_inconsistency` checks and that
`export._stitch_slots` refuses on.

| field | 13-field schema |
|---|---|
| **fidelity / destruction site** | four floats and two booleans → a 5-tuple of ints, `measure_extractor.py:684-690` |
| **consumers** | prod_omr 5, all reading `x` / `system_index` only |
| **who should read it** | `_drop_close_outliers` (which of a close pair is spurious — currently decided with no evidence at all), `resegment_fused_measures`, and the measure-count check, which grades its own confidence and cannot see the barlines' |
| **volume** | 10¹–10² per page |
| **failure direction** | over-claims — a barline accepted on 5 of 22 votes at connectivity 0.71 is indistinguishable from one accepted on 22 of 22 at 1.00 |
| **arity** | four prongs, unrecorded |
| **cost to gather** | zero — all four numbers are live in the accepting loop |
| **settling measurement** | none needed to RECORD it (byte-identical). To consume it: `_drop_close_outliers`' choice against hand-read barline truth on the scan gate's own pages |

### R1.2 The rest of stage 3, by the schema

| # | signal | destroyed at | consumers | should read it | volume | fail dir. |
|---|---|---|---|---|---|---|
| S36 | **component `y`, `area`, and the aspect ratio** in the barline shape test | `:163` unpacks `x_l, y_l, w_l, h_l, area` and reads `w_l`/`h_l` only; the aspect `h_l/max(w_l,1)` is formed and destroyed at `:168` | none | a component's vertical POSITION against the staff — the map's row for this | 10³/page | over-claims |
| S37 | **the height FRACTION `h_l / staff_span`** | never formed — only `h_l < min_height` | none | the vote. A barline at 0.81 of the span and one at 1.00 are one vote each | 10³/page | over-claims |
| S38 | **`_spans_system`'s per-band ink** | `weakest = min(weakest, …)` at `:323` | none | ⚠️ **WHERE the column breaks.** A barline broken by a printing defect and a stem that stops at its own staff give the same scalar; the band index says which | 10¹/system | over-claims |
| S39 | **`_intersystem_connectivity`'s per-gap ink fraction** | `if col_ink_fraction.max() > 0.5: n_connected += 1` at `:388` — the magnitude dies in the comparison | none | the same question. ⚠️ And **WHICH gaps failed is never formed**: at connectivity 0.73 on a 12-staff system, three failing gaps that are CONTIGUOUS are a real structural break and three scattered ones are noise. Contiguity is one pass over a list the function already has | 10²/page | over-claims |
| S40 | **`barlines_cross_gaps`** — the open-score verdict | a local at `:579`, never written to the page dict | none | ⚠️ a page-level STRUCTURAL fact — the same class of fact as `weight_routing`, which *is* recorded. Round 1's page-truth sibling work found the pipeline "emits zero layout information"; this is a concrete instance | 1/system | over-claims |
| S41 | **the cue-C override flip** (`:617`) | silent — `barlines_cross_gaps = True` with no record | none | anyone auditing `OMR_CHOIR_GROUPING`, a default-ON flag whose own FINDINGS had to hand-adjudicate 10 pages | 1/system | over-claims |
| S42 | **`n_votes / n_staves`** — the vote FRACTION | never formed; `min_votes` is a step function of `n_staves` (`:521-535`) | none | a 5-of-22 rescue and a 22-of-22 acceptance | 10²/page | over-claims |
| S43 | **`_cell_line_offset`'s winning shift and its score** | ⚠️ **partly kept** — the shifted grid reaches `staff_line_ys_canonical`, and `annotate/recut_cells.py` reads the provenance. But the SCORE at the winning shift, and the runner-up shift, die in the search | `probe` (recut only) | the grid-reliability question round 1's N1 is about | 10⁴/doc | over-claims |
| S44 | **`_neighbour_room`'s two distances** | consumed by `grown()` into a 4-or-6 decision (`:1118`) and dropped | none | ⚠️ the pad actually used is not on `MeasureCell` either, so **no consumer can tell a 4-space cell from a 6-space one** — and the map's own warning is that cell height moves DETECTIONS, not just crops | 10⁴/doc | over-claims |

### R1.3 ⚠️ C3 is no longer what the backlog says, and the four-reason list omits a fifth site

The backlog's **C3** reads *"One-line percussion staves are detected and then
dropped by `if len(s.line_ys) >= 5`. All 11 present… A pipeline ceiling with a
location."* **That is now stale in the tree's favour.** `OMR_ONE_LINE_STAVES`
exists (`ENV_ONE_LINE_STAVES`, `:921`, default OFF), and
`_admit_one_line_staves`' docstring (`:985-1006`) enumerates the four things the
filter guards and states that **three stay filtered by design** — the barline
vote, the system x-edges, and the resegmentation kernel — with only the CELL
opened. The map's three line numbers have also drifted: `:464`, `:1231`, `:1560`.

⚠️ **There is a fifth `len(line_ys) >= 5` site and the four-reason list does not
mention it:** `_neighbour_room:849`,
`if other is staff or len(other.line_ys) < 5: continue`. A five-line staff
adjacent to a percussion rule therefore sees `inf` room on that side and grows
its pad to `PAD_MAX_STAFF_LINES = 6` — the maximum — **exactly where the flag
puts a new cell.**

⚠️ **And the ownership layer cannot tell the two kinds of staff apart.**
`transcribe.py:4711-4714` builds `_bands` from **all** `pws.staves` with no
five-line filter, so a one-line staff enters as
`(top_y, bottom_y, line_spacing_px)` where `top_y == bottom_y` — a **zero-height
band** — and `line_spacing_px` answers with `nominal_line_spacing_px`
(`types.py:102`, the property the verifier's **E1** correctly identifies as
having 15 production readers; confirmed, set at `staff_detector.py:1037` only
when `len(line_ys) < 2`).

Traced through, this is safe but blind:

| consumer | behaviour on a zero-height band | verdict |
|---|---|---|
| `_distance_to_band` | degenerates to `|y − rule|` | **correct** for a single rule |
| `_ledger_ladder` | anchors on the rule and expects rungs at `spacing` intervals; a percussion part prints none, so `complete` is ~never 1 | **benign** — a five-line staff with a real ladder wins rank 2 |
| `_drop_unladdered_noteheads` | `if spacing <= 0: continue` guards a staff with no nominal spacing | **safe** |

**The information finding:** nothing in `bands` distinguishes *"a staff with
five lines"* from *"a single printed rule"*, and no consumer records that a
contest involved one. For the one-line workstream that is the entry point —
the flag's blast radius reaches `_dedupe` through a tuple shape that cannot
express the difference, and `_neighbour_room` maximises the overlap on exactly
those pages. **UNMEASURED: I did not run the flag on.** The named run is one
page with a percussion staff, `OMR_ONE_LINE_STAVES=0` vs `1`, comparing
`n_cross_staff_duplicates_removed`.

---

## R2. The two hypotheses round 1 left open — both now settled, both NEGATIVE

⚠️ **Both are clean negatives and I am reporting them as prominently as I would
have reported hits.** Round 1 named the measurements; they ran; the answers are
no. Per §A00 this does not condemn the mechanisms — it prices them.

### R2.1 N4 — the fabricated beam-bar positions: UNREACHABLE, and for an interesting reason

`probe/probe_beam_bar_positions.py`, output `beam-bar-census.json`.

Round 1 (§5.2 N4) found that `_stacked_bar_count` measures the bars' real rows
(`cols & ~above`, `line_detection.py:374-376`), reduces them to a median count,
and `detect_beams:546` then **fabricates** the coordinates by splitting the
box into `n_bars` equal slices — coordinates that `rhythm._beams_attached_to_stem`
clusters to decide durations. I called it the strongest never-gathered item.

**Measured over 5 pages — 2 scanned editions and 3 engraved fixtures, including
the two pages the docstrings use as their own worked examples (Mozart 41,
Brahms 1) — 277 accepted beam components:**

| | components | `n_bars ≥ 2` |
|---|--:|--:|
| scan (Beethoven 5 / Litolff p1, Brahms 1 / Breitkopf p1) | 97 | **0** |
| engraved (Mozart 41, Brahms 1, Tchaikovsky 6, page 0) | 180 | **0** |
| **total** | **277** | **0** |

**`n_bars` is 1 on every component.** The fabrication branch never executes, so
N4 costs nothing today. ⚠️ **The mechanism is real and the exposure is zero** —
exactly the distinction §A00 asks for.

**Why, and this is the part worth keeping.** After the horizontal opening, two
stacked beam strokes are separated by white and come out as **separate connected
components**; they only share one when the print merges them. So
`_stacked_bar_count`'s entire median-over-columns machinery — an elaborate
function with a measured docstring and a documented bug history — has a
**non-trivial branch that fired 0 times in 277 components.** The label-mask fix
that motivated it (sampling the component's own ink instead of the opened image)
is precisely what drove `n_bars` to 1: the docstring's own Brahms Violin 2
example reports the *pre-fix* behaviour.

⚠️ Controls: my replication of the accept path mirrors `detect_beams`' filters
exactly and calls the real `ld._stacked_bar_count`, so `n_bars` is the
production value. DPI 600 = `transcribe.py:4027`'s default, which
`orchestral_eval` takes. **Limit:** page 0 of each work, n = 5 pages. A page
whose print merges its beams would show a non-zero rate and none of these do.

**N5b survives and is now measured.** The box fill ratio
(`area/(w·h)`), which `connectedComponentsWithStats` computes and `detect_beams`
uses only as a floor, is available on every one of the 277: **scan median 0.933
(min 0.285), engraved median 0.640 (min 0.358)**. The module's docstring
predicts 43–46% for sloped bars against 95% for level ones and the engraved
median sits between them, which is what a corpus of mixed slopes should look
like. It remains free, and it remains uncomputed.

### R2.2 The ladder inversion — FORMALLY REAL, EMPIRICALLY ABSENT; and the floor it implied is REFUSED

`probe/probe_ladder_inversion.py`.

⚠️ **First, the honest answer to the coordinator's question about the dumps: they
genuinely cannot answer it.** `dump_contests.py:80-95` records per-staff
`clef`/`instrument` and per-pair classes, pitches and confidences, and **no
geometry** — no bbox on a contest, no band on a staff. So I asked it off committed
TRANSCRIPTIONS instead, which carry `staff_geometry.line_ys_page` and
`bbox_page`, importing the real `_ledger_ladder` and `_ledger_rows` rather than
reimplementing them.

**Question 1 — the inversion.** For every notehead sitting INSIDE its own
staff's five lines (where `_ledger_ladder` returns `(0,0)` for "needs no
ladder"), does any other staff hold a COMPLETE ladder out to it (which would win
rank 2 and take the glyph away)?

| | noteheads | inside their own five lines | **inversions** |
|---|--:|--:|--:|
| beet5-p02 | 626 | 398 | **0** |
| brahms1 | 4260 | 3059 | **0** |

**Zero of 3,457.** The collapse is real in the code and unreachable on these
pages: a complete ladder from a neighbour would need every rung between that
neighbour's edge and a glyph lying inside another staff's printed lines.
⚠️ **LIMIT, which bounds the conclusion:** a committed transcription is
POST-dedupe, so the losing copy of each historical contest is gone. This
measures the geometry, not the firings. **Naming the run that would close it
completely, as instructed:** one `OMR_CONTEST_DUMP=1` pass with
`dump_contests.py` extended to record each contest's `bbox_page` and each
staff's band — the same run the coordinator would need for round-1 item 1
anyway.

**Question 2 — the ingredient.** `_ledger_rows:2510` filters on
`det["class"] != "ledgerLine"` and admits everything else. How many of those
detections sit INSIDE some staff's five-line band, a position a real ledger line
can never occupy?

**479 of 633 (0.757) on beet5-p02; 302 of 768 (0.393) on brahms1.** ⚠️ Reported
per page and not pooled — the two differ by publisher *and* by weights file, and
a 0.757/0.393 spread is not one number.

**Question 3 — does it matter?** For every notehead OUTSIDE its own band with a
COMPLETE ladder — the trusted tier's actual verdicts — how many of the matched
rungs are those impossible in-band ones?

| | outside their band | complete ladders | ladders using ≥1 impossible rung |
|---|--:|--:|--:|
| beet5-p02 | 228 | 26 | **0** |
| brahms1 | 1201 | 222 | **0** |

**Zero of 248**, and zero of 328 matched rungs. The ladder's own geometry — an
expected position within 0.35 spaces plus a 0.25-width x-overlap — already
filters the impossible rungs out. **The trusted tier does not rest on them.**

**Question 4, which is round-1 §6 item 5's reach probe — and it kills the
recommendation.** How many complete ladders survive a confidence floor on the
rungs?

| floor | beet5-p02 rungs → ladders | brahms1 rungs → ladders |
|---|---|---|
| none | 633 → 26 (1.000) | 768 → 222 (1.000) |
| 0.30 | 428 → 22 (0.846) | 560 → 184 (0.829) |
| **0.40** | 180 → **15 (0.577)** | 231 → **94 (0.423)** |
| 0.50 | 51 → 4 (0.154) | 90 → 34 (0.153) |

⚠️ **A 0.40 floor destroys 42–58% of the tier's verdicts.** The low-confidence
rungs are **load-bearing**: they complete real ladders. So the two facts round 1
put side by side are about **different populations** — the *impossible* rungs
(39–76%) are inert, and the *low-confidence* rungs are useful. **Round 1's §6
item 5 is refused on its own reach probe, which is the step §A00 said could kill
it and did.** I am withdrawing it.

⚠️ What survives: `_ledger_rows` still reads no confidence, and that is still a
Class-C fact. What does not survive is the recommendation attached to it.

---

## R3. The census — replacing round 1's §3.5 floor with a method

`probe/probe_decision_census.py`. Mechanical, over the seven slice files.

⚠️ **Definitions are stated in the probe so the numbers are arguable rather than
a judgement.** A *decision point* is an `If`/`IfExp`/comprehension-filter whose
test contains a `Compare`, or a call to `max`/`min`/`sorted`/`most_common`/
`median`/`argmax`/`argmin`/`Counter`. **Bare truthiness (`if x:`, `if x is
None:`) is excluded** — that is control flow, and the exclusion is the whole
difference between this number and `grep -c if`.

| file | decision points | **discarding** | selector calls |
|---|--:|--:|--:|
| `yolo_detector.py` | 21 | 4 | 6 |
| `line_detection.py` | 52 | 12 | 22 |
| `pitch_resolver.py` | 14 | 4 | 3 |
| `rhythm.py` | 134 | 34 | 36 |
| `voicing.py` | 21 | 7 | 9 |
| `measure_extractor.py` | 165 | 41 | 66 |
| `transcribe.py` | 386 | 95 | 69 |
| **TOTAL** | **793** | **197** | **211** |

A **discarding** decision point is one where the compared quantity is COMPUTED
INSIDE THE TEST (a Call, BinOp or Subscript operand rather than a bare name), so
it cannot outlive the comparison — the mechanical form of this audit's central
pattern. **197 of 793 = 0.248.**

⚠️ **What this number is and is not.** It is a *reproducible upper bound on
sites worth inspecting*, not a defect count: many of the 197 are correct (an
empty-gap constant is meant to consume its quantity). It is useful because it is
mechanical, it can be re-run after any change, and **793 against the map's ~176
§5 rows for the whole pipeline** puts a number on the coordinator's *"what is
missing outranks what is wrong"* — for these seven files alone.

### R3.1 Silent deletion — the class, per the verifier's D2

A *drop site* reduces a collection the pipeline carries forward: it mutates via
`.remove`/`del`, returns a filtering comprehension, or builds a `kept` list in a
loop containing `continue`. Predicates are excluded. It *accounts* for what it
removed if it returns a count, increments one, or writes an `n_*` key.

**18 drop sites in the seven files; 14 write no count (0.778).**

| accounts for its removals | does not |
|---|---|
| `_drop_clipped_notehead_fragments` · `_drop_unladdered_noteheads` · `_drop_furniture_measures` · `_dedupe_cross_staff_detections` | `_drop_paired_strokes` · `_deduplicate_beams` · `_beamed_groups` · `_tuplet_groups` · `_filter_stems_overlapping_tremolo` · `_find_internal_barline_candidates` · `_chord_span_states` · `group_chords_in_measure` · (+ detector-side `detect_stems`/`detect_beams`, and 4 hand-adjudicated out: `parse_pages`, `_ledger_rows`, `_window_blind_systems`, `_measure_x_boundaries` collect rather than drop) |

⚠️ **My own rule has two known misses, stated so the number reads as a floor in
a known direction:** `rhythm.resolve_rhythms_for_cell` (the spurious-rest
filter — it returns a *dict*, so the build-`kept` pattern does not match) and
`measure_extractor._drop_close_outliers`. Both write no count. Counting them,
**16 of 20**.

**So round 1's R0-a sentence becomes:** the spurious-rest filter is one of
roughly sixteen drop sites that write no count, against four that do — and
**the four that do are exactly the three the pipeline surfaces as `n_*`
counters plus the deduper.** The pattern is not an oversight in one function; it
is that accounting was added only where somebody went looking.

---

## R4. Tie and articulation pairing

Round 1 predicted these would be the `_pair_dots_to_targets` shape. They are,
plus one item that is not.

| # | signal | destroyed at | consumers | volume | note |
|---|---|---|---|---|---|
| S45 | **`_pair_ties_in_cell`'s `best_left_dx` / `best_right_dx`** | argmin, discarded at `:2272`/`:2277` | none — the output is two `set`s of ids, and the JSON carries bare `tied_to_next` / `tied_from_prev` booleans | 10³/doc | the `_pair_dots_to_targets` shape exactly |
| S46 | ⚠️ **the two tie ends' MUTUAL y-difference** | **never formed** | — | 10³/doc | ⚠️ **the new one.** The docstring states the exact constraint — *"real tied notes are at the same y-position by definition"* — and then applies `y_tolerance = max(avg_nh_h * 3, 30)` (`:2251`), about three staff spaces, SEPARATELY to each end against the tie's own centre. The two chosen noteheads are never compared **to each other**; the only test is `best_left is not best_right` (`:2279`). A tie whose ends sit two spaces apart is accepted identically to one whose ends coincide, and `30` is another bare pixel constant in canonical coordinates |
| S47 | **`_attach_articulations_in_cell`'s winning `dx`** | `best = (dx, n)` formed at `:2219`, and only `best[1]` is read at `:2222` | none | 10³/doc | placement margin |
| S48 | **which marks were left unattached, and why** | `if best is None: continue` (`:2220`) | ⚠️ the function DOES return `placed`, so the count of successes is accounted — but the 21-of-218 abstentions the docstring cites come from an offline benchmark, not from the run | 10²/doc | the abstention is the interesting half and it is the unrecorded one |
| S49 | **a double-attach of the same mark kind** | `out.setdefault(...).append(kind)` (`:2222`) admits duplicates; `voicing.py:262` silently dedupes them later | none | 10²/doc | a conflict absorbed downstream rather than reported — the `_pair_dots_to_targets` double-dot hazard in a second place |

⚠️ **Coordinated, not merged, per the brief.** Agent II's finding that 263 of the
436 class-disagreeing contests are arc classes is about `_dedupe`; S46 is about
the *pairing* rule that consumes surviving ties. They meet at the tie inventory
and I have not written their half.

---

## R5. Round-2 conclusions, folded into round 1's ranking

**Round 1's items 1–4 stand unchanged.** Item 5 is withdrawn (§R0-c). Three new
items, cheapest first.

### 6 · Put an evidence field on `Barline` — free, byte-identical

The four numbers already exist in the accepting loop (§R1.1). **Payoff:**
`_drop_close_outliers` currently chooses between two barlines *with no evidence
at all*; the measure-count check grades its own confidence and cannot see the
barlines'; and `barlines_cross_gaps` is a page-level structural verdict the
pipeline forms and forgets. **Risk:** none. **Settling measurement:** none for
recording. **Harness: none.**

### 7 · Record the fifth `len(line_ys) >= 5` site's consequence for the one-line workstream

Not a code change — a **measurement**, and the entry point that workstream asked
for. `_neighbour_room:849` maximises the pad exactly where `OMR_ONE_LINE_STAVES`
adds cells, and `_bands` cannot express the difference between a five-line staff
and a rule. **Settling measurement:** one page carrying a percussion staff,
flag off vs on, comparing `n_cross_staff_duplicates_removed` and the surviving
detections per staff. **Harness: none.** ⚠️ Do this before the flag is
considered for default-on.

### 8 · Two dead-branch cleanups the census surfaced — measure before removing

`_stacked_bar_count`'s multi-bar branch fired **0 times in 277 components**
(§R2.1) and `_deduplicate_beams`' confidence sort cannot compare a CV beam with
a YOLO one (round 1 §3.1). ⚠️ **Neither should be deleted on these numbers** —
5 pages and one code path respectively — and the project's own standard is that
a null on a corpus without the defect is not evidence. What they should get is
**a recorded assertion**: `n_bars > 1` and a CV/YOLO comparison are both cheap
to count, and if they stay at zero across the standing benchmarks the branches
can go with evidence instead of an argument.

---

## R6. What round 2 did NOT cover, and what is still UNMEASURED

- **`resegment_fused_measures` and `majority_bars_by_system`** (`measure_extractor.py:1418-1704`) — read for the census, not written up by the schema. They are the largest remaining stage-3 gap.
- **`_cell_line_offset`'s search internals** (S43) — the winning score and runner-up shift; I recorded that they die and did not enumerate the branch structure.
- **The labeling pipeline's read of `measure_extractor`** — the 15-importer blast radius the coordinator named. I verified the count exists; I did not trace what `annotate/recut_cells.py` and `training/` actually consume.
- **UNMEASURED:** the one-line-staves interaction (§R1.3, run named) · the post-dedupe limit on §R2.2 (run named) · whether `n_bars > 1` occurs on any page (5 pages, 0 hits) · whether the 197 discarding decision points contain defects (the census does not adjudicate) · S46's cost — I did not measure how many ties are paired across a y-gap large enough to be wrong.
- ⚠️ **Substrate:** §R2.2 uses the same two committed transcriptions as round 1 §4.2. §R2.1's five pages are new. The census reads source only.

---
---

# ROUND 3 — N4 overturned and priced, the instruments fixed, three corrections

**Written after the verifier's round-2 report (D17–D19, M11–M13) and the
coordinator's round-3 brief.** Tree `61eefe21` + audit commits.
**No benchmark was run, no weights loaded, no behaviour changed.**

## R7. ⚠️ N4 IS REAL. MY RETRACTION WAS THE ERROR — and here is what it costs

### R7.1 The retraction, and why it was wrong

Round 2 §R2.1 headed N4 **"UNREACHABLE"** on 277 components over 5 pages with
zero multi-bar. The verifier (D17) widened my own probe over ten pages I omitted
and found **31 multi-bar components in 805**. It reproduced my census exactly
first, so the disagreement is sampling, not method.

⚠️ **The bias is identifiable, not bad luck: both scan pages in my census are
`p1` rows — the two cleanest prints in the gate.** Print-merged beams live on
the worse prints. Every hit is on p2/p3/p4/p6 or Bach.

⚠️ **And my own report contains the standard that should have stopped me.**
§R5 item 8: *"a null on a corpus without the defect is not evidence"*, and §R6
listed the 5-page limit under UNMEASURED. **The hedge was right and the heading
overrode it.** The verifier's M13 is the general lesson and I accept it: *a
stated limit that is cheap to close should be closed, not declared.* Closing it
cost eleven minutes of wall clock and no weights.

### R7.2 Priced — the whole 20-row scan gate plus every engraved fixture

`probe/probe_beam_bar_positions.py` (rewritten, §R8), 31 pages, **2,073 accepted
beam components**. Output `beam-bar-census.json`.

| | components | `n_bars ≥ 2` |
|---|--:|--:|
| **scan** (20-row gate) | 1,815 | **51** |
| **engraved** (11 fixtures, page 0) | 258 | **0** |
| **total** | **2,073** | **51 (0.0246)** |

Multi-bar components appear on **9 of the 20 scan rows** — Brahms 1 p2 13, p3 7,
p4 2 · Dvořák 9 p7 9, p6 3, p5 2 · Bach 9 · Mahler 5 p3 4, p2 2 — and on **none
of the eleven engraved fixtures**. The branch is live, it is scan-only, and it is
rare.

### R7.3 The question the coordinator asked: does the difference change a decision?

Not *do the coordinates differ* — they must — but does the difference cross the
cluster tolerance `BEAM_Y_CLUSTER_FACTOR × spacing = 0.35 spaces`, which is what
`rhythm._beams_attached_to_stem` counts levels at. Fabricated gaps are all
`h/n_bars` by construction; measured gaps vary. So:

```
levels_fabricated = n  if h/n > tol else 1        (all gaps identical)
levels_measured   = 1 + #(measured gap > tol)
```

| quantity, over the 51 | median | p75 | p90 | max | over 0.35 sp |
|---|--:|--:|--:|--:|--:|
| bar-CENTRE displacement, fabricated vs measured | **0.082 sp** | 0.157 | 0.249 | **0.664** | **6 of 51** |
| BAND-EDGE displacement (what the end-window test reads) | **0.241 sp** | — | 0.554 | **1.037** | **15 of 51** |

⚠️ **LEVEL-COUNT FLIPS: 4 of 51 (0.078).** On these the fabrication changes how
many beam levels the component resolves to — i.e. it changes a duration:

| row | n_bars | fabricated → measured | fabricated gap | measured gap |
|---|--:|---|--:|---|
| dvorak-405834-p6 | 2 | **2 → 1** | 0.365 sp | 0.325 sp |
| dvorak-405834-p7 | 2 | **2 → 1** | 0.508 sp | 0.340 sp |
| mahler-local-p3 | 2 | **2 → 1** | 0.404 sp | 0.301 sp |
| brahms-317803-p2 | 2 | **1 → 2** | 0.336 sp | 0.468 sp |

**Three of the four INVENT a level** — even division spreads two merged bars
wider than they are, the gap clears the tolerance, and a note is read one
value too short. **One LOSES a level**, reading a note one value too long. Every
one of the four straddles 0.35: the fabricated and measured gaps sit on opposite
sides of it, which is the signature of a decision made on a coordinate nobody
measured rather than of a large error.

**So N4's verdict, stated to its evidence:** a real defect, with a real
consequence, on **4 components across 31 pages** — scan-only, ~0.2 duration
errors per scanned page, invisible on engravings. The mechanism is exactly as
round 1 described it; my round-2 reach figure was the thing that was wrong.

### R7.4 The verifier's open alternative, adjudicated by the counting method

D17 left open a worse reading: multi-bar fill median **0.472** is the docstring's
own signature for a *sloped single* bar (43–46%), so some of the 51 might be one
sloped bar split in two. Confirmed on my wider sample — multi-bar fill median
0.472 (p10 0.339, p90 0.702) against **single-bar 0.875**.

⚠️ **I adjudicate this against the counting method, not the ink, and say which
it is.** `_stacked_bar_count` counts ink RUNS in a column of the component's own
label mask. **A single sloped bar crossed by a vertical column yields one run,
whatever its slope** — that is the property the function was rewritten to
exploit. Two runs in a column therefore require two vertically separated
strokes. And my independent re-measurement agrees with `_stacked_bar_count` on
**51 of 51** components. The low fill is what a 2-bar box *should* show: two thin
strokes plus the white gap between them inside one bounding box.

⚠️ **That is an inference from the method, not an inspection.** The check that
would settle it is cropping the 51 boxes and looking; I did not do it, and it is
the one thing about N4 still open.

⚠️ **And a label of mine that the verifier quoted was wrong.** My round-2 probe
printed *"columns disagreed with the median count: 0 of 13"* while counting
**components**, not columns. The verifier read it as columns and concluded *"0
disagreements of 31"*. Corrected in the probe and here: **components whose
measured count matches `_stacked_bar_count`: 51 of 51. Sampled COLUMNS differing
from their own component's median: 907.** The conclusion — these are not median
noise — survives on the first figure, which is the one that carries it.

### R7.5 What to do about it

**Round-2 item 3 stands and is now priced.** `_stacked_bar_count` should return
the bar positions it already computes and `detect_beams` should use them.
⚠️ **Do not expect the metric to move**: 4 duration errors across 31 scanned
pages sits inside the scan gate's ±6-edit noise floor. Ship it because it is
free and correct, and assert the invariant (`fabricated == measured` where the
mask agrees) rather than a score. The A/B that *could* see it is the scan gate's
**duration rate** on the four named rows, not pooled OMR-NED.

---

## R8. The instruments — `OMR_FIXTURE_ROOT` and a non-zero exit

The verifier's failure mode is worse than round 1's: not a wrong path, but a
probe that **prints a clean all-zero table at exit 0** when it cannot find its
inputs. Mine did exactly that — `probe_beam_bar_positions` printed
`!! missing …` to *stderr* and **continued**, ending `wrote … (0 components)`
at exit 0. That is the stale-tree incident in miniature, and it is the shape
that produced my own N4 retraction.

⚠️ **The verifier's withdrawal of its earlier advice is right: relative paths
genuinely cannot work here.** `library/` and the `omr-orchestral-e2e/fixtures/`
build products are gitignored and exist in the main checkout only.

**Applied to all five probes** (`OMR_AUDIT_GUARD` block, identical in each):

- inputs resolved from `Path(__file__).resolve().parents[3]`, **never the CWD**;
- `OMR_FIXTURE_ROOT` names the checkout holding anything gitignored, defaulting
  to the main checkout;
- `_require(paths, what)` → **exit 2** on a missing input *or an empty set*;
- `probe_beam_bar_positions` additionally exits 2 on a bad `OMR_FIXTURE_ROOT`
  and on a zero-component census, because zero components over 31 pages is an
  instrument failure and not a result.

Verified: all five run identically from `/`; `OMR_FIXTURE_ROOT=/nonexistent`
exits 2; `_require([])` and `_require(['/nonexistent'])` both exit 2.

---

## R9. Corrections folded in

| | correction | applied |
|---|---|---|
| **D17** | N4 is not unreachable | §R7 — the retraction is overturned and the item priced |
| **D18** | the census-vs-map ratio compares AST nodes in 7 files with curated rows across 40+ modules | ⚠️ **the comparison is withdrawn.** §R3's number stands alone: **793 decision points, 197 discarding (0.248), 211 selector calls, over seven files** — a mechanical, re-runnable floor on sites worth inspecting. It is not set against the map's row count, because a single map row covers many nodes and many nodes correctly have no row |
| **D19** | §R3.1's four hand-adjudicated false positives name `_measure_x_boundaries`, which is not in the probe's 14 | ⚠️ corrected: the four are `parse_pages`, `_ledger_rows`, `_window_blind_systems` and **`_dedupe_cross_staff_detections`** — the last a genuine false positive of the rule, since it *does* write `n_cross_staff_duplicates_removed` and the report already places it in the accounts-for-its-removals column. **The numbers (14, and 16 of 20) are unaffected** |
| **mine** | the "columns disagreed" label counted components | §R7.4 |

---

## R10. M11 and M12 — the retraction's evidence is now reproducible, and stronger

**M11 was right and it is the more serious of the two.** §R2.2's Q3 and Q4
tables carried a retraction the coordinator had already relayed, and **no
committed probe emitted them** — `probe_ladder_inversion.py` stopped at Q2. By
this audit's own standard that made the retraction unverifiable until the
verifier rebuilt it. **Q3 and Q4 are now inside my probe**, importing
`_LEDGER_RUNG_EXPECTED_SLACK` / `_Y_TOL_SPACES` / `_MIN_X_OVERLAP` from the
module so the mirror cannot drift from the rule, and they reproduce the
published tables exactly.

**M12 — the direct measurement, taken by the verifier, folded in with credit.**
I argued "different populations" from the survival table; the confidence of the
*matched* rungs settles it in one line. My probe now emits it and reproduces the
verifier's figures:

| | all `ledgerLine` | rungs INSIDE a band (impossible) | rungs MATCHED by a complete ladder |
|---|---|---|---|
| beet5-p02 | n=633, median 0.337, 71.6% <0.40 | n=479, median 0.327, **74.9%** <0.40 | n=31, median **0.447**, **38.7%** <0.40 |
| brahms1 | n=768, median 0.344, 69.9% <0.40 | n=302, median 0.314, **90.7%** <0.40 | n=297, median **0.400**, **49.8%** <0.40 |

The ladder's geometry selects rungs **better than the pool** (0.447/0.400 vs
0.337/0.344) and rejects the impossible ones outright (75–91% sub-0.40,
contributing **0** matches) — *and* **39–50% of the rungs it does use are still
under 0.40**, which is exactly why a 0.40 floor destroys 42–58% of its verdicts.
**Round-1 item 5 stays withdrawn, now on a measurement rather than an
inference.** Credit to the verifier for taking it.

---

## R11. Continuing — `resegment_fused_measures`, and what the labeling pipeline consumes

### R11.1 `majority_bars_by_system` → `resegment_fused_measures`

| # | signal | destroyed at | consumers | should read it | volume |
|---|---|---|---|---|---|
| S50 | **the majority SIZE `mode_k`** | `mode_value, mode_k = Counter(counts).most_common(1)[0]` (`:1460`); `mode_k` is compared once (`mode_k * 2 <= total`) and dropped — only `mode_value` is returned | none | the steering decision. **"11 of 12 staves agree" and "7 of 12 agree" steer a split identically** | 10¹/page |
| S51 | ⚠️ **WHICH staves are short** | `counts` is a bare list of per-staff totals (`:1453-1454`); the staff indices are dropped at that line | none | ⚠️ **`resegment_fused_measures` then re-derives it downstream by CELL WIDTH.** The identity of the deviating staff is known exactly, one function earlier, and thrown away — so the split hunts by geometry for a staff the vote could have named | 10¹/page |
| S52 | **the abstention** (no strict majority) | `continue` at `:1462` (`mode_k * 2 <= total`, `:1461`) — the system is simply absent from the dict | none | a 2-2 or 3-3 split is a real disagreement and is indistinguishable from a system that was never examined | 10¹/page |
| S53 | **`_select_steered_splits`' three rejection reasons** | three silent `continue`s (`:1490`, `:1494`, `:1498`) — no candidates, would overshoot the known count, would cut a sliver | none | which of the three fired is the difference between "no evidence here", "the count is already met" and "a false barline was refused" | 10¹/page |

The pattern is the same one the whole audit has traced, and here it costs a
**re-derivation**: a fact is computed precisely (S51), discarded, and looked for
again by a weaker proxy in the next function.

### R11.2 What the labeling pipeline actually consumes — and it is not a function

The coordinator's 15-importer question. Six labeling/training modules import
`measure_extractor`, and every one takes the same two entry points —
`detect_barlines`, `extract_measures`. ⚠️ **But the real coupling is not the
import. `select_cells_orchestral.py:59-60` and `recut_cells.py:113-114`
MONKEY-PATCH the module's global pad constants**:

```python
_me.PAD_ABOVE_STAFF_LINES = ORCH_PAD_STAFF_LINES   # 5.0, not the pipeline's 4
_me.PAD_BELOW_STAFF_LINES = ORCH_PAD_STAFF_LINES
```

⚠️ **`PAD_MAX_STAFF_LINES = 6` is NOT patched**, so the grow-where-there-is-room
rule still runs on top of the 5.0 base — a labeled cell's pad is 5.0 **or up to
6**, decided per staff by `_neighbour_room`.

**This is S44 becoming expensive.** A stored label lives in the cell's CANONICAL
frame, so a cell cut at pad 5 and the same cell cut at pad 6 are not slightly
different pictures — they are the same music at a different scale, with every
box landing somewhere else. `MeasureCell` records `bbox_page_px`,
`staff_line_ys_canonical` and `upscale_factor` **but not the pad it was cut
with**, so nothing can say which frame a batch is in.

The project has already paid for that absence: `recut_cells` **derives** the mode
by cutting under each and keeping the one whose `cell_canonical_w`/`_h` the
manifest already agrees with, aborting on a mismatch. That derivation exists
precisely because the producing module does not write the field. **One integer on
`MeasureCell` would replace it** — and it is the cheapest item in this whole
audit that a second workstream is actively working around.

---

## R12. Still open after round 3

- **Not adjudicated by inspection:** whether any of the 51 multi-bar components is a sloped single bar (§R7.4). The run-count argument says no; cropping the 51 boxes would settle it.
- **Not covered:** `resegment_fused_measures`' own body past `_select_steered_splits` (the renumbering and the width guards), and `_cell_line_offset`'s search internals (S43).
- **UNMEASURED, unchanged from round 2:** the one-line-staves flag interaction (§R1.3, run named) · the post-dedupe limit on the ladder probe (run named) · whether the 197 discarding decision points contain defects.
- ⚠️ **A standing lesson I am recording against myself:** round 2 produced a confident negative from a 5-page sample whose bias was visible in the row names, and stated the correct standard two sections away from the heading that broke it. **The rule I will apply from here: a null result gets the same sampling scrutiny as a positive one, and a heading may not be stronger than the section's own hedge.**

---
---

# ROUND 4 — stage 1, `preprocessing.py`

**171 lines, four decision points, and the map's own verdict on it:** *"none of
stage 1's four constants is documented against a measurement. This is the
shallowest-evidence stage in the pipeline."* Everything downstream is built on
its output. Tree `80ee701d`; one new committed probe
(`probe/probe_sauvola_dpi_scale.py`, exits 3 on a bad `OMR_FIXTURE_ROOT`,
verified) and `sauvola-dpi-scale.json`. **No fix proposed, per the brief.**

⚠️ **Measuring stage 1 is unavoidably measuring its output** — there is no
earlier artefact. What this round does *not* do is read the final page dict:
parts C and D below read only rasters, and where a number needs `detect_staves`
(which consumes the binary this stage produced) it is marked **(downstream)**
and carries its own control.

## R13. ⚠️ THE SAUVOLA WINDOW — the suspicion is CONFIRMED, and the reason nobody has seen it is the corpus

### R13.1 (A) What 25 pixels spans — confirmed, and wider than the map suggests

`binarize` calls `threshold_sauvola(gray, window_size=25, k=0.2)`. 25 is a
**pixel** constant. Measured on four real pages at both live DPIs *(downstream:
spacing and thickness come from `detect_staves`)*:

| page | dpi | spacing px | thick px | **W in staff spaces** | W in line-thicknesses |
|---|--:|--:|--:|--:|--:|
| Beethoven 5 / Litolff (scan) | 300 | 7.75 | 2.00 | **3.23** | 12.50 |
| " | 600 | 15.75 | 4.00 | **1.59** | 6.25 |
| Brahms 1 / Breitkopf (scan) | 300 | 16.00 | 4.00 | **1.56** | 6.25 |
| " | 600 | 32.00 | 7.00 | **0.78** | 3.57 |
| Brahms 1 (engraved) | 300 | 20.50 | 3.00 | **1.22** | 8.33 |
| " | 600 | 41.50 | 5.00 | **0.60** | 5.00 |
| Mozart 41 (engraved) | 300 | 20.50 | 3.00 | **1.22** | 8.33 |
| " | 600 | 41.00 | 5.00 | **0.61** | 5.00 |

**The window spans 0.60 to 3.23 staff spaces across live configurations — a
5.4× spread — and halves between the two DPI regimes, both of which ship.** On
three of four pages at 600 dpi it is **under one staff space**: the local
statistics for a pixel inside a notehead see almost nothing but that notehead.

⚠️ **And DPI is not the only source of the spread.** At a *fixed* 600 dpi the
window runs 0.60 to 1.59 staff spaces across editions — 2.6× — because staff
spacing at a given DPI is a property of the print. A `window = f(dpi)` rule
would not make this scale-invariant.

**(B) The control**, because A is downstream: spacing must scale ~2.0× from 300
to 600, being a physical distance × dpi/72. Measured **2.032 / 2.000 / 2.024 /
2.000**. The geometry is stable, so A can be read.

### R13.2 (C) The direct experiment — and it says the choice does not matter

Same 600-dpi raster, `window=25` (ships) versus `window=51` (the DPI-scaled
equivalent of 25-at-300). No staff detection anywhere.

| page | ink@25 | ink@51 | **pixels differing** | median run 25 → 51 |
|---|--:|--:|--:|---|
| Beethoven 5 / Litolff | 0.0820 | 0.0820 | **0.0000** | 4.0 → 4.0 |
| Brahms 1 / Breitkopf | 0.0941 | 0.0960 | 0.0023 | 7.0 → 7.0 |
| Brahms 1 engraved | 0.0915 | 0.0932 | 0.0020 | 5.0 → 5.0 |
| Mozart 41 engraved | 0.0991 | 0.1008 | 0.0020 | 5.0 → 5.0 |

**Doubling the window changes at most 0.23% of pixels and does not move the
stroke thickness at all.** On Beethoven it changes *exactly nothing*.

⚠️ **This is the point at which I would have written "measured, does not
matter" — and it would have been my round-2 retraction again.** Applying my own
rule prospectively, as instructed: *what is the bias in this sample?*

- **Beethoven 5 / Litolff is CCITT bitonal at native 600 ppi.** The source
  raster is 1-bit. An adaptive threshold has nothing to adapt to, which is why
  it scores exactly 0.0000 — the page is *structurally incapable* of showing
  the effect.
- **Two of the four are LilyPond vector renders** — near-bimodal grey by
  construction, same objection.
- That leaves **one** page, and it is the one with the largest effect.

### R13.3 ⚠️ The corpus cannot answer this question — every scan-gate row is bitonal

From `works.json`'s own `raster` field, all six distinct editions behind the
20-row scan gate:

| edition | raster |
|---|---|
| Beethoven 5 / 984073 | ccitt **bitonal** |
| Beethoven 5 / 575951 | jbig2 **bitonal** |
| Dvořák 9 / 405834 | jbig2 (indexed) |
| Brahms 1 / 317803 | ccitt **bitonal** |
| Mahler 5 / local | jbig2 **bitonal** |
| Bach BWV1048 / 468678 | jbig2 **bitonal** |

**Not one greyscale scan is in any standing benchmark.** So the entire
justification in `binarize`'s own docstring — *"handles uneven illumination and
yellowed paper much better than Otsu — important for scanned scores where some
pages are darker than others"* — describes a capability **no benchmark
exercises**.

**Full census of the score library, 289 edition PDFs:** 212 bitonal (73.4%),
**48 non-bitonal 8-bit (16.6%)**, 29 vector. Roughly one edition in six is a
page where the threshold has real work to do, and none of them is measured.

### R13.4 (D) On greyscale scans the window is decisive

Same experiment, four 8-bit editions from the store:

| page | dpi | grey levels | ink@25 | ink@51 | **differing** | median run 25 → 51 |
|---|--:|--:|--:|--:|--:|---|
| Beethoven 9 / Schott 1826 | 300 | 236 | 0.1167 | 0.1326 | 0.0185 | 8 → 8 |
| " | **600** | 236 | 0.0908 | 0.1175 | **0.0284** | **8 → 16** |
| Beethoven 7 / Steiner 1816 | 300 | 215 | 0.0804 | 0.1083 | 0.0280 | 11 → 16 |
| " | **600** | 219 | **0.0377** | **0.0817** | **0.0441** | **11 → 23** |
| Haydn 100 / Breitkopf 1857 | 300 | 256 | 0.1560 | 0.1611 | 0.0095 | 4 → 5 |
| " | **600** | 256 | 0.1478 | 0.1558 | 0.0119 | **5 → 8** |
| Brahms Tragic / Simrock 1881 | 300 | 228 | 0.0199 | 0.0228 | 0.0030 | 2.5 → 3 |
| " | 600 | 236 | 0.0174 | 0.0198 | 0.0024 | 4 → 4 |

**On Beethoven 7 at 600 dpi the shipped window keeps 0.0377 ink and the
scale-equivalent window keeps 0.0817 — 2.17×, and the median stroke goes 11 px
to 23 px.** That is the predicted mechanism: a window narrower than the stroke
cannot see paper, so the interior of thick ink is thresholded away.

**The sensitivity grows with DPI on three of the four** (0.0185→0.0284,
0.0280→0.0441, 0.0095→0.0119) and **falls slightly on the fourth**
(Brahms Tragic, 0.0030→0.0024) — which is also the sparsest page in the set, at
1.7–2.0% ink. Stroke thickness doubles at 600 on three of four; Brahms Tragic
is unchanged. **Three of four, not four of four, and the exception is the page
with least ink to lose.**

⚠️ **WHAT THIS DOES NOT SHOW.** It does **not** show that 51 is right and 25 is
wrong. More ink can be bleed-through retained rather than strokes recovered; I
did not adjudicate against print truth and there is none for these pages. What
is established is that **the choice is consequential on 16.6% of the store and
inert on the 83% the benchmarks are drawn from.**

### R13.5 A constraint any future fix must respect, found by crashing

`threshold_sauvola` **refuses an even window on any dimension** — the first run
of this probe died on `window_size=50`. A `window_size = f(dpi)` rule must round
to odd or it raises at run time on some DPIs and not others.

## R14. The other three decision points, by the 13-field schema

| # | signal | measures / unit | fidelity — destroyed at | consumers (read, not grepped) | should read it | volume | fail dir. | arity |
|---|---|---|---|---|---|---|---|---|
| S54 | **Hough per-line `rho`** (`:112-119`) | line position, px | ⚠️ `HoughLines` returns `[rho, theta]` per line; `:127` reads `line[0][1]` **only**. Every position is computed and dropped in the comprehension | none | staff lines are parallel and **evenly spaced** — the rho spread would say whether the accepted lines are staff lines at all, or a table rule and a row of text baselines | 1/page | over-claims | 1-of-N |
| S55 | **the number of Hough lines** (`:121`) | count | `lines is None or len(lines) == 0 → return 0.0` | none | ⚠️ **`skew_correction_deg = 0.0` means BOTH "no line was found" and "the angle was under the dead band"** — two opposite situations, one value, and the field *is* consumed (see S57) | 1/page | over-claims | count |
| S56 | ⚑ **the SPREAD of `angles_deg`** (`:127-128`) | degrees | `median(angles_deg)` at `:128` — the distribution dies there | none | ⚠️ a **bimodal** set rotates by the midpoint of two modes, which is wrong for both — a silent wrong answer, not an abstention. One `stdev` call | 1/page | over-claims, invisibly | continuous |
| S57 | **`skew_correction_deg`** (`types.py:26`) | degrees | kept | ⚠️ **CONSUMED** — `staff_labels.py:175` reads it in production, plus `run_pipeline.py:88` and `transcribe.py:4221` serialise it. **The one stage-1 output that is not Class C** | — | 1/page | — | continuous |
| S58 | **`pix.colorspace` / bpc** (`render_page:37-47`) | the source raster's depth | ⚠️ **never formed.** The dispatch reads `pix.n` (channel count) only | none | ⚠️ **R13 makes this the load-bearing field of the whole stage**: bpc separates the 16.6% of editions where binarisation decides something from the 73% where any window gives the same answer. It is in hand at render time and `PageImage` has no place to put it | 1/page | absence is total | 1-of-N |
| S59 | **`page.rotation`, `page.get_text()`** | — | never read | none | rotation would bound the deskew search; the text layer is separately re-derived much later by `staff_labels` | 1/page | — | — |
| S60 | **`max_correction_deg` as a CHECK** | degrees | ⚠️ **does not exist** — see R14.1 | — | — | 1/page | — | — |

### R14.1 ⚠️ Two corrections to the standing documents

**(a) A docstring describing a check that is not implemented.** `deskew`'s
docstring (`:103-104`) says *"If no clear skew is detected (or it exceeds
`max_correction_deg`), the page is returned unrotated."* There is **no such
test in the function.** `max_correction_deg` appears only as the Hough
`min_theta`/`max_theta` bound (`:117-118`). The difference is real: a bound
makes an over-skewed page **invisible to the search** (its staff lines fall
outside the theta range, so `lines` comes back `None` and the page abstains),
whereas a check would *detect and reject* it. The abstention is the safer
behaviour, but a page that yields a few in-range noise lines can still be
rotated by their median with nothing rejecting it. New; same family as map D11.

**(b) The map's `input_domain.py` claim is imprecise.** Its stage-1 row says
`input_domain.py` *"sits in the same package unconsulted"*. It **is** consulted
— `transcribe.py:3896-3898`, by `_route_weights`. The accurate statement is
narrower and more interesting: **the same input is classified twice, at two
scopes, for two purposes, and neither knows about the other** — `input_domain`
at document level for weight routing, and `pix.n` at page level for channel
dispatch — while the field that would serve *both* (S58) is formed by neither.

## R15. The never-gathered register — stage 1

**(i) computed and discarded:** S54 (rho), S56 (the angle spread) — both die in
the expression that consumes them. Cited, not re-derived.

**(ii) available and never computed** — inputs in hand, no line forms it:

| | quantity | inputs in hand | the decision blind to it | cost |
|---|---|---|---|---|
| **N17** | ⚠️ **the source raster's BIT DEPTH** | `pix` at `render_page:37`; `doc.extract_image()` one call away | everything downstream that assumes binarisation did something. **R13's whole finding is that this field separates the two populations**, and `PageImage` records `dpi` but not depth | one field |
| **N18** | **the angle spread / modality** | `angles_deg` at `:127` | S56 — one `stdev`, and a bimodal page currently rotates by the midpoint silently | one call |
| **N19** | **the Hough line count and rho positions** | `lines` at `:120` | S54/S55 — and it would separate "no lines found" from "angle under the dead band", which today share the value 0.0 | two fields |
| **N20** | **the local contrast the threshold actually saw** | Sauvola's own `m` and `s` maps, computed inside `threshold_sauvola` and discarded with it | ⚠️ a page whose `s` is near zero everywhere is bitonal, and the adaptive threshold is a no-op on it — the same fact as N17, measured rather than declared | skimage returns only the threshold map; needs `_mean_std`, so this is class (iii) |

**(iii) obtainable with a new read:** N20 as noted. Also **print truth for a
greyscale page** — the thing that would say whether 25 or 51 is *right* rather
than merely different. None exists; it would have to be hand-adjudicated, and
that is the blocker on turning R13 into a fix.

## R16. Ranked conclusions

**9 · Record the raster's bit depth on `PageImage` (N17) — free, byte-identical.**
It is one field at `render_page`, and R13 shows it is the discriminator between
a stage where binarisation decides something and one where it cannot. It would
also let any benchmark state its own exposure, which is the gap R13.3 found.
**Settling measurement:** none needed to record. **Harness: none.**

**10 · Build a greyscale row into the scan gate before touching the window.**
⚠️ **This is the prerequisite, not the fix.** The window cannot be re-tuned
against a corpus that is 100% bitonal — every arm would score identically and
the A/B would report a flawless null, which is this project's most familiar
failure shape. 48 editions are available; one row would make the question
answerable. **Settling measurement:** the row must first be shown to *move* when
the window moves — otherwise it is not a row for this question.

**11 · Record the angle spread and the Hough line count (N18, N19) — free.**
Both are one expression. N19 additionally splits the overloaded `0.0`.

⚠️ **No change to `window_size` is recommended, and I would refuse one tonight
even if asked.** Binarisation is upstream of literally everything; the two
candidate values differ by 2.17× in ink on a real page; and there is no truth
against which to say which is right. The measurement says *where to look*, not
what to do.

## R17. Not covered, and what is UNMEASURED

- **`k = 0.2`** — untouched. It interacts with the window (Sauvola's `T = m(1 + k(s/R − 1))`), so the two-parameter surface is unexplored and I measured one axis of it.
- **The 0.1° dead band** — I did not measure how many real pages land inside it, i.e. how often `0.0` means "small" rather than "none".
- **Whether 25 or 51 is CORRECT** on any page. Not measured, no truth exists, and R13.4 is explicitly framed as "consequential", never "wrong".
- **The downstream cost of the window on greyscale pages.** I measured rasters. Whether a 2.17× ink change moves note recall is a full-pipeline question on pages no harness holds.
- **n = 4 greyscale pages, one page each, 4 editions.** The effect is large and consistent in direction on 3 of 4, and the fourth is the sparsest. ⚠️ By my own round-2 rule this is a *positive* on a small sample and deserves the same scrutiny a null would get: the honest claim is "consequential on the greyscale pages measured", not "consequential on greyscale pages".
- ⚠️ **A naming discrepancy in the brief, reported rather than guessed at.** There is no `fixture_root.py`. The tree has **`_fixtureroot.py`** (2 functions, 7 users) and **`_fixtures.py`** (5 functions, richer API, 17 users) — 24 between them, which is where the brief's figure comes from. `_fixtureroot.py`'s own docstring nominates **`_fixtures.py`** as the survivor. I used `_fixtureroot` because this probe renders PDFs rather than globbing committed `.omr.json`, which is what `_fixtures.py`'s pattern constants serve.

---
---

# ROUND 5 — what is actually inside `wrong note`? (Sean's question)

**The claim under test.** The coordinator told Sean that the scan gate's largest
addressable bucket — `wrong note`, **22,174 edits, 29.6% of 74,956** — is driven
by DURATIONS, on the hollow-notehead story. Sean asked whether that is measured
or inferred, and whether PITCH — via the clef, key and ownership faults this
audit has just located — could be the real driver.

**Both of us were reasoning past the metric.** My own §3 established that under
`AllObjects` musicdiff annotates a note by `pitch.step + octave` and **`wrong
pitch` is structurally unreachable**; verified again here at the source —
`AllObjects = 32767`, `Voicing = 1 << 17`, `32767 & 131072 = 0`. So `wrong note`
is the bucket of notes that **did not pair**, and it does not record *why*.

Artefacts: the 20 scan-gate pairs from the `fix-beam-bars` `basectl` arm on the
merge base **`974971e3`** — a base-tree run, not tonight's main. Committed with
both arm CSVs at `benchmarks/omr-wrongnote-decomposition-2026-09/`. **No
`scan_eval`/`orchestral_eval` was run.**

## R18. THE ANSWER

> **Of the 22,174 `wrong note` edits: ~0% are clef-caused, ~0% key-caused, at
> most ~5% ownership-caused, about 12.6% are notes and rests that are simply
> absent — and roughly 80% cannot be attributed to pitch or duration by any
> instrument available, because they are notes that failed to pair and the
> metric does not record the reason. Where the metric CAN attribute — the notes
> that did pair — duration and head-shape errors outnumber pitch-spelling
> errors 2,770 to 82, a ratio of 34 to 1.**

**So the coordinator's claim was overstated and Sean's alternative is not
supported either.** The honest position is that the bucket is dominated by
*non-pairing*, and the two named causes are each measured small.

## R19. The clef hypothesis — measured directly, and it is not the driver

musicdiff has a flag built for exactly this question. `detaillevel.py:104-109`:

> *"If specified, note staff positions will be compared instead of note pitches.
> This is good for ML training, **where an erroneous clef or ottava should not
> propagate errors into every affected note.**"*

`m21utils.py:291` confirms the mechanism: with the flag, a note is annotated
`N{diatonicNoteNum − mid_line}` instead of `step+octave`. **A clef flip changes
the pitch and leaves the staff position untouched**, so the difference between
the two arms is the clef/ottava contribution — asked of the same 20 pairs, by
the same tool.

| bucket | `AllObjects` | `+NoteStaffPosition` | delta |
|---|--:|--:|--:|
| entire measure insert/delete | 29,655 | 27,346 | **−2,309** |
| **wrong note** | **22,174** | **23,168** | **+994** |
| entire staff insert/delete | 17,520 | 17,520 | 0 |
| wrong note head | 1,788 | 1,904 | +116 |
| wrong flag/beam | 688 | 771 | +83 |
| wrong keysig | 507 | 499 | −8 |
| wrong accidental | 82 | 123 | +41 |
| **TOTAL** | **74,956** | **73,978** | **−978** |

⚠️ **The two arms are NOT comparable bucket-by-bucket, and that is itself the
finding.** Changing the annotation changes the ALIGNMENT: whole measures that
could not pair now pair (−2,309), and the notes inside them are then charged
individually (+994). The delta is a redistribution, not a subtraction.

**What survives that caveat, and it is decisive:**

- **Neutralising clef/ottava spelling moves the entire pool by 978 edits — 1.3%.** A mechanism worth 1.3% of the pool cannot be the driver of a 29.6% bucket.
- **`wrong note` does not fall. It rises.**
- **On the five rows carrying all eleven mid-staff clef flips** (`probe_clef_midstaff_flips.py`, re-run: 11 flips confirmed), `wrong note` falls on **none** — deltas 0, +1, +3, +6, +27.
- **The two largest `wrong note` rows carry no clef flip at all**: `dvorak-p7` 4,270 and `bach-p1` 3,825, together **36.5% of the bucket**. The rows *with* flips hold 19.0%.

**Key signatures cannot enter this bucket at all, structurally.** A key flip
changes a note's `alter`, not its step or octave, and `AllObjects` annotates by
step+octave. It surfaces as `wrong keysig` (507) and `wrong accidental` (82).
⚠️ This is a stronger statement than "measured small" and it did not need an
arm — it follows from the annotation rule.

**Ownership is bounded, not measured.** The committed contest dumps hold **816
notehead contests, 550 decided by distance**. At ~2 edits per wrongly-awarded
note that is **≤1,100 edits, ≤5% of the bucket** — an upper bound assuming
*every* distance call went the wrong way, which it certainly did not.

## R20. What the metric CAN attribute: paired notes, and it is not close

For notes that *did* pair, musicdiff names the fault:

| paired-note fault | edits |
|---|--:|
| wrong note head (hollow vs filled) | 1,788 |
| wrong flag/beam | 688 |
| wrong dot | 282 |
| wrong tuplet | 12 |
| **duration / head-shape subtotal** | **2,770** |
| wrong accidental (the only pitch-spelling bucket) | **82** |

**34 to 1 in favour of duration.** ⚠️ This is a real result about a real
population, and it is **not** a decomposition of the 22,174 — it is the
*complement* of it. It says: where we can see the cause, it is duration. It
cannot be extrapolated to the notes that did not pair, and I am not
extrapolating it.

## R21. A third cause neither hypothesis named: **absent rests**

Counting `<note>` elements directly, no alignment and therefore no alignment
assumptions:

| | pitched notes | **rests** | grace |
|---|--:|--:|--:|
| truth | 9,083 | **5,732** | 25 |
| pred | 9,219 | **3,520** | 0 |
| delta | **+136** | **−2,212** | −25 |

⚠️ **musicdiff annotates a rest as a note**, so `noteins`/`notedel` on rests land
in `wrong note`. **2,212 missing rests ≈ 10% of the bucket — larger than the
ownership bound and eight times the clef effect.** Neither the duration story
nor the pitch story mentions rests.

And the bucket's scale makes sense only this way: combined `<note>` elements on
both sides are **27,579**, and `wrong note` is **22,174 — 80% of every note and
rest on both sides fails to pair.** That is the real shape of the problem.

## R22. ⚠️ The hollow-notehead contradiction — resolved, and it is an EDITION effect

CLAUDE.md says both that the heads are *"not detected"* and that *"twenty of
twenty-six duration errors are a half read as something shorter"*. Counting
written `<type>` in truth and prediction:

**Pooled hollow (whole/half/breve/long): truth 1,285, pred 1,198 — a ratio of
0.932.** Not the 8-of-68 catastrophe. The "detected but mis-typed" reading is
closer to right *pooled* — but the pooled figure conceals two opposite faults:

| edition | truth hollow | pred hollow | ratio | |
|---|--:|--:|--:|---|
| Mahler 5 / Peters | 178 | 95 | **0.53** | UNDER |
| **Beethoven 5 / 984073** | 509 | 314 | **0.62** | UNDER |
| Beethoven 5 / **575951** | 509 | 484 | **0.95** | ~ok |
| Brahms 1 / Breitkopf | 62 | 193 | **3.11** | **OVER** |
| Dvořák 9 / Simrock | 27 | 104 | **3.85** | **OVER** |
| Bach / Peters | 0 | 8 | ∞ | **OVER** |

⚠️⚠️ **The two Beethoven rows are the same music and the same plate — 509 hollow
notes in both truths — and they score 0.62 and 0.95.** The variable is the
raster, not the music. **The hollow-notehead story is an EDITION effect**, and
CLAUDE.md's forensics came from `beethoven-984073-p1`, the worst edition of the
six. Even there this arm reads 31 of 68, not 8 — the graft weights already
recovered most of it.

**Programme consequence, and it is the reason this was worth measuring:** a
labeling campaign aimed at *detecting more hollow noteheads* would help two
editions and actively harm three, where the detector already emits **3–4× too
many**.

## R23. Recall — pooled parity hiding 14% dispersion

Pooled pitched notes: truth 9,108, pred 9,219, **+1.2%**. Net recall is not the
problem. ⚠️ **But the sum of absolute per-row deviation is 1,277 notes = 14.0% of
truth**, cancelling to +1.2%: **583 notes missing** on the 13 under-detecting
rows, **694 spurious** on the 7 over-detecting ones. A pooled note-count parity
is not evidence of per-page parity, and reporting only the pooled figure would
have been the same error as reporting a pooled OMR-NED for a bimodal corpus.

## R24. ⚠️ An instrument I built, tested, and withdrew

I first decomposed pitch-vs-duration with a per-row **bag of notes** keyed on
pitch alone and on duration alone. It gave a clean-looking answer — 15.0%
duration-only, 21.1% pitch-only — **and it is an artefact.** The duration
alphabet is 3–15 distinct values per page against 24–89 for pitch, so the
duration bag's intersection **saturates**: it reaches >90% of `min(|T|,|P|)` on
7 of 20 rows, which makes "duration matched" ≈ "the note exists at all". The
number measures alphabet size, not agreement. **Withdrawn before reporting.**

⚠️ **And my own comparison script printed a flawless all-zero table on its first
run** — the exact failure I have flagged in three other agents' probes tonight.
Cause: a guard keying on column 0 of a CSV whose first column is empty, so every
data row was skipped. The committed version asserts a non-zero parsed row count
and exits non-zero otherwise.

## R25. Limits, stated

- ⚠️ **Roughly 80% of the bucket is unattributable** with any instrument I have. That is the answer, not a gap in it — musicdiff records that a note did not pair, never why. Attributing it would need an onset-and-staff aligner independent of pitch, and the part correspondence needed to build one is itself broken (`entire staff insert/delete` = 17,520 edits).
- The two detail arms differ in **alignment**, so only the total (−978) and the direction of `wrong note` (+994) are safe to read. Per-bucket deltas are not.
- The ownership figure is a **bound**, not an estimate.
- **n = 20 pages, 6 editions.** The hollow finding splits 3 editions one way and 3 the other, so it is a real split on this corpus; whether the ratio generalises to the other 42 non-bitonal or 200-odd bitonal editions in the store is unmeasured.
- One base-tree arm. No repeat run, so per-row figures carry the gate's documented **±6 edit** noise; every number I lean on here is ≥978.

## R26. ADDENDUM — the third arm finished, and it changes R18

The `AllObjects | Voicing` arm (detail `163839`) completed after §R18–R25 were
written. I read it rather than leaving a completed arm unread, because §R18
leaned on the Voicing exclusion. **It materially updates the answer, and it
partly vindicates the claim I called overstated.** CSV committed as
`arm-allobjects-voicing.csv`.

`detaillevel.py:100-104`: with Voicing, musicdiff *"compare[s] which voice and
which chord each note is in… we compare the best matching pairs of voices"* —
i.e. it aligns voice-to-voice instead of flattening them.

| bucket | `AllObjects` | `+Voicing` | delta |
|---|--:|--:|--:|
| entire measure insert/delete | 29,655 | **7,239** | **−22,416 (−76%)** |
| **wrong note** | **22,174** | **10,226** | **−11,948 (−54%)** |
| entire staff insert/delete | 17,520 | 16,777 | −743 |
| wrong flag/beam | 688 | 2,535 | +1,847 |
| wrong note head | 1,788 | 3,390 | +1,602 |
| wrong accidental | 82 | 555 | +473 |
| wrong tie | 68 | 453 | +385 |
| **TOTAL** | **74,956** | **53,097** | **−21,859 (−29%)** |

**Same files, same tool, same predictions.** The only change is that voices are
matched instead of flattened — and **more than half of `wrong note` and three
quarters of `entire measure insert/delete` dissolve.**

⚠️ **So R18's "roughly 80% unattributable" is a property of the CONFIGURATION,
not of the data.** Under a voice-aware alignment most of that mass resolves into
named buckets. I am correcting my own headline: the bucket is not intrinsically
opaque; the standing detail level makes it so.

⚠️ **`wrong direction` +7,475 is an ARTEFACT and is excluded from every reading
above.** It multiplies ~50× uniformly on every row (18→891, 7→791, 13→744,
14→605, 33→608), which is what per-voice replication of a page-level direction
looks like — not a finding about directions.

### What it does to Sean's question — it strengthens the duration answer

| | duration/head family | pitch spelling | ratio |
|---|--:|--:|--:|
| `AllObjects` | 2,770 | 82 | **33.8 : 1** |
| `+Voicing` | **6,574** | **555** | **11.8 : 1** |

The `+Voicing` figure rests on **2.5× the attributed population** (7,129 vs
2,852), so it is the better-supported of the two — and it points the same way.
**Duration and head-shape dominate pitch spelling in both configurations.**

**Net verdict on the two hypotheses, revised:**

- **The coordinator's "durations" claim is better supported than I allowed in R18** — on the largest attributable population available it wins 11.8 : 1. What remains wrong with it is the *hollow-notehead* framing, which R22 shows is an edition effect running in **both** directions.
- **Sean's pitch hypothesis stays refuted**, and this arm adds to it: `wrong accidental` — the only pitch-spelling bucket — is 555 of 53,097 (**1.0%**) even after voice-aware alignment pairs everything it can.

### ⚠️ A measurement-layer finding that is not mine to act on

**29% of the standing scan gate's pooled edit count — 21,859 edits — is
attributable to voice-flattening in the metric's own configuration, not to
anything the pipeline did.** That is a benchmark-era question with large
consequences: switching detail level would make every historical figure
incomparable, exactly the discontinuity CLAUDE.md documents for the 3-work → 11-work
boundary.

**I am reporting it, not recommending it.** It belongs to Agent III and to
Sean. ⚠️ And it must not be read as "the pipeline is better than we thought" —
the predictions are identical; only the accounting changed.
