#!/bin/zsh
# The mutation battery for the tie-chain accounting.
#
# ⚠️ ONE RED ARM IS NOT A BATTERY. Measured in this repo: five of six mutants
# survived behind one that did not, so every arm below is run and the survivors
# are named rather than the failures counted.
#
# ⚠️ A BATTERY OF *REFUSAL* ARMS CAN PASS BY REFUSING EVERYTHING, so arm 6 is
# the positive control in the same class: it breaks the case that must NOT be
# counted, and if the suite stays green the counter is firing on everything.
#
# Usage:  zsh benchmarks/omr-staged-tie-chain-2026-09/probe/battery.sh
# Run from the repo root. Restores the file on exit, including on Ctrl-C.
set -u
F=tools/omr/staged/export.py
T=tools/omr/tests/test_staged_tie_chain.py
BAK=$(mktemp)
cp $F $BAK
trap 'cp $BAK $F; rm -f $BAK' EXIT INT TERM

arm () {  # arm <name> <sed program>
  cp $BAK $F
  perl -0pi -e "$2" $F
  if cmp -s $BAK $F; then
    print -r -- "ARM $1: ⚠️ MUTATION DID NOT APPLY — the arm tests nothing"
    return
  fi
  out=$(python3 -m pytest $T -q 2>&1 | tail -2 | head -1)
  print -r -- "ARM $1: $out"
}

# 1. a chain is a link: collapse the union-find so every link is its own chain
arm "chain-is-a-link" 's/parent\[ra\] = rb/pass  # MUTANT/'
# 2. count chains but never the long ones
arm "no-long-chains"  's/if n > 2:/if n > 99:/'
# 3. every link called a barline crossing
arm "always-crossing" 's/if sm != tm:/if True:/'
# 4. the shared-quantity split reverts to counting everything
arm "unsplit-census"  's/and str\(v\["value"\]\) == family//'
# 5. the wrong-note counter fires on every chord tie
arm "wrong-note-always" 's/and not head\.get\(key\)//'
# 6. POSITIVE CONTROL: the wrong-note counter never fires
arm "wrong-note-never"  's/and not head\.get\(key\)/and False/'
# 7. abstentions on a shared quantity go back into both family ROWS
arm "abstain-in-both-rows" \
    's/            abstained = collections\.Counter\(\)\n/            abstained = collections.Counter(v["reason"] for v in verdicts if v["outcome"] != "decided")\n/'
# 8. the top-level map accumulates instead of being assigned -- the historical
#    double count, reached by making the write an accumulation again
arm "abstain-accumulates" \
    's/unattributed\[quantity\] = dict\(collections\.Counter\(/unattributed[quantity] = dict(collections.Counter(unattributed.get(quantity, {})) + collections.Counter(/'
