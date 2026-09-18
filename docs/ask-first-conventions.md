# ASK FIRST — how would a human get this, and what convention governs it?

**Standing instruction from Sean, 2026-09-18.** It applies to **every job in
this repository**, before any mechanism is built. It is not a phase, a
checklist item, or something the plan stage owns; it is one moment, before the
first line of code.

> *"I want to make sure that in our process of building out, the agent takes
> one moment before building to ask me what I — or a human — would do to get
> the information, or what are the main conventions of engraving that apply to
> the current job. Many times I feel like the agent is building in a
> counter-intuitive way, or blind to obvious conventions."*

---

## 1. THE RULE

**Before writing the mechanism, answer three questions out loud** — in the
brief, in the first message of the job, or at the top of the findings file:

1. **HOW WOULD A HUMAN GET THIS?** Not a musician in the abstract — Sean, or
   an editor with the plate in front of them. *Which mark do they look at, and
   what do they already know that makes it unambiguous?*
2. **WHAT ENGRAVING CONVENTION GOVERNS IT?** An engraver does not place ink
   freely. A convention is what they do **because that is how music is set**,
   and it is usually rigid enough to be a **search constraint** rather than a
   statistic.
3. **ASK SEAN.** One line, before the code. He is a musician and reads these
   plates; this is the **cheapest evidence in the project** and it costs a
   message. A job that genuinely cannot ask must write the assumption down —
   see §4.

⚠️⚠️ **THE ORDER IS THE WHOLE POINT, AND ALL THREE ARE ROUTINELY SKIPPED —
because a plausible mechanism can be written without any of them.** A
mechanism built without them is not merely weaker than one built with them; it
is frequently **aimed at the wrong quantity altogether**, and then measured,
tuned and defended on that wrong quantity. The measurement cannot save you: it
will faithfully report how well you did the wrong thing.

**The one-sentence test:** *if Sean read this design over your shoulder, would
he say "that is not how it is printed"?* If you cannot answer that, you have
not done step 1.

---

## 2. THE COST OF SKIPPING IT — this repo's own record

These are not cautionary tales. Every row is a convention that was **already
true of the page** before we built anything, and the figure is what it was
worth once somebody finally said it.

