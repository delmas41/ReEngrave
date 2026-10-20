#!/bin/sh
# 2.180: my look-sheets (not for Sean). usage: sh sheets.sh DATADIR
D="$1"
P=benchmarks/omr-augmentation-dots-2026-10/probe/x4_sheet.py
python3 $P bra $D/bra_x1.json $D/bra_fates.json $D/s_bra_stacc.png d_staccato 24 1
python3 $P bra $D/bra_x1.json $D/bra_fates.json $D/s_bra_ghost.png b_head_abstained 18 1
python3 $P bra $D/bra_x1.json $D/bra_fates.json $D/s_bra_amb.png c_role 24 1
python3 $P bra $D/bra_x1.json $D/bra_fates.json $D/s_bra_wedge.png d_staccatissimo 18 1
python3 $P bra $D/bra_x1.json $D/bra_fates.json $D/s_bra_narr.png b_narrowed 12 1
python3 $P lit $D/lit_x1.json $D/lit_fates.json $D/s_lit_stacc.png d_staccato 24 1
python3 $P lit $D/lit_x1.json $D/lit_fates.json $D/s_lit_amb.png c_role 24 1
