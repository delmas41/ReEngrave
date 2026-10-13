# omr-held-out-2026-10 -- do the 2026-10-11/12 rules generalise? (ROADMAP 2.101)

See also: FINDINGS-2.102.md (the 2.102 follow-up on the gaps this check found).

Diagnosis only, STAGED, no product code. Sean 2026-10-12: "Are the changes we are making
general enough to move score reading forward or are we just messing around with specifics for
these 2 scores?"

## Setup

Three orchestral scans, none Litolff or Breitkopf, 4 consecutive pages each from the movement's
first music page, `--weights auto`, through INFER, one gather at a time, Surya on:

| doc | edition | pdf pages | what it is |
|---|---|---|---|
| Dvorak 8 mvt 1 | Novello 1892 (Dover reprint) | 4-7 | dense tutti, bracketed horn pairs, 17 staves, clean thick print |
| Schumann 2 mvt 1 | Peters 1887 | 1-4 | engraved-plate scan, 14 staves, many chords and slurs |
| Tchaikovsky 4 mvt 1 | Jurgenson | 2-5 | thin, grey, worn plate; meter NOT read (336 bars unassessable in base AND arm) |

BASE = `2e286351` (detached worktree), ARM = `7eec1bd9` (this lane's tree), ARM2 = `f5f43143`
(main once 2.98 landed; 2.98 was not on main when the lane started). Records (not committed):
`library/_shared-records/held-out-2101/`. The arm also carries landings NOT under test (2.83 flag
tip, 2.12m, the 2.87 stem finder): stem-tip rows change a lot (Dvorak `stem_tip_ink` 825 -> 253
observations, 421 new `ambiguous` abstentions) and are attributed to no rule below. Probes in this
directory: `probe_reach.py`, `compare.py`, `cases.py`, `suspects.py`, `naming.py`, `heldlist.py`,
`arm2.sh`; tiles `make_tiles.py` + `pick.py` + `pick_298.py`.

## Page proxies, base -> arm

| | Dvorak 8 | Schumann 2 | Tchaikovsky 4 |
|---|---|---|---|
| notes reaching file / gathered | 149 -> 168 / 672 | 629 -> 677 / 1404 | 168 -> 165 / 439 |
| bars held out (do not add up) | 100 -> 94 | 106 -> 104 | 32 -> 32 |
| noteheads+rests in held bars | 301 -> 286 | 560 -> 579 | 60 -> 77 |
| rests written | 214 -> 222 | 140 -> 154 | 75 -> 83 |
| add-up control exact/short/overfull | 561/0/0, same | 378/0/0, same | 165/0/0, same (336 no meter) |
| staves held out / parts named | 0 / 17 of 17, same | 0 / 14 of 14, same | 0 / 15 of 62, same |
| accounting balanced | yes | yes | yes |

The overfull control is 0 by construction since 2.8 (held bars are never written), so it is not
evidence. What got worse: Tchaikovsky's held bars hold 17 more events (bar count unchanged, 1 bar
swapped; the extra events are rests newly read inside bars that still do not add up); Schumann
holds 19 more noteheads (37 chords refused by 2.89, by design); Dvorak lost 2 halves base had
decided.

## Per rule: reach and what it decided

"Eye" is my reading of the tiles, NOT evidence (rule 7); Sean's answers decide.

| rule | Dvorak | Schumann | Tchaikovsky |
|---|---|---|---|
| 2.80 missed-rest witness | 561 cells witnessed; reconcile decisions 6 -> 3 | 378; 18 -> 14 | 501; 1 -> 0 |
| 2.80b narrow box = 8th rest | 105 narrow boxes, 0 true, 9 false, 89 no ink | 37, 0 true, 13 false | 209, 0 true, 24 false |
| 2.81 ph2 bare stem by the bar | 18 (15 q, 3 e) | 117 (105 q, 12 e) | 0 of 46 with evidence (no meter) |
| 2.88 hollow half from head | 2 tip-unread (both already half in base), 1 other; 2 base halves now narrowed | 1 new | 0 |
| 2.89 disagreeing chord refused | 14 notes | 37 | 2 |
| 2.90 two voices at one x | two-voice bars 0 -> 1 | 0 -> 1 (held by sum 4 -> 11) | 1 -> 2 |
| 2.93/2.94/2.95 naming | 0 (identical names, no shared_word, no worn recovery, no condensed block) | 0 | 0 |
| 2.98 lone whole rest = bar (ARM2) | 187 bars written as bar-length rest (measure rests 45 -> 232) | 0 | 1 |
| 2.99 rests from unboxed ink | 11 decided (8 e, 3 q), 2 stroke refusals, 47 abstain | 0 | 24 decided (22 e, 2 q), 4 stroke/thin refusals, 124 abstain |

