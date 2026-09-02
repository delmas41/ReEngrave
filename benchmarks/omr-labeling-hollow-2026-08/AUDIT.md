# Audit of the merged labels (2026-09-02)

Sean labelled this batch in **blank-canvas mode**: `detections/` was emptied to
48 stubs, the model's 262 pre-labels were moved aside to
`detections-pre-labels/`, and he drew **only hollow noteheads** — 29 boxes over
25 cells. Exported as-is that would have taught the model that every black
notehead, rest and accidental in those cells is background, so the pre-labels
were merged back in (`verdicts-merged/`) and every box was then looked at on
the cell image before export.

`verdicts/` is untouched. It is the human record and nothing in this pass
writes to it.

**Result: 24 of 25 cells exported, 28 boxes** —
`data/user-labeled/v7-2026-09-02-hollow/`.

---

## ⚠️ Read this before training on v7

**Only one of 117 model pre-labels survived the audit.** On this print the
detector is not "mostly right and needing confirmation" (which is what the
batch README assumed when it planned triage mode) — it is wrong nearly
everywhere. 116 of the 117 non-structural pre-labels in the exported cells
were culled, most of them firing on ink that is not a symbol at all.

**So the exported label files are single-purpose.** They say *these 27 blobs
are hollow noteheads* (plus one confirmed black notehead) and nothing else. In
the 24 cells there are also **unlabelled** clefs (1 treble), slur arcs (~20),
dynamic letters (2 `p`), a fermata, and the left/right barlines — all clearly
visible, none boxed, and therefore all trained as background. That is a real
cost against classes the pipeline uses downstream (`export.annotate_slurs`
consumes YOLO `slur`/`tie` detections; the clef reader consumes `clefG`).

The completeness rule was applied on the **enumeration the batch is about** —
noteheads, rests, accidentals, augmentation dots, flags. Widening it to
clefs/slurs/dynamics would have excluded essentially the whole batch, so the
tradeoff is recorded here rather than taken silently. **A training decision
for Sean:** use v7 for the notehead classes, or weight it down, or drop it.

---

## What was excluded, and why

| | cells | boxes |
|---|--:|--:|
| Sean's cells with drawn boxes | 25 | 29 hollow |
| — excluded for completeness | 1 | 2 hollow |
| **exported to v7** | **24** | **28** (27 hollow + 1 pre-label) |
| cells with no verdict file | 23 | — |

### The one excluded cell

**`beet5-p6-sys0-s8-m13` — an obvious hollow notehead is unboxed.**
At the top of the crop (`x≈150-320, y≈0-115`, about 80% of the head visible
before the cell boundary cuts it) there is an unmistakable ring with a white
diagonal counter — the same signature as the two heads Sean *did* box lower in
the cell. It belongs to the staff above, which is presumably why it was passed
over. An unboxed instance of exactly the class the batch teaches is the worst
kind of incompleteness, so the cell is out. Cost: 2 hollow boxes
(`noteheadHalfInSpace` + `noteheadHalfOnLine`).

The overlay is `overlays/beet5-p6-sys0-s8-m13.overlay.png` (untracked; regenerate
from `cells/`).

### The 23 cells with no verdict file

**Not skipped — inspected.** Sean went through all 48; the UI only writes a
verdict file once something is decided, so browsing a cell that contains no
hollow notehead leaves no file. Batch coverage was 48/48.

They are absent from v7 because their remaining content — black noteheads,
rests, beamed groups — carries **no human verification**, and the pre-labels
are exactly the ones this audit found unusable.

*Agent cross-check, all 23 viewed:* no hollow noteheads. Nine Beethoven cells
hold beamed black eighths, whole rests, an 8th rest, `p` dynamics, a flat; ten
Boléro cells (a clean Durand engraving, not a bled scan) hold solid heads under
beams, an 8th rest and a treble clef. **Sean's read is confirmed on all 23 —
nothing to flag.**

They remain available as **agent-audited negative candidates** — scan-domain
short bars with no hollow head in them — should a future training decision want
hard negatives. That is a versioned decision for later, not part of v7.

---

## Per-cell

`pre` = pre-labels present · `struct` = dropped by class · `cull` = dropped in
this audit · `kept` = pre-labels exported as TP.

