# Handoff — three clef jobs, in this order

> Written at the end of the 2026-08-31 session. Everything below is measured, and
> the numbers are reproducible from the two harnesses named in each section. Do
> them in order: (1) is a decision that is ready, (2) has a lead that (3) is the
> check on.

## Run both harnesses. Always both.

```bash
# from the repo root
python3 benchmarks/omr-clef-geometry/probe_clef_rejection.py \
    --pdf ~/Downloads/Nottebohm-Beethovens-Studien-1873.pdf          # coverage
python3 benchmarks/omr-clef-geometry/check_clef_precision.py \
    --nottebohm ~/Downloads/Nottebohm-Beethovens-Studien-1873.pdf    # precision
```

The precision harness needs its LilyPond corpora built once (gitignored):
`cd benchmarks/omr-clef-geometry && lilypond reference-clefs.ly
piano-false-positives.ly` — the "fatal error" it ends on is harmless, the PDFs
appear.

**Current baseline, shipped config:**

```
69 of 206 located (33.5%)
reference 5/5 exact | coverage 7/9 | orchestral misses 6 | sweep misses 10
                                                        | FALSE POSITIVES 6
```

Never judge a change on one harness. Every promising change in this area has
looked like a large gain on one and lost on the other.

---

## 1. Turn the clustering on — a decision that is ready

`ClefLocatorConfig.cluster_y_gap_spaces` is `None` and has been held back for two
sessions on the strength of "14 right and 5 wrong", which was measured before
there was a corpus that could see either number. Set it to **1.0**.

| arm | located | orch misses | sweep misses | FALSE POS |
|---|---:|---:|---:|---:|
| shipped | 69 | 6 | 10 | **6** |
| **clustering ON** | **77** | **5** | **7** | **7** |

Eight more located clefs and four fewer misses, for **one** more false positive.
The false-positive RATE is flat (6/69 against 7/77), which is the test this layer
actually applies — "coverage bought at a worse precision than the layer already
has" is the trade it refuses, and this is not that.

The one extra false positive is **p54 s8**, a bass clef whose dots sit outside the
frame the veto is given; it is item 2's first case, so 1 and 2 compose.

Also run, because clustering changes what the whole header layer sees:
`pytest tools/omr/tests -q` (1084), `benchmarks/omr-score-order/eval_score_order.py`
(11/12, 5/10, 23/23), and `eval_pipeline_clefs.py --contextual --dossier --assist
vision` (69/69, base-3 52/52 — costs about a cent).

## 2. The six remaining false positives — and a lead

With the shipped config, six of the sweep corpus's 24 non-C clefs survive every
gate:

| | truth | read as | symmetry |
|---|---|---|---:|
| p2 s3 | BASS | tenor | 0.795 |
| p6 s17 | BASS | tenor | 0.729 |
| p14 s6 | BASS | alto | 0.750 |
| p30 s13 | BASS | tenor | 0.720 |
| p36 s5 | BASS | tenor | 0.702 |
| p60 s0 | treble | alto | 0.791 |

**Five of six are bass clefs, and four read as TENOR — the same structural bug
the mezzosoprano fix just closed.** A bass clef's F line and a tenor clef's C line
are both the fourth line from the bottom, so a bass clef that survives the
symmetry gate names tenor for the same reason a G clef named mezzosoprano.

**The lead**, measured on this corpus:

| answer | real C clefs | the misreads | overlap? |
|---|---|---|---|
| **tenor** | 9, symmetry **0.809 – 0.959** | 5, symmetry **0.702 – 0.795** | **none** |
| alto | 55, symmetry 0.714 – 0.932 | 13, symmetry 0.729 – 0.907 | heavy |

A tenor-specific symmetry floor — the same shape as `min_symmetry_mezzosoprano`
— removes all five tenor misreads at **zero cost on this corpus**. And it must
NOT be generalised to alto, where the two populations sit on top of each other.

**The trap, and it is the reason for item 3.** The tenor gap is **0.795 to
0.809 — fourteen thousandths**, on 9 real clefs and 5 misreads, all from ONE
edition. The mezzosoprano gap was 0.815 to 0.981 and rested on a clef that
appears zero times in twenty pages of Nottebohm; this one does not have that
margin or that rarity. **Do not ship a tenor floor on this evidence alone.**
Build item 3 first and check the gap survives a second printer's ink.

The sixth (p60 s0, a treble read as alto) is not covered by any of this.

## 3. A second edition, which is the check on item 2

Everything above is one scanned Beethoven 5 (IMSLP 575951). A threshold tuned on
one edition's ink is the failure mode this whole area keeps repeating.

`ground-truth-mahler5-p72.json` already exists here and was made for exactly this
reason — Edition Peters, Mahler 5, "deliberately a DIFFERENT edition and publisher
… because edition overfit is the clef specialist's likeliest failure". The score
is at `~/Documents/Gradus-Assets/Scores/Scores For Gradus/PDF Scores/Mahler_5_.pdf`.

Build the sweep corpus for it the same way `beethoven5-clef-sweep.json` was built:

1. run the locator with clustering ON over a page range, collecting every staff it
   LOCATES a C clef on;
2. render each header crop — anchor on `staff.x_start`, not the header window's
   `x0`, or on many pages you will get the margin label instead of the clef;
3. read the glyph by eye, in montages of about a dozen;
4. record `{page, staff, c_clef, note}`, with the real C clefs included as the
   counterweight — a corpus of only failures scores a veto that fires on
   everything as perfect;
5. exclude anything you cannot read confidently rather than guessing at it.

Then re-check item 2's tenor gap on it. If the gap holds, ship the floor. If it
closes, the answer is not a threshold and the write-up is worth more than the
change would have been.

## What is already settled, so it is not re-litigated

* **The F-clef veto's blindness is fixed** (it was handed the `header_frac` strip
  and searched only inside the candidate box, so an F clef's dots — which are to
  the RIGHT of its body — were never in view). The structural fix is landed and
  measured neutral.
* **Loosening the dot thresholds is refused with numbers on both sides**: it buys
  3 fewer false positives and costs 27 genuine C clefs.
* **`FALSE POSITIVES 0` on the four older corpora meant nothing** for this layer —
  none of them contained a bass clef the locator was liable to misread. The sweep
  corpus is what makes the number real.

Full write-ups: `RESULTS.md`, last three sections.
