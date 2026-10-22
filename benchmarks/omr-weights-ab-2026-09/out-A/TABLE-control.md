# Weights A/B — production-control vs production-control_copy

Family: `rest`. Pages: `1`. Weights differ; pipeline, pdf and pages are identical.

## 1. GATHER — boxes by class

| class | production-control | production-control_copy | delta |
|---|--:|--:|--:|
| rest16th | 3 | 3 | +0 |
| rest8th | 127 | 127 | +0 |
| restHBar | 1 | 1 | +0 |
| restHalf | 2 | 2 | +0 |
| restQuarter | 92 | 92 | +0 |
| restWhole | 125 | 125 | +0 |

**Total boxes gathered:** production-control 350, production-control_copy 350 (delta +0)

## 2. ADJUDICATE — per quantity, verdicts and refusals

### `duration` (no difference)

| outcome/value/reason | a | b | delta |
|---|--:|--:|--:|
| ['abstained', None, 'rest_stands_where_no_rest_hangs'] | 23 | 23 | +0 |
| ['abstained', None, 'unreadable_rest'] | 1 | 1 | +0 |
| ['decided', (('beam_levels', 0), ('beats', 0.25), ('dots', 0), ('is_rest', True), ('written', 0.25)), 'rest_class'] | 3 | 3 | +0 |
| ['decided', (('beam_levels', 0), ('beats', 0.5), ('dots', 0), ('is_rest', True), ('written', 0.5)), 'rest_class'] | 127 | 127 | +0 |
| ['decided', (('beam_levels', 0), ('beats', 1.0), ('dots', 0), ('is_rest', True), ('written', 1.0)), 'rest_class'] | 92 | 92 | +0 |
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

### `rest_is_not_a_rest` (no difference)

| outcome/value/reason | a | b | delta |
|---|--:|--:|--:|
| ['decided', False, 'rest'] | 209 | 209 | +0 |
| ['decided', True, 'rest_clipped_by_crop'] | 47 | 47 | +0 |
| ['decided', True, 'rest_has_a_stem'] | 39 | 39 | +0 |
| ['decided', True, 'rest_is_a_duplicate_box'] | 36 | 36 | +0 |
| ['decided', True, 'rest_outside_its_staff'] | 17 | 17 | +0 |
| ['decided', True, 'rest_touches_two_staff_lines'] | 2 | 2 | +0 |

## 3. Sean's rest-queue verdicts vs each record's surviving rests

### production-control
cells with a Sean verdict AND a record rest reading: 8 (class, cell) rows — surviving 11, Sean TP 17, best-case matched (min per cell/class) 11

| cell | class | record surviving | Sean TP | Sean FP | Sean unsure |
|---|---|--:|--:|--:|--:|
| cell/1/0/0/1 | rest8th | 3 | 3 | 0 | 0 |
| cell/1/0/0/1 | restQuarter | 0 | 1 | 1 | 0 |
| cell/1/0/1/1 | rest8th | 3 | 3 | 0 | 0 |
| cell/1/0/1/1 | restQuarter | 0 | 2 | 1 | 0 |
| cell/1/0/1/5 | rest8th | 1 | 1 | 0 | 0 |
| cell/1/0/2/2 | rest8th | 1 | 1 | 1 | 0 |
| cell/1/0/2/5 | rest8th | 1 | 4 | 0 | 0 |
| cell/1/0/9/5 | rest8th | 2 | 2 | 0 | 0 |

### production-control_copy
cells with a Sean verdict AND a record rest reading: 8 (class, cell) rows — surviving 11, Sean TP 17, best-case matched (min per cell/class) 11

| cell | class | record surviving | Sean TP | Sean FP | Sean unsure |
|---|---|--:|--:|--:|--:|
| cell/1/0/0/1 | rest8th | 3 | 3 | 0 | 0 |
| cell/1/0/0/1 | restQuarter | 0 | 1 | 1 | 0 |
| cell/1/0/1/1 | rest8th | 3 | 3 | 0 | 0 |
| cell/1/0/1/1 | restQuarter | 0 | 2 | 1 | 0 |
| cell/1/0/1/5 | rest8th | 1 | 1 | 0 | 0 |
| cell/1/0/2/2 | rest8th | 1 | 1 | 1 | 0 |
| cell/1/0/2/5 | rest8th | 1 | 4 | 0 | 0 |
| cell/1/0/9/5 | rest8th | 2 | 2 | 0 | 0 |

## Verdict

**ZERO differences at stage 2.**
