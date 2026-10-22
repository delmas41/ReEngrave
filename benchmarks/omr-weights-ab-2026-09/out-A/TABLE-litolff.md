# Weights A/B — production-litolff vs candidate-litolff

Family: `rest`. Pages: `1-4`. Weights differ; pipeline, pdf and pages are identical.

## 1. GATHER — boxes by class

| class | production-litolff | candidate-litolff | delta |
|---|--:|--:|--:|
| rest16th | 3 | 0 | -3 |
| rest32nd | 0 | 1 | +1 |
| rest8th | 38 | 21 | -17 |
| restHalf | 1 | 1 | +0 |
| restQuarter | 209 | 208 | -1 |
| restWhole | 395 | 368 | -27 |

**Total boxes gathered:** production-litolff 646, candidate-litolff 599 (delta -47)

## 2. ADJUDICATE — per quantity, verdicts and refusals

### `duration`

| outcome/value/reason | a | b | delta |
|---|--:|--:|--:|
| ['abstained', None, 'rest_stands_where_no_rest_hangs'] | 24 | 24 | +0 |
| ['decided', (('beam_levels', 0), ('beats', 0.125), ('dots', 0), ('is_rest', True), ('written', 0.125)), 'rest_class'] | 0 | 1 | +1 |
| ['decided', (('beam_levels', 0), ('beats', 0.25), ('dots', 0), ('is_rest', True), ('written', 0.25)), 'rest_class'] | 3 | 0 | -3 |
| ['decided', (('beam_levels', 0), ('beats', 0.5), ('dots', 0), ('is_rest', True), ('written', 0.5)), 'rest_class'] | 38 | 21 | -17 |
| ['decided', (('beam_levels', 0), ('beats', 1.0), ('dots', 0), ('is_rest', True), ('written', 1.0)), 'rest_class'] | 209 | 208 | -1 |
| ['decided', (('beam_levels', 0), ('beats', 4.0), ('dots', 0), ('is_rest', True), ('written', 4.0)), 'rest_class'] | 363 | 337 | -26 |
| ['narrowed', None, 'rest_slot_contradicts_class'] | 9 | 8 | -1 |

### `glyph_owner`

| outcome/value/reason | a | b | delta |
|---|--:|--:|--:|
| ['decided', 'staff/2/0/1', 'distance'] | 2 | 2 | +0 |
| ['decided', 'staff/2/0/2', 'distance'] | 4 | 2 | -2 |

### `rest_is_not_a_rest`

| outcome/value/reason | a | b | delta |
|---|--:|--:|--:|
| ['decided', False, 'rest'] | 376 | 340 | -36 |
| ['decided', True, 'rest_clipped_by_crop'] | 6 | 8 | +2 |
| ['decided', True, 'rest_has_a_stem'] | 193 | 194 | +1 |
| ['decided', True, 'rest_is_a_duplicate_box'] | 19 | 10 | -9 |
| ['decided', True, 'rest_off_center'] | 29 | 26 | -3 |
| ['decided', True, 'rest_outside_its_staff'] | 1 | 2 | +1 |
| ['decided', True, 'rest_touches_two_staff_lines'] | 22 | 19 | -3 |

## 3. Sean's rest-queue verdicts vs each record's surviving rests

### production-litolff
cells with a Sean verdict AND a record rest reading: 0 (class, cell) rows — surviving 0, Sean TP 0, best-case matched (min per cell/class) 0

| cell | class | record surviving | Sean TP | Sean FP | Sean unsure |
|---|---|--:|--:|--:|--:|

### candidate-litolff
cells with a Sean verdict AND a record rest reading: 0 (class, cell) rows — surviving 0, Sean TP 0, best-case matched (min per cell/class) 0

| cell | class | record surviving | Sean TP | Sean FP | Sean unsure |
|---|---|--:|--:|--:|--:|

## Verdict

**Differences found** — see deltas above.
