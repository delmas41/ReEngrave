"""Print one page's staff identity from a replay JSON, both arms side by side."""
import json
import sys

d = json.load(open(sys.argv[1]))
page = int(sys.argv[2])
off = {(p, s, i): n for p, s, i, n in d["rows_off"]}
on = {(p, s, i): n for p, s, i, n in d["rows_on"]}
print("reference OFF:", d["reference_off"])
print("reference ON :", d["reference_on"])
for sy in sorted({s for p, s, _i in off if p == page}):
    ks = sorted([k for k in off if k[0] == page and k[1] == sy],
                key=lambda k: k[2])
    print(f"\np{page}.s{sy}  ({len(ks)} staves)")
    print("  OFF:", [off[k] for k in ks])
    print("   ON:", [on[k] for k in ks])
later = [k for k in off if k[0] >= 44 and off[k] != on[k]]
print(f"\nfinale-page staff records changed: {len(later)}")
