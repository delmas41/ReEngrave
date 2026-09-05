# Handoff — scanned-weights round 4, and why three hypotheses died

**Branch:** `claude/reengraved-scanned-weights-175fce` (worktree
`.claude/worktrees/reengraved-scanned-weights-175fce`), based on `origin/main`
`7291212`. Everything below is COMMITTED on that branch. **Production scan
weights are UNTOUCHED and nothing has shipped.**

---

## 0. ⚠️ READ THIS BEFORE COMPARING ANY NUMBER BELOW

**EVERY scan-e2e figure in this document is pooled over the FIVE verified rows
that existed on 2026-09-04** — beethoven-984073, beethoven-575951, dvorak-405834,
brahms-317803, mahler-local. Production = 0.7517 over THAT pool.

⚠️ **The scan benchmark's era moved TWICE the same day**, per the
industry-comparison session: 5 rows -> 11 (`results-restamp-composed.json`,
0.8303 / 35,046 edits) -> 20 (`results-reconciliation.json`, 0.8444 / 74,968).
A pooled OMR-NED is a property of the work set it is pooled over, so **a figure
here and a figure from the 11- or 20-row pool are measurements of different
things and differencing them is invalid in either direction** — the same rule
`CLAUDE.md` enforces for the engraved 3->11 boundary.

If you resume this work, **re-baseline production on the current pool first**
and re-run any candidate against it. Do not carry 0.7517 forward.

⚠️ **AND ~2676 EDITS PER ARM ARE NOT A WEIGHTS SIGNAL.** `entire staff
insert/delete` is 2676 in EVERY arm measured here — production and all
candidates alike, identical to the edit. The industry-comparison work then
showed that on the 11-row pool 87% of the `entire staff` bucket is
**CONDENSATION**, with detection exactly right. So a large, constant slice of
these pooled figures is inert to anything a checkpoint can change, and the
weights-sensitive portion is much smaller than the headline suggests. Read the
per-CATEGORY deltas (wrong note, note head), not the pooled ratio, when judging
a checkpoint.

For context on where the detector actually stands against Audiveris, measured
on our own fixtures with our own scorer (`benchmarks/omr-vs-industry-2026-09/`).
⚠️ OMR-NED is LOWER-IS-BETTER, so read the direction carefully:

    engraved            ours 0.1125   Audiveris 0.1252   -> WE LEAD
    scan, 11-row pool   ours 0.8345   Audiveris 0.7919   -> AUDIVERIS LEADS

We win every major READING category on the scan pool (wrong note -88, note head
-490, beams -46, directions -104) and the ENTIRE pooled deficit is the `entire
staff` bucket — of which 87% was proved to be CONDENSATION with our detection
exactly right.

⚠️ **So do NOT spend weight iterations on that gap.** It is a part-model
artifact, not a detector or weights problem, and no checkpoint can move it.

---

## 1. The one-line state

Round 3 and round 4 both **FAILED** the scan-e2e gate. The labeling work
succeeded and is banked. The blocker is not the labels, not the training image
size, and not page density — all three were tested and refuted. What remains is
that **any fine-tune on this corpus immediately degrades the base model's
breadth**, and that is where the next session should start.

## 2. What shipped into the tree (all committed, all reversible)

| what | where |
|---|---|
| 760 human boxes over 493 cells (rests+accidentals, clefs, Simrock draw-from-scratch) | `benchmarks/omr-labeling-*/verdicts/` |
| v13–v21, superseding v7/v8 | `data/user-labeled/` + `catalog-versions.txt` |
| v22 = Simrock 110 dense cells, 759 boxes | `data/user-labeled/v22-2026-09-04-simrock-dense` |
| audited model completions (marks, noteheads) | `benchmarks/*/marks-completion/`, `notehead-completion/` |
| pass configs incl. the rich draw palette | `benchmarks/omr-labeling-survey-2026-09/pass-configs/` |
| production + 4 candidate scan-e2e arms | `benchmarks/omr-scan-e2e-2026-09/results-round*.json` |
| 3 drafted non-German benchmark rows (UNVERIFIED, held out on purpose) | `benchmarks/omr-scan-e2e-2026-09/works-draft-nongerman.json` |

