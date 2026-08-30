# The key-signature "blindness" is a class-ROLE mismatch — 2026-08-29

**The detector is not blind to Beethoven 5 p.15's key signatures. It finds the
flats at conf 0.25 and labels them `accidentalFlat`, and the key-signature path
consumes only `keyFlat` / `keySharp`, so they are discarded before anything
positional runs.**

```bash
python3 benchmarks/omr-keysig-blindspot-2026-08/probe_keysig_inputs.py \
    --pdf <beethoven-5.pdf> --page 15 --dpi 600 --staves 0 1 2
python3 benchmarks/omr-keysig-blindspot-2026-08/probe_accidental_role.py \
    --pdf <beethoven-5.pdf> --page 15 --dpi 600
```

## What was believed

`benchmarks/omr-detection-probe-2026-08/findings.md` closed with this as the one
survivor of the July domain-gap conclusion:

> on Beethoven 5 p.15, key signature flats are not detected at conf 0.25, 0.10
> **or 0.05** — the same three markers at every threshold [...] That is a genuine
> blindness to one class on one kind of print, not a scale artefact.

`docs/next-steps-omr-2026-08-28.md` carried it forward as "the sharpest open
detection question in the project", and `NOTES.md` #4b parked key-signature
inference from the music behind it, on the correct principle that there is no
case for guessing a signature while the printed one sits unread.

## What is actually there

The same probe file's own method note says to check what the model was shown
before concluding it cannot see something. Doing that:

| staff 0 header, conf 0.25 | |
|---|---|
| `keyFlat` | **0** |
| `accidentalFlat` | **3** |

Three flats, on a page in C minor, at the shipping confidence. The header crop
(`crops/s1_header.png`) shows a treble clef followed by three unmistakable flats
— the window is correctly placed and the glyphs are large and clean.

`accidentalFlat` and `keyFlat` are two DSv2 classes for the *same glyph in
different roles*. The role is contextual — a flat is a key signature because of
where it sits relative to the clef and the first note — and a per-cell detector
is the worst-placed component in the pipeline to decide it. The model got the
glyph right and the role wrong.

`_detect_key_sig_from_cell` states the assumption in its own docstring:

> the detector's keySharp / keyFlat markers (**which DSv2 emits distinctly from
> inline accidentals**)

On this print it does not.

## What changes if the same fit is given the accidentals

The positional machinery already exists and is role-agnostic:
`key_signature_geometry.fit_key_signature` fits observed staff positions to the
slot table for (clef, N). It is fed only key markers. Feeding it the accidental
detections instead, with each staff's real clef from a pipeline run:

| | staves |
|---|---:|
| read by the shipping marker path | **1** of 22 |
| newly read from accidentals | **+4** |

Three of the four read **−3** — the movement's concert signature — including
staff 20 under an *alto* clef, which is also a check that the real clef matters
and a forced treble would have got it wrong.

## What this does NOT establish

- **The fourth staff is doubtful.** Staff 19 reads −1 from a *single*
  `accidentalFlat`. One accidental is exactly what an inline accidental looks
  like, and the header cell contains music as well as the header, so some of
  these detections are genuinely inline notes.
- **−3 is not the per-staff ground truth.** The movement is C minor, but written
  signatures differ per transposing part — a B♭ clarinet writes one flat here,
  horns and trumpets often none — so "every staff should read −3" is wrong, and
  a staff reading −1 is not necessarily an error. This page has no per-staff
  ground truth; the dossier knows the written keys but cannot be joined, because
  the work has 18 parts and the page has 22 staves.
- **This is a diagnosis, not a shipped fix.** Routing accidentals into the
  key-signature reader naively would import inline accidentals as signatures.
  The missing constraint is positional: only accidentals left of the first
  notehead can be a signature, which is an x-cut the header window does not
  currently apply.

## Why it matters beyond this page

The parked NOTES.md #4b — infer the key signature from the music — was parked
behind exactly this question, and the answer redirects it. There is no need to
infer a signature statistically from inline-accidental letter frequencies when
the printed signature is being detected correctly and thrown away on a
technicality of class naming. Fix the role, then see what inference is still
needed.

It also generalises: any DSv2 class pair that encodes a *role* rather than a
*shape* has the same failure mode, and the pipeline's own positional readers are
better placed to assign the role than the detector is.

## Method note, the fourth time

This is the fourth confident conclusion in two days that described the
instrument rather than the page — after the `imgsz` flood, the "28 runs with
11-space gaps" band artefact, and the A4 staff-ladder rendering. The pattern is
identical every time: a measurement is taken through one component, and the
component's own assumption is invisible in the number. Here the assumption was
in a docstring, in parentheses.
