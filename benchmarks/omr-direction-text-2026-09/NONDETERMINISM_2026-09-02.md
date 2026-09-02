# The same scan page, twice, gives two different scores

Found while measuring something else. `docs/next-steps-omr-2026-09-01.md` §4b
leaves the `--direction-text` default open and names the missing measurement —
the flag, on a scan, end to end — so `eval_flag_on_scan.py` runs each page twice
and diffs the two exports with every `<direction>` block removed. Anything left
would mean the flag is not the additive pass it is documented to be.

Page 84 of the Litolff Beethoven 5 came back with **485 lines left over**: part
names shifted across seven staves, one clef, and note content.

**It is not the flag.** It is not the flag in a way that matters more than the
flag does.

## The controls, in the order they were run

| | what varied | result |
|---|---|--:|
| flag ON vs OFF | the reader | 485 lines |
| **OFF vs OFF**, resident Surya | nothing | **485 lines** |
| **OFF vs OFF**, fresh Surya server per run | nothing | **497 lines** |
| **`--no-contextual` twice** | nothing, no OCR anywhere | **identical** |

The first row is what the harness reported and what it would have been
reasonable to publish. The second kills it: the same 485 lines appear between
two runs that both have the reader OFF, so the difference was never the flag's.

The third rules out the mechanism worth suspecting next. Surya runs as a
long-lived server here (`OMR_SURYA_KEEP_ALIVE`), and a server that carries state
across requests would explain a page reading differently depending on what was
asked before it. Spawning a fresh server per run does not fix it.

The fourth locates it. With `--no-contextual` there is no OCR in the pipeline at
all, and two runs agree **exactly** — 1302 detections, 640 noteheads, 238
measures, and the same hash over every staff's geometry. Everything beneath the
label readers is reproducible.

## So it is the label readers, and they are on by default

`contextual._labels_for_page` is the only thing left between the two, and the
tier counts move between runs of the same input:

| run | text layer | surya | tesseract |
|---|--:|--:|--:|
| resident, 1 | 0 | **10** | 2 |
| resident, 2 | 0 | **1** | 8 |
| fresh, 1 | **1** | 0 | 8 |
| fresh, 2 | 0 | **10** | 2 |

Surya resolves ten labels or one. When it goes quiet Tesseract fills the gap,
reads the same margins differently, and the part assignment slides by a staff:
`Flute → Oboe`, `Oboe → Clarinet`, `Timpani → Trumpet`, `Harp → Violin`. A clef
and a run of notes follow it out.

**This is the default configuration.** `surya_fallback=True`, and none of it is
behind `--direction-text`. A user transcribing this page twice gets two
different scores.

⚠️ ~~**The text-layer row is the one to explain before acting.**~~ **CLOSED, and
it was a wrong lead.** `label_tiers` is CONTRIBUTION, not production: line 408
sets `tiers[0] = 0` when Surya's read wins, exactly as line 525 does for the
vision rung. So a stable text layer reads 1 when Surya is silent and 0 when
Surya overrules it, with its own output fixed throughout. Nothing to hunt for in
the PDF.

**What to follow instead.** The tight Surya test has since been run — 20 crops,
same order, shuffled, and in a second process; 0 of 20 differ — so the reader is
a fixed function of its input, and the layer beneath is byte-exact by row four.
What is left is whether Surya is CALLED SUCCESSFULLY, and `contextual.py:386`
swallows every exception into a `logger.warning` with nothing in the result.
An intermittent failure there is indistinguishable from the reader finding
nothing. That is the `_optional_pass_failure` shape, at a call site that does
not use it. Hypothesis, not a finding — the warning appears in no log kept from
these runs.

## What this does NOT say

**It does not say Surya is non-deterministic**, and the evidence here cannot.
Every count above is downstream of the reader, so a rung that abstains for some
other reason produces the same table. `SURYA_BAKEOFF_2026-08-31.md` measured 45
replays and found a fixed function of its input — with the caveat, recorded at
the time, that replaying one image cannot see a shared prompt cache. Settling it
needs the tight test neither of those ran: **the same crops, twice, in one
process, compared directly.** Until that is run, "the readers disagree between
runs" is what is measured and "Surya samples" is a hypothesis.

**It does not say the page is unusual.** One page of one edition was tested this
way because one page failed a different check. How much of the corpus is
affected is unmeasured, and every end-to-end scan number this project holds was
taken from a single run.

## What it cost the measurement it interrupted

The flag is exonerated on page 84 and the four other scan pages were clean, so
the additivity finding stands where the pipeline is stable. But a harness that
diffs two runs of a pipeline that does not reproduce is measuring the pipeline,
not the change — so `eval_flag_on_scan.py` now runs the OFF/OFF control itself
whenever a page differs, and reports `FLAG` or `UNSTABLE` rather than a line
count. It handed me the wrong conclusion for about ten minutes, and it was the
control and not the harness that took it back.
