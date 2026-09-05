# H4 — the one question, drafted for Sean to decide

**2026-09-05. A DRAFT FOR A DECISION, NOT A PROPOSAL TO BUILD.** The coordinator
is putting this to Sean because it is an interaction design and he owns it.
Nothing here is implemented and nothing should be until he has ruled.

## Why a human is on the table at all

Not as a fallback. As **the only known source**, established by proof rather
than by exhaustion:

* multiplicity is not on the page — 62 staves encoded as 1 part against 72 as
  >1, under **identical printed labels**, and **not one of eleven page-side
  signals separates them**; the best ensemble scores **0.526** against an
  `always 1` baseline of **0.538**;
* the worked case is the Viola: `Viola` / `Bratsche` is one part in Litolff
  Beethoven, Simrock Dvořák and Breitkopf Brahms, `Violen` is two in Peters
  Mahler, `Violino I` is one in three editions and `Zweite Violinen` is **three**
  — with nothing on those pages differing;
* and the prize is the largest number in this area: oracle split **−7,118
  edits**, and stitch + oracle composing **superadditively to −9,369**.

## What the question is

One artifact, asked once per document: **the ordered roster.**

```
For this score, confirm the lineup as printed, top to bottom of a full system:

   1  Flauti            [ 2 players ]
   2  Oboi              [ 2 players ]
   3  Clarinetti in B   [ 2 players ]
   4  Fagotti           [ 2 players ]
   5  Corni in Es       [ 2 players ]
   6  Trombe in C       [ 2 players ]
   7  Timpani           [ 1 player  ]
   8  Violino I         [ 1 part    ]
   9  Violino II        [ 1 part    ]
  10  Viola             [ 1 part    ]
  11  Violoncello       [ 1 part    ]
  12  Basso             [ 1 part    ]
```

Pre-filled by the roster pre-pass (H2), corrected by eye. **The human confirms a
draft; they do not type a score into a form** — the same shape as the pre-fill
campaign's queue, and for the same reason.

## What one answer unlocks

| question | what the roster gives | consumer |
|---|---|---|
| identity | a name for every staff, including the **115 of 407** that print none | clef seeding, part naming |
| continuity | the anchor `build_reference` currently guesses from one system | `_stitch_slots` / `OMR_SLOT_STITCH` |
| **multiplicity** | **the count — the only known non-dossier source** | `OMR_CONDENSED_PARTS` |

Leverage: **407 staves across ~6 editions ≈ one question per document.**

## ⚠️ Three constraints that are already paid for — do not relitigate them

1. **It must abstain where the staff's IDENTITY is unconfirmed, not merely where
   the count is ambiguous.** Measured: a label-keyed count source on Beethoven 5
   p.4 slot 6 would confidently hand a **Trumpet's 2 players** to a printed
   `Violino I` whose truth is **1**. **So H4 depends on H1′** — the roster must
   be attached to the right staff before its counts mean anything.
2. **Coverage before gain.** The oracle map misses **4 of 20 rows** holding
   **4,944 of the 5,400 surviving `entire staff` edits (92%)** — Mahler 5 is 38
   reference parts against 13–18 printed staves. A roster question that reaches
   *those* rows is worth more than one improving rows already covered. Any
   pricing must report reach first.
3. ⚠️ **The count the reference wants is a property of the ENCODING, and a human
   reading the printed page cannot always supply it.** This is the sharpest
   limit and it must be said to Sean plainly: a conductor looking at
   `Violino II` sees one printed staff and one section; the Peters encoding
   splits it into **three parts**. The human can answer *"how many players does
   this staff carry"* — the engraving's question. They cannot answer *"how many
   `<part>` elements did this encoder emit"* without the encoding in front of
   them, and if they had that, it would be the answer key.

   **So H4's honest ceiling is the printed-players question, not the oracle
   arm.** The −9,369 figure is measured against printed truth in `works.json`,
   which is the players reading — so the ceiling is real for the benchmark as
   scored. But a future reference encoded by a different tool could disagree
   with a *correct* human answer, and no design fixes that.

## Answer-key discipline

The human reads **the printed score**. They do not read the reference encoding
and they do not read a dossier. That is legitimate — but an evaluation arm in
which a human supplied the roster **must be named for it, every time, and can
never enter a headline pooled figure.** Same standing as the oracle arm.

## The three decisions that are Sean's

1. **Is one question per document the right budget** — or should it be per
   movement (a movement can change lineup), or a two-tier "confirm / correct"
   where an unedited draft costs nothing?
2. **Where does it live** — the annotate UI (which already has the queue,
   hotkeys and autosave patterns), the web app's `ScoreProcess` step, or a CLI
   flag pointing at a small hand-written roster file?
3. **What happens when the human is absent** — abstain to `always 1` (the
   shipped default, 0.538, and what Audiveris does), or refuse the split
   entirely? ⚠️ The measured trap: `always 1` is **better than every page-side
   ensemble tried**, so "no answer" must fall back to it and not to a guess.

## What I would NOT do

* **Ask per staff.** 407 questions to buy what ~6 answers buy.
* **Ask for anything the page already gives.** Breitkopf labels every staff and
  scores **0 in class (a)**; on such a document the draft should be complete and
  the question a glance.
* **Let the answer silently widen.** A roster is a claim about **this
  document**; it must not be cached onto another edition of the same work,
  which is the answer-key line one step away.
