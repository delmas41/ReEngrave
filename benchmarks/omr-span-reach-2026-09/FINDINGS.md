# Span reach — the population is 26 of 43, and the fix has a limit

⚠️ **Written by the coordinating session from the agent's report.** The agent's
harness refused `Write` on a file named for a report — the third agent to hit
that block today — so the probes, JSON outputs, hand-read truth files and margin
crops in this directory are its work, and this narrative is its report
transcribed. Every number below traces to a committed artefact here.

## 1. The screen, and the control that licenses it

`lineup_spans` is a function of the `(page, [system sizes])` profile alone, and
`detect_staves` already sets `system_index` — so **reach costs a render plus a
staff detection per page, ~1-3.5 s.** No detector, no margin reader, no export
(`probe/span_profile.py`).

It reproduces both known works exactly — **Beethoven 5 → 2 spans, boundary 44**;
**Brahms 1 → 2 spans, boundary 45** — and agrees with the pipeline's own answer:
`dump_spans.py` on the Beethoven 6 compose cache returns the identical
`0-26 / 27-45 / 46-78`.

## 2. The reachable population: **26 of 43 = 60%**

Multi-movement orchestral editions ≤150 pages, 15 publishers (`out/summary.json`).
Distribution: **1 span ×17, 2 ×17, 3 ×8, 4 ×1.** So the earlier n=2 was not
"nearly the whole population" — it was two of twenty-six.

| edition | pg | spans | boundaries |
|---|--:|--:|---|
| Beethoven 9 / Litolff | 189 | **4** | 48, 114, 167 |
| **Beethoven 6 / Litolff** | 79 | **3** | 27, 46 |
| Berlioz *Fantastique* | 148 | 3 | 73, 139 |
| Lalo *Symphonie espagnole* / Durand | 147 | 3 | 37, 101 |
| Mahler 4 / 1911 | 125 | 3 | 25, 73 |
| Prokofiev 1 / Éditions Russes | 97 | 3 | 36, 55 |
| Schumann 3 / Peters | 93 | 3 | 19, 46 |
| Sibelius 5 / Hansen | 134 | 3 | 32, 42 |
| Tchaikovsky 4 / Jurgenson | 226 | 3 | 42, 159 |
| **Brahms 4 / Breitkopf** | 99 | 2 | 41 |

Plus sixteen more two-span editions (Nielsen 4, Fauré *Requiem*, Rachmaninoff
PC2, Bizet, Sibelius 2 and 7, Mendelssohn 5, Nutcracker, Tchaikovsky VC, Brahms
PC1, Saint-Saëns PC2, Beethoven PC4, Schumann 2, both Brahms 1 scans…).
One-span controls behave: Dvořák 6/7/9, Beethoven 3, Beethoven 7, Mozart 40,
Mozart *Requiem*, Enigma, Glazunov 5. **~4 min a work.**

⚠️ Selection used encoding-derived per-movement part counts
(`probe/inventory.py`); **every span figure is page-derived.** Of eleven works
the encodings predicted would grow, several take one span — the encoding
generates candidates, it is not an oracle.

## 3. Third work — Beethoven 6 / Litolff, 79 pages, 3 spans. **The fix holds.**

`compose.py` unchanged, one shared read pass (2067 s), both arms off it. 288
staves on 28 FULL systems against two lineups **hand-read off the print**
(`out/crops/p020`, `p054`):

| arm | correct | wrong | unnamed |
|---|--:|--:|--:|
| spans-off / veto-off | 236 | 52 | 0 |
| spans-off / veto-on | 236 | 27 | **25** |
| **spans-on / veto-off** | **286** | **2** | 0 |
| spans-on / veto-on | **286** | **2** | 0 |

Impossible names **124 → 38**. Page 20 goes 8/10 → **10/10**.

⚠️ **The veto alone fixes nothing here** — it converts 25 wrong `Timpani` into
`unnamed` and leaves 25 violas named `Violin` standing. Spans fix both **by
naming**. That is the same shape the Beethoven 5 composition found: spans supply
the truth rather than merely refusing a falsehood.

⚠️ **The residual 2 wrong, and 34 of the 38 residual impossible, are ONE lexicon
collision and not a span fault.** Litolff abbreviates *Tromboni* as `Tb.`, and
`instruments.lookup("Tb.")` returns **Tuba at HIGH confidence** on a work with no
tuba — the same family as the documented `Tr.` = Trombe/Tromboni fix.
`instruments.py` was deliberately NOT touched: `Tb.` really is Tuba on other
editions, so this needs the 1422-label validation harness, not a one-liner.

Sub-finding: the "both sides established" guard swallows the Storm's own step
(13→14 at p54), so span 3 pools movements III+IV+V and three movement-III pages
carry Storm slots — cleaned up by the veto. **Spans and the veto compose, and
each does something the other cannot.**

## 4. Fourth work — Brahms 4 / Breitkopf. ⚠️ **The first document the fix cannot reach, and the AXIOM is why**

772 staves / 52 systems, three hand-read lineups: correct **550 → 556**, wrong
**222 → 216**, impossible **5 → 0**. Improvement, no regression, essentially flat.

Read off the print, movements III and IV **both print 16 staves with different
lineups**:

    III   Gr.Flöte Kl.Flöte Ob Kl Fag Kfag Hr Hr Trpt Pk Triangel + 5 strings
    IV    Fl Ob Kl Fag Kfag Hr Hr Trpt Pos Pos Pk        + 5 strings

`lineup_spans` keys on staff **COUNT**, so pages 41-98 are one span and pages 41
and 76 receive the byte-identical 16-name assignment. Movement IV's winds each
land one slot low (`Oboe`→`Piccolo`, `Clarinet`→`Oboe`, …) and its two trombone
staves come out `Trumpet` and `Timpani`: **~150 wrong names across 22 systems
that no span arrangement can reach.**

**A lineup SWAP at constant size is outside the axiom** — *"a page whose largest
system is larger than every page before it has proved the lineup GREW there."*
This is the first measured instance. (Ten of the counted "wrong" are
`Triangle → Percussion`, a granularity artefact, not a slide.)

## 5. What to do next, in order

1. **`Tb.` → Tuba.** Largest single residual on the third work. Needs the lexicon
   harness, not a one-liner.
2. **The constant-size swap.** Brahms 4 is reproducible with its truth committed
   here. Any fix needs a signal other than staff count — the margin labels on
   p41 and p67 disagree, and that is the signal.
3. ⚠️ **The early-boundary population is unrepresented.** Every measured work has
   its boundaries at pages 27-46, but the screen found four documents whose FIRST
   boundary is page 6, 9, 11 or 15 — Beethoven PC4, Saint-Saëns PC2, Bizet,
   Sibelius 2: a soloist-first concerto climbing to its tutti. That is the shape
   of the "run starts mid-movement" hazard and nothing has priced it.
   **Beethoven PC4 at 68 pages is the cheapest probe.**
4. Beethoven 9 (4 spans, ~190 pages ≈ 80 min read) is the only document with
   more than three.

⚠️ A correct/wrong table on any further work needs **hand-read lineups**; both
here came from committed margin crops.