| cell | exported | human boxes | pre | struct | cull | kept |
|---|---|---|--:|--:|--:|--:|
| `beet5-p2-sys0-s2-m3` | yes | 1 (HalfOnLine) | 4 | 1 | 3 | 0 |
| `beet5-p2-sys0-s3-m11` | yes | 1 (HalfInSpace) | 2 | 0 | 2 | 0 |
| `beet5-p2-sys0-s3-m14` | yes | 1 (HalfOnLine) | 1 | 1 | 0 | 0 |
| `beet5-p2-sys0-s3-m6` | yes | 1 (HalfOnLine) | 9 | 0 | 9 | 0 |
| `beet5-p2-sys0-s3-m7` | yes | 1 (HalfOnLine) | 5 | 1 | 4 | 0 |
| `beet5-p2-sys0-s3-m8` | yes | 1 (HalfOnLine) | 10 | 1 | 9 | 0 |
| `beet5-p2-sys0-s7-m1` | yes | 1 (HalfOnLine) | 8 | 3 | 5 | 0 |
| `beet5-p2-sys0-s8-m8` | yes | 1 (HalfOnLine) | 4 | 2 | 2 | 0 |
| `beet5-p2-sys0-s9-m15` | yes | 1 (HalfOnLine) | 6 | 1 | 5 | 0 |
| `beet5-p4-sys0-s2-m6` | yes | 2 (OnLine+InSpace) | 3 | 3 | 0 | 0 |
| `beet5-p4-sys0-s5-m5` | yes | 2 (InSpace+OnLine) | 5 | 2 | 3 | 0 |
| `beet5-p4-sys0-s6-m4` | yes | 1 (HalfInSpace) | 2 | 0 | 2 | 0 |
| `beet5-p4-sys0-s6-m5` | yes | 1 (HalfInSpace) | 6 | 2 | 3 | **1** |
| `beet5-p4-sys1-s14-m0` | yes | 1 (HalfOnLine) | 8 | 1 | 7 | 0 |
| `beet5-p4-sys1-s14-m1` | yes | 1 (HalfOnLine) | 1 | 0 | 1 | 0 |
| `beet5-p4-sys1-s14-m2` | yes | 1 (HalfOnLine) | 0 | 0 | 0 | 0 |
| `beet5-p6-sys0-s0-m4` | yes | 1 (HalfOnLine) | 4 | 0 | 4 | 0 |
| `beet5-p6-sys0-s6-m1` | yes | 1 (HalfOnLine) | 7 | 1 | 6 | 0 |
| `beet5-p6-sys0-s8-m13` | **NO** | 2 (InSpace+OnLine) | 2 | 0 | 2 | 0 |
| `beet5-p6-sys1-s12-m10` | yes | 1 (HalfOnLine) | 1 | 0 | 1 | 0 |
| `beet5-p6-sys1-s14-m5` | yes | 1 (HalfOnLine) | 5 | 0 | 5 | 0 |
| `beet5-p6-sys1-s15-m1` | yes | 1 (HalfOnLine) | 10 | 1 | 9 | 0 |
| `beet5-p6-sys1-s9-m1` | yes | 1 (HalfOnLine) | 17 | 1 | 16 | 0 |
| `beet5-p6-sys1-s9-m2` | yes | 1 (HalfOnLine) | 9 | 1 | 8 | 0 |
| `beet5-p6-sys1-s9-m9` | yes | 2 (OnLine+InSpace) | 14 | 2 | 12 | 0 |

---

## Dropped by class, before looking at anything

24 pre-labels — `beam` 17, `staff` 4, `brace` 2, `ledgerLine` 1. Per CLAUDE.md
these are never labelled: staff lines, stems and beams are detected by
classical CV upstream (`staff_detector`, `line_detection`) and YOLO cannot bbox
a thin line. `brace` is page furniture on the same footing and appears in none
of v1–v6. `ledgerLine` is the one judgement call — v1/v2/v3 carry 7 such boxes
between them, but CLAUDE.md calls ledger lines "low-value" and the single
instance here would have been 1 of many in its cell, i.e. incomplete either
way. **Overrule it by editing `DROP_CLASSES` in the merge and re-running if you
disagree** — no ledger information is lost, the box is still in
`detections-pre-labels/`.

## Culled in the audit — 116 boxes, by reason

