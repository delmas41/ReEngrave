# Key-signature reading — measured results

Everything here is reproducible from this directory:

```bash
python3 benchmarks/omr-key-signature/eval_key_signatures.py
```

Ground truth is `ground_truth.json` — the printed key signature of every staff
on three pages, read off the page by eye. That file is the irreplaceable part;
the rest regenerates.

The layer being measured is described in `tools/omr/README.md` → "Reading a
staff's header". Briefly: a key signature is N copies of one glyph at staff
positions fixed by the clef, so it is read by fitting POSITIONS to the slot
table for (clef, N) rather than by counting detections, and the readings are
then reconciled across the whole page.

---

## The headline: three layers, three different failures

Bach WTC p.17 — E major, four sharps on every staff of five systems, a clean
modern engraving where the detector fires on its own.

| | correct |
|---|---|
| counting the detector's markers (what the pipeline used to do) | 6 / 10 |
| fitting their positions to the slot table | 7 / 10 |
| …then reconciling across the page | **10 / 10** |

Each step fixes a different thing, which is why all three are needed:

- **The fit** rescued one staff whose five markers were the four real sharps —
  landing exactly on the bass slots [2, 5, 1, 4] — plus one stray above the
  staff. Counting reads five sharps; the fit sets the stray aside and reads
  four.
- **The vote** rescued three staves that had lost their FIRST sharp to the
  detector and read +1, +1 and +2. Nothing local can recover that: the fit
  requires the first slot to be observed, and lifting that rule is what once let
  two glyphs report five sharps. Only the page can say, and it does — the same
  part reads four sharps in the other systems.

## Degraded prints: the vote's real job is rejection

Beethoven 5 p.2 and Beethoven 6 p.2 — 19th-century orchestral prints where the
detector emits **zero** key-signature markers, so the CV locator is doing the
reading. 42 staves across both systems of both pages, with the true clef
supplied (see "What component mode does not measure" below).

| | correct | wrong | missed | correct abstentions |
|---|---|---|---|---|
| locator, per-staff | 10 | 7 | 19 | 8 |
| locator, after the vote | 10 | **2** | 22 | 8 |

Wrong answers down 71% for no loss of correct ones. The trade the vote makes is
`wrong → missed`, and that is the right trade: a missed key signature leaves a
staff where it already was, a wrong one re-pitches every note on it.

Both surviving errors are the same staff — the Beethoven 6 clarinet, whose one
printed sharp was read as a flat. It agrees with the page's reference signature
and so cannot be told from a non-transposing part by any structural argument.

Recall of about a third is the honest figure on this material. Where the layer
does read a signature it reads it exactly: the three-flat staves come back with
all three accidentals matched at residuals of 0.03 and 0.24 steps against a
half-step tolerance.

---

## After the clef-branch merge (2026-08-28)

The Phase-1 x-extent fix from `claude/clef-recognition-improvement-ab75f6`
changes the geometry the CV locator was tuned against, and its heavier
rule-stripping changes what survives in the header mask. Component mode moved,
measurably and for the worse:

| the two orchestral pages, after the vote | correct | wrong |
|---|---|---|
| before the merge | 10 | 2 |
| after, with the merged `header_ink` | 6 | 7 |
| after, with the pre-merge `header_ink` | 4 | 0 |

**It does not reach the output.** Pipeline mode is unchanged, verified
like-for-like at identical settings on both sides of the merge:

| page | mode | before | after |
|---|---|---|---|
| wtc-p17 | pipeline | 10 correct / 0 wrong | 10 correct / 0 wrong |
| beet5-p2 | pipeline | 0 correct / 0 wrong, 0/22 voted | 0 correct / 0 wrong, 0/22 voted |

On the degraded page the clef gate closes either way, so the locator never
speaks and no wrong signature ships. The regression is confined to a mode that
forces a path the pipeline does not take — which is precisely why component mode
is documented below as not being a score for the layer.

**The open follow-up** is to retune the locator against the new Phase-1
geometry. Until that happens the component figures above are the honest state,
and this section — not the tables further up, which are pre-merge — is the
current record.

## What component mode does not measure

`--mode component` forces the CV locator onto every staff and hands it the true
clef. That is deliberate — it isolates the reader from clef detection, which is
a real ceiling on the end-to-end result and would otherwise hide what the reader
itself can do — but it is **not a score for the layer**, for two reasons.

**It bypasses the detector.** On WTC p.17 component mode scores 0 correct / 5
wrong, forcing the locator onto a page the detector reads perfectly well. The
pipeline scores 10/10 on that same page because it prefers the detector and
falls back to the locator only where the detector is silent. That ordering is
the whole game on clean engravings, and component mode inverts it.

**It supplies the clef.** In the pipeline the clef must be read, and a staff
whose clef is only the positional default is skipped, because a signature fitted
against a guessed clef is a guess squared — measurably: with every staff
defaulted to treble, two bass staves carrying three flats fitted cleanly as two
sharps. So end-to-end recall on degraded scans is lower than component mode
suggests, and key-signature reading **inherits the clef problem**. The two
improve together.

Use `--mode pipeline` for the number that describes what lands in the output.

---

## Reading the score columns

`missed` and `wrong` are kept apart everywhere in this benchmark and should stay
that way. They are not the same failure:

- **missed** — the layer abstained on a staff that has a signature. Costs
  recall; the staff keeps whatever it had.
- **wrong** — the layer asserted a signature that isn't there. Re-pitches every
  note on the staff for the rest of the system.

A layer that abstains is behaving correctly even when its recall is poor. Any
future summary that merges these two columns hides the property this whole layer
is designed around.

---

## Pages, and why each is here

| page | material | what it tests |
|---|---|---|
| `beet5-p2` | degraded 19th-c orchestral, concert C minor | three different written signatures for one concert key (3♭ / 1♭ clarinet / none for horns, trumpets, timpani) — breaks both naive counting and any "all staves agree" check |
| `pastoral-p2` | degraded 19th-c orchestral, concert F major | a transposing part printing the OPPOSITE accidental to the rest of the page (1♯ clarinet against 1♭) |
| `wtc-p17` | clean modern engraving, E major | the path where the DETECTOR fires, which the locator never reaches — and five systems of the same signature, so the cross-page vote is checkable by eye |

One caveat is recorded in `ground_truth.json` itself: Beethoven 6 ordinal 5
(Violino I) is read as one flat, but the flat is hard to make out at that
staff's print quality. It is marked `uncertain` in the file rather than silently
asserted.