Schumann holds no unboxed rest ink (287 of 288 unboxed rows are ink the detector already named):
2.99 is inert there for want of a population, not a threshold. 2.93-2.95 fix Litolff/Brahms-
specific failures (mis-classed viola clef under a condensed block; worn `Ob.`; crook-only horn
pair); none of these printings presents one, so the held-out set shows they are quiet (0 names
changed, 0 harm), not that they generalise.

## The named suspects

* 2.99's 45% stroke cut (`THIN_STROKE_MAX_COLUMN_SHARE`). Decided eighth rests' max column share:
  Dvorak 0.71-0.83 (Litolff about 0.75); Tchaikovsky 0.47-0.67, median 0.62, one at 0.47, two
  hundredths above the cut. On a thin worn plate real rests live at the cut; a slightly thinner
  scan loses them. A risk, not a present error (the one thin refusal, 0.41, was 1.1 x 1.25 spaces,
  not rest-shaped anyway).
* 2.99 / 2.80b shape windows: Tchaikovsky abstains on 124 `shape_cannot_tell`, 44 of them
  rest-sized (width 1.0-1.6, height 1.5-3.5) -- where missed rests would hide; only one tile
  looked. Dvorak: 9 of 47. Tchaikovsky eighths (height 1.8-2.2) sit inside the 1.5-2.5 window.
* 2.80b: 0 true decisions on 3 scores, most boxes have no measurable ink: quiet, no evidence of
  help outside Brahms.
* 2.88 raw-centre cut: no held-out half on the unread-tip path that base lacked; it cost 2 base
  halves in Dvorak (cell `4/0/13/1`).

## Print check

`out/print/2.101-review/`: 17 tiles (phone width, subject in blue corners, bar in red, staff
drawn), readings only in `manifest.json`, `answers.template.json` to fill. Frame control (staff
lines fitted locally at the subject): all 17 pass, and the same lines shifted half a space fail on
all 17. Eye-check: eighth rests, quarter rests, the flat refused as a stroke, the halves and the
whole-bar rests look right; Tchaikovsky tile with three similar quarter-rest-like marks is the
one to watch. Sean's answers are the evidence.

## Sean's 17 tile answers (2026-10-12)

Verbatim: *"1. 4 rest 2. 8 rest 3. 1 rest 4. 8 rest 5. Flat acc 6. 4 (part of a tuplet: 3 quarters) 7. 4 8. 4 rest 9. 1 rest 10.4 11. c for common time meter 12. 4 rest 13. C meter 14. 8 rest 15. 4 rest 16. 8 rest 17. Trem slashes"*. Per tile in `out/print/2.101-review/answers.json` (scored against `manifest.json`, which agrees with the scoring below).

| rule (decider) | tiles | result |
|---|---|---|
| 2.99 rests from unboxed ink (`adjudicate_unboxed_ink_is_a_rest`) | 2, 4, 14, 16 eighth; 12, 15 quarter | 6 of 6 decided right |
| 2.99 refusal (`stem_stroke_not_a_rest`) | 5 | right (a flat) |
| 2.99 abstained (`shape_cannot_tell`) | 1, 8 | misses, not wrong: both real quarter rests |
| 2.98 whole-bar rest | 3, 9 | 2 of 2 right |
| 2.81 bare stem by the bar (`infer:collapse_bare_stem_by_bar`) | 7 right; **6, 10 WRONG** | decided eighth where Sean reads a quarter (6 sits in a 3-quarter tuplet, so the bar's arithmetic is not the plain meter's) |
| 2.88 hollow-head half (`adjudicate_duration`, reason `hollow_head_bare_stem`) | **11 WRONG** (arm = base, decided half; it is the C common-time meter sign); **17 WRONG** (arm decided half, base decided quarter via `head_and_marks`; it is tremolo slashes); 13 arm right (C meter, arm narrowed via `head_fill_from_ink` where base decided half) | the class mistakes non-notes for hollow heads |

Reading: the rest rules (2.98, 2.99) generalise to other publishers; 2.81 and the hollow-head rule do not yet. 2.81 settles a length by the bar without knowing about tuplets; the hollow-head rule is fed meter signs and tremolo slashes. Tile 17 is a regression the arm introduced (base was also wrong, as a quarter). Tile 11 is wrong in base too. Not fixed here (diagnosis lane, no `tools/` change).
