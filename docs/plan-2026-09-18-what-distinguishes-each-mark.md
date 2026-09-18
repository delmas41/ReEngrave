# The forward plan: for every family — what fact DISTINGUISHES it, in what frame, at what stage, and can that decision abstain?

**2026-09-18.** Sean's own diagnosis at the end of the session that produced
[the breakthrough document](breakthrough-2026-09-18-the-unit-of-enquiry.md),
[the stage charter](stage-charter-2026-09-18-what-each-stage-does.md) and
[the boxing proposal](proposal-2026-09-18-boxing-is-a-decision.md). **This is the
work plan those three documents imply.**

---

## 1. SEAN'S STATEMENT, verbatim

> *"I think I have a good understanding now of where this is going wrong and I
> know that it is not the system or the later stages. It seems to me right now
> that it is more about the initial classification and how that is passed
> along. This whole process with the stems has been a perfect example of that.
> We weren't measuring certain classes and had nowhere for them to go and spent
> a lot of time measuring the wrong things for stems that ended up being
> variable. This clarifies the work moving forward: we need to address what is
> essential for each mark and symbol and determine at which stage information
> is addressed."*

**It is established rather than a hunch, and each half has its evidence:**

* **"not the later stages"** — `tools/omr/staged/trace.py`'s funnel shows the
  stages abstaining properly, correcting each other (EVALUATE changes 50
  duration values and collapses 5 narrowings; `pitch` changes 186 as `reowned`)
  and balancing their own books on both publishers.
* **"the initial classification and how that is passed along"** — and *how it
  is passed along* is the sharper half. The class is not merely sometimes
  wrong; `gather.py:373` files it with `log.observe`, **as a fact about the
  page**, with its own subject address, so **nothing downstream is permitted to
  doubt it.** Of 28 adjudicators exactly one ever questions it, narrowly.
