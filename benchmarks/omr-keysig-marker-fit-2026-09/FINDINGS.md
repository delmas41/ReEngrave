# The slot-table fit on the DETECTOR's key markers — measured, and NOT worth a GATHER change

**2026-09-21. NO CODE UNDER `tools/`** (`git diff -- tools/` is empty for this
lane). The measurement `docs/NEXT-2026-09-21-keysig-reading-lever.md` asked for,
run on both shared records.

---

## Ask-first block

**CONVENTION.** A key signature is a run of accidentals at fixed staff
positions for (clef, N) — so the POSITIONS decide it, not the count. Not in
doubt; it is the project's paid-for method and `key_signature_geometry` is it.

**NOT CONFIRMED WITH SEAN.** Nothing here proposes a default, a constant or a
flag.

**WHAT WOULD FALSIFY §5.** A document where the markers' box centres sit on
the slots on BOTH publishers. Breitkopf's do not, by −1.29 steps.

---

## 0. ⚠️⚠️ THE BRIEF'S PREMISE IS FALSE, AND IT REFRAMES THE JOB

> `fit_key_signature` **is that reader, and it has never been given the
> detector's markers as its ink source**; it is fed the CV locator's ink only.
> So: **same reader, different ink.**
> — `docs/NEXT-2026-09-21-keysig-reading-lever.md:46`

**It has been given exactly that since `7c6b6481`, 2026-08-28** — *"omr: fit
the DETECTOR's key-signature markers too, not just the locator's"*:

| | |
|---|---|
| `transcribe.py:856` | `fit_key_signature(positions, clef, accidental, _DETECTOR_FIT_CONFIG)` |
| `positions` | `_staff_positions_for(markers, cell)` — box centres as diatonic steps below the top line, in x-order, off the cell's own `staff_line_ys_canonical`, `None` where there is no geometry |
| `markers` | detections whose class starts `keysharp` / `keyflat` |
| `_DETECTOR_FIT_CONFIG` | `KeySignatureFitConfig(max_outliers=1)`, written for this ink |

⚠️ **AND THE BRIEF CONTRADICTS ITSELF AGAINST ITS OWN AUTHOR'S CODE.**
`staged/adjudicators/header.py:17`, same branch, same session: the legacy path
*"falls back to counting them where **the slot fit abstains**"* — a sentence
that presupposes the fit it elsewhere says has never existed.

**So this is a PORT of a shipped LEGACY reader, not a new one — the sixth
instance of the symbol sweep's §2a family** (*"'Shipped' means the legacy path
— the staged reader is systematically weaker than the documents say"*), found
in the family that sweep's own ranked #4 points at.

## 1. ⚠️ HALF THE UNIT IS NOT ON THE RECORD, AND THE TREE ALREADY NAMES THE CONSUMER

`fit_key_signature` wants steps below the TOP STAFF LINE. `_cell_grid` returns
`(top_y, half_step)`; two consumers use it (`Q.NOTEHEAD_STAFF_POSITION`,
`Q.CLEF_POSITION`) and **`Q.CELL_STAFF_SPACE` files `half_step` and DROPS
`top_y`**. Verified: **0 of 40,878 rows** carry the cell's top line in the cell
frame. `Q.CELL_POSITION_BASIS` exists and is only ever *abstained*, never
observed with a value.

`_cell_grid`'s own docstring names this exact consumer:

> a consumer asking "where is this OTHER glyph, in staff steps" had nothing to
> ask with. That is the pattern this architecture exists to kill.

It was **half-fixed**: `half_step` rescued onto the record, `top_y` not.

⚠️ **RECOVERABLE WITHOUT A RE-GATHER.** For any notehead,
`pos_float = (y_center - top_y) / half_step` (`gather.py:497`), so
`top_y = (y + h//2) - pos_float * half_step`.

**POSITIVE CONTROL, AND IT CAN FAIL** (`probe_backsolve_control.py`): every
notehead in a cell must back-solve to the same `top_y`.

| spelling | cells EXACT (<1e-9) | max spread |
|---|--:|--:|
| `y + h // 2` (what the record uses) | **598 / 598** | **0.000000** |
| `y + h / 2.0` | 154 / 598 | 0.500000 |

⚠️ **A SPELLING DIVERGENCE, RECORDED AND IMMATERIAL HERE**: the legacy
`_staff_positions_for` uses `y_canonical + height_canonical / 2.0` (float) while
the staged `d.y_center` is `y + h // 2` (floor). They differ by ≤0.5 canonical
px = **0.011 steps**, against a `max_residual` of 0.5 — 45× under the gate. Not
a fault today; it would become one if either side tightened.

