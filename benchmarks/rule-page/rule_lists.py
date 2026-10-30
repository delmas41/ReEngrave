"""ROADMAP 2.237: the three lists (DEAD / SAME ANSWER AS THE OWNER / DISAGREES) for every B and C rule and every D:cutoff rule, from the fresh
fire counts (`fires-<plate>-<tag>.json`) and the parity file `rule_parity.py` wrote.  Prints markdown; deletes nothing.

    python3 benchmarks/rule-page/rule_lists.py PARITY.json [TAG]

DEAD       fires 0 on BOTH plates' sample (8 pages each).  A candidate only: 0 on a sample is not 0 on the movement, so the deletion lane must
           also show the rule's 10-22 whole-movement count and a byte-identical file with the rule removed.
SAME       box-level parity: (same + merged) / refusals >= 95% on a plate, with at least 10 refusals pooled.  `merged` is the owner folding a
           same-family twin into one mark (2.186): the rule's job (one ink, one mark) done; reported apart.
NO PARITY  the rule's subject is not a box the owner claims for: parity is undefined, never "same" by default.
DISAGREES  the rest with refusals: ownership OWNS the ink of a box the rule refused, or is silent.
"""
import json
import sys
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))
import build_rule_page as B  # noqa: E402
import rule_kinds as K  # noqa: E402
import rule_parity as RP  # noqa: E402


def main():
    parity = json.load(open(sys.argv[1]))
    tag = sys.argv[2] if len(sys.argv) > 2 else B.FRESH_TAG
    fresh = B.load_fresh(tag)
    old = B.load_fires()
    inv = B.code_inventory()
    fn = {d["quantity"]: "%s.%s" % (d["module"], d["function"]) for d in inv["decisions"]}
    scope = []
    for e in K.RULES:
        if e.kind in ("B", "C") or e.kind == "D:cutoff":
            scope.append(e)
    dead, same, no_par, dis = [], [], [], []
    for e in scope:
        reasons = [r.strip() for r in e.reasons.split(",")]
        nf = [sum(fresh[p].get((_dec(inv, e.quantity), r), {}).get("n", 0) for r in reasons) for p in ("L", "B")]
        no = [sum(old[p].get((_dec(inv, e.quantity), r), {}).get("n", 0) for r in reasons) for p in ("L", "B")]
        row = dict(rule=e.name, kind=e.kind, family=e.family, code="%s (%s): %s" % (e.quantity, fn.get(e.quantity, "?"), ", ".join(reasons)),
                   fresh=nf, old=no, fate=e.fate[:60])
        if sum(nf) == 0:
            dead.append(row)
            continue
        if e.quantity not in RP.BOX_DECISIONS or e.quantity == "notehead_is_an_eighth_rest":
            row["why"] = RP.NO_BOX.get(e.quantity, "subject is not a box the owner claims for")
            no_par.append(row)
            continue
        agg = {}
        for p, pl in (("L", "litolff"), ("B", "brahms")):
            c = dict(refusals=0, same=0, disagrees=0, merged=0, silent=0, near=0, with_margin=0)
            for r in reasons:
                x = parity.get(pl, {}).get("per", {}).get("%s|%s" % (e.quantity, r))
                if x:
                    for k in c:
                        c[k] += x.get(k, 0)
            agg[p] = c
        row["parity"] = agg
        tot = sum(agg[p]["refusals"] for p in agg)
        if tot == 0:
            row["why"] = "fires, but no refusal/narrowing verdict to compare (the exit is a positive or passthrough verdict)"
            no_par.append(row)
            continue
        ok = all((agg[p]["same"] + agg[p]["merged"]) >= 0.95 * agg[p]["refusals"] for p in agg if agg[p]["refusals"]) and tot >= 10
        (same if ok else dis).append(row)

    def pc(r):
        a = r["parity"]
        return " | ".join("%s: n=%d same %d, merged %d, disagrees %d, silent %d" % (p, a[p]["refusals"], a[p]["same"], a[p]["merged"], a[p]["disagrees"], a[p]["silent"]) for p in ("L", "B"))

    def nearcol(r):
        a = r["parity"]
        wm = sum(a[p]["with_margin"] for p in a)
        nr = sum(a[p]["near"] for p in a)
        return "%d/%d on a margin < 0.05" % (nr, wm) if wm else "no margin filed (structural or none)"

    out = []
    out.append("### DEAD: fires 0 on both plates (fresh %s sample); 10-22 whole-movement count beside" % tag)
    for r in dead:
        out.append("- %s [%s] `%s` -- fresh 0 / 0; 10-22 %d / %d; fate was: %s" % (r["rule"], r["kind"], r["code"], r["old"][0], r["old"][1], r["fate"]))
    out.append("")
    out.append("")
    out.append("### DEAD BY REASON (a reason inside a live row that fired 0 / 0 on the fresh sample; 10-22 count beside)")
    for e in scope:
        qd = _dec(inv, e.quantity)
        if all(sum(fresh[p].get((qd, r.strip()), {}).get("n", 0) for p in ("L", "B")) for r in [""]) and False:
            continue
        rs = [r.strip() for r in e.reasons.split(",")]
        if sum(sum(fresh[p].get((qd, r), {}).get("n", 0) for r in rs) for p in ("L", "B")) == 0:
            continue                      # whole row already listed above
        dd = [r for r in rs if sum(fresh[p].get((qd, r), {}).get("n", 0) for p in ("L", "B")) == 0]
        if dd:
            out.append("- %s `%s`: %s" % (e.name, e.quantity, ", ".join("%s (10-22: %d / %d)" % (r, old["L"].get((qd, r), {}).get("n", 0), old["B"].get((qd, r), {}).get("n", 0)) for r in dd)))
    out.append("")
    out.append("### SAME ANSWER AS THE OWNER (>= 95% same+merged, >= 10 refusals)")
    for r in same:
        out.append("- %s [%s] `%s` -- fires %d / %d; %s; %s" % (r["rule"], r["kind"], r["code"], r["fresh"][0], r["fresh"][1], pc(r), nearcol(r)))
    if not same:
        out.append("- (none)")
    out.append("")
    out.append("### DISAGREES (box-level parity below 95%), biggest first")
    dis.sort(key=lambda r: -sum(r["parity"][p]["refusals"] - r["parity"][p]["same"] - r["parity"][p]["merged"] for p in r["parity"]))
    for r in dis:
        a = r["parity"]
        bad = sum(a[p]["disagrees"] + a[p]["silent"] for p in a)
        out.append("- %s [%s] `%s` -- fires %d / %d; %s; not agreeing %d; %s" % (r["rule"], r["kind"], r["code"], r["fresh"][0], r["fresh"][1], pc(r), bad, nearcol(r)))
    out.append("")
    out.append("### FIRES BUT NO BOX-LEVEL PARITY POSSIBLE")
    for r in no_par:
        out.append("- %s [%s] `%s` -- fires %d / %d (10-22: %d / %d): %s" % (r["rule"], r["kind"], r["code"], r["fresh"][0], r["fresh"][1], r["old"][0], r["old"][1], r.get("why")))
    print("\n".join(out))


def _dec(inv, quantity):
    for d in inv["decisions"]:
        if d["quantity"] == quantity:
            return d["name"]
    return quantity


if __name__ == "__main__":
    main()
