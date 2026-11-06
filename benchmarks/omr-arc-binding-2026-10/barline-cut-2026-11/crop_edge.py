"""Box end exactly at the crop edge (<= 0.25 sp) vs the same box slid to a random x in its cell; left and right ends separately. Real arcs only."""
import json

for plate in ("litolff", "brahms"):
    led = json.load(open("../deep-dive-2026-11/results/%s.base.ledger.json" % plate))["rows"]
    lp = {p: r["fate"] for r in led for p in r["pieces"]}
    d = json.load(open("results/%s.cut.json" % plate))
    for name, f in (("real arcs (ledger pages)", lambda r: r["key"] in lp and lp[r["key"]] != "not_an_arc"),
                    ("real arcs with a page curve", lambda r: r["key"] in lp and lp[r["key"]] != "not_an_arc" and r["curve"])):
        rs = [r for r in d["rows"] if f(r)]
        n = len(rs)
        ol = sum(r["l_edge"] <= 0.25 for r in rs)
        orr = sum(r["r_edge"] <= 0.25 for r in rs)
        cl = sum(r["chance_l25"] for r in rs)
        cr = sum(r["chance_r25"] for r in rs)
        print("%s %-28s boxes %4d | LEFT end at edge: %4d (%.1f%%) chance %.1f%% x%.1f | RIGHT end at edge: %4d (%.1f%%) chance %.1f%% x%.1f | both ends %.1f%% ; both-ends chance (indep.) ~%.1f%%" % (
            plate, name, n, ol, 100 * ol / n, 100 * cl / n, ol / max(cl, 1e-9), orr, 100 * orr / n, 100 * cr / n, orr / max(cr, 1e-9),
            100 * sum(r["l_edge"] <= 0.25 and r["r_edge"] <= 0.25 for r in rs) / n, 100 * (cl / n) * (cr / n)))
