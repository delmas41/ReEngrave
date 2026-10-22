# Stem attribution — a stroke belongs to the head at ONE OF ITS ENDS

The ranked first item of `docs/handoff-2026-09-18-three-lanes-and-the-print.md`
§5, taken as far as geometry can take it.

**Read [FINDINGS.md](FINDINGS.md).** In one line: the convention is MEASURED
and holds (bimodal, 72% / 77% of pairs within half a notehead height of an
end), the fault is real (**148 and 228 heads** take a direction from a stroke
that does not end at them), the true owner is on the record in **90% / 94%** of
those — and **no constant-free rule separates a chord from a passing stroke**,
because the gap between consecutive claimants has no empty interval on either
plate. So the question goes to the print.

| file | what it is |
|---|---|
| `probe_where_along_the_stem.py` | the reach and the convention check, off the committed records |
| `preregister.py` | the two strata, seeded and fixed BEFORE any strip existed |
| `crop_strips.py` | full-width staff strips, ticks in the margin, page-wide frame control |
| `mutate.py` | 17 arms over the three instruments |
| `out/{litolff,breitkopf}.json` | every (head, stroke) pair with both frames |
| `out/sample-*.json` | the pre-registered draw |
| `out/strips-*/`, `out/manifest-*.json` | 79 strips; ids opaque, strata held apart so the pass can be blind |

**Nothing under `tools/` changes.** No weights, no re-gather, no detector.

## For the person with the plate

One question per strip: **is the vertical stroke under the marked head THIS
head's stem, or does it belong to another note?** Answer
`this_heads_stem` / `another_notes_stem` / `cannot_tell` / `not_a_notehead`,
by tile id, into `ADJUDICATION-<label>.json`. The two red ticks in the top and
bottom margins give the head's x; nothing is drawn on the music.
