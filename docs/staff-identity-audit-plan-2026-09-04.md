# What is this staff? — a multi-signal identity audit (plan, 2026-09-04)

Sean's framing, and it reorients the condensed-parts work: **stem direction
answers "how do I render two lines", not "what is this staff."** Identity needs
several weak signals combined — clef, the key signature a transposing
instrument prints, the instrument's range, and the continuity of a line through
the score — and the honest first step is to find out **how much each signal
actually knows**, separately, before any of them is wired into an inference.

This is a plan for an AUDIT, not for a classifier. It emits evidence and scores
it against a hand-verified key; it changes no pipeline behavior. The repo has
been burned twice by the opposite order (the label rule that was 74/74 on two
works and +2,181 edits on a third; the stitching hypothesis that owned 13% of
the bucket it was designed for), and both were caught by measuring first.

## What we are asking, precisely — three questions, not one

They need separating because they have different evidence and different
consumers:

1. **Which instrument is this staff?** (identity) — consumes: clef seeding, key
   fitting, cross-staff range vetoes, part naming.
2. **How many reference parts does it carry?** (multiplicity) — the condensed
   question; consumes `OMR_CONDENSED_PARTS`.
3. **Is this the same part as that staff on the previous system/page?**
   (continuity) — consumes `_stitch_slots` / `OMR_SLOT_STITCH`.

A signal can be strong for one and useless for another. The audit scores all
three per signal.

## The signals, and what each can and cannot know

| # | signal | where it lives now | speaks about |
|---|---|---|---|
| S1 | margin label | `staff_labels*.py` ladder → `instruments.lookup` | identity, multiplicity (plural sections) |
| S2 | clef | `clef_geometry` / detector / `clef_locator` | identity (narrows family: alto ⇒ viola, bass ⇒ low family) |
| S3 | **printed key signature vs the page's concert key** | `key_signature_vote` + `instruments.fifths_offset` | identity — this is the transposition fingerprint |
| S4 | observed pitch envelope vs `written_range` | `pitch_resolver` output + `instruments.written_range` | identity (veto), multiplicity (two envelopes) |
| S5 | vertical position / score order | `score_layouts.py`, ten standard orders | identity (prior) |
| S6 | line continuity across systems & pages | `slots.py` alignment + register stability | continuity, identity (propagation) |
| S7 | intra-staff texture: divisi stems, dyads, rest asymmetry, `a 2` text | `voicing.py`, direction text | **multiplicity only** |
| S8 | **bracket / brace grouping** — which family block this staff sits in, and whether a brace joins it to its neighbour | `system_grouping.py` → `Staff.group_index` (already extracted; verified on Beethoven 9 p5: 4 winds \| 2 horns \| 5 strings) | identity (block prior), **multiplicity** (a brace says one section on two staves; no brace inside a block says condensed) |

**S8 is free and already computed, which makes it the cheapest thing in the
table.** `system_grouping` separates bracket groups by the gap-and-ink signature
it uses for systems (a bracket group boundary inks the bracket but not the
barline), and it writes `Staff.group_index` — nothing downstream currently reads
it for identity. The block a staff sits in constrains the instrument far more
than raw vertical position does (S5 assumes a standard order; a bracket is what
the engraver actually printed), and it is the natural *frame* for the others:
S3's transposition classes, S5's order prior and S6's continuity should all be
scored **within a block** rather than across the page. For multiplicity it cuts
the other way and just as usefully — a **brace** over two staves says one
section printed on two (divisi across staves, not condensation), while a single
staff in a block whose neighbours are braced pairs is the condensation
signature. ⚠️ Note the honest limit: group detection is measured for *systems*
(43% → 86%, then 22/23 with the left-edge split) but **its per-block accuracy
has never been scored on its own** — the audit must measure S8 as a signal, not
inherit the system figure.

**S3 is the signal this project has never mined, and Sean is right that it is
the sharp one.** On a page whose concert key is 3 flats, a clarinet in B♭
prints 1 flat and a horn in F prints 2 — so *the difference between this
staff's key signature and the page's modal key signature is a direct estimate
of `fifths_offset`*, which `instruments.py` already stores per instrument. It
cannot name an instrument alone (several share an offset), but it partitions
the page into transposition classes, and combined with S2/S5 it is close to
decisive for the brass/woodwind block that S1 most often fails on.