## 2. REACH — measured before accuracy, and it is the smaller half

⚠️ A cell with no notehead has NO unit and **ABSTAINS**; it is never handed a
nominal spacing. That is this project's own precedent and it costs 4 staves.

| | Litolff Beethoven 5 pp.1-4 | Breitkopf Brahms 1 pp.0-3 |
|---|--:|--:|
| key verdicts abstaining | 26 | 21 |
| carrying detector markers | 12 | 10 |
| out — `needs_clef` | 2 | 0 |
| **out — no unit (cell 0 has no notehead)** | **4** | 0 |
| **MEASURABLE** | **6** | **10** |
| the fit ANSWERS | **2** | **3** |
| the fit ABSTAINS | 4 | 7 |

The brief's 10-and-10 reproduces exactly; the unit test it could not have asked
for removes 4 more on Litolff.

⚠️ **SEVERAL STAVES CARRY A SINGLE MARKER** (3 of Litolff's 6, 2 of
Breitkopf's 10), and with one observation a "fit" degenerates toward the count
the brief's own trap section condemns — it is one slot match inside
`max_offset`. **The population with enough ink to be a run is nearer 3 and 8.**

## 3. ACCURACY — Litolff only, and the constant wins flat

⚠️ **BREITKOPF CANNOT BE SCORED.** Its truth is a dossier — an ENCODING, not
the page — usable to show a value is impossible, never to score accuracy. So
**n = 6 staves, 1 document, 1 publisher.**

| | |
|---|--:|
| READING | right **1**, wrong **1**, abstained **4** |
| FILE (an abstention exports no `<key>`, which reads as no accidentals) | 0/6 → **1/6** |
| **NULL — "3 flats on every one"** | **6/6** |

**The fit scores 1 of 6 where a constant scores 6 of 6.**

⚠️⚠️ **AND THE REACHABLE POPULATION IS BIASED TOWARD WHERE THE CONSTANT WINS:
all 6 are truth −3**, while the full 26 abstaining staves are `{-3: 17, 0: 8,
-1: 1}`. The constant is inadmissible by this project's doctrine (*a fallback
must never convert "cannot tell" into a definite answer*) and on the full set it
would write **9 confidently wrong** signatures. **The same shape the carry arm
hit** — *"the 4 staves the carry actually reached are all truth −3"*. Two
independent levers, one biased sub-population.

**The one wrong answer is the brief's own trap, realised.** `staff/3/0/1`
(Oboi) carries **one** marker at 2.86 steps; treble's first flat slot is 4.0,
so an offset of −1.14 lands inside `max_offset = 1.25` and it reads **−1**
against a printed **−3**.

⚠️ **The abstentions are CORRECT, not timid.** `[5.98, 5.5]` and
`[1.36, 0.82]` are not slot patterns in any table; the reader refuses them.

### The `<alter>` column, which the brief could not have asked for

Lane A (`e8cf5b26`, on main 2026-09-21 01:22 — **after** this branch diverged
at 09-20 23:09) made `Q.KEY_SIGNATURE` drive `<alter>` through
`respell_accidental` (`consequences.py:415`, `export.py:761`). A key signature
now changes **what the staff SOUNDS like**, so the brief's Control 2 is much
stronger than it reads.

| | notes altered the print does NOT | left natural that the print alters |
|---|--:|--:|
| the fit | **0** | **113** |
| the NULL | 0 | 0 |

⚠️ **Read that with §3's bias warning**: the NULL's two zeros are a property of
this sub-population being entirely −3, not of the constant being good.

## 4. ⚠️⚠️ THE TWO PUBLISHERS FAIL DIFFERENTLY, AND NEITHER IS FIXED BY THE OTHER'S FIX

`probe_offset.py` — each staff's observed positions minus the slot table for
its own clef:

| | pooled median offset | spread |
|---|--:|--:|
| Litolff | **−0.100** | **5.66** |
| Breitkopf | **−1.256** | **1.02** |

* **Litolff's markers are correctly CENTRED and NOISY.** The median is ~0; the
  spread is 5.66 because individual markers are junk (−3.16, +2.50). The fit
  abstains because they do not form a run. **A tolerance change cannot help.**
