# ROADMAP 2.58 -- did the GATHER reorder help or hurt? (2026-10-07)

STAGED, GATHER+ADJUDICATE only (`--through adjudicate`, `--weights auto`,
`OMR_DIRECTION_TEXT_SCAN_GATE=1 OMR_SURYA_KEEP_ALIVE=0`). BASE = `286289dd^`
(3493d3ef), ARM = `286289dd`, each in its own detached worktree, one tree
otherwise identical. `run.sh` runs it, `ab_compare.py` counts, `ab_sheet.py`
cuts the sheet (`out/print/ab_2.58_gather_order.png`). Raw output: `out/`.

**What the reorder changes.** `gather_empty_bar_rest_search` now runs right
after detection, before `gather_lowconf_rescue`, which reads its row off the
real log instead of re-running the search on a scratch Log. The one record
change it can make: a bar the rescue filled keeps a `found=False`
`empty_bar_rest_search` row (it used to be skipped), and
`adjudicate_empty_bar_whole_rest` abstains on it (`not_found_by_search`). It
can touch nothing else (notes, owners, durations, meter, clef, key read none
of this).

**Pages.** Litolff 1-3 (together), 6, 12; Brahms 0-1 (together), 7.

## Result

| quantity | change beyond noise |
|---|---|
| rest-search rows, found=False | +15 (Litolff 1-3), +4 (Litolff 6); 0 on Litolff 12, Brahms 0-1, Brahms 7 |
| `empty_bar_whole_rest` abstained (not_found_by_search) | the same +19 |
| glyph boxes gathered (2,639 / 5,342 / 3,157 / 5,717 / 2,875) | 0 |
| rests found (found=True rows), whole-rest decided | 0 |
| notehead owner, duration, staff position, event, voices, meter, clef | 0 changed (`readout diff`: 19 differences, all the line above) |

Noise: A/A (BASE twice, Litolff p6) = 0 differences. Brahms p7 A/A: BASE twice
= 0; ARM twice differs in ONE decision (staff/7/0/5 key signature, decided
`-1` fitted_no_markers vs abstained no_evidence, and 2 `keysig_template_fit`
rows). The first ARM run had it, the second ARM run did not and equals BASE
exactly, so it is run-to-run noise in the header key reader (which the reorder
does not touch), not the reorder. The ARM record in `ab_compare` output for
`bra7` is the noisy first run; the key line there is that noise.

## Wall time (s, gather+adjudicate, per run)

BASE / ARM: Litolff p6 275 (and 291 second BASE) / 254; p12 479 / 737; p1-3 568 / 591;
Brahms p7 314 / 251 (rerun 701 / 503); p0-1 1059 / 1240. The machine was
shared with other sessions' gathers; the same code (BASE p7) took 314 and 701,
so these are load, not an effect of the commit. The expected saving (the rescue
no longer re-runs the search on a throwaway Log) is not visible above that noise.

## Sheet

12 of the 19 changed bars (seeded round-robin over runs), staff named from
the record's own `instrument` verdict, rescued head(s) boxed orange. Staff
lines are drawn LOCALLY (fitted at two stretches of the bar, 1 px) and
re-measured at a third stretch: 1.2 px or less except two bottom lines
(2.2, 3.1 px: a head/ledger overlaps that stretch); the control (same line
drawn 4 px off) reads 2.8-5.1 px, so it can fail (`out/sheet_checks.txt`).

## Verdict

NEUTRAL, with one small real gain: no note, rest, owner, duration or meter
decision moved on 5 pages / 2 plates; the only change is the 19 rescued bars
now carry an honest "searched for a whole rest, found none" row where they
carried none. Nothing for Sean to adjudicate on the print; the sheet is
for confirming those bars hold real heads (they do on all 12 tiles seen).
Not measured: a whole movement (a GATHER change is only priced by full re-gather).