⚠️ **The signals are NOT independent, and the audit must record the chain.**
Key-signature reading is *chosen by the clef* (a wrong clef gives wrong
signatures, not abstentions — documented). Pitch envelopes come from
`pitch_resolver`, which consumes the clef and the key. So S3 and S4 inherit
S2's errors. Any confusion matrix that treats them as independent votes will
overstate the ensemble. The audit reports each signal **conditioned on whether
the clef was read or defaulted**.

## The audit's output — one row per staff per page

```
work, page, system, staff_index,
  s1_label_raw, s1_instrument, s1_confidence, s1_source(text|tesseract|surya|vision|none)
  s2_clef, s2_source(detector|geometry|locator|default), s2_defaulted(bool)
  s3_staff_fifths, s3_page_modal_fifths, s3_implied_offset, s3_candidate_instruments
  s4_pitch_lo, s4_pitch_hi, s4_n_notes, s4_range_compatible[list], s4_two_envelopes(bool)
  s5_position_index, s5_score_order_prediction
  s6_slot_id, s6_continuous_with_prev(bool), s6_register_delta
  s7_divisi_bars, s7_dyad_bars, s7_rest_asymmetry, s7_a2_text(bool)
  s8_group_index, s8_group_size, s8_braced_with(staff_index|none), s8_block_position
  TRUTH_instrument, TRUTH_parts[], TRUTH_source(works.json hand-verified)
```

Then three scorecards — for identity, multiplicity, continuity — each reporting
per signal: **coverage** (how often it speaks at all), **precision when it
speaks**, **and what it adds over the best cheaper signal**. That last column
is the one that matters: a signal that is 95% right but only ever agrees with
the label it duplicates buys nothing.

## Corpus, and the answer-key discipline

- **Primary**: the 11-row scan benchmark. `works.json` carries hand-verified
  `staves[i].parts` per page plus hand-read clef and key columns — the key for
  all three questions. **Scoring only, never input.**
- **Secondary for identity**: the 166-staff clef ground truth
  (`eval_pipeline_clefs.py --wide`, 10 pages / 4 publishers) and the 1,380
  margin labels across 10 editions.
- ⚠️ **Dossiers are barred as input here** — they are generated from the same
  MusicXML used as truth. They may appear as a *ceiling arm* ("what if identity
  were known"), clearly labeled, never as a signal.

## What a good result looks like, and what would kill it

- **Good**: S8 assigns blocks that contain the truth's family ≥90% of the time
  and scoring the other signals within a block beats scoring them page-wide;
  S3 speaks on ≥60% of wind/brass staves and, given a read clef,
  narrows to a transposition class that contains the truth ≥90% of the time;
  S4 vetoes at least as reliably as it does for cross-staff notes; S6 propagates
  a confident identity to staves where every page-side signal is silent.
- **Kill criteria, stated in advance**: if S3's implied offset is right less
  often than the score-order prior S5 alone, it is not a signal — it is a
  restatement of "this staff is in the brass block." If every signal collapses
  to S1 (label present ⇒ everything agrees; label absent ⇒ everything abstains),
  the audit's answer is *labels remain the binding constraint* — which is
  already CLAUDE.md's documented conclusion for clefs, and would be an honest
  negative worth recording rather than a disappointment.
- **The multiplicity question may answer differently from identity**, and that
  is a real possible outcome: S7 + S1-plurality could carry multiplicity while
  identity stays label-bound. That would still unlock `OMR_CONDENSED_PARTS`
  without a dossier — the outcome Sean is holding out for.

## Deliberately not in scope

Building the combiner. The audit ends at "here is what each signal knows, here
is what they add to each other, here is the confusion structure." Whether that
becomes weighted voting, a decision cascade in cheapest-first order (the label
ladder's shape), or nothing at all, is the next decision and wants these
numbers in hand.

Also out: divisi stem-splitting as a *rendering* improvement (the condensed
session's named next increment) — related but separate, and it should not be
bundled with an identity question.
