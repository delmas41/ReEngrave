# ROADMAP 2.21 — voice split by stem direction: a convention question for Sean

PATH: STAGED. EVIDENCE + QUESTION lane, no `tools/` changes. Branch
`claude/voice-split-question-2.21`.

## THE QUESTION

**On one staff, when do stems pointing different ways mean TWO voices (two
parts sharing a staff, e.g. Fl. 1/2, or a genuine divisi), and when is it ONE
line whose stems just flip as it crosses the middle line? What on the page
tells you — is it enough that no two of the "two voices'" notes ever sound
at the same time?**

## Why this is being asked now

`tools/omr/voicing.split_events_into_voices` (the rule
`adjudicate_voices` calls, staged and legacy alike) makes two voices in a bar
wherever ANY event has an up stem and ANY other event has a down stem,
regardless of whether they ever occur at the same x position:

> "If at least one event has stem-up AND another has stem-down at a
> different x position, emit TWO voices." (`tools/omr/voicing.py:319`)

ROADMAP 2.19 (`benchmarks/omr-bar-sum-holdout-2026-09/FINDINGS.md` §15c/§15f)
found this rule is load-bearing in 17 of the 156 bars 2.8 holds out on
Breitkopf 317803 p1 (Brahms 1, mvt 1) because a bar's two "voices" are judged
against the meter SEPARATELY, and a bar wrongly split in two rarely sums to
anything a musician would recognise. It could not be fixed without a
convention answer (CLAUDE.md rule 3).

## What was checked before asking

- `git log --all -S "adjudicate_voices"` and `-S "split_events_into_voices"`,
  and `ls benchmarks | grep -i voice`: one prior benchmark,
  `benchmarks/omr-staged-voices-2026-09/FINDINGS.md` (2026-09-10). It
  measures REACH (19 two-voice bars of 853 judged on Litolff, 112 of 595 on
  Brahms) and a real accounting bug in the exporter (a chord straddling two
  streams gets written twice) — it never asks whether the SPLIT ITSELF is
  right. This is the first lane to put that question to Sean.
- All 17 bars named by 2.19 were pulled from the saved p1 record
  (`out/r219/held-brahms-p1-base.json`, produced by 2.19's
  `probe/held_funnel_2_19.py`; no new gather run) and read by their
  streams' pitches in x-order (time order).

## What the 17 bars actually show

**In every one of the 17, the two streams the rule assigned never contain a
real note at the same x.** The "second voice" always starts only after the
"first voice" has finished (or vice versa) — there is no point in any of the
17 bars where a note in stream 1 and a note in stream 2 would need to sound
together. Two are a plain scale (crop #3: Ab3-G3-F3-Eb3-Db3-Ab2, one
continuous descending run cut where the stem flips) and one is a single
repeated bass figure with one held note ahead of it (crop #7: one Db3, then
five slurred repeats of Gb2). None of the 17 look like a genuine second part
sharing the staff (e.g. two simultaneous pitches at one x, which none of
them have).

## Candidate conventions, and how they would score on the 8 crops below

| # | candidate | crops it gets right (of 8, by my eye) |
|---|---|---|
| 1 | **Two voices only if some event in voice 1 and some event in voice 2 share an x** (i.e. they actually sound together) — a bar with no simultaneity is always ONE line | 8 / 8 |
| 2 | **Stem direction alone never splits voices** — a real second voice needs a second, independent piece of evidence (e.g. a printed "a2"/"divisi" text, two stems on one notehead, or a second set of ledger lines) | 8 / 8 (same population on this page — no crop has such a second witness) |
| 3 | **Stem direction DOES split voices, unconditionally** (today's rule) | 0 / 8 — every crop is one line by my reading |
| 4 | **A voice split needs an unbroken run of consistent same-direction stems on EACH side, at least N notes long** (guards against one mis-stemmed note flipping a whole bar) | would still pass all 8 (each side here is 1-5 consistent notes), so it does not distinguish 1 from 2 on this sample — untested contrast case not found on this page |

Candidates 1 and 2 are not the same rule in general (a bar could have
simultaneous notes with only one stem direction read, or non-simultaneous
notes with a printed "a2"), but on this page's 17 bars they agree, because no
bar here has both simultaneity AND a single direction, or a printed divisi
marking with no simultaneity. **Nothing on this page's crops distinguishes
them — a case with real answer NO simultaneity + Sean says "still two
voices" would.**

## Manifest

`benchmarks/omr-voice-split-2026-09/out/print/voice-2026-09-29-manifest.json`
— one entry per crop, `VERDICT_none_yet: null`. My own per-crop reading (not
shown to bias the manifest) is in
`benchmarks/omr-voice-split-2026-09/out/claude_reading.json`.

## The 8 crops

`out/print/voice-2026-09-29-01.png` … `-08.png`, cut from the PDF at 600 dpi
(style: `benchmarks/omr-owner-domain-2026-09/crop_losers_2_6b.py`'s frame
control, all 8 passed). The staff the bar is filed on is a green band with
its lines drawn; the bar's `Q.CELL_BOX` x-span is two red verticals; heads
the record's `Q.VOICES` verdict put in voice 1 are boxed ORANGE, voice 2
PURPLE. Each sheet's own header states, in x (time) order, which notes
landed in which voice and asks the same one-line question.

| # | cell | bar in file | what it reads as |
|---|---|---|---|
| 1 | `cell/1/0/1/5` | 6 | rest, rest, Db5·Db5 (v2), then E4 (v1) — no shared x |
| 2 | `cell/1/0/1/6` | 7 | E4 (v1), B4·B4 (v2), then Db4 (v1) — no shared x |
| 3 | `cell/1/1/3/5` | 13 | one descending scale, Ab3-G3-F3 (v2) then Eb3-Db3-Ab2 (v1) |
| 4 | `cell/1/0/10/2` | 3 | B4 (v2), 3 shared rests, Ab4·Ab4 (v1) — no shared x |
| 5 | `cell/1/0/11/4` | 5 | Ab3-F4 (v2), then Ab3-Ab3-G3-G3 (v1) — a leap, not two lines |
| 6 | `cell/1/1/10/3` | 11 | F3-D4 (v1), C4 (v2), Bb3-Bb3 (v1), C4+C4 (v2) — no shared x |
| 7 | `cell/1/1/11/0` | 8 | Db3 (v2), then five repeats of Gb2 (v1) — no shared x |
| 8 | `cell/1/1/11/3` | 11 | Bb2-Bb2-C3-D3 (v1), then D3-Eb3 (v2) — one ascending bass line |

## Files

- `probe/crop_voice_split_2_21.py`: the crop script (reuses
  `crop_losers_2_6b._frame_ok` and `record_io.load_record`, no `tools/`
  change).
- `out/print/voice-2026-09-29-*.png`, `voice-2026-09-29-manifest.json`.
- `out/claude_reading.json`: my own reading, kept apart from the manifest.
- Source data: `benchmarks/omr-bar-sum-holdout-2026-09/out/r219/held-brahms-p1-base.json`
  (2.19's own dump, unmodified) and the saved record
  `/private/tmp/claude-501/…/scratchpad/brahms-p1.record.json` (2.19's
  fresh gather of Breitkopf 317803 pdf idx 1, `1983a9a2`, `--no-surya`, OCR
  on). Both pre-existed this lane; nothing was re-gathered.

## What this lane did NOT do

No code changed. No default flipped. `python3 -m tools.omr.staged.check`
was not re-run because nothing in `tools/` moved (rule 9's converse: no new
flag, benchmark item, or handoff — the benchmark directory and the
`out/print` crops ARE the roadmap item this lane is filed against, 2.21).
