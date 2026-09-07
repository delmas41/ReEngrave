#!/bin/bash
# Read pass + margin labels for two ONE-SPAN controls, so the swap rule can be
# asked the dangerous question: does it split a document the count rule leaves
# whole?
#
#   Brahms 3 / Breitkopf  — the SAME PUBLISHER as the work the rule is built on,
#                           and Breitkopf labels every system, so it is the
#                           highest-exposure control available.
#   Dvorak 9 / Simrock    — a different publisher, four movements, and a work
#                           whose movements genuinely differ in instrumentation
#                           (the cor anglais of the Largo), so a fire here needs
#                           adjudicating rather than dismissing.
#
# ⚠️ SURYA: the first attempt ran OMR_SURYA_KEEP_ALIVE=0, which is the correct
# setting for an UNATTENDED run — a worker per page, owned by the run. Measured
# 65 s/page (the ~70 s llama.cpp model load, paid once per page), i.e. ~3 h for
# these two works, so this run attaches to the machine's resident server
# instead and is polled. ⚠️ NEVER `pkill -f llama-server`: one machine has one
# server and sibling sessions read through it. This run only READS it.
set -euo pipefail
cd "$(dirname "$0")/../../.."
OUT=benchmarks/omr-lineup-swap-2026-09/out
LIB=/Users/seanjohnson/Desktop/ReEngrave/library/editions
export OMR_SURYA_KEEP_ALIVE=1

run () {  # tag pdf pages
    mkdir -p "$OUT/$1"
    python3 -u benchmarks/omr-spans-veto-composition-2026-09/probe/compose.py \
        "$2" --out-dir "$OUT/$1" --pages "$3" --dpi 600 \
        --cache "$OUT/$1/cache600" --veto report
}

run brahms3 \
    "$LIB/brahms/symphony-3-op90/brahms--symphony-3-op90--breitkopf-hartel-brahms--imslp317593.pdf" \
    0-85
run dvorak9 \
    "$LIB/dvorak/symphony-9-op95/dvorak--symphony-9-op95--simrock-1894--imslp405834.pdf" \
    0-79
echo "CONTROLS DONE"