**Training mix now:** 14 versions, 752 cells, **5211 boxes, 6.9/cell**, class
profile 45.3% notehead / 12.0% accidental / 10.3% rest / 9.6% dynamic / 7.2%
slur+tie — i.e. it now tracks v1–v4 (44.3/9.8/11.4/8.1/5.8) at 3.9x the volume.
v7/v8 were 92.4% noteheads with ZERO rests, accidentals, dynamics or slurs.

## 3. The measurements that matter

**Gate axis 2 — scan-e2e, 5 verified rows. Production is the number to beat.**

| checkpoint | trained | epochs | pooled OMR-NED | edits | predicted |
|---|--:|--:|--:|--:|--:|
| **production** | 896 | **1** | **0.7517** | 7894 | **4350** |
| round3 e3 | 2048 | 3 | 0.7525 | 7016 | 3172 |
| round3 e5 | 2048 | 5 | 0.7579 | 7134 | 3262 |
| round3 e10 | 2048 | 10 | 0.7705 | 7312 | 3339 |
| round4 e5 | 2048 | 5 | 0.7588 | 7220 | 3364 |
| imgsz512 e1 | 512 | 1 | 0.7646 | 7404 | 3533 |
| imgsz512 e5 | 512 | 5 | 0.7539 | 6885 | 2982 |

**Gate axis 1 — beet5-p1, where every checkpoint WINS. Do not gate on it alone.**

| | dense recall | F1 | half-notes | black | with-duration R |
|---|--:|--:|--:|--:|--:|
| production | 0.941 | 0.625 | 27 | 79 | 0.435 |
| round3 e5 | 0.991 | 0.930 | 32 | 66 | 0.571 |
| round4 e5 | 0.986 | 0.914 | 34 | 75 | 0.605 |
| round4 e30 | 1.000 | 0.871 | 44 | — | 0.626 |

## 4. ⚠️ THREE HYPOTHESES TESTED AND DEAD — do not re-run these

1. **"The label distribution caused the suppression."** MINE, and wrong.
   Rebuilding the mix from 92.4% noteheads to a v1–v4 match moved predicted
   symbols only 3262 → 3364 against production's 4350. Dvorak/Simrock — the page
   the 110 new cells targeted — did improve 0.5931 → 0.5529, so the labeling
   worked; it just was not the bottleneck.
2. **"Train/inference scale mismatch."** MINE, and wrong. Inference calls
   `imgsz_for_cell`, which sizes each cell so a staff space is
   `TARGET_STAFF_SPACE_PX = 16` — measured 224–512, median **320** over 80 real
   cells, against training at 2048 (6.4x) and production's 896 (2.8x). Looked
   damning. But training AT 512 predicted **fewer** symbols (2982), not more.
3. **"Image size should track page density."** Sean's, and wrong for an
   instructive reason: canonical cell rescaling ALREADY normalises density —
   every publisher lands at 288–352 inference imgsz with a ~100 px staff space.
   Litolff and Simrock share imgsz 320 and prefer OPPOSITE training scales.

⚠️ **A fourth reading of mine was also wrong and is worth recording because it
was seductive:** I inferred from edit counts (production 7894 vs imgsz512 6885)
that production must be over-detecting and our checkpoints were secretly better.
Element counts against truth refute it outright:

| element | truth | production | imgsz-512 |
|---|--:|--:|--:|
| note | 922 | **901** | 560 |
| tie | 227 | 58 | **0** |
| slur | 202 | 147 | **0** |
| accidental | 85 | 79 | **0** |

Production is close to truth everywhere; imgsz-512 emits ZERO ties, slurs and
accidentals. OMR-NED divides by `truth + predicted`, so a model that
under-predicts is flattered — `CLAUDE.md` warns about this symmetry and I read
it the wrong way round. **Always check element counts against truth before
believing an OMR-NED delta.**

## 5. What actually survives, and the next experiment

**Every fine-tune degrades the base immediately.** One epoch already drops
predictions 4350 → 3533. More epochs make it worse. Production is the only
checkpoint that is barely moved from the base, and it is the only good one.

The likely cause is a corpus-scale mismatch: ~750 cells / 5211 boxes / ~30
classes against DSv2's 208 classes and hundreds of thousands of annotations.
Fine-tuning trades the base's breadth for our narrow slice. This project has hit
the same wall three times before — the clef fine-tune collapsed dense notehead
recall 2506 → 114, v5/v6 are excluded from the catalog for it, and domain
augmentation measured augmented 0.122 < clean 0.384 < production 0.652.

**So the next lever is METHOD, not data:**

