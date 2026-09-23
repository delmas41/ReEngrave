# Two OCR repairs to the lexicon — and one of them was removing a SINGER

**2026-09-22.** Sean: *"do the ocr folds."* Scoped in
`benchmarks/omr-instrument-channels-2026-09/FINDINGS.md` §15, where opening the
Breitkopf plate showed that three staves our reader could not name are labelled
in full on the page and were lost to OCR damage.

---

## 1. ⚠️⚠️ THE FIRST ONE IS NOT A MISS, IT IS A MISREAD

Breitkopf Brahms 1 prints **`Flöten`**. Tesseract returned **`Flo6ten 2`** —
the umlaut broken into a letter and a digit. `Flöten` resolves to **Flute at
coverage 1.00**; `Flo6ten 2` resolved to **Tenor — a SINGER**.

The mechanism is not the fold. `instruments._search` bounds an alias with
**LETTER lookarounds**, so a digit inside a word reads as a word boundary on
both sides: `ten` inside `flo6ten` matched **word-bounded, on the EXACT pass,
before any fold ran**. The only thing that kept a singer off a printed flute
staff of a Brahms symphony was `work_roster`'s family veto — and **a work whose
roster we do not hold has no veto.** It is `Tr. Alt.` → *Alto* arriving from a
different cause.

⚠️ That is why the repair is in `normalize_label` and **not** in `_fold_ocr`. A
fold-side repair runs only after the exact pass has failed, and here the exact
pass is where the damage happens.

## 2. THE TWO RULES, AND WHY EACH IS SAFE

**a. A digit BETWEEN two letters is noise.** Admitted on the rarity argument
`_OCR_FOLD` states, and here the rarity is **total: not one of the 842 aliases
contains a digit**, so the rule can never merge two names and is provably a
no-op on the alias side. A part number IS a digit a label carries, and it is a
SEPARATE TOKEN which `_STRIP_TOKENS` already removes.

⚠️⚠️ **`0` AND `1` ARE EXEMPT, AND THE EXEMPTION IS DERIVED FROM `_OCR_FOLD`
RATHER THAN WRITTEN OUT.** Those are exactly the digits the fold already claims
as letter confusions (`0 → o`, `1 → i`), and stripping them would destroy the
recovery that claim buys: `Vio1ino` folds to `vioiino` and matches `violino`
folded, but stripped first it is `vioino` and matches nothing. Deriving it means
adding a digit to the fold removes it from here in the same edit.

**b. An alias carrying `ß` also gets its `b`-spelled form.** Breitkopf prints
`Kontrabaß`; Tesseract returned `KontrabaB`, which resolved to nothing.

⚠️⚠️ **A CHARACTER FOLD `B → ß` IS REFUSED AND THE REASON IS IN THIS FILE'S OWN
HISTORY.** A bare `B` is a KEY in this vocabulary — German `B` is B-flat, and
`Cl. B.` is a clarinet in B-flat, a trap `instruments.py` already records — so a
fold would reach every label carrying a key. Generating the `b`-spelled form of
an alias that ALREADY carries `ß` can only add a spelling of a word the lexicon
holds. **Exactly two of the 842 aliases qualify** (`kontrabaß`, `kontrabaßs`),
both Contrabass, so the derived set is two strings. It is the `_CONTRA_ALIASES`
cross-product pattern rather than a hand list, so a future `ß` alias gets its
variant without anyone remembering.

## 3. THE FALSE-POSITIVE SURFACE, PRICED ON BOTH COMMITTED CORPORA

`probe_corpus.py` resolves every string in both corpora against `origin/main`
and against the tree, and prints every difference — a recovery and a regression
look identical until you name which is which.

| corpus | distinct strings | resolved before | after | GAINED | **LOST** | **CHANGED** |
|---|--:|--:|--:|--:|--:|--:|
| `labels.json` (real margin labels) | 448 | 297 | 297 | 0 | **0** | **0** |
| `part-names.json` (reference encodings) | 1271 | 878 | 878 | 0 | **0** | **0** |

