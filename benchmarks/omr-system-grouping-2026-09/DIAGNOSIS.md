# Diagnosis — where system grouping actually fails (2026-09-01)

From the full-library sweep (`sweep.jsonl`, 964 ok pages / 235 editions) + a
quantitative stratification (`scratchpad/diagnose.py`) + visual confirmation.
**Partly adjudicated**: fragmentation fingerprints are a PROXY for over-splitting,
now confirmed by eye on TWO independent cases across different works/publishers/eras:
Bruckner *Te Deum* p13 (Eulenburg pocket, choral) `[1,1,1,5,1,7,1,1,1,2]`, and
Mozart *Don Giovanni* p534 (Breitkopf 1801, opera recitative) `[2,3,1,1,1,1,1]` —
the bottom 5-staff system split into 5 lone staves, the top block split at the
D. Elvira vocal staff. Same mechanism both times: vocal staff + sparse page →
the thin systemic barline is the only connector and the scan doesn't preserve
it. Remaining crops are in `crops/` for fuller adjudication.

## Headline: failures do NOT stratify by publisher. They stratify by SCORE TYPE.

Sean's hypothesis was "the rules change by publisher." The data says the failure
axis is **vocal/choral vs instrumental**, not publisher.

**Vocal vs instrumental fragmentation fingerprints** (share of pages):

| bucket | pages | frag% | any size-1 sys | run ≥3 size-1 | size-1 next to big |
|---|--:|--:|--:|--:|--:|
| instrumental | 844 | 4.3% | 1.5% | **0.0%** | 0.9% |
| vocal | 120 | 9.2% | 6.7% | **2.5%** | 2.5% |

The catastrophic signature (a *run* of ≥3 lone-staff "systems") is **0.0% on
instrumental pages, 2.5% on vocal pages**. Every worst-fragmentation page is
vocal (Bruckner Te Deum, Mozart Don Giovanni/Figaro/Zauberflöte) — except two
"manuscript" Berlioz pages (handwritten, a different problem; that edition was
also pulled from the corpus mid-sweep) and one pedagogical bass-exercise (Vidal
178 Basses).

**Publisher stratification (instrumental pages only, ≥8 pages):** essentially
**every publisher is 0.0% fragmentation** — Breitkopf, Litolff, Eulenburg,
Peters, Simrock, Jurgenson, Durand, Bärenreiter all clean. The only nonzero
rows are `unknown-edition` (a 4-work catch-all bucket, 50% — not a real
publisher) and `breitkopf-und-hartel` at 4% (2 of 50 pages, both vocal works
mis-bucketed: Mendelssohn *Hebrides* opening + a Handel item). **There is no
publisher signal in instrumental grouping.**

## Why vocal music breaks (mechanism, confirmed)

Confirmed visually on Bruckner *Te Deum* p13 (`crops/...te-deum...p013-overlay.png`):
a chorus+orchestra tutti that should be 2 systems is split into `[1,1,1,5,1,7,
1,1,1,2]`. Two conventions stack, exactly as the research predicted:

1. **Vocal staves are never joined by barlines** (Trap 2, publisher-conventions.md
   §Traps) — an engraving rule in every source. So the S/A/T/B gaps carry *no*
   bridging ink, and the connectivity rule (break where bridging==0) shatters
   them into lone staves.
2. **It's a pocket score** (Eulenburg, staff-space small) — so even the
   orchestra family boundaries are bridged only by the ~2px systemic barline,
   which degrades on the small scan. Pocket + choral stacks both traps.

This is **over-SPLITTING**, and it is invisible to no metric — it produces the
lone-staff fragments the sweep flagged.

## The other failure direction: over-MERGES (instrumental, rarer)

The fragmentation metric only catches over-SPLITS. The 3 known GT failures
(B9 p25, B9 p60, B5 p40 — all Litolff instrumental) are over-MERGES: stray ink
(a measure number, restarted instrument labels) fakes a bridge across a real
system boundary, so two systems merge into one. These produce FEWER, BIGGER
systems (no fragmentation) and don't show in the table above. They are rarer
(3/23 on GT) but real, and the constructive rebuild must not reintroduce them.

