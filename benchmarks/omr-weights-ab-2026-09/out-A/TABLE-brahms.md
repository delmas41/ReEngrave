# Weights A/B — production-brahms vs candidate-brahms

Family: `rest`. Pages: `1-4`. Weights differ; pipeline, pdf and pages are identical.

## 1. GATHER — boxes by class

| class | production-brahms | candidate-brahms | delta |
|---|--:|--:|--:|
| rest16th | 4 | 5 | +1 |
| rest32nd | 0 | 1 | +1 |
| rest64th | 1 | 1 | +0 |
| rest8th | 575 | 559 | -16 |
| restHBar | 3 | 92 | +89 |
| restHalf | 8 | 13 | +5 |
| restQuarter | 328 | 342 | +14 |
| restWhole | 480 | 485 | +5 |

**Total boxes gathered:** production-brahms 1399, candidate-brahms 1498 (delta +99)

## 2. ADJUDICATE — per quantity, verdicts and refusals

### `duration`

| outcome/value/reason | a | b | delta |
|---|--:|--:|--:|
| ['abstained', None, 'rest_stands_where_no_rest_hangs'] | 80 | 85 | +5 |
| ['abstained', None, 'unreadable_rest'] | 3 | 92 | +89 |
| ['decided', (('beam_levels', 0), ('beats', 0.0625), ('dots', 0), ('is_rest', True), ('written', 0.0625)), 'rest_class'] | 1 | 1 | +0 |
| ['decided', (('beam_levels', 0), ('beats', 0.125), ('dots', 0), ('is_rest', True), ('written', 0.125)), 'rest_class'] | 0 | 1 | +1 |
| ['decided', (('beam_levels', 0), ('beats', 0.25), ('dots', 0), ('is_rest', True), ('written', 0.25)), 'rest_class'] | 4 | 5 | +1 |
| ['decided', (('beam_levels', 0), ('beats', 0.5), ('dots', 0), ('is_rest', True), ('written', 0.5)), 'rest_class'] | 575 | 559 | -16 |
| ['decided', (('beam_levels', 0), ('beats', 1.0), ('dots', 0), ('is_rest', True), ('written', 1.0)), 'rest_class'] | 328 | 342 | +14 |
| ['decided', (('beam_levels', 0), ('beats', 2.0), ('dots', 0), ('is_rest', True), ('written', 2.0)), 'rest_class'] | 7 | 10 | +3 |
| ['decided', (('beam_levels', 0), ('beats', 3.0), ('dots', 1), ('is_rest', True), ('written', 3.0)), 'rest_class'] | 0 | 1 | +1 |
| ['decided', (('beam_levels', 0), ('beats', 4.0), ('dots', 0), ('is_rest', True), ('written', 4.0)), 'rest_class'] | 400 | 401 | +1 |
| ['decided', (('beam_levels', 0), ('beats', 6.0), ('dots', 1), ('is_rest', True), ('written', 6.0)), 'rest_class'] | 1 | 1 | +0 |

### `glyph_owner`

| outcome/value/reason | a | b | delta |
|---|--:|--:|--:|
| ['decided', 'staff/1/0/0', 'distance'] | 1 | 2 | +1 |
| ['decided', 'staff/1/0/1', 'distance'] | 1 | 2 | +1 |
| ['decided', 'staff/1/0/1', 'hairpin_separates'] | 5 | 3 | -2 |
| ['decided', 'staff/1/0/3', 'distance'] | 6 | 7 | +1 |
| ['decided', 'staff/1/0/3', 'hairpin_separates'] | 0 | 2 | +2 |
| ['decided', 'staff/1/0/8', 'distance'] | 12 | 13 | +1 |
| ['decided', 'staff/1/1/0', 'distance'] | 2 | 2 | +0 |
| ['decided', 'staff/1/1/1', 'distance'] | 0 | 2 | +2 |
| ['decided', 'staff/1/1/5', 'distance'] | 11 | 10 | -1 |
| ['decided', 'staff/1/1/6', 'distance'] | 8 | 9 | +1 |
| ['decided', 'staff/2/0/4', 'distance'] | 6 | 5 | -1 |
| ['decided', 'staff/2/1/13', 'distance'] | 8 | 8 | +0 |
| ['decided', 'staff/2/1/4', 'distance'] | 11 | 9 | -2 |
| ['decided', 'staff/2/1/7', 'distance'] | 22 | 19 | -3 |
| ['decided', 'staff/3/0/5', 'distance'] | 2 | 3 | +1 |
| ['decided', 'staff/3/0/7', 'distance'] | 11 | 11 | +0 |
| ['decided', 'staff/3/1/3', 'distance'] | 2 | 2 | +0 |
| ['decided', 'staff/3/1/7', 'distance'] | 18 | 21 | +3 |
| ['decided', 'staff/3/1/8', 'distance'] | 12 | 8 | -4 |
| ['decided', 'staff/4/0/6', 'distance'] | 4 | 4 | +0 |
| ['decided', 'staff/4/1/4', 'distance'] | 4 | 2 | -2 |
| ['decided', 'staff/4/1/7', 'distance'] | 4 | 5 | +1 |

