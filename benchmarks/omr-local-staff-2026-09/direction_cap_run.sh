#!/bin/bash
# Held-out pages for the direction-word cap. Run from the repo root (a worktree needs the CLAUDE.md 5a symlinks).
L=/Users/seanjohnson/Desktop/ReEngrave/library/editions
LIT=$L/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf
BR=$L/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf
O=benchmarks/omr-local-staff-2026-09/out/direction_cap
mkdir -p $O
for p in ${LIT_PAGES:-4 6 9 12 15}; do python3 benchmarks/omr-local-staff-2026-09/direction_cap_heldout.py "$LIT" $p lit_$p $O > $O/lit_$p.log 2>&1; done
for p in ${BR_PAGES:-3 7 12 18 24}; do python3 benchmarks/omr-local-staff-2026-09/direction_cap_heldout.py "$BR" $p br_$p $O > $O/br_$p.log 2>&1; done
