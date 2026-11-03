"""2.255 census: every far-head ledger abstention in the 20261029-night replay slices (both plates), by reason; and the
reason behind each far head the 2.248 r4 ON arm WROTE blue (r4_all_blue.txt)."""
import collections
import json
import os

B = "/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/lane-report-slices-20261029-night/"
HERE = os.path.dirname(os.path.abspath(__file__))
blue = {l.split()[3]: l.split() for l in open(os.path.join(HERE, "r4_all_blue.txt"))}


def short(why):
    w = str(why)
    return w.split(" ")[0] if not w.startswith("not_a_note") else w


for plate in ("litolff", "brahms"):
    allr = collections.Counter()
    other = set()
    own_ab = {}
    for line in open(B + plate + "/abstentions.jsonl"):
        r = json.loads(line)
        q = r.get("quantity")
        if q == "far_head_ledger_position":
            own_ab[r["subject"]] = r["detail"]
            allr[short(r["detail"].get("ledger_reason"))] += 1
    for line in open(B + plate + "/observations.jsonl"):
        if '"far_head_owner_ledger"' not in line:
            continue
        r = json.loads(line)
        s = r["subject"]
        p = s.split("/")
        if s in own_ab and (r.get("detail") or {}).get("candidate") != "staff/%s/%s/%s" % (p[1], p[2], p[3]):
            other.add(s)
    print(plate, "far abstained", len(own_ab), "of which read toward another staff", len(other))
    split = collections.Counter((k if not str(k).startswith("not_a_note") else "not_a_note", s in other)
                                for s, d in own_ab.items() for k in [short(d.get("ledger_reason"))])
    for k, v in sorted(split.items(), key=lambda t: -t[1]):
        print("   ", k[0], "toward-other" if k[1] else "nobody-reads", v)
    print("  WRITTEN BLUE (r4 ON) by reason:")
    for s, d in own_ab.items():
        if s in blue:
            print("    ", s, blue[s][4], str(d.get("ledger_reason"))[:70], "geom", d.get("geometry_position"))
