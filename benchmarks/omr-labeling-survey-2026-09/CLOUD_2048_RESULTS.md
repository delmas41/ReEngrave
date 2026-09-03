# The cloud imgsz-2048 hollow run — measured, NOT shipped

**Date:** 2026-09-03 · **GPU:** rented vast.ai RTX 4090 (~$0.50 total) ·
**Verdict:** KEEP current production scan weights. p29 is a real half-note gain
but carries a **completeness regression**; iterate the completion, don't ship.

Follows `SHIP_RESULTS.md` (the local imgsz-896 hollow ship) and the decision to
run the "proper" recipe on a cloud GPU (`CLOUD_HANDOFF.md`). The domain **weight
router** (main `7c76ef8`) landed while this ran, so a scan checkpoint would ship
into the **Scanned PDF Weights** slot only — engraved input routes elsewhere.

## What ran

Fine-tuned from the **pre-hollow 2048 base** (`imgsz2048-ft-30ep.pt`) at native
**imgsz 2048** on the Phase-1+2 hollow mix (v1–v4 dense ×3 oversample + v7–v11
hollow; **Tchaikovsky v12 held out**), `save_period=1`, music-aug, nc=208. Two
runs: **10 epochs**, then **30 epochs** (the 10-ep tail was still rising). All
checkpoints pulled + stripped to `omr-weights/cloud-2048{,-30ep,-ablation}/`
(gitignored, kept for the next iteration).

## Results (all vs current production scan weights)

**30-epoch best = `epoch29.pt` ("p29"), on the weights-sensitive axes:**

| axis (Beethoven 5 scan p.1) | production | p29 |
|---|--:|--:|
| dense notehead recall (forgetting, scan cells) | 0.941 | **0.950** held |
| scan half-notes | 27 | **35** |
| scan with-duration recall | 0.435 | **0.605** (+39%) |

**But the 5-page / 4-publisher scan-e2e (full-symbol OMR-NED) REGRESSES:**

| page | publisher | prod | p29 |
|---|---|--:|--:|
| Beethoven 5 (984073) | Litolff | 0.6925 | 0.7037 |
| Beethoven 5 (575951) | Litolff | 0.7660 | 0.7250 |
| **Dvořák 9** | **Simrock** | **0.4381** | **0.6692** ✗ |
| Brahms 1 | Breitkopf | 0.9205 | 0.9446 |
| Mahler 5 | Peters | 0.7122 | 0.6520 |
| **pooled** | | **0.7512** | **0.7761** |

p29 predicts **fewer symbols on every page** and breaks the Dvořák page.

## The three things this settled

1. **imgsz is a NON-FACTOR.** prod and p29 are **byte-identical at 512 / 1024 /
   1280** (`imgsz_sweep.log`) because the pipeline canonically rescales each
   measure cell before detection — the letterbox size doesn't change what the
   model sees. So the scan-e2e comparison was like-for-like; there was no hidden
   resolution handicap, and "best at ~1048" does not apply to this cell-based
   pipeline (likely a memory of the older full-page path).

2. **The regression is COMPLETENESS, not notes.** p29 reads noteheads/half-notes
   markedly better but detects fewer **rests + accidentals** → sparser
   transcriptions → the OMR-NED rise. Same page, two metrics disagree because
   they measure different things: note-recall (p29 wins) vs full-symbol edit
   distance (p29 loses).

3. **Mechanism — the completion scope, one level down.** The completion step
   labeled only **black noteheads + augmentation dots** (rests/accidentals were
   dropped as FP-prone), so on the Phase-2 cells rests+accidentals were
   **unlabeled background**. One epoch (the 896 ship) barely notices; **30
   epochs taught p29 to suppress them.** The exact "unboxed = background" trap
   the labeling discipline warns about, applied to the completion pass.

Also measured: the **±Tchaikovsky ablation** — adding the low-res v12 *halved*
the half-note gain (35 → 13) while nudging dense up (its cells complete to ZERO
black noteheads — the blur defeats the detector). **Drop v12** from any mix;
defer low-res to its own methodology.

## Verdict + next iteration

**Do NOT ship p29.** The completeness loss is a real quality regression (a user
would have to re-add missing rests/accidentals), and shipping needs a robust win.

The half-note gain is genuine, so the fix is a **targeted next iteration**, not
abandonment:
- **Complete the cells FULLY** — label rests + accidentals in the hollow cells
  (a second completion pass, or a rests/accidentals labeling sweep) so a longer
  fine-tune can't suppress them.
- and/or **fewer epochs** — the earlier checkpoints suppress less; the 10-epoch
  run was at parity (no completeness loss but no clear gain either).
- **Widen the scan-e2e benchmark to non-German publishers** (Universal/Vienna,
  Novello/English, Durand/French) before the next ship — the German-only 5-page
  set caught this regression; the non-German traditions the Phase-2 labels cover
  should be in the validation too. Each new row needs a verified measure window.

Everything is banked: the Phase-2 labels (v9–v12 on main), the cloud pipeline
(`run_cloud_training.sh`, `oversample_dense.py`, `CLOUD_HANDOFF.md`), the
router, and the p29 checkpoints on disk. Production scan weights are untouched.
