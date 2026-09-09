# Staged pipeline health — 318 test functions

Derived from the tests that already exist. It asks whether each stage and decision is WORKING, never whether it scores well.

## Per stage

| stage | tests | files |
|---|--:|---|
| ADJUDICATE | 239 | `test_staged_adjudicate.py`, `test_staged_candidates.py`, `test_staged_clef.py`, `test_staged_discipline.py`, `test_staged_duration.py`, `test_staged_glyph_families.py`, `test_staged_groups.py`, `test_staged_header_rhythm.py`, `test_staged_health.py`, `test_staged_identity_chain.py`, `test_staged_inventory.py`, `test_staged_ownership.py`, `test_staged_pipeline.py`, `test_staged_record_coverage.py`, `test_staged_stage_contract.py` |
| EVALUATE | 97 | `test_staged_candidates.py`, `test_staged_clef.py`, `test_staged_discipline.py`, `test_staged_duration.py`, `test_staged_identity_chain.py`, `test_staged_pipeline.py` |
| EXPORT | 32 | `test_staged_export.py` |
| GATHER | 41 | `test_staged_glyph_families.py`, `test_staged_pipeline.py`, `test_staged_record_coverage.py`, `test_staged_single_gather.py` |
| GROUPS | 44 | `test_staged_groups.py` |
| META | 13 | `test_staged_inventory.py` |
| PIPELINE | 92 | `test_staged_divergence_units.py`, `test_staged_groups.py`, `test_staged_pipeline.py`, `test_staged_single_gather.py` |
| RECORD | 294 | `test_staged_adjudicate.py`, `test_staged_candidates.py`, `test_staged_clef.py`, `test_staged_discipline.py`, `test_staged_divergence_units.py`, `test_staged_duration.py`, `test_staged_export.py`, `test_staged_glyph_families.py`, `test_staged_groups.py`, `test_staged_header_rhythm.py`, `test_staged_identity_chain.py`, `test_staged_ownership.py`, `test_staged_pipeline.py`, `test_staged_record.py`, `test_staged_record_coverage.py`, `test_staged_stage_contract.py` |

## Per decision — decides / abstains / records

| decision | decides | abstains | records | tested in |
|---|--:|--:|--:|---|
| `system_membership` | 1 | 2 | 2 | `test_staged_stage_contract.py` |
| `staff_group` | 3 | 3 | 3 | `test_staged_adjudicate.py`, `test_staged_groups.py`, `test_staged_pipeline.py`, `test_staged_stage_contract.py` |
| `measure_partition` | 1 | 9 | 8 | `test_staged_export.py`, `test_staged_groups.py`, `test_staged_stage_contract.py` |
| `staff_ordinal` | 4 | 14 | 5 | `test_staged_duration.py`, `test_staged_identity_chain.py`, `test_staged_ownership.py`, `test_staged_record.py` |
| `system_staff_count` | 8 | 22 | 17 | `test_staged_divergence_units.py`, `test_staged_duration.py`, `test_staged_export.py`, `test_staged_groups.py`, `test_staged_identity_chain.py`, `test_staged_ownership.py`, `test_staged_stage_contract.py` |
| `instrument` | 8 | 4 | 7 | `test_staged_adjudicate.py`, `test_staged_divergence_units.py`, `test_staged_duration.py`, `test_staged_identity_chain.py`, `test_staged_ownership.py` |
| `slot_index` | 3 | 3 | 2 | `test_staged_adjudicate.py`, `test_staged_duration.py`, `test_staged_export.py`, `test_staged_groups.py` |
| `part_partition` | 1 | 9 | 9 | `test_staged_export.py`, `test_staged_stage_contract.py` |
| `group_symbol` | 2 | 4 | 1 | `test_staged_identity_chain.py`, `test_staged_pipeline.py`, `test_staged_stage_contract.py` |
| `clef` | 21 | 21 | 23 | `test_staged_adjudicate.py`, `test_staged_candidates.py`, `test_staged_clef.py`, `test_staged_divergence_units.py`, `test_staged_duration.py`, `test_staged_export.py`, `test_staged_groups.py`, `test_staged_header_rhythm.py`, `test_staged_identity_chain.py`, `test_staged_ownership.py`, `test_staged_pipeline.py`, `test_staged_record.py`, `test_staged_stage_contract.py` |
| `key_signature` | 5 | 6 | 2 | `test_staged_divergence_units.py`, `test_staged_duration.py`, `test_staged_header_rhythm.py`, `test_staged_stage_contract.py` |
| `glyph_owner` | 2 | 7 | 1 | `test_staged_duration.py`, `test_staged_ownership.py` |
| `arc_owner` *(stub)* | **0** | 4 | 1 | `test_staged_adjudicate.py`, `test_staged_discipline.py`, `test_staged_glyph_families.py`, `test_staged_health.py`, `test_staged_inventory.py`, `test_staged_stage_contract.py` |
| `arc_kind` *(stub)* | **0** | 5 | 1 | `test_staged_adjudicate.py`, `test_staged_discipline.py`, `test_staged_glyph_families.py`, `test_staged_health.py`, `test_staged_inventory.py`, `test_staged_stage_contract.py` |
| `articulation_owner` *(stub)* | **0** | 4 | 1 | `test_staged_adjudicate.py`, `test_staged_discipline.py`, `test_staged_glyph_families.py`, `test_staged_health.py`, `test_staged_inventory.py`, `test_staged_stage_contract.py` |
| `wedge_anchor` *(stub)* | **0** | 4 | 1 | `test_staged_adjudicate.py`, `test_staged_discipline.py`, `test_staged_glyph_families.py`, `test_staged_health.py`, `test_staged_inventory.py`, `test_staged_stage_contract.py` |
| `tuplet_ratio` | 2 | 2 | 1 | `test_staged_duration.py`, `test_staged_export.py`, `test_staged_stage_contract.py` |
| `duration` | 3 | 9 | 14 | `test_staged_candidates.py`, `test_staged_duration.py`, `test_staged_export.py`, `test_staged_glyph_families.py` |
| `meter` | 1 | 7 | 10 | `test_staged_candidates.py`, `test_staged_divergence_units.py`, `test_staged_export.py`, `test_staged_groups.py`, `test_staged_header_rhythm.py` |
| `dynamic` *(stub)* | **0** | 4 | 1 | `test_staged_adjudicate.py`, `test_staged_discipline.py`, `test_staged_glyph_families.py`, `test_staged_health.py`, `test_staged_inventory.py`, `test_staged_stage_contract.py` |
| `direction` *(stub)* | **0** | 4 | 1 | `test_staged_adjudicate.py`, `test_staged_discipline.py`, `test_staged_health.py`, `test_staged_inventory.py`, `test_staged_stage_contract.py` |

## Consequences (EVALUATE)

| consequence | cause → effect | state |
|---|---|---|
| `restate_pitch` | `clef` → `pitch` | real |
| `size_measure_rest` | `meter` → `duration` | real |
| `reconcile_duration` | `meter` → `duration` | real |
| `move_glyph` | `glyph_owner` → `pitch` | real |
| `respell_accidental` | `key_signature` → `accidental` | real |
| `name_part` | `instrument` → `part_name` | real |
| `join_parts` | `part_partition` → `part_name` | STUB |

## ⚠️ EMPTY CELLS

none

⚠️ The shape classifier is TEXTUAL and undercounts. Confirm any zero with one `grep` before believing it.
