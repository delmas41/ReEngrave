# Tie or slur — the rules, from Sean, 2026-09-11

Verbatim, then indexed. **This is a statement about how the music is ENGRAVED,
not about our pipeline**, and it is the kind of fact this project almost never
has written down: a reader who knows the convention, stating it unprompted
after looking at a real page.

> *"if the arcs are connected to note heads they could be tied or slurs but if
> if spans more than two note it definitely a slur. If it connects to the stem
> near the note it could be either but if it is connected to the stems edge
> away from the note head then it is a slur. If the notes connected by the arc
> have different pitches it is a slur. If there are 2 arcs on top of each other
> then the lower is a tie and the upper is a slur."*

| # | the rule | decides | reads |
|--:|---|---|---|
| **S1** | an arc connected to NOTEHEADS | **ambiguous** — tie or slur | — |
| **S2** | an arc spanning **more than two notes** | **SLUR** | note count |
| **S3** | connected to the stem **NEAR the notehead** | **ambiguous** | geometry |
| **S4** | connected to the stem's **edge AWAY from the notehead** | **SLUR** | **geometry** |
| **S5** | the connected notes have **different pitches** | **SLUR** | resolved pitch |
| **S6** | **two arcs stacked**: lower / upper | **TIE** / **SLUR** | **geometry** |

---

## ⚠️ What is already in the tree, and why the split matters

**S2 and S5 exist** as `OMR_ARC_RECLASS` (`tie_to_slur_flagged_span`,
`tie_to_slur_flagged_diff_pitch`, `…unpaired_span`, `…unpaired_diff_pitch`) —
**measured on both families and REFUSED**: engraved +6 edits, **scan +149**.
CLAUDE.md states the reason, and it is about S5's INPUT rather than about the
grammar:

> *a scan's resolved pitch at an arc's ends is downstream of exactly what scans
> get wrong (`wrong note` = 26% of that pool)*

⚠️ It also records that the refusal is **not uniform across the four rules**:
`tie_to_slur_flagged_diff_pitch` is the PROVABLE one and the three works where
it fires alone are **−4 edits, i.e. BETTER**; every edit-positive work fires a
`span` or `unpaired` rule, which are INFERRED. **So S5's problem is that we
cannot read the pitch, not that Sean's rule is wrong.**

**S4 and S6 are NOT implemented anywhere** — `grep` for a stem attachment POINT
or for stacked arcs returns nothing but prose. ⚠️⚠️ **And they are the two that
read GEOMETRY rather than resolved pitch, which is exactly what makes them
viable where the refused version is not.** A boxed arc and a boxed stem are
read off the same ink the arc itself is; neither needs the pitch resolver,
whose failures are what sank S5 on a scan.

⚠️ **S3/S4 have an input that already exists as of 2026-09-11.** The arc
recovery work established that *an arc over stemmed notes is drawn from STEM
TOP to STEM TOP* (median offset **0.52 notehead widths**) and now joins arcs to
stems; `Q.STEM` carries **1,920 rows** on these four pages. What S4 adds is
**WHERE ALONG THE STEM** — the notehead end against the far end — which is a
new measurement over data already in hand.

---

## ⚠️ How to treat these rules

**As a hypothesis with a named author, to be MEASURED — not as an oracle.**
This repo's record is that a stated convention holds until a second publisher
is tried: the meter carry held on one document and split on the second, and the
arc offset distribution is explicitly expected to differ *"on a print whose
slurs sit over noteheads rather than stems"*.

⚠️ **S6 in particular is a claim about ENGRAVING that our detector may not be
able to see**: two stacked arcs must first be DETECTED as two arcs, and the
arc-recovery work found **48 arc pairs in one cell at IoU ≥ 0.7, 19 of them on
two different staves, some pairs disagreeing about their own kind**. **Measure
how often S6's precondition is even met before measuring whether S6 is right.**

⚠️ And the standing hazard applies: *the case that most needs an arbiter is the
case where the arbiter is silent*. S4 needs a stem; a page whose stems are not
read gets no answer from it, and that is likely to be the same page whose arcs
are worst.

---

# ⚠️⚠️ A SEPARATE CORRECTION, SAME DAY — recorded here because it is the same
# failure shape: the MANAGER PARAPHRASED SEAN AND THE PARAPHRASE WAS MEASURED

Sean's observation 3 said: *"Many whole note rest which equal 2 beats are
showing up as a **single quarter note**."* The manager briefed it as a quarter
**REST**. The rest-sizing job then proved — rigorously, with an empty interval,
0 of 209 overlapping — that our quarter rests **are** genuinely quarter rests.

**That answered a question Sean had not asked.** He clarified: *"in bars where
it should be just whole note rest in two four. It's showing an actual quarter
note, not a quarter note rest."*

**Measured on the current tree, one re-export of the shared record:**

| | |
|---|--:|
| bars whose ENTIRE content is one PITCHED note | **118** |
| ...of which the bar is UNDERFULL | **44** |
| ...of which the lone note is a QUARTER in a 2/4 bar | **26** |

Named examples: `P1 m45 C5`, `P1 m85 D5`, `P1 m88 D5`, `P1 m89 D5`,
`P2 m49 F5`, `P2 m87 A5` — each `dur=96` against a bar of `192`.

⚠️ **This is a DIFFERENT fault from the one that was repaired.** The rest work
closed *a whole rest is not sized to the bar* (the meter, an empty interval,
92/92 against 0/195). This one is **a pitched note standing where the page
prints silence** — a false positive, or a note attributed to the wrong staff,
not a mis-sized rest. **Neither the rest job nor the arc job was looking at
it**, and the bar-fill figure it contributes to (18.4% of bars SHORT) was
reported without anybody opening the short bars.

⚠️ **The plausible mechanism, stated as a hypothesis and NOT measured**: in 2/4
an engraver fills a silent bar with one centred WHOLE REST, which is a small
filled rectangle hanging under a staff line — and a notehead is a small filled
oval. **They are confusable ink.** The arc-recovery work already found the
mirror of this on the same document: a `restWhole` detected at 0.56 *"where no
whole rest exists"*. ⚠️ **Do not build on that guess** — the last three jobs
each refuted the mechanism their brief proposed.

⚠️ **The manager's own probe of this failed**: it guessed the record's schema
(`rows` / `log`) and reported `n=0` for both arms, which is the shape of a
clean zero that is really a dead instrument. The record's top level is
`record / summary / adjudication / agreement / evaluation / stubs /
provenance`. **Use the reader API, not a hand-rolled walk**, and print a
positive control before any zero.

**The lesson, which is this file's own subject matter arriving one level up:
Sean's words are the truth statement, and a paraphrase of them is not.** The
rules S1-S6 above are recorded VERBATIM before being indexed for exactly this
reason.
