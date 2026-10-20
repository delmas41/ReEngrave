#!/bin/sh
# 2.180: my look-sheets of dots BESIDE an undotted note (x7 output). usage: sh sheets3.sh DATADIR
D="$1"
P=benchmarks/omr-augmentation-dots-2026-10/probe/x4_sheet.py
python3 - "$D" <<'PY'
import json, sys
D = sys.argv[1]
for p in ("bra", "lit"):
    R = json.load(open("%s/%s_beside.json" % (D, p)))
    for r in R:
        r["key"] = r["state"]
    json.dump(R, open("%s/%s_beside_k.json" % (D, p), "w"))
PY
KEY=UNDOTTED python3 $P bra $D/bra_x1.json $D/bra_beside_k.json $D/v_bra_d.png d_ 30 3
KEY=UNDOTTED python3 $P bra $D/bra_x1.json $D/bra_beside_k.json $D/v_bra_c.png c_ 30 3
KEY=UNDOTTED python3 $P lit $D/lit_x1.json $D/lit_beside_k.json $D/v_lit_d.png d_ 30 3
KEY=UNDOTTED python3 $P lit $D/lit_x1.json $D/lit_beside_k.json $D/v_lit_c.png c_ 14 3
KEY=UNDOTTED python3 $P bra $D/bra_x1.json $D/bra_beside_k.json $D/v_bra_bax.png b_,a_,x_,f_ 30 3
