# Notehead box cap / the one-head check (ROADMAP 2.222)

The cause lane's findings are in `cause/FINDINGS.md`. This file holds the build lane's results.

## 2.222 one-head check

### m0 (2026-10-29): which written notes `not_one_head` touches. STOPPED here: most of them are real single heads.

**Cause.** 2.220's `not_one_head` comes from the head's TRIMMED ink, and the trim gets it wrong on the merging Litolff plate.
`too_small` is 261 of the 365 Litolff hits. Taking out the bare staff-line pixels takes rows out of a black head that sits on a
line or touches its neighbours, so the head trims to about 0.4-0.6 sp tall. `too_tall` and `too_wide` are the same heads fused
with a neighbour, a stem or a beam. So the verdict measures the trim, not the box.

**Process lesson.** The 2.220 tiles that justified "not_one_head finds junk" (m1, 7 of 12) were drawn from boxes that were
mostly NOT in the exported file (DECISIONS 2026-10-28 correction). On the file, the same verdict is mostly real notes. A
verdict that is going to DECIDE something is sampled from the population it will act on (the exported file) before a lane
builds on it.

**Count. FILE level, by box subject, ON arm of the 2.220 m2b replay.** Source: `agent-abe33f84eed18488d/out/lane-report/2.220-m2/report-b/work/*.on.symbols.json`
plus that run's saved gather slices, which carry `Q.HEAD_INK`. This is the 2.220 m2 subset (Litolff p4, p6 and Brahms p5, p14),
NOT the full frozen sample: no saved gather of the frozen sample carries `Q.HEAD_INK`, because it was only added on 10-28.
Script: `one_head/m0_census.py`.

| plate | written notes | not_one_head | too_small | too_tall | too_wide | foreign | no_head_ink |
|---|---|---|---|---|---|---|---|
| Litolff p4, p6 | 1205 | 365 (30%) | 261 | 50 | 48 | 2 | 4 |
| Brahms p5, p14 | 1256 | 28 (2%) | 12 | 2 | 10 | 4 | 0 |

Detector score, the proposed second witness: the median for `not_one_head` is 0.55 on Litolff, against 0.80 for the rest.
But 126 of the 840 one-head Litolff notes are also under 0.5, and on my crops the low-score `not_one_head` boxes were real heads.
Rescue readers account for 24 of the 365 Litolff hits and 1 of the 28 Brahms hits.

**My crop look (not Sean's).** 24 crops, seed 2222, drawn at random from the `not_one_head` written notes (16 Litolff, 8 Brahms):
`out/print/2.222-m0-look/sheet.png`, with the key in `key.json`.
- Real single heads: 19 of 24.
  - Litolff: 15 of 16.
  - Brahms: tiles 19-23. Two of these, 21 and 23, are halves.
- Not a head: 3.
  - Litolff tile 14 (score 0.32) is a slash or flag piece.
  - Brahms tiles 17 and 24 (scores 0.65 and 0.42) are an eighth flag boxed as a head.
- Several heads in one box: 1, Brahms tile 18 (score 0.45, a cluster with a natural).
- On these crops, low score does not separate the two groups. Real heads scored 0.11, 0.26, 0.28 and 0.36; the flags scored 0.65 and 0.42.

**Rough scale (from my crops, not a measurement):** about 80% of the 393 hits are real notes. Split by plate, that is about 340
of Litolff's 365 and about 20 of Brahms's 28. If those were marked or split, that would be hundreds of real notes on 4 pages, so
I did not build. The m0 stop rule applies.

**What would have to change before a build.** The check needs a head count that does not depend on the line-cut trim, for example:
- counting oval cores, i.e. head-tall columns grouped into head-width runs, on the RAW raster;
- 2.129's stacked-head fit on the box's own column (it already counts k heads in a blob).

It also needs a second witness that is not the detector score, because the score does not separate here. Flags boxed as heads
(Brahms 17, 24) have a different signature: tall, thin, attached to the stem end. That is closer to 2.214 and 2.210 territory
than to a size test.

**Running unattended (no one waits on it):** a GATHER of the full frozen sample on main's defaults, so `Q.HEAD_INK` is filed.
It runs one plate at a time with the detector cache. Script: `out/lane-report/2.222-gather/run.sh`; output goes to
`out/lane-report/2.222-gather/{litolff,brahms}.record.json`, with `done` written when it finishes. It exists so the next step
can repeat this census on all 16 pages by replaying the saved gather, without gathering again.
