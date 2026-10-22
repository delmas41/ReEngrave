# Symbol dossiers — what sets each mark apart, and where the pipeline decides it

**2026-09-20, Sean's brief.** One file per FAMILY, one section per SYMBOL. This
is research, not repair: **no fixes, no test batteries, no long runs.** A tiny
probe on a few measures is allowed only where a claim cannot be settled from the
tree, and the dossier must say when one was used.

Why per symbol and not per family (Sean): *"I am not sure families is detailed
enough. I think we need per symbol information."* Why conceptual first: the
convention registry (`docs/engraving-conventions.md`, 114 entries, 94 reaching
no decision) will carry much of the wiring, *"but will most likely not cover
every symbol, and these questions may shape how we implement and refine the
conventions."* The two are the same job from two ends; the answers may differ,
and where they differ that is the finding.

## The five questions — Sean's wording

1. **What fact OR facts set this mark apart from what it may be confused with?**
   (And: what CAN it be confused with?)
2. **Is YOLO, classical CV, or some other method best for determining what this is?**
3. **Where on the page is the important information found** to help determine
   what this is? (There may be several things, contextually.)
4. **How does each stage handle this mark** — where are decisions made, and
   where is other information gathered?
5. **Can we say "I don't know" or "best guess"?** And: how does the certainty of
   this mark affect how we read other things?

## The template — copy for every symbol

```
## <symbol name as the class space or the CV reader names it>

What it is on the page, in one sentence. Which classes / readers produce it.

### 1. What sets it apart — and what it is confused with
### 2. Best method: YOLO / CV / other
### 3. Where on the page the deciding information lives
### 4. Stage by stage — GATHER / ADJUDICATE / EVALUATE / INFER / EXPORT
### 5. Abstain or best-guess — and what leans on this mark's certainty

**Evidence grade:** for every claim, MEASURED HERE (file + figure + n) /
LITERATURE (citation) / ASSERTED (nobody has measured it). A registry handle
(`[C..]`) where one exists.
```

## Rules every dossier follows

* **The tree outranks any document, including CLAUDE.md.** Q4 is answered by
  reading `tools/omr/staged/` (`gather.py`, `adjudicate.py`,
  `adjudicators/`, `consequences.py`, `evaluate.py`, `infer.py`, `export.py`)
  and grepping for the quantity — not from memory and not from prose. A family
  with NO quantity or NO decision is a finding, stated plainly.
* **Never invent a number.** Every figure carries its file path and its n.
  Where nothing is measured, write ASSERTED and move on.
* **"Confused with" is concrete**: name the other symbol or the non-symbol ink
  (a barline fragment, a neighbouring staff's note through the cell padding,
  bleed), and where the repo has already measured that confusion, cite it.
* **Q5 has two halves and both are required**: (a) can the current decision
  abstain, and does it; (b) which OTHER marks' readings depend on this one, and
  does this mark's reader fail on the same pages as theirs (the independence
  check — *the bars are not an independent umpire over a bad reading*).
* **Written for Sean to read.** Plain, short, no walls of warning glyphs. He is
  the domain expert; the music is not what needs explaining.
* End each file with **"What we do not know"** and **"Questions for Sean"**.
