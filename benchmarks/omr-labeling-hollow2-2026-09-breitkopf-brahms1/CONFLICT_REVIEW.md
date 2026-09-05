# The five CONFLICTs, reviewed (2026-09-03)

Every conflict box was cropped at high zoom from the cell images, checked
against the reference's own XML (`score.xml` out of `reference.mxl`), and
against the verdict files. **The tremolo hypothesis the handoff recorded is
refuted for all five** — the encoding is not tremolo-blind (it carries 168
`<tremolo type="single">` elements elsewhere in this movement); these bars
simply hold none. Two unrelated causes account for everything. Verdicts stay
Sean's to click; each entry below says what the print shows and what, if
anything, is left to do.

## Cause 1 — the reference's TIE-SPLITS (3 of 5; a pre-fill collapse gap)

**`brahms1-p2-sys0-s2-m2`** (m10, Bb Clarinet 1/2) — both conflicts, one box.
The page prints ONE hollow half with an augmentation dot, on-line (notehead
centre y≈362 against measured line y≈367, no stroke anywhere on the stem at
4× zoom). The reference encodes P5 m10 as **Bb4 tied eighth + quarter +
dotted-quarter** — `<tie>` on every fragment, no `<tremolo>` — a plain
3-beat note split at beat boundaries. The aligner double-counted the one
printed head against two of the fragments, hence two conflicts for one glyph.
→ **Sean's existing `H0: noteheadHalfOnLine` is correct as printed; nothing
to change.**

**`brahms1-p2-sys0-s3-m6`** (m14, Bassoon 1/2) — same shape: P7's **E4 tied
eighth + dotted-quarter + quarter**, one printed hollow head (scan-degraded —
the counter is the thin-sliver closed form this project has already
documented), on-line by ledger calibration. Both of the cell's "missing"
hints point at blank paper — they are the other tie fragments, which never
had their own heads. → **Sean's existing `noteheadHalfOnLine` is correct;
ignore the two missing-note hints.**

**The gap this names:** a within-measure tie chain is ONE printed note
whenever the engraver had a single value for it, and the pre-fill already
owns the right mechanism — tremolo/tremolando are *reconciled by the
reading*. Tie chains should reconcile the same way: collapse to one head of
the summed value where the reading placed one head at that position, leave
as written where it placed several (a 2.5-beat tie has no single glyph and
IS printed as two tied heads — `s15-m7` below contains exactly one). That
change turns all three of these conflicts into confirmations, and the
summed values (dotted halves) make the hollow reading *agree* with the
reference instead of fighting its fragments.

## Cause 2 — accidental glyphs misdetected as hollow heads (2 of 5)

**`brahms1-p2-sys1-s26-m0`** (m15, Contrabass): the conflict box holds **a
flat sign's loop**, not a notehead, sitting before a beamed run of six black
Gb2 eighths. **`brahms1-p4-sys1-s15-m7`** (m55, Oboe 1/2): the box holds **a
natural sign** (the `<accidental>natural</accidental>` on the tied B4 later
in the bar); the "Cb5 quarter" the conflict names is the tie-in note, whose
2.5-beat tied value legally prints as two tied heads, so no hollow
abbreviation was ever plausible there. → **Sean's empty verdicts on both
cells are already right; nothing to click.** These two are the detector
inventing a head from round accidental ink — the same family as the three
phantom TPs in `s3-m4` that the admission probe isolates
(`benchmarks/omr-prefill-admission-2026-09/`): a false detection that
happens to sit where the alignment can claim it. The conflict route caught
these two only because the invented head was hollow; a black one would have
sailed through as TP, which is what cell-level parity consistency is for.

## The optional tremolo1–5 pass

**No support from this sample: zero tremolo strokes in the four cells**, and
none of the implicated reference measures carries `<tremolo>`. The pass
stays parked until a batch actually shows strokes the detector mishandles.

## batch_config state on Sean's Mac (diagnosed, deliberately not touched)

The ACTIVE `batch_config.json` is an uncommitted working-tree edit holding a
**stale 9-class completion palette** — the pre-`fd28a76` snapshot, missing
the slur / tie / hairpin classes that commit added because a completion pass
without them trains real ink as background. `batch_config.hollow.json` is a
byte-identical backup of the committed hollow config. So the restore choice
depends on the next pass: **continuing completion work needs
`cp batch_config.completion.json batch_config.json` (the canonical 14-class
palette), not the hollow restore** the handoff suggested; returning to
hollow sweeps restores `batch_config.hollow.json`. Either way the server
must be restarted to pick it up — the completion cells got stamped
`hollow noteheads` precisely because it was not.