| the convention | what it cost / bought |
|---|---|
| **An engraver fills an otherwise silent bar with ONE centred whole rest, whatever the meter — the glyph stands for THE BAR.** | 558 of 618 wrong rest durations on the scan gate. Ledger: `rest.type` **933 → 10**, `rest.duration_ql` **328 → 4**, `matched_exact` **3,154 → 4,077** — 1,251 attribute errors, and OMR-NED charged **nothing** for any of them. |
| **A slur is drawn OVER its notes; a hairpin is drawn BETWEEN them.** | `_noteheads_under` is a perfectly good overlap test that scores **0 of 4** on hairpins — Mahler's Trumpet diminuendo spans page x 5922-6068 in a bar whose only notehead spans 5817-5897. **Not one pixel of overlap.** |
| **A note ON A LINE takes its dot in the space ABOVE, half a staff space up.** | Signed offsets are bimodal and nothing else: **52 at 0.00 spaces, 52 at +0.50, nothing between +0.57 and +3.75.** The window is ASYMMETRIC because a dot never goes *under* its note. |
| **A beam stroke runs from the FIRST stem it joins to the LAST, and a stem stands at the SIDE of its notehead.** | The outer note's centre overshoots the stroke by **0.35-0.47 notehead widths** — the stem offset and nothing else. Closing it took the engraved fixture from **12 assessable / 7 correct → 16 / 16**. |
| **An arc over stemmed notes is drawn stem-top to stem-top, for the same reason.** | `<slur>` **32 → 40**, `<tied>` **80 → 91**, `arc_binds_fewer_than_two_notes` **551 → 519**. No new constant. |
| **An engraver announcing a new meter prints it TWICE — the courtesy after the final barline governs no bar.** | All four TRUE changes sit at a non-last cell; **both cautionaries at a LAST cell.** False meter changes **10 → 3**, no true change lost. |
| **A meter is printed at a movement's START and nowhere else.** | The whole reason `OMR_METER_CARRY` exists. Systems decided **1 of 5 → 5 of 5**; bars that add up **54.4% → 81.2%**, 298 wrong→exact and 0 the other way. |
| **A key change is printed at ONE bar of ONE system, on EVERY staff of it — so the BAR is the shared fact even where the VALUE differs by transposition.** | **7 of 7** spurious mid-staff flips stopped. |
| **A tie's two heads are at ONE STAFF POSITION, by definition.** | ⚠️ **The function's own docstring said exactly this and neither pairing rule ever used it.** Same-pitch links max **0.168** spaces, one-step-apart links min **0.435** — a measured empty interval that was sitting there the whole time. |
| **A time signature's placement is RIGID** — numerator in the upper two spaces, denominator in the lower two, centred. | Turns a 2-D search into a 1-D one. **4 correct, 0 wrong, 12 correct abstentions**, where the detector reads **zero** digits on the same page. |
| **A notehead is one staff space tall, because that is what a notehead IS.** | Interior noteheads **0.61-1.12** spaces, crop fragments **0.29-0.56**. Pooled 0.2209 → 0.2137. |
| **An engraver opens the gap above a staff PRECISELY so its ledger notes and their slurs can live there.** | Which is why "nearest staff" is the wrong rule for exactly the case the padding exists for. Pooled **2,473 → 2,371** edits. |
| **A trombone section is scored by REGISTER, a trumpet section by NUMBER AND KEY.** | `Tr. Alt.` had been reading as *Alto*, a singer, at HIGH confidence. |
| **An engraver does not name one section with two different abbreviations on one system.** | 24/29 → **26/29**; the 17-staff finale system **16/17 → 17/17 exact**. |
| **A barline is a STRAIGHT line, not a vertical one** (the plate is warped). | One barline's x drifts **40 px** top to bottom. Page 1: **17/17 barlines, 0 false, 16 measures of 16.** |

⚠️ **And the sharpest one of all is not a mechanism at all.** On Phase 2
observation 3, *"the manager paraphrased 'quarter note' as 'quarter rest' and a
job rigorously answered the wrong question."* One clarifying line would have
cost a message and saved a session. **Asking is not overhead; it is the
cheapest measurement available.**

---

## 3. ⚠️⚠️ A CONVENTION IS A HYPOTHESIS AND A CHEAP TEST — NEVER A LICENCE

This rule makes it **easier** to be confidently wrong, so it comes with a
guard, and the guard is not optional. Everything the repo already demands
still applies: measure the reach, state the n, name the control, keep the
refusals.

**A convention tells you WHERE TO LOOK and WHAT WOULD FALSIFY IT. It does not
tell you that you are right.** The tell that a convention is real is a
**measured empty interval** — 0.00 vs +0.50 for the dot, 0.168 vs 0.435 for the
tie, 0.61 vs 0.56 for the notehead. The tell that it is a story is a smooth
slope with a threshold fitted into it.

**This repo has refuted conventions too, including Sean's own:**

- **S4** — an arc's side relative to the stem. Sean stated it; the narrow test
  failed; Sean said ***"don't give up — adjust the rules to be broader"***
  (which was right: a narrow operationalisation failing is evidence about the
  operationalisation). Widened to full reach it is **REFUTED** — SIDE flat at
  −0.001 / −0.030, the sweep never clearing p = 0.079. **The refutation was
  worth more than the repair would have been.**
- **"Whether a staff's label means one part or two"** is a property of the
  **ENCODING, not the engraving** — a label-derived rule is 74/74 on
  Beethoven/Brahms and **+2,181 edits on Dvořák**.
