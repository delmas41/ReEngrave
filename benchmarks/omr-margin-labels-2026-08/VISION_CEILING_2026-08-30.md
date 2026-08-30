# The margin-label lever is closed on the Pastoral — measured 2026-08-30

**`PIPELINE_CLEF_RESULTS.md` names "more labels" as the lever for the last two
clef errors. It is not available: the vision reader reads this page's margin
PERFECTLY, and the page does not print a label below the horns.**

## What was proposed

End-to-end clef accuracy is 50/52. The two remaining errors are the same staff —
the Pastoral viola, alto in both systems, read treble in one and defaulted treble
in the other. `PIPELINE_CLEF_RESULTS.md` closes:

> The lever for it is more labels, not a better join [...] One more label anywhere
> below the strings would anchor the whole section.

The dossier join trusts a slot only when it is pinned by a labelled slot *above
and below*. The strings carry no label, so the join stops at the winds.

## What the vision reader actually recovers

`staff_labels_vision` reads the margin with Claude, one call per system. On
pastoral-p2 (20 staves, 2 systems, 2 API calls, about 2¢):

| source | labels |
|---|---:|
| PDF text layer (free) | 4 |
| **margin read with Claude** | **10** |

All ten at `high` confidence, and all ten correct: Fl., Ob., Cl., Fag., Cor. in
each of the two systems. It more than doubles the free result — the text layer
misses Ob., Fag. and Cor. entirely.

**And every one is a wind or a horn.** The deepest label is staff 4 of 10 in
system 0. Staves 5-9 — the rest of the brass and the whole string section — get
nothing.

## That is not a reading failure. Look at the margin

`evidence/pastoral-p2-system0-margin.png` is the crop the model was given. It
contains exactly five printed labels, against staves 0-4, and clean empty margin
beside staves 5-9. There is nothing there to read.

The reader scored **5 of 5** on what is printed, and correctly reported nothing
for the five staves that carry no label. It is at ceiling.

## The edition never labels its strings

Not a property of this page. Text-layer labels over pages 1-3 of the same score:

| page | staves | labels | what they are |
|---|---:|---:|---|
| 1 | 20 | 4 | Fl, Cl (x2 systems) |
| 2 | 23 | 10 | Fl, Ob, Cl, Fag, Cor |
| 3 | 18 | 8 | Fl, Ob, Cl, Cor, Fag |

Winds and horns, every page, never a string. This is ordinary pocket-score
practice: the strings are identified by position and clef, and an engraver does
not name what every reader can already see.

So "one more label below the strings" is not a thing a better reader can obtain,
on this edition, at any price. The lever named in `PIPELINE_CLEF_RESULTS.md`
should be considered closed, and that file's suggestion is superseded by this
measurement.

## What the evidence points at instead

The anchoring rule wants a labelled slot above *and* below, and below the
strings there will never be one. But the string section is the part of the score
order that needs a label least — `benchmarks/omr-score-order/RESULTS.md` measured
exactly this and recorded it as one of two findings worth carrying forward:

> The strings at the bottom are the same in every tradition; the middle of the
> woodwind is where traditions differ.

So the natural fix is not another label but **treating the foot of the system as
an implicit anchor**: every layout in `score_layouts.py` ends the same way, so
the bottom of an orchestral system pins the string section as firmly as a printed
name would.

That is a change to `dossier.join_parts_to_slots`, not to any reader, and it
carries real risk — the same file records that an unanchored join walks into the
strings and gets three staves wrong. It wants its own measurement against the
52-staff hand-read set before it goes anywhere near `main`.

## Reproducing, and the SDK workaround

`staff_labels_vision` uses `output_config` (structured outputs), which needs
`anthropic >= 0.116`. The **host** SDK is 0.28.0 — the July upgrade only reached
the Docker container — so the module cannot run from the host interpreter. It
does not need the full pipeline, though: the margin path is render → detect
staves → crop, so a venv with `anthropic`, `numpy`, `opencv-python-headless`,
`pymupdf` and `scikit-image` runs it without ultralytics or torch.

```bash
python3 -m venv /tmp/vision-venv
/tmp/vision-venv/bin/pip install "anthropic>=0.116" numpy opencv-python-headless pymupdf scikit-image
/tmp/vision-venv/bin/python -c "..."   # reads ANTHROPIC_API_KEY from backend/.env
```

Upgrading the host SDK would remove the need for this and is the better fix.