| reason | n | what the ink actually is |
|---|--:|---|
| inside a human hollow-head box | 45 | the model firing `noteheadBlack*` / `flag8thDown` on the *same* glyph Sean called hollow — up to 8 mutually-overlapping boxes on one head (`s15-m1`, `s9-m9`) |
| on a slur or tie arc | 34 | bled arcs read as `restWhole` (conf up to 0.52) or noteheads; on this print a slur bleeds into a 400px horizontal lens |
| on the barline / system rule | 17 | stacked boxes at `x=0` or at the cell's right edge — `s9-m1` has 5, `s3-m8` has 3 `restQuarter` 200–273px tall on one barline |
| **empty box** | 10 | nothing at all under it once the staff lines are removed — the model fired on a staff line |
| on a stem | 5 | including a `restQuarter` 63×223 and a `rest8th` |
| on the dynamic letter `p` | 3 | `s3-m6` prints a bold italic **p**; three boxes split its bowl and stem as noteheads |
| edge-clipped fragment | 2 | < 0.6 staff space tall at the crop boundary — the class `transcribe._drop_clipped_notehead_fragments` removes in production |

By class: `noteheadBlackOnLine` 48, `noteheadBlackInSpace` 32, `restWhole` 28,
`restQuarter` 5, `flag8thDown` 2, `rest8th` 1.

**These pre-labels were never triaged to conf ≥ 0.50 + per-class NMS** the way
CLAUDE.md's recipe prescribes: the floor in `detections-pre-labels/` is 0.25
and the duplicate-suppression clearly did not run per class. That is most of
the explanation for the 116.

## The one pre-label kept

`beet5-p4-sys0-s6-m5` **D1**, `noteheadBlackInSpace`, conf 0.32, bbox
(343, 299, 68, 90). Read twice, at 4× on the un-stripped cell: a solid rounded
blob in the space above the top staff line with the stem attached on its left
and descending through the line — a stem-down black notehead, correctly
classed. The first reading called it a flag and was wrong. The diagonal streak
to its lower left is ambiguous bleed and stays unboxed.

## Sean's own boxes

**Not second-guessed** — no class or position was changed, and none of the 29
is physically impossible (every box contains ink, and every one contains
notehead-scale ink). Two observations, not corrections:

- The boxes are **generous**: 159–298 px wide and 150–208 px tall against a
  100 px staff space, i.e. 1.5–3× a notehead's own extent. YOLO will learn a
  slightly loose box prior for `noteheadHalf*` from these 27 examples.
- Three of them (`s15-m1`, `s9-m1`, `s6-m1`) enclose an ink mass dense enough
  that a second note may sit inside the same box. Left alone; flagged here.

---

## Catalog: **not rebuilt**, and that is the finding

`build_catalog_yaml.discover_versions()` unions **every** `vN-*/` directory
under `--root`. There is no `--only` / `--exclude` flag; the only knob is
`--root`.

The committed `catalog.yaml` was generated **2026-07-10** and unions v1–v4
(136 train / 25 val). v5 and v6 landed on main on 2026-08-29 (`e333292`) and
are on disk but *not* in it. PROJECT_STATUS §"open decisions" #13 records the
exclusion as deliberate — 62 clef-heavy cells narrow the density prior, which
is what collapsed dense-page noteheads 2506 → 114.

So **the exclusion is maintained by nobody re-running the builder.** Running it
today would silently pull in v5, v6 *and* v7 and reverse a recorded decision.
`catalog.yaml`, `_catalog_*.txt`, `_catalog_summary.json` and `_nc208/` are
therefore left exactly as they were, and **whether v7 enters the catalog is a
training-time decision for Sean**, alongside the standing v5/v6 one.

⚠️ Worth fixing separately: a deliberate exclusion that survives only as long
as nobody runs a documented command is a footgun of the same shape as the
nc=214 one that was closed in July.

---

## How to reproduce the audit view

`overlays/` is gitignored (`benchmarks/*/overlays/`). Each PNG is the cell and
its staff-line-removed variant side by side, with pre-labels in green,
class-dropped pre-labels in grey and Sean's boxes in magenta. Regenerate from
`cells/` + `detections-pre-labels/` + `verdicts/`. **The staff-line-removed
panel is what made the audit possible** — on this print the staff lines are
40 px thick and everything reads as one black mass until they are taken out.