* **"a perfect example"** — the stem case is both halves at once: **nowhere for
  the non-stem vertical lines to go** (no quantity exists; only `Q.STEM`, the
  six filters' survivors), **and** six filters **measuring the wrong thing** —
  dimension bounds on an object the engraver varies on purpose (2.16 → 6.78
  staff spaces, median 3.93, n = 1,919).

## 2. THE QUESTION, in four parts

Sean's plan asks two of these. The third and fourth are added here, and §5 says
why each is needed.

> **For every family: what fact DISTINGUISHES this mark from the things it could
> be mistaken for — in what FRAME is that fact expressed — at what STAGE is it
> decided — and can that decision ABSTAIN?**

| part | the failure it prevents | the instance that taught it |
|---|---|---|
| **what fact** | measuring the wrong property | six filters bounding a variable-length stem |
| **what frame** | a clean, believable, WRONG answer | the barline test, uncomputable; **three mutually-disagreeing box conventions in one record** |
| **what stage** | a decision taken where it cannot be revisited | the class `observe`d as fact before any stage runs |
| **can it abstain** | *cannot tell* converted into a definite answer | `NO_INK` on 2,377 cells that hold ink |

## 3. ⚠️ THE GUARD — "essential" means essential for DISTINGUISHING

**"What is essential for each mark" runs away without this**, because it
collides with Sean's own standing instruction on the ink layer:

> *"Theoretically every position can at some point contribute even if that is
> not with our current pipeline. We are still discovering what works best and
> for testing we need to hold on to everything because we can't yet know all of
> what will be helpful."*

**Both are right, and the stem case resolves them.** The test is not *"what
could we record about a stem"* — under that reading everything is essential and
the plan has no edge. The test is:

> **What would tell this mark from the other things it might be?**

**Length failed that test for a stem and passed it for an accidental, a barline
and a clef. Attachment passed it for a stem.** That is a criterion that can be
applied to one family in an afternoon, and it is what Sean's own reasoning
produced. ⚠️ It does **not** license discarding anything: *hold everything*
governs GATHER, and *what distinguishes* governs which fact a DECISION reads.
**They operate at different stages and do not conflict.**

## 4. ⚠️⚠️ THE ONE EXCEPTION — not every loss is upstream, and one is a flag rather than a rebuild

*"It is not the later stages"* is right about the **diagnosis** and would be
wrong as a **work plan**. On Breitkopf the dominant loss is
**`duration_narrowed`, 537 events** — which is **INFER's exact population, and
`OMR_INFER` is default OFF.** That is not a classification problem. It is a
capability that was built, measured and never switched on.

**So the forward work has two tracks and they must not be merged**: the
architecture question below, and a **separate, already-paid-for** decision about
the fourth stage's default. ⚠️ Its own findings say what is missing before that
flip — the inferences have never been checked against the print.

## 5. WHY THE TWO ADDED PARTS ARE NOT PADDING

**THE FRAME.** The barline test — *a barline's two ends sit on the outer staff
lines, a stem's do not* — is Sean's strongest discriminator and it **cannot be
computed today**, not because it is in the wrong stage but because the two facts
are in incompatible coordinate systems: `Q.STEM` is in cell coordinates and
carries **no page coordinates at all**, while `Q.STAFF_LINES` is page pixels,
and the per-cell row that looked like a bridge stores `lines: 5` — **the count
of lines, not their positions.** ⚠️ This hazard appeared **four times in one
evening**: `Q.GLYPH_BOX` is `[name, x, y, w, h]`, `Q.INK`'s box is CORNERS,
`Q.STEM`'s documented convention was **wrong in the code**, and subject keys
**collide across documents** because a subject's last coordinate is a positional
index. **Read one as another and you get a negative width and a clean,
believable zero** — it cost one probe an entire run.

**CAN IT ABSTAIN.** A fact decided where it cannot abstain is a fact that cannot
be revisited. `NO_INK` is the proof: a stem candidate **rejected by a filter**
is recorded as *"no ink"* — and `Q.INK`'s own `no_ink` fires **zero** times on a
record where it covers all 1,183 cells, so **every one of those 2,377 claims is
false about the ink.** ⚠️ Its sharpest form is **ten lines apart in one gatherer
and backwards**: `gather.py:1070` writes `NO_INK` for a cell that HAD detections
(**997** firings) while `:1079` writes the honest `NO_DETECTIONS` for a cell
with none (**3**).

## 6. THE SCOPE — a SWEEP, not family-by-family as things break

⚠️ **"Nowhere for them to go" is not special to vertical lines.** It is the same
shape as **rests having had no quantity at all** (838 detected glyphs the record
could not carry), fermatas and ornaments having none, and **accidentals having
no gathered quantity to this day** (they are an EVALUATE consequence). **The
stem family is simply the one examined hardest.**

**And most of the instrument exists.** `tools/omr/staged/capture.py --check`
already asks a version of this question per family — what shape, what position,
what image, what resolution — built for Sean's earlier question about ink.
**Extending it to "what fact distinguishes this family from its neighbours, in
what frame, at what stage, abstainable?" is an extension of a working tool, not
a new programme.** Every figure it reports is derived from the registry rather
than hand-listed, which is what keeps a sweep honest as the vocabulary grows.

## 7. THE WORKED EXAMPLE, because one family is done end to end

The stem family is the template, and it is the only one carried all the way:

| | |
|---|---|
| **what fact** | **ATTACHMENT** — a notehead at one END, offset half a notehead width from that head's centre. **NOT length**: 2.16 → 6.78 spaces, and a barline at 4.00 sits at the **median** |
| **what frame** | page pixels, so the run's endpoints can meet `Q.STAFF_LINES` — **absent today** |
| **what stage** | *no head at either end ⇒ NOT a stem* is **forced** → EVALUATE. *A head at an end ⇒ IS a stem* is **likely** → INFER. **The halves go to different stages** |
| **can it abstain** | yes — and its cost measured **0 of 68** on hand truth, with a positive control moving it 0 → 1 |

⚠️ **And the surprise that made the frame question necessary**: the veto fired on
**24 accidentals, clefs and rests of 33** — the whole thread had framed it
against **barlines** — because **the pipeline has no category for "a vertical
line that is not a stem."** ⚠️ **OPEN QUESTION FOR SEAN, not yet answered:
should an accidental's vertical stroke be in that rule's domain at all?**

## 8. ⚠️ WHAT THIS PLAN DOES NOT CLAIM

* **It is not measured.** It is a plan drawn from measurements, and §7's own
  accuracy is unestablished — **no note has been checked against the print in
  any stem arm**, and whether the veto ever refuses a *real* stem needs print
  adjudication of its 33 firings.
* **It does not say the detector should be replaced.** Boxes are demonstrably
  fine for noteheads on clean engraving (**856 of 856**). The narrow claim is
  that **a box cannot carry a merge, a split or a sub-part**, and on these plates
  those are the common cases.
* **It does not price the architecture.** Routing is **BY CLASS** today, so
  making the classification abstainable touches every family's dispatch — the
  largest change this codebase could undergo — and record size is already
  **0.6-3.1 MB/page** for the ink layer alone.
* **n is 2 publishers and 8 pages throughout, with one adjudicator**, and on the
  Litolff plate **~60% of noteheads cannot be adjudicated by eye at all**,
  controls and sample alike. **No OMR-NED figure anywhere, deliberately** — the
  metric is symmetric and pays for emitting fewer symbols.

**Attribution, since it matters for who to ask about what**: §1 is Sean's
diagnosis and §7's central claim (*length identifies everything except a stem*;
*a stem is known by its attachment*) is his. The two added parts of the question
in §2, the guard in §3, the exception in §4 and the sweep scope in §6 are the
assistant's, and each names the instance that produced it.
