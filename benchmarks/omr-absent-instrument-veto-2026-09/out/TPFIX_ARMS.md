# `tpfix-*` — the A/B behind the `Tp.` → Timpani fix (2026-09-06)

Four committed extracts, two windows × two arms, for `5d6e76a8`
(`contextual._resolve_ambiguous_labels`: the positional prior may not move a
staff onto an instrument a different alias on the same system already names).

⚠️ **An extract with no arm definition is a trap**, so both arms are stated
exactly. Everything here was produced on one tree; the ONLY difference between
arms is the guard.

| file | window | arm |
|---|---|---|
| `tpfix-control-p23p44.extract.json` | `--pages 23,44` | guard REMOVED |
| `tpfix-fix-p23p44.extract.json`     | `--pages 23,44` | guard present |
| `tpfix-control-p0004.extract.json`  | `--pages 0-4`   | guard REMOVED |
| `tpfix-fix-p0004.extract.json`      | `--pages 0-4`   | guard present |

**Arm definition.** The control arm is the fixed tree with exactly this hunk
deleted from `_resolve_ambiguous_labels` — nothing else, no flag, no revert:

```python
lexicon = label.instrument.name if label.instrument else None
if chosen.name != lexicon:
    aliases = claimed.get(system_index, {}).get(chosen.name, set())
    if aliases - {label.alias or ""}:
        continue
```

**Reproduce** (~90 s and ~4 min respectively; the second needs the hunk removed):

```bash
export OMR_SURYA_KEEP_ALIVE=1 OMR_ABSENT_INSTRUMENT_VETO=report
python3 -u -m tools.omr.transcribe \
  library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf \
  --pages 23,44 --no-direction-text --out /tmp/arm.json
python3 benchmarks/omr-absent-instrument-veto-2026-09/probe/extract.py /tmp/arm.json /tmp/arm.extract.json
python3 benchmarks/omr-absent-instrument-veto-2026-09/probe/score_full_systems.py beet5 /tmp/arm.extract.json
```

## What they show

**`--pages 23,44` — the bug fires.** Scored against the hand-read lineup:
control **24/29** (wrong 5, size-17 system 16/17), fix **26/29** (wrong 3,
size-17 system **17/17 exact**). `Timpani -> Trumpet` ×2 eliminated, no other
confusion moved. Exactly **3 staff records differ**, all slot 8, all
`Trumpet(score_order_ambiguity)` → `Timpani(label)`.

**`--pages 0-4` — the bug does not exist there.** The two arms are
**IDENTICAL**: `pages` and `contextual` both hash to the same value
(`64863bb701c7bf54`, `8a1d3e74dfdae84c`), and the only differing top-level key is
`source`, which records the input path. ⚠️ **This is the production window** —
`backend/modules/local_omr.py:233` is `pages = list(range(min(n_pages,
max_pages)))` with `OMR_MAX_PAGES` defaulting to 5, so the web app always
transcribes pages 0-4 and this fix is inert on that path. Pages 0-4 are
movements 1-3: an 11-slot reference, no trombones, the timpani at slot 6 where
the canonical layout also puts it, so nothing overturns.

**And the whole work does not show it either** — `whole-report2.extract.json`
(committed, 88 pages) already has slot 8 = Timpani and
`ambiguous_labels_resolved = 1`.

## ⚠️ Three cells, not two

The bug needs a window that **spans the movement boundary** — holding both a
reduced system and the finale's full lineup, so the timpani has a trombone run
to be displaced past — and thin enough that the layout fit has little evidence.
So **narrow-at-the-front** (pages 0-4, what production does) and
**narrow-anywhere** (`--pages 23,44`, what a repro does) are DIFFERENT regimes,
and a whole work is a third. Scored only on the first and third, this fix
measures **exactly zero, twice**.

Score identity work on all three. A real fix reading as zero in both obvious
cells is the failure mode this table exists to prevent.
