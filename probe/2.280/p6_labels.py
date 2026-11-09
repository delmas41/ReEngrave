"""2.280 probe 6: MY LOOK labels (ours, not evidence) for every stratum-A head (narrowed, no touching stem), sorted-sub order, 12 per sheet (p4_sheet.py OFFSET).
R = a rest (whole / half block) kept as a head; N = not a note (accidental, clef piece, word letter, slur piece); H = a real head fused into a clump / ledger-line stem (Litolff);
Brahms: D = head of a second whose stem is on its partner, S = single head with a stem fused or near; U = unclear. Crosstab with the mechanical cause (p3)."""
import collections
import json

LIT = "HRRRRRHHHHRH" "HRHRRHRHRRRU" "HHHHHUNHHHHH" "RHRHHR"
BRA = "SDNNSSSSNNDD" "DDNNNNDDDDNS" "NNSSSDSDNDND" "DDDDD"
for plate, lab in (("litolff", LIT), ("brahms", BRA)):
    B = json.load(open("out/2.280/buckets_%s.json" % plate))
    subs = sorted(s for s, b in B.items() if b["stratum"] == "A")
    assert len(subs) == len(lab), (plate, len(subs), len(lab))
    ct = collections.Counter()
    out = {}
    for s, l in zip(subs, lab):
        ct[(l, B[s]["cause"])] += 1
        out[s] = l
    json.dump(out, open("out/2.280/labels_%s.json" % plate, "w"))
    pg = collections.Counter((l, B[s]["page"][:40], B[s]["reach_sp"] >= 1.5) for s, l in zip(subs, lab))
    print("  -- by label: does a PAGE stroke / head_stem_reach already hold a stem-shaped stroke at the head?")
    for k, v in sorted(pg.items()):
        print("   %s  %-42s reach>=1.5sp:%s  %d" % (k[0], k[1], k[2], v))
    print(plate, dict(collections.Counter(lab)))
    for k, v in sorted(ct.items()):
        print("   %s  %-62s %d" % (k[0], k[1], v))
