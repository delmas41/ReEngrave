# The `p0p3` arm at `--bar-beats 3.0` — the experiment the empty cell asked for

**Run 2026-09-16 on tree `ab448cc8`, clean working tree, by session
`reengrave-duration-reader-191f40`.** Record
`library/_shared-records/brahms1-breitkopf-p0-p3.record.json`, **md5
`52b98f1cdfee3b39f10e56c592828ea4` verified against the receipt in
`benchmarks/omr-shared-records-2026-09/FINDINGS.md` before a byte was read.**

Instrument: `benchmarks/omr-rest-sizing-2026-09/rest_sizing_arm.py`, one
invocation per arm, `--env OMR_METER_CARRY=0` and `=1`, `--bar-beats 3.0`.
**No re-gather** — the flag is ADJUDICATE-stage, so the arm rebuilds a `Log`
from the record's GATHER rows and re-runs ADJUDICATE + EVALUATE. ⚠️ It is
**blind by construction to a GATHER change**; nothing here is evidence about
one.

⚠️ **Why this tool and not `local_arm.sh`:** `9e175f2d` names it, on the
grounds that the flags are ADJUDICATE-stage and this answers in minutes. That
commit also supplies the reading rule followed here — **read the per-system
table, not the reach header**, which counts abstentions and reads 0 on this
document.

---

## THE RESULT: the carry accepts nothing, and the misread does NOT propagate

```
REACH: 7 systems carry a meter verdict, 7 DECIDED, 0 abstained   [IDENTICAL in both arms]

  system/0/0   decided  voted         6/8    <- CORRECT (Brahms 1 mvt 1 is 6/8)
  system/1/0   decided  voted         9/4    <- THE MISREAD, and it is VOTED
  system/1/1   decided  change_only   4/4
  system/2/0   decided  change_only   4/4
  system/2/1   decided  change_only   4/4
  system/3/0   decided  change_only   4/4
  system/3/1   decided  change_only   4/4
```

**The two arms are BYTE-IDENTICAL.** `p0p3-0.musicxml` and `p0p3-1.musicxml`
both md5 `420136cb25d13ade43ff51ef23f649cf`; the two JSON reports differ in the
`env` line and nowhere else. Both files are committed even though identical —
git stores one blob for identical content, so it costs nothing and lets a
checkout verify the claim with `md5` instead of taking it on trust.

**No system reads `carried`.** Whatever the carry was asked, it accepted
nothing on any of the seven.

### What is MEASURED and what is INFERRED — they are not the same here

**MEASURED:** 0 systems carried; the exported files are byte-identical; 7 of 7
decided with 0 abstaining.

**INFERRED:** that the carry was *asked and refused* rather than *never handed a
candidate*. The inference is `9e175f2d`'s AST argument — `_change_only` is the
THIRD rung of `_carry_meter -> _meter_from_bars -> _change_only`, so a
`change_only` verdict is positive evidence the chain ran and the carry was
asked first. On that reading the carry was offered the `9/4` misread on five
systems and declined five times.

⚠️⚠️ **THIS INSTRUMENT DOES NOT FULLY ESCAPE THE AMBIGUITY `9e175f2d` NAMED
FOR `local_arm.sh`.** It prints a per-system *reason*, but **a refused carry and
an unasked carry both fall through to the identical `change_only`**, and
`support` is `None` on every row, so the weighing itself is not recorded. If
someone needs *asked-and-refused* separated from *never-formed-a-candidate*,
this arm cannot supply it and a probe that dumps the carry's own `Ruling` is
what would.

---

## ⚠️⚠️ THE FIXTURE PR #39 NAMES IS NOT WHAT THE SHARED RECORD PRODUCES NOW

PR #39 reports `system/0/0` reading **`C`** (4.0 quarters) at `voted` on a 6/8
movement, and that pairing — a voted misread beside an abstaining neighbour —
is what defined the empty cell.

**Re-adjudicated from the shared record on `ab448cc8`, `system/0/0` reads
`6/8` and is CORRECT**, and the voted misread has moved to `system/1/0` at
`9/4`. **Nothing abstains at all.**

This is **not** a refutation of PR #39's argument: it read committed FIXTURE
records across five generations, and this is one shared record on today's tree.
But it does mean **the experiment was specified against a fixture the shared
record does not reproduce**, and anyone re-running it should know which of the
two they are holding.

## SO THE EMPTY CELL IS STILL EMPTY

The cell is *a **VOTED** misread propagating across many systems*. On `p0p3` a
voted misread exists (`9/4`) and **does not propagate** — the carry accepts it
nowhere. That is the flag behaving **correctly**, and it is therefore not the
hazard case. **Filling the cell needs a document where the carry ACCEPTS a
misread, and this is not one.**

## ⚠️ AND THE DOCUMENT IS BADLY WRONG INDEPENDENT OF THIS FLAG

At the printed bar length of 3.0 quarters, **1,079 of 1,099 rests in the file
are not it**:

| length | count | |
|--:|--:|---|
| 0.5 | 433 | ✗ |
| 4.0 | 366 | ✗ |
| 1.0 | 260 | ✗ |
| **3.0** | **20** | ✓ |
| 9.0 | 11 | ✗ |
| other | 9 | ✗ |

`notes` 2,513, `notes_not_written_total` **876**, `measure_rests_read` 104,
`empty_bars_padded` 38, `empty_bars_padded_without_meter` 7 — **all identical
in both arms.** The meter carry is not the lever on this page: **nothing
abstains for it to act on.**

## Not established

* **No print was consulted** and no crop was read. The `6/8` is called correct
  on the committed dossier, not on the page.
* **Nothing about a GATHER change** — the instrument is blind to those.
* **Nothing about propagation across a movement**, which is what the empty cell
  is for and what this run does not supply.
* n = 1 document, 1 publisher, 4 pdf pages, 7 systems.

## Reproduce

```bash
python3 benchmarks/omr-rest-sizing-2026-09/rest_sizing_arm.py \
    library/_shared-records/brahms1-breitkopf-p0-p3.record.json \
    --env OMR_METER_CARRY=0 --bar-beats 3.0 \
    --out-xml out/p0p3/p0p3-0.musicxml --json-out out/p0p3/p0p3-0.json
# then again with =1
```