- **"A meter stack is two digits aligned in x and adjacent in y"** — TRUE `dy`
  32-548 against FALSE 26-555. Total overlap.
- **A PAGE truth is not an ENCODING truth**: MusicXML writes a `<slur>` at each
  END and the engraver draws ONE arc; a clef is printed at every system and
  declared once (28 glyphs vs 14 `<sign>`). **Half of "the convention" questions
  are really "whose convention — the engraver's or MusicXML's?"**

So the honest form of step 2 is: *"the convention says X, which predicts Y
about this page; Y is checkable in N minutes; here is the check."*

---

## 4. WHEN YOU CANNOT ASK

Cloud sessions, overnight runs and dispatched agents often have nobody to ask.
**"Could not ask" must never become "did not think about it."**

Write it down instead, at the top of the brief or FINDINGS, in this shape:

> **CONVENTION ASSUMED:** an engraver prints X because Y.
> **WHAT WOULD FALSIFY IT:** <the cheap check, or the crop to look at>.
> **NOT CONFIRMED WITH SEAN.**

That is the same ABSENT/DECLINED discipline `record.py` enforces on the
pipeline, applied to the people building it: *an assumption stated is a thing
a later reader can refute; an assumption buried in a mechanism is not.* A job
that ships a convention-shaped claim with no such block has converted **cannot
tell** into a definite answer — which this project already refuses everywhere
else.

---

## 5. EVERY HANDOFF CARRIES THIS

A handoff that ranks work without saying what convention governs it hands the
next session the same blindness. **Every handoff, brief and dispatched job
carries the pointer**, and any job whose work touched a convention says which
one:

```markdown
⚠️ **ASK FIRST** — before building, say how a HUMAN would read this off the
page and what ENGRAVING CONVENTION governs it, and ask Sean in one line.
[docs/ask-first-conventions.md](ask-first-conventions.md). Cannot ask →
write the assumption and its falsifier down.
```

⚠️ **Older handoffs are NOT retrofitted, and this was checked rather than
assumed.** A dated record is what that session knew on that day, and rewriting
it is the ledger overwriting the tree. The **one** exception is the handoff
CLAUDE.md currently names as *START HERE*
([docs/handoff-2026-09-17-infer-rule-two.md](handoff-2026-09-17-infer-rule-two.md)),
which carries the block above as a **dated addition that changes none of its
findings** — because a pointer nobody reaches is not a pointer. The rule
applies **from 2026-09-18 forward**; §2 is the argument that it should have
applied all along.

---

## 6. WHAT THIS IS NOT

- **Not a request for permission.** It is one question about the page, not a
  gate on starting work. Sean has repeatedly said *build*, most recently *"I
  want progress in the build not just more measurements."*
- **Not an excuse to stop and wait.** Ask, then do every part of the job that
  does not depend on the answer while you wait.
- **Not a new stage.** It is upstream of GATHER — it decides *what mechanism
  to build*, not what the pipeline does with a page.
- **Not a substitute for measurement.** See §3. A convention that cannot name
  its own falsifier is a guess in better clothes.

---

## 7. THE FAMILY THIS BELONGS TO

Three named failure families in CLAUDE.md, and this is the fourth — the one
that runs **before** the other three, because all of them are about a value
that exists and is not used:

1. *The value existed and nothing read it* — `Q.STEM` gathered and unread three
   separate times; `pdf_path` rasterised and dropped on **every staged run this
   repo had ever made**.
2. *A rule described in a docstring and never built* — `adjudicate_slot_index`
   stating the short-system rule in bold, on a function that returns the
   ordinal on every path.
3. *A premise encoded in a refusal outlives its reason* — the refusal is right,
   the reason expires, nothing re-asks.
4. **THIS ONE: *the convention was on the page and nobody asked what it was.***
   The tie docstring is where all four meet — the convention was **known,
   written down, correct, and read by neither rule that needed it.**
