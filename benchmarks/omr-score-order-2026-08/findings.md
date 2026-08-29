# The instrument lexicon, measured against real engravers' part lists

**Date:** 2026-08-29
**Verdict:** lexicon coverage **93% → 99%** of 2,345 real part names; symphonic
works in score order **74 → 89** of 105. Score order is confirmed as a
convention strong enough to resolve labels by, and Baroque confirmed as a
genuinely different layout.

```bash
python3 benchmarks/omr-score-order-2026-08/score_the_lexicon.py
python3 benchmarks/omr-score-order-2026-08/score_the_lexicon.py --misses
```

---

## A better ruler than scanned pages

`instruments.lookup` was checked against hand-written cases and whatever labels
a few scanned pages happened to yield — which is how `Tp.` came to be decided
by one Beethoven page.

The Gradus MusicXML library (`gradus-vercel/public/scores`, 507 works) is a
better ruler. `<part-list>` is what an engraver wrote, in the order they wrote
it, with no OCR in between: **111 orchestral works, 2,345 part names**, from
Mozart 40 and 41 through Beethoven 1-9, Brahms 1-4, Dvořák 9, Tchaikovsky
4/6/1812, Bruckner 5, Mahler 5, Holst's *Planets*, Ravel and Boulanger.

## Score order is a real constraint, and it is a better test than coverage

Two numbers, answering different questions. **Resolved** is what fraction of
real part names the lexicon can read at all. **Monotone** is how many works come
out in score order — woodwind, brass, percussion, harp and keyboards, strings.

The second is the sharper test, because a misread label usually still *reads*.
`Basso` resolves cleanly and resolves WRONG, and only the order shows it.

Measured before this round: 93% resolved, and 74 of 111 works monotone. Every
one of the 24 symphonic violations was traced by hand, and **not one was real
layout variation.** They were all the lexicon:

| what broke | reading | cost |
|---|---|---|
| `Basso`, `Bässe.` | "Bass voice" — it is the contrabass at the foot of the strings | 8 works |
| `Tenor Tuba in B♭` | "Tenor" (voice) — the word *Tuba* is in the label and loses, because the alias index is longest-first | all 8 Holst movements |
| `Violoncellos`, `Contrabasses`, `Violen`, `Hoboen`, `Contrafagotte` | unread — English and German plurals | 40 names |
| `Cymbal`, `Glockenspiel`, `Xylophone`, `Tam-tam`, `Tubular Bells`, `Tambourine` | unread — common percussion | 53 names |
| `Violone`, `Kontrabaß`, `Celesta`, `Mezzo`, bare `Bass` | unread | 40 names |

## What changed

Aliases for everything in the table above, and — the part that matters —
`Basso` / `Bässe` / `Bass` added to `AMBIGUOUS_ALIASES` rather than assigned.

That last distinction is the point. These are not names the lexicon was reading
wrongly; they are names **no lexicon can read alone**. `Basso` under a cello is
a contrabass and under a tenor is a bass voice, and the word is identical. The
existing machinery already knows what to do with that — `AMBIGUOUS_ALIASES`
offers the readings and `score_layouts.resolve_ambiguous_label` picks the one a
fitted layout proposes — so the fix is to feed that mechanism, not to pick a
winner.

`Tenor Tuba` is the opposite case and got the opposite fix: it is not ambiguous
at all, it was simply losing to a longer alias, so it becomes an alias of Tuba.

## What it is worth

|  | before | after |
|---|---:|---:|
| part names resolved | 2185/2345 (93%) | **2321/2345 (99%)** |
| symphonic works in score order — lexicon alone | 74/105 | 81/105 |
| — with ambiguity settled by position | — | **89/105** |

The last row is what the score-order prior buys: eight works where the lexicon
offers two readings and only position separates them.

## Baroque is a different layout, and that is not a bug

**0 of 6** Brandenburg movements are monotone, correctly. The continuo
harpsichord comes *last*, after the strings, and Brandenburg 4 puts the
soloist *first*, above the flutes. This is why the score-order prior needs a
library of layouts rather than one canonical order, and why the benchmark
reports Baroque separately instead of counting it as failure.

## Still unread, and deliberately

`Continuo` (8 names) is Baroque and names a function rather than an
instrument — a keyboard and a bass string instrument together. It wants the
Baroque layout, not an alias.

## The remaining 16

Sixteen symphonic works are still non-monotone with position-aware resolution,
and they are mostly Holst, whose percussion battery and two harps sit in an
order the family ranking does not capture. Worth a look, but the return is much
smaller than the 8 above and the cause is the rank table rather than the
lexicon.
