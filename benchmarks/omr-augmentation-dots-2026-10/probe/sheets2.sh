#!/bin/sh
# 2.180: my look-sheets of unplaced dots (x6 output). usage: sh sheets2.sh DATADIR
D="$1"
P=benchmarks/omr-augmentation-dots-2026-10/probe/x4_sheet.py
KEY=head_same_cell python3 $P bra $D/bra_x1.json $D/bra_unpl.json $D/u_bra_wedge.png c_role 24 2 wedge_without_a_head
KEY=head_same_cell python3 $P bra $D/bra_x1.json $D/bra_unpl.json $D/u_bra_amb_head.png c_role 30 2 dot_role_ambiguous
KEY=no_head python3 $P bra $D/bra_x1.json $D/bra_unpl.json $D/u_bra_amb_nohead.png c_role 30 2 dot_role_ambiguous
KEY=head_other python3 $P bra $D/bra_x1.json $D/bra_unpl.json $D/u_bra_amb_other.png c_role 24 2 dot_role_ambiguous
KEY=no_head python3 $P bra $D/bra_x1.json $D/bra_unpl.json $D/u_bra_ssimo.png d_stacc 18 2