1. **Freeze the backbone**, train only the detection head (`--freeze N` in
   ultralytics). Preserves base features by construction.
2. **Rehearsal** — mix DSv2 samples back into the fine-tune so the other ~190
   classes are refreshed. The standard anti-forgetting method and untried here.
3. **Much lower LR / fewer steps** than `optimizer=auto` picks (it chose AdamW
   lr 4.7e-05).
4. If none work: **do not fine-tune for the broad metric at all.** Use a
   specialist only where it wins (hollow noteheads) and route to it, which is
   what the existing scan/engraved router already does structurally.

**Cheap to test:** an imgsz-512 run is 30 epochs in **2.7 minutes**; 2048 is 28
minutes (batch 16 vs 2). So a method sweep costs pennies — rent, test, destroy.

**Sweep checkpoints are preserved at `omr-weights/round4-sweep/`** (gitignored,
2.2 GB, survives reboot):

    best_320.pt best_512.pt best_768.pt best_1024.pt best_2048.pt   (30 epochs)
    e1_320.pt e1_512.pt                                             (1 epoch)
    r4_2048_e5.pt r4_512_e5.pt                                      (the gated ones)

⚠️ `e1_768.pt` is 241 MB against the others' 335 MB — a TRUNCATED transfer.
Do not use it. 896 was queued behind 1408 and never ran; the box is destroyed,
so re-run it if wanted (~4 min).

## 6. How to run the gate

```bash
# BOTH axes. They disagree — round 3 won axis 1 at every epoch and still failed.
./benchmarks/omr-labeling-survey-2026-09/run_gate_round3.sh <ckpt.pt> <tag>
```
⚠️ Pass **absolute** weights paths. `DEFAULT_WEIGHTS` is repo-relative and names
a gitignored file, so in a worktree the baseline arm silently measures nothing.
Set `OMRNED_PYTHON=/Users/seanjohnson/Desktop/ReEngrave/.venv-omrned/bin/python`
and symlink `.venv-surya`.

## 7. Loose ends

- **3 non-German benchmark rows drafted, unverified.** Mahler 1 / Elgar 1 / La
  mer have NO reference encoding and can never be rows; the substitutes are
  Holst/Goodwin & Tabb (English), Tchaikovsky 4/Jurgenson (Russian) and
  Tchaikovsky 4/Heugel (French). Each needs a human to confirm the page starts
  at bar 1 and holds N bars. Held out of `works.json` deliberately —
  `scan_eval` refuses a pooled figure while any row is `first_pass`.
- **2 label candidates in v1–v4** (`mahler5-p175-sys4-s12-m4`,
  `debussy-la-mer-p105-…-s4-m1`) are clipped edge fragments, not noteheads —
  0.54 and 0.51 staff spaces, 7 px and 22 px from their cell's top edge, above
  their own staff. Correct fix is DELETE, not relabel. Sean's call; untouched.
- **`_drop_clipped_notehead_fragments` runs on MODEL detections only.** A human
  labelling a padded cell sees the same ambiguous ink with nothing checking. The
  peer session shipped an edge-fragment check into
  `benchmarks/omr-snap-ledger-2026-09/audit_ledger_zone_labels.py`.
- ⚠️ **`CLAUDE.md`'s labeling recipe still says `--imgsz 2048` for `run_yolo`.**
  That is wrong for cell batches — it produced boxes on barlines and nothing on
  noteheads. Use `benchmarks/omr-labeling-survey-2026-09/prelabel_percell.py`.
- **Ledger-zone label audits over-flag**: 6 of 7 Simrock candidates were false
  positives (ledger rungs survive staff removal and bias blob measures). Read
  the tool's rate as an upper bound, adjudicate by eye.
- **Brahms 1 batch** is shared with another session; its verdicts were merged
  here additively. Check `inspected_passes` before assuming a pass ran.


## 8. Cost and instances

Total spend **$0.74** of a $10 budget. Three instances were rented: the first
(France) trained rounds 3-4; the second (Delaware) was destroyed unused because
its `ssh5` proxy refused connections before key exchange while the instance
reported "running" — a broken host, not an auth or boot problem; the third
(BC Canada) ran the imgsz sweep. **All three are destroyed — nothing is
billing.**

⚠️ Two rent attempts failed with `no_such_ask` — offers taken between listing
and click. Sean's vast.ai session had also silently logged out at one point.
Verify on the Instances page that you got the machine you picked; the offer
list re-sorts under you.
