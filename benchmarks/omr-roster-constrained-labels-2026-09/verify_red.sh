#!/bin/bash
# Each test is verified RED by BREAKING the mechanism it guards, one at a time,
# and confirming exactly that test fails. A test that passes both ways guards
# nothing — this repo has shipped one (`benchmarks/omr-margin-labels-blob-2026-09
# /FINDINGS.md`: a length assertion a single huge glyph satisfied), and two of
# the arms below were written wrong the first time and caught here:
#
#   * the length floor and the ambiguity rule were perturbed TOGETHER, and
#     admitting two-letter tokens makes `in` match everything, so ambiguity
#     saved the abstention and both tests passed;
#   * the flag-off wrapper test passed a PDF outside the store, so it would have
#     passed with the flag defaulted on.
#
#   bash benchmarks/omr-roster-constrained-labels-2026-09/verify_red.sh
set -u
cd "$(git rev-parse --show-toplevel)" || exit 1
M=tools/omr/work_roster.py
C=tools/omr/contextual.py
T=tools/omr/tests/test_work_roster.py
BAK=$(mktemp -d)
cp "$M" "$BAK/wr.py"; cp "$C" "$BAK/cx.py"
restore() { cp "$BAK/wr.py" "$M"; cp "$BAK/cx.py" "$C"; }
trap restore EXIT

run() {
  out=$(python3 -m pytest "$T::$1" -q 2>&1 | grep -E "^[0-9]+ (passed|failed)|failed," | tail -1)
  echo "  $1 -> $out"
}
patch() { python3 -c "
import sys
p, old, new = sys.argv[1], sys.argv[2], sys.argv[3]
s = open(p).read()
assert old in s, 'anchor not found: ' + old[:60]
open(p, 'w').write(s.replace(old, new, 1))
" "$@"; }

echo "== 1. multi-word aliases admitted (the cross-family reach) =="
patch "$M" 'for alias in aliases_of(inst) if " " not in alias]' 'for alias in aliases_of(inst)]'
run test_a_multi_word_alias_is_not_a_truncation_target
restore

echo "== 2. disambiguation tried before recovery =="
python3 - "$M" <<'PY'
import sys
p = sys.argv[1]; s = open(p).read()
a = s.index('        rec = recover_truncated(text, roster)\n        if rec is not None:\n            return Decision("recovered", rec, before=hit.instrument.name,')
b = s.index('        admitted = [alt for alt in hit.alternatives', a)
c = s.index('        return Decision("vetoed"', b)
open(p, 'w').write(s[:a] + s[b:c] + s[a:b] + s[c:])
PY
run test_recovery_outranks_disambiguation
restore

echo "== 3. section words not read off the raw string =="
patch "$M" '    families |= _families_from_raw(entry.get("raw") or {})
' ''
run test_a_section_word_the_parser_dropped_still_admits_its_family
restore

echo "== 4. the source_kind gate removed =="
patch "$M" '    if entry.get("source_kind") != "catalog":
        return None
' ''
run test_only_the_catalog_tier_is_read
restore

echo "== 5. the complete-parse gate removed =="
patch "$M" '        if not roster.complete:
            return Decision("unchanged", None)
' ''
patch "$M" '    if roster.complete and not roster.admits_family(' '    if not roster.admits_family('
run test_an_incomplete_roster_neither_vetoes_nor_recovers
restore

echo "== 6a. the retained-fraction floor lowered =="
patch "$M" 'MIN_KEPT_FRACTION = 0.5' 'MIN_KEPT_FRACTION = 0.3'
run test_a_tail_too_short_a_share_of_its_alias_abstains
restore

echo "== 6c. spelled-out counts admitted as name tokens =="
patch "$M" '_COUNT_WORDS = frozenset("""' '_COUNT_WORDS = frozenset("""  # noqa
""") or frozenset("""'
run test_a_spelled_out_count_is_not_a_name
restore

echo "== 6b. ambiguity resolved by taking a candidate instead of abstaining =="
patch "$M" '    if len(hits) != 1:
        return None
' '    if not hits:
        return None
'
run test_ambiguity_within_the_roster_abstains
restore

echo "== 6d. a known alias admitted as a fragment =="
patch "$M" '        if token in known:' '        if False and token in known:'
run test_a_token_the_lexicon_already_knows_is_not_a_fragment
restore

echo "== 6e. families read from the parse only, not the raw fields =="
patch "$M" '            out.add(hit.instrument.family)' '            pass'
run "test_a_work_whose_SINGERS_only_the_other_field_names_still_admits_them[mahler--symphony-4]"
restore

echo "== 7. the wrapper unwired (the ladder returns the raw read) =="
patch "$C" '    if not work_roster.enabled() or not labels:
        return labels
' '    return labels
'
run test_the_wrapper_repairs_labels_when_the_flag_is_on
restore

echo "== 8. the flag defaulted ON =="
patch "$M" 'os.environ.get("OMR_ROSTER_LABELS", "0")' 'os.environ.get("OMR_ROSTER_LABELS", "1")'
run test_the_wrapper_is_inert_when_the_flag_is_off
restore

echo "== green again =="
python3 -m pytest "$T" -q 2>&1 | grep -E "^[0-9]+ (passed|failed)|failed," | tail -1
