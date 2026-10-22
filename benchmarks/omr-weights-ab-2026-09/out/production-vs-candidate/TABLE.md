# Weights A/B — production vs candidate

Family: `rest`. Pages: `1`. Weights differ; pipeline, pdf and pages are identical.

## 1. GATHER — boxes by class

| class | production | candidate | delta |
|---|--:|--:|--:|
| rest16th | 3 | 3 | +0 |
| rest8th | 127 | 128 | +1 |
| restHBar | 1 | 1 | +0 |
| restHalf | 2 | 2 | +0 |
| restQuarter | 92 | 91 | -1 |
| restWhole | 125 | 125 | +0 |

**Total boxes gathered:** production 350, candidate 350 (delta +0)

## 2. ADJUDICATE — per quantity, verdicts and refusals

### `duration`

| outcome/value/reason | a | b | delta |
|---|--:|--:|--:|
| ['abstained', None, 'rest_stands_where_no_rest_hangs'] | 23 | 23 | +0 |
| ['abstained', None, 'unreadable_rest'] | 1 | 1 | +0 |
| ['decided', (('beam_levels', 0), ('beats', 0.25), ('dots', 0), ('is_rest', True), ('written', 0.25)), 'rest_class'] | 3 | 3 | +0 |
| ['decided', (('beam_levels', 0), ('beats', 0.5), ('dots', 0), ('is_rest', True), ('written', 0.5)), 'rest_class'] | 127 | 128 | +1 |
| ['decided', (('beam_levels', 0), ('beats', 1.0), ('dots', 0), ('is_rest', True), ('written', 1.0)), 'rest_class'] | 92 | 91 | -1 |
| ['decided', (('beam_levels', 0), ('beats', 2.0), ('dots', 0), ('is_rest', True), ('written', 2.0)), 'rest_class'] | 2 | 2 | +0 |
| ['decided', (('beam_levels', 0), ('beats', 4.0), ('dots', 0), ('is_rest', True), ('written', 4.0)), 'rest_class'] | 102 | 102 | +0 |

### `glyph_owner` (no difference)

| outcome/value/reason | a | b | delta |
|---|--:|--:|--:|
| ['decided', 'staff/1/0/0', 'distance'] | 1 | 1 | +0 |
| ['decided', 'staff/1/0/1', 'distance'] | 1 | 1 | +0 |
| ['decided', 'staff/1/0/1', 'hairpin_separates'] | 5 | 5 | +0 |
| ['decided', 'staff/1/0/3', 'distance'] | 6 | 6 | +0 |
| ['decided', 'staff/1/0/8', 'distance'] | 12 | 12 | +0 |
| ['decided', 'staff/1/1/0', 'distance'] | 2 | 2 | +0 |
| ['decided', 'staff/1/1/5', 'distance'] | 11 | 11 | +0 |
| ['decided', 'staff/1/1/6', 'distance'] | 8 | 8 | +0 |

### `rest_is_not_a_rest`

| outcome/value/reason | a | b | delta |
|---|--:|--:|--:|
| ['decided', False, 'rest'] | 314 | 313 | -1 |
| ['decided', True, 'rest_is_a_duplicate_box'] | 36 | 37 | +1 |

## 3. Sean's rest-queue verdicts vs each record's surviving rests

### production
cells with a Sean verdict AND a record rest reading: 10 (class, cell) rows — surviving 21, Sean TP 17, best-case matched (min per cell/class) 17

| cell | class | record surviving | Sean TP | Sean FP | Sean unsure |
|---|---|--:|--:|--:|--:|
| cell/1/0/0/1 | restQuarter | 2 | 1 | 1 | 0 |
| cell/1/0/0/1 | rest8th | 3 | 3 | 0 | 0 |
| cell/1/0/1/1 | restQuarter | 3 | 2 | 1 | 0 |
| cell/1/0/1/1 | rest8th | 3 | 3 | 0 | 0 |
| cell/1/0/1/5 | rest8th | 1 | 1 | 0 | 0 |
| cell/1/0/2/2 | restWhole | 1 | 0 | 0 | 2 |
| cell/1/0/2/2 | rest8th | 1 | 1 | 1 | 0 |
| cell/1/0/2/5 | rest8th | 4 | 4 | 0 | 0 |
| cell/1/0/3/4 | restQuarter | 1 | 0 | 1 | 0 |
| cell/1/0/9/5 | rest8th | 2 | 2 | 0 | 0 |

### candidate
cells with a Sean verdict AND a record rest reading: 10 (class, cell) rows — surviving 21, Sean TP 17, best-case matched (min per cell/class) 17

| cell | class | record surviving | Sean TP | Sean FP | Sean unsure |
|---|---|--:|--:|--:|--:|
| cell/1/0/0/1 | restQuarter | 2 | 1 | 1 | 0 |
| cell/1/0/0/1 | rest8th | 3 | 3 | 0 | 0 |
| cell/1/0/1/1 | restQuarter | 3 | 2 | 1 | 0 |
| cell/1/0/1/1 | rest8th | 3 | 3 | 0 | 0 |
| cell/1/0/1/5 | rest8th | 1 | 1 | 0 | 0 |
| cell/1/0/2/2 | restWhole | 1 | 0 | 0 | 2 |
| cell/1/0/2/2 | rest8th | 1 | 1 | 1 | 0 |
| cell/1/0/2/5 | rest8th | 4 | 4 | 0 | 0 |
| cell/1/0/3/4 | restQuarter | 1 | 0 | 1 | 0 |
| cell/1/0/9/5 | rest8th | 2 | 2 | 0 | 0 |

## Verdict

**Differences found** — see deltas above.