**So the two directions have distinct homes:**
- over-SPLIT ← vocal/choral gaps (+ thin pocket-score systemic barlines). The big prize.
- over-MERGE ← stray ink on dense instrumental pages. The 3 known cases.

## Scan-quality is the real "publisher" effect (second-order, confirmed)

Beethoven 5 p57, **same 1870 Litolff plate, two different scans**: one reads
`[17]` (one system), the other `[9,15]` (two). Same engraving, opposite grouping
— driven purely by which scan preserved the thin bridging ink. This is the
"publisher enters via scan quality" prediction, confirmed. (Brahms 1 and Mozart
41 scan-pairs show only size wobble, not count splits.)

## The K.183 cross-publisher pair is NOT a grouping difference

Bärenreiter reads `[8,8,8]` (24 staves), Breitkopf `[7,7,7]` (21 staves) — but
**both group cleanly into 3 consistent systems**. The difference is *staff count*
(a real edition/detection difference upstream), not a grouping-rule difference.
Further evidence that the grouping rule itself doesn't vary by publisher.

## Grouping matters on ~half the corpus

Of 844 instrumental pages, 48% are single dense systems (grouping trivial) and
**52% are multi-system (grouping is load-bearing)**. So this is not a rare
concern — but on those instrumental multi-system pages the current rule is
already near-clean.

## Implications for the fix (re-prioritized)

1. **Instrumental orchestral grouping mostly works already** (over-splits ~0%);
   the residual there is the rarer stray-ink over-merge. If Sean's throughput is
   mostly symphonies, grouping is largely fine today except those.
2. **The big prize is vocal/choral/opera scores.** And there, barline detection
   *cannot* help at vocal gaps — the ink is absent by convention. The fix MUST
   lean on non-barline positive evidence: the **header-column cross-check**
   (clefs/labels aligned across the system's staves) and **bracket structure**,
   which is exactly the Audiveris-shaped constructive approach already planned.
   A "vocal staves belong to the system bracketed around them" rule is needed.
3. **Scan quality, not publisher, is the modifier** — so the constructive rule
   must be robust to a 2px systemic barline (back it with brackets + header
   column), and a dossier-supplied structure is the safety net when the image
   simply lacks the ink.
4. **Adjudicate the crops** to confirm the proxy before building — but the
   direction is already clear and visually confirmed on the decisive case.

## The cheap fix was tested and ruled out (x_start audit, `xstart-audit/`)

The conventions memo's "single most actionable finding" — that the gap scan
might drop the ~2px systemic barline via an `x_start` off-by-one — was tested
with a controlled LilyPond experiment and **refuted**. `_robust_x_window`
already puts the window's left edge at `median(x_start) − 4·spacing` (4
staff-spaces LEFT of the staff edge), so the systemic barline is comfortably
inside; a 1px barline column at the worst resolution is still counted; measured
headroom ≈5.4 staff-spaces vs ~2–3 sp of real x_start spread. **No window fix is
warranted.**

This is important: it proves the vocal/pocket over-splits are **not** a coding
slip — they are the genuine mechanism (a thin systemic barline that the scan
degrades into a broken column, and/or vocal gaps + far-left bracket spines the
in-window barline scan legitimately can't see). The audit flags the one
remaining structural gap precisely: **a gap bridged only by ink >4sp left of
x_start (a bracket/brace spine) with nothing in-window is a bracket-DETECTION
problem, not a window tweak.** That is exactly the Audiveris-style bracket read
the fix plan already calls for. Both the diagnosis and the audit converge on the
same conclusion: there is no shortcut; the fix is the constructive rebuild with
**bracket detection + header-column positive evidence** as redundant cues, so
grouping no longer depends on a fragile 2px line surviving the scan.