### `rest_is_not_a_rest`

| outcome/value/reason | a | b | delta |
|---|--:|--:|--:|
| ['decided', False, 'rest'] | 859 | 902 | +43 |
| ['decided', True, 'rest_clipped_by_crop'] | 145 | 142 | -3 |
| ['decided', True, 'rest_has_a_stem'] | 190 | 215 | +25 |
| ['decided', True, 'rest_is_a_duplicate_box'] | 138 | 160 | +22 |
| ['decided', True, 'rest_off_center'] | 22 | 23 | +1 |
| ['decided', True, 'rest_outside_its_staff'] | 41 | 49 | +8 |
| ['decided', True, 'rest_overlaps_a_notehead'] | 1 | 2 | +1 |
| ['decided', True, 'rest_touches_two_staff_lines'] | 3 | 5 | +2 |

## 3. Sean's rest-queue verdicts vs each record's surviving rests

### production-brahms
cells with a Sean verdict AND a record rest reading: 20 (class, cell) rows — surviving 28, Sean TP 33, best-case matched (min per cell/class) 26

| cell | class | record surviving | Sean TP | Sean FP | Sean unsure |
|---|---|--:|--:|--:|--:|
| cell/1/0/0/1 | restQuarter | 0 | 1 | 1 | 0 |
| cell/1/0/0/1 | rest8th | 3 | 3 | 0 | 0 |
| cell/1/0/1/1 | restQuarter | 0 | 2 | 1 | 0 |
| cell/1/0/1/1 | rest8th | 3 | 3 | 0 | 0 |
| cell/1/0/1/5 | rest8th | 1 | 1 | 0 | 0 |
| cell/1/0/2/2 | rest8th | 1 | 1 | 1 | 0 |
| cell/1/0/2/5 | rest8th | 1 | 4 | 0 | 0 |
| cell/1/0/9/5 | rest8th | 2 | 2 | 0 | 0 |
| cell/2/0/1/0 | restWhole | 1 | 1 | 0 | 0 |
| cell/2/0/13/1 | restWhole | 1 | 1 | 0 | 0 |
| cell/2/0/3/3 | restQuarter | 1 | 0 | 1 | 0 |
| cell/2/0/8/3 | restQuarter | 1 | 0 | 1 | 0 |
| cell/3/0/1/0 | restQuarter | 0 | 0 | 1 | 0 |
| cell/3/0/1/0 | rest8th | 2 | 2 | 0 | 0 |
| cell/3/0/12/2 | restQuarter | 1 | 1 | 0 | 0 |
| cell/3/0/12/2 | rest8th | 2 | 3 | 0 | 0 |
| cell/3/0/13/3 | restQuarter | 1 | 1 | 1 | 0 |
| cell/3/0/13/3 | rest8th | 3 | 3 | 0 | 0 |
| cell/3/0/2/0 | rest8th | 2 | 2 | 0 | 0 |
| cell/3/0/3/8 | rest8th | 2 | 2 | 0 | 0 |

### candidate-brahms
cells with a Sean verdict AND a record rest reading: 19 (class, cell) rows — surviving 27, Sean TP 29, best-case matched (min per cell/class) 24

| cell | class | record surviving | Sean TP | Sean FP | Sean unsure |
|---|---|--:|--:|--:|--:|
| cell/1/0/0/1 | restQuarter | 0 | 1 | 1 | 0 |
| cell/1/0/0/1 | rest8th | 3 | 3 | 0 | 0 |
| cell/1/0/1/1 | restQuarter | 1 | 2 | 1 | 0 |
| cell/1/0/1/1 | rest8th | 3 | 3 | 0 | 0 |
| cell/1/0/1/5 | rest8th | 1 | 1 | 0 | 0 |
| cell/1/0/2/2 | rest8th | 1 | 1 | 1 | 0 |
| cell/1/0/9/5 | rest8th | 2 | 2 | 0 | 0 |
| cell/2/0/1/0 | restWhole | 1 | 1 | 0 | 0 |
| cell/2/0/13/1 | restWhole | 1 | 1 | 0 | 0 |
| cell/2/0/3/3 | restQuarter | 1 | 0 | 1 | 0 |
| cell/2/0/8/3 | restQuarter | 1 | 0 | 1 | 0 |
| cell/3/0/1/0 | restQuarter | 1 | 0 | 1 | 0 |
| cell/3/0/1/0 | rest8th | 2 | 2 | 0 | 0 |
| cell/3/0/12/2 | restQuarter | 1 | 1 | 0 | 0 |
| cell/3/0/12/2 | rest8th | 2 | 3 | 0 | 0 |
| cell/3/0/13/3 | restQuarter | 0 | 1 | 1 | 0 |
| cell/3/0/13/3 | rest8th | 3 | 3 | 0 | 0 |
| cell/3/0/2/0 | rest8th | 2 | 2 | 0 | 0 |
| cell/3/0/3/8 | rest8th | 1 | 2 | 0 | 0 |

## Verdict

**Differences found** — see deltas above.
