"""2.251 carry: change AND return recall of step 1's claims (scan_claims.py output) at every print-confirmed change inside a system.

python3 work-2.251/recall.py PLATE CLAIMS.json
A change at bar b (kind K, from the reference encoding, print-confirmed in FINDINGS) is CLAIMED when a claim of K's family stands on
the change's staff in the cell of bar b or of bar b-1 (a change stands at the end of the bar before, or at the head of its own bar).
Its RETURN is the next printed clef on that staff in the same system (the next change on the list), or the system's end (nothing to
claim: the header of the next system resets). Staff: the staff the claim stands on is checked by hand from the crops (bassoon / Vcl.).
"""
import json, os, sys
sys.path.insert(0, os.path.join(os.getcwd(), "work-2.251"))
import barmap  # noqa: E402

# (bar, part, family) -- the print-confirmed changes inside a system (FINDINGS "Count"; kinds from the reference MXL)
CHANGES = {
    "litolff": [(36, "fag", "C"), (38, "fag", "F"), (102, "fag", "C"), (107, "fag", "F"), (110, "fag", "C"), (111, "fag", "F"),
                (114, "fag", "C"), (115, "fag", "F"), (146, "fag", "C"), (159, "fag", "F"), (211, "fag", "C"), (228, "fag", "F"),
                (282, "fag", "F"), (303, "fag", "C"), (315, "fag", "F"), (319, "fag", "C"), (323, "fag", "F"), (346, "fag", "C"),
                (351, "fag", "F"), (387, "fag", "C"), (390, "fag", "F"), (396, "fag", "C"), (411, "fag", "F"), (470, "fag", "C"),
                (476, "fag", "F"), (483, "fag", "C"), (501, "fag", "F"),
                (94, "vc", "F"), (154, "vc", "F"), (331, "vc", "C"), (346, "vc", "F"), (411, "vc", "F")],
    "brahms": [(18, "fag", "C"), (20, "fag", "F"), (46, "fag", "C"), (50, "fag", "F"), (76, "fag", "F"), (89, "fag", "C"),
               (97, "fag", "F")],
}


def systems(plate):
    out = []
    b = 1
    for pg, si, nst, nc in barmap.layout(plate):
        out.append((pg, si, b, b + nc - 1))
        b += nc
    return out


def where(plate, bar):
    for pg, si, b0, b1 in systems(plate):
        if b0 <= bar <= b1:
            return pg, si, bar - b0, b1 - b0
    return None


def main():
    plate, cpath = sys.argv[1], sys.argv[2]
    claims = [c for c in json.load(open(cpath)) if not c.get("candidate")]
    ch = sorted(CHANGES[plate], key=lambda t: (t[1], t[0]))
    rows = []
    for i, (bar, part, fam) in enumerate(ch):
        pg, si, cell, last = where(plate, bar)
        cands = [c for c in claims if c["page"] == pg and c["system"] == si and c["change"] and c["family"] == fam
                 and c["cell"] in (cell - 1, cell)]
        nxt = ch[i + 1] if i + 1 < len(ch) and ch[i + 1][1] == part else None
        ret = "system end"
        ret_ok = True
        if nxt is not None and where(plate, nxt[0])[:2] == (pg, si):
            ncell = where(plate, nxt[0])[2]
            rc = [c for c in claims if c["page"] == pg and c["system"] == si and c["change"] and c["family"] == nxt[2]
                  and c["cell"] in (ncell - 1, ncell)]
            ret = "bar %d %s" % (nxt[0], nxt[2])
            ret_ok = bool(rc)
        # a cautionary clef at the system's end governs nothing on this system: the return is the next header
        rows.append((bar, part, fam, pg, si, cell, ["%s/%s c%d %s" % (c["staff"], c["family"], c["cell"], c["kind"]) for c in cands],
                     ret, ret_ok))
    n_ch = sum(1 for r in rows if r[6])
    n_both = sum(1 for r in rows if r[6] and r[8])
    for r in rows:
        print("%4d %-3s %s  p%d s%d c%-2d  change %-28s  return %-12s %s" % (r[0], r[1], r[2], r[3], r[4], r[5],
              ",".join(r[6]) or "MISSED", r[7], "claimed" if r[8] and r[7] != "system end" else ("MISSED" if not r[8] else "-")))
    print("%s: changes %d, change claimed %d, change AND return claimed %d" % (plate, len(rows), n_ch, n_both))


main()