* **Breitkopf's markers are TIGHT and systematically DISPLACED.** Five staves
  abstain with internally consistent offsets — `[-1.41,-1.38,-1.26]`,
  `[-1.40,-1.31]`, `[-1.30,-1.26]`, `[-1.32,-1.63]` — spreads of 0.04 to 0.31,
  medians of −1.28 to −1.48, against `max_offset = 1.25`.
  **The cap sits essentially ON this publisher's median bias (−1.256 vs
  1.25), so roughly half its staves fall outside by a fraction of a step.**

**Those are probably correct readings rejected by a hair**, and they are the
real reason Breitkopf answers only 3 of 10.

### ⚠️ The obvious cause was tested and is REFUTED

A flat is not vertically symmetric — bowl low, ascender high — so the box
CENTRE should read high of the slot, on every plate, since it is the same
SMuFL glyph. `probe_centroid.py` recomputes every offset from `y_top + f·h`:

| f | Litolff median | Breitkopf median |
|--:|--:|--:|
| **0.50** (the pipeline's box centre) | **−0.090** | **−1.291** |
| 0.75 | +1.497 | **+0.096** |

**The two publishers want DIFFERENT reference points**, so it is not glyph
geometry — a glyph-shape bias would be identical on both. **A fix that works on
one publisher and not the other is the shape this repo refuses** (*never tune a
threshold on one edition*). The cause is upstream, in the DETECTOR's box for
key accidentals on Breitkopf, and **is not identified here.**

⚠️ **The discriminator is UNAVAILABLE on this corpus**: both documents are
flat-key (C minor), so sharps-vs-flats cannot be compared. **A sharp-key
document would settle it** — if sharps read ~0 and flats ~−1.25 on the same
plate, the glyph explanation returns.

## 5. RECOMMENDATION — do NOT port it, and the reason is not the score

**Leave `adjudicate_key_signature` alone. Do not file `top_y`. Do not move
`max_offset`.**

The port costs a GATHER change (`top_y` onto `Q.CELL_STAFF_SPACE`), a wiring
change, and a **re-gather to price honestly** — `readjudicate` and
`reexport_arm` are structurally blind to a GATHER change. It buys, on the only
document with print truth, **one correct key signature and 13 correctly-altered
notes**, alongside one wrong reading that now moves a staff's sounding pitch.

⚠️ **The blocker is NOT the fit, and that is the transferable part.** The reader
behaves correctly on both plates — it answers where there is a run and refuses
where there is not. What stops it is the INK: noisy on Litolff, systematically
displaced on Breitkopf. **Porting it would move a correct reader onto ink that
is not ready for it.**

**The cheap next measurement, if anyone returns to this:** a sharp-key
document, to settle §4. That is a `git`-free, weights-free question the dossiers
can answer — `data/dossiers/*.json` say which works are in sharp keys.

## 6. WHAT IS NOT ESTABLISHED

* **n = 6 staves for accuracy**, 1 document, 1 publisher, 4 pages, a scan, and
  all 6 share one truth value (−3). **Nothing here is a rate.**
* **No print was consulted by this lane.** The truth is the committed hand-read
  file; no crop was cut and no marker was looked at.
* **Breitkopf is REACH ONLY** — its 3 answers are unscored, and the `missed` /
  `over` columns print `--` there for that reason.
* **The back-solve is a MEASUREMENT DEVICE, not the fix.** It is exact
  (598/598) but it is not what a shipped port would do; that would file `top_y`.
* **The §4 cause is not identified**, only that the obvious one is refuted.
* **No export, no file, no OMR-NED** — the metric is symmetric and would pay
  for writing fewer `<key>` elements either way.
* **No mutation battery was run on this arm.** Its controls are the back-solve
  agreement (598/598, and the wrong spelling scores 154, so it distinguishes)
  and the reach-first DEAD exit; that is weaker than a battery and is stated
  rather than implied.

## 7. RUNNING IT

```bash
B=benchmarks/omr-keysig-marker-fit-2026-09
R=/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records
python3 $B/marker_fit_arm.py $R/beethoven5-p1-p4-ink-identity.record.json \
    --truth benchmarks/omr-keysig-truth-2026-09/truth.json --json $B/out/litolff.json
python3 $B/marker_fit_arm.py $R/brahms1-breitkopf-p0-p3.record.json \
    --json $B/out/brahms1-breitkopf.json          # REACH only: dossier truth cannot score
python3 $B/probe_offset.py ; python3 $B/probe_centroid.py
```

Seconds, no weights. The arm exits **2** and prints `DEAD` if nothing is
measurable, so a zero can never read as a clean result.
