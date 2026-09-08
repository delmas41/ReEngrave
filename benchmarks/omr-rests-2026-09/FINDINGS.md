# Step 3 — rests: the first look, and 80% of it is one mechanism

Step 3 as the handoff sets it: *"476 rests carry a wrong duration against 235
notes — 55% of the duration mass, and every duration analysis in this repo is
note-level and therefore blind to the larger half. Nobody has looked."*

Instrument: `tools/omr/symbol_ledger`, over the 11 committed scan-gate
pred/truth MusicXML pairs already on disk (no re-transcription).

---

## 1. ⚠️ STEP 3 IS BLOCKED BY STEP 4, AND THE NUMBER SAYS SO

Of **4,239 rest rows, only 416 are assessable — 9.8%** — and they come from
**2 of 11 rows, both Dvořák**. On the other nine the part join fails
(`part_join: unresolved`), so every symbol is `uncorresponded` with reason
`part_unresolved` and nothing can be compared to anything.

That is Step 4's bucket (`entire staff` / no part correspondence) sitting
**upstream** of Step 3, exactly as the handoff predicts: *"8 of 20 rows have NO
part correspondence — 51% of symbols. Larger than everything about notes, and
upstream of all of it."*

⚠️ **So every figure below is TWO DVOŘÁK PAGES.** It is not a corpus result and
must not be quoted as one.

## 2. The handoff's ratio holds on this slice

On the assessable rows, attribute errors split **rests 174 / notes 123**. Rests
are the larger half here too — a different slice from the one that produced the
476/235 figure, agreeing in direction.

## 3. ⚠️ 139 of 173 rest duration errors are ONE mechanism

|  ours (type, ql) | truth (type, ql) | n |
|---|---|--:|
| **`whole`, 4.0** | **`None`, 2.0** | **139** |
| `32nd`, 0.125 | `16th`, 0.4375 | 8 |
| `half`, 3.0 | `None`, 2.0 | 5 |
| everything else | | ≤3 each |

**We emit a whole-measure rest as a literal whole note — 4.0 quarter-lengths —
regardless of the meter.** Dvořák 9 mvt 1 is in **4/8**, so a bar holds 2.0;
we write 4.0 and the bar comes out twice over-full.

⚠️ **THE SIZING CODE IS CORRECT AND IS SIMPLY NOT FED.**
`export._measure_rest_beats` computes `num * 4.0 / den` — 4/8 → 2.0 — and
`_dotted_duration_for_beats(2.0)` returns `('half', 0)`. The fault is the
argument: both call sites resolve `m_time = measure.get("time_signature") or
<staff/part fallback>`, and when neither carries a meter the value is `None`,
where `_measure_rest_beats` falls back to **4.0 (a whole rest)** by documented
design. That fallback is right for an unknown meter and wrong here, because
the meter is NOT unknown.

⚠️⚠️ **THE FILE CONTRADICTS ITSELF, WITHIN ONE PART.** Measured on every part
of the Dvořák p5 export:

    part P1: divisions=8  time=4/8  bar_ql=2.0  rests=7  whole-rests-too-long=5
    part P2: divisions=8  time=4/8  bar_ql=2.0  rests=9  whole-rests-too-long=5
    part P3: divisions=8  time=4/8  bar_ql=2.0  rests=9  whole-rests-too-long=6

The exporter writes `<time>4/8</time>` into the part's own `<attributes>` and
then writes a 4.0-quarter rest into that part's 2.0-quarter bars. **It had the
meter in hand and did not use it** — the same shape as this project's recurring
detected-then-dropped family, one level down: *known-then-not-consulted*.

Secondary, same rows: truth marks these `<rest measure="yes"/>` and we emit a
plain `<rest/>`.

## 4. ⚠️ I NEARLY REPORTED THIS EXACTLY INVERTED

The ledger emits a row per symbol **on both sides**, and all 174 of these rows
are the **`truth`** side — so `attrs` is TRUTH and `partner_attrs` is OURS. The
first cut of this analysis read `attrs` as ours and produced the table
backwards, concluding that *we* omitted `<type>` and *truth* said `whole`. The
raw XML is what caught it: our rest carries `<type>whole</type>` and truth's
carries none.

**Check `side` before reading `attrs` on any ledger row.** Nothing in the
column names says which way round they are.

## 5. What to do next, and how to price it

Feed the meter to the empty-measure path — the sizing function already does the
arithmetic. ⚠️ **Do not ship it unmeasured**, and note the pricing problem
before starting: the scan gate can assess only 9.8% of its own rest rows, so it
is a poor instrument for this. The engraved benchmark pairs 1:1 by construction
and can see all of them; that is where the A/B belongs, with the scan gate as a
secondary check.

⚠️ And the deeper question this raises is Step 4's, not Step 3's: **why does the
staff carry no `time_signature` on these pages** when the page-level reader
found 4/8 and wrote it into `<attributes>`?

## 6. Reproduce

```bash
M=benchmarks/omr-scan-e2e-2026-09/fixtures
for t in "$M"/*.truth.musicxml; do b=$(basename "$t" .truth.musicxml)
  python3 -m tools.omr.symbol_ledger \
      "$M/$b.restamp-composed.omr.musicxml" "$t" --json "led/$b.json"; done
python3 benchmarks/omr-rests-2026-09/probe_rest_durations.py led/
```