**Nothing is lost and nothing changes instrument** over 1,719 distinct strings.
⚠️ `part-names.json` is in there precisely because the margin lexicon is NOT
meant to match it: it is the surface on which `Vier Flöten` → **Piano** and
`Soprano Saxophone` → **Alto** were caught.

### 3a. ⚠️⚠️ AND THE GAINED ZERO IS A FACT ABOUT THE CORPORA, NOT THE REPAIRS

Both committed corpora **predate these gathers and contain none of the strings
this change fixes**. So a 0/0/0 here could equally be a probe that is not
running, which this repo treats as a suspect rather than a result.

**`probe_control.py` is the positive control**: it injects the `c/e` fold that
`instruments.py` **refuses by name** and requires the same comparison to move.
It moves — on exactly one string, and the string is **`Veelle.`**, which is
what CLAUDE.md's own history names as the price of that refusal. The instrument
reproduces a documented result it was not built to find, so its zero is a
result.

## 4. THE GAIN, ON THE READS THAT MOTIVATED IT

`margin-reads-2026-09-22.json` — **every** margin label the two shared staged
records hold, verbatim, committed here because the older corpora do not contain
them. 64 distinct strings:

| | |
|---|---|
| resolved before → after | **52 → 53** |
| GAINED | `'\| KontrabaB'` → **Contrabass** |
| **CHANGED** | `'Flo6ten 2'` → **Tenor (voice) → Flute (woodwind)** — CROSS-FAMILY |
| LOST | **0** |

The one cross-family change is the singer being removed. ⚠️ `resolved_at_capture`
in that file is what the LEXICON said, **not** what the plate prints; the print
truth for these three labels is hand-read and its crop is committed at
`benchmarks/omr-instrument-channels-2026-09/out/print/brahms-system-head.png`.

## 5. CONTROLS

- both corpora, both directions, against `origin/main` — **0 lost, 0 changed**;
- a **positive control** that injects a refused widening and requires movement;
- **9 unit tests**, including that no alias carries a digit and that every
  `ß` alias has its variant — the rarity arguments asserted, not remembered;
- **mutation battery: 6 RED, 0 survived, 0 bad anchors, restore hash-verified.**
  ⚠️ Its first run had **one survivor and it was a real gap**: the part-number
  test used only EXEMPT digits (`1`, `2`) and digits standing before a space, so
  a rule that stripped any digit merely FOLLOWED by a letter passed it. Closed
  with `3Flauti` and `Fag2`, which can see it.

## 6. WHAT IS NOT ESTABLISHED

- ⚠️ **`c → e` IS NOT PROPOSED AND WAS NOT TOUCHED.** It is the largest
  remaining population here — **five staves** reading `Vel.` for `Vcl.` on
  Breitkopf — and `instruments.py` refuses it by name as a common-letter pair,
  priced at `Fug.`→`Fag.`, `Oh.`→`Ob.` and `Veelle.`. Re-litigating it needs a
  corpus argument, not this page.
- **The gain is two staves**, on one document, one publisher. Neither changes
  the FILE: both slots are already named from other systems (see
  `omr-instrument-channels-2026-09` ADDENDUM 2), so the value is that a wrong
  READING stops being produced — and one of them was a singer.
- **No page was re-gathered**, no export was run, and **no OMR-NED figure is
  claimed** — musicdiff does not score `<part-name>`.
- The remaining refused labels on that record are noise (`|`, `2`, `of`,
  `(Es)`, `| | ©`) or the genuinely truncated horn labels, and nothing in the
  lexicon reaches them.

```bash
python3 probe_corpus.py            # both corpora, before vs after
python3 probe_control.py           # the positive control for its zero
python3 mutate.py                  # 6 RED, 0 survived
```
