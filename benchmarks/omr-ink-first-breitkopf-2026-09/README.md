# The ink-first test on the SHATTERING plate

Lane D, 2026-09-22. Closes the named blocking artefact of
`docs/breakthrough-2026-09-18-the-unit-of-enquiry.md` §7 and runs its
falsification test where that section says the test belongs.

⚠️ **THE SYNTHESIS IS IN THE COMMIT MESSAGES, NOT IN A FINDINGS FILE.** The
harness refused one — as it did for `omr-ink-first-2026-09`, which records the
same thing in its own provenance note. Read, in order:

| commit | what it holds |
|---|---|
| `4f420417` | **the result**: §7's falsifier FIRES on both plates, the premise check, the residue split, all controls |
| `b040808c` | the separating VALUES in the one bucket geometry did not choose (margin 0.02 spaces) |
| `b5210bf4` | the tree check: the ink layer this gather ran is byte-identical to `origin/main` |

## What is here

| | |
|---|---|
| `probe_ink_first_breitkopf.py` | the test. `--plate`, `--population`, `--attribution`, and two fault-reproducing positive controls (`--wrong-join`, `--drop-junk`) |
| `cross_gather_control.py` | does this gather reproduce the committed 2026-09-18 one? |
| `clean_bucket_values.py` | the values, not the AUC, inside the one census bucket not chosen by geometry |
| `extract_ink_join.py` | projects a full staged record onto the four quantities this test reads |
| `mutate.py` | 11 arms, 11 RED, 0 survivors |
| `out/RECEIPT.json` | the artefact's md5, how it was made, and its controls |

## The artefact

`out/brahms1-breitkopf-p0-p3.gather.json` — md5 `213bcb92…`, 15,212 `Q.INK`
rows over 818 cells, pdf pages 0-3 of Brahms 1 / Breitkopf. Copy at
`library/_shared-records/brahms1-breitkopf-p0-p3-ink.gather.json`.
⚠️ GATHER-ONLY: it carries no verdicts.

```bash
python3 benchmarks/omr-ink-first-breitkopf-2026-09/probe_ink_first_breitkopf.py \
    --record benchmarks/omr-ink-first-breitkopf-2026-09/out/brahms1-breitkopf-p0-p3.gather.json
```
