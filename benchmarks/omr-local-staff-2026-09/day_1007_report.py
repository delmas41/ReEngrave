"""day 2026-10-07 read, step 3: NEW (`...20261007-day`, main 2baf8875) vs BASE (`...20261007-night`, main 3aef0c7d +
OMR_FARHEAD_OWNER_LEDGERS=1 OMR_MARK_GROUPS=1), GATHER+ADJUDICATE verdicts only, numbers first.  Reads only the small JSONs
`day_1007_extract.py` and `night_1007_replay.py` wrote (x/<doc>-<tag>.json, x/rep_{new,base}_<short>.json, x/truth.json).

  python3 day_1007_report.py <dir holding x/> [--docs a,b]

Far-head block, owner-change block, head_changes, clusters: reused from `night_1007_report` with the tags swapped.
New here: arcs, marks/groups/owners, dots, durations, and a per-quantity verdict diff (clef/key/meter/bars/rests/...).
"""
from __future__ import annotations
import collections, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import night_1007_report as NR
import overnight_1004_report as R

NEWTAG, BASETAG = "20261007-day", "20261007-night"
NR.R6.NEWTAG, NR.R6.BASETAG = NEWTAG, BASETAG


def jl(s):
    try:
        return json.loads(s)
    except Exception:
        return s


def vget(D, q, s):
    return D["allv"].get(f"{q}|{s}")


def subjects(D, q):
    pre = q + "|"
    return {k[len(pre):]: v for k, v in D["allv"].items() if k.startswith(pre)}


def klass(D):
    if "_cls" not in D:
        D["_cls"] = {s: str(c) for s, c, b in D["boxes"]}
    return D["_cls"]


def arcs(N, B):
    out = {}
    for name, D in (("NEW", N), ("BASE", B)):
        v = subjects(D, "arc_is_not_an_arc")
        refused = collections.Counter(x[2] for x in v.values() if x[0] == "decided" and x[1] == "true")
        kept = sum(1 for x in v.values() if not (x[0] == "decided" and x[1] == "true"))
        own = collections.Counter(f"{x[0]}:{x[2]}" for x in subjects(D, "arc_owner").values())
        out[name] = dict(arc_subjects=len(D["arc_boxes"]), refused_by_reason=dict(refused), refused=sum(refused.values()),
                         kept=kept, owner_by_outcome_reason=dict(own))
    on, ob = subjects(N, "arc_owner"), subjects(B, "arc_owner")
    rn, rb = subjects(N, "arc_is_not_an_arc"), subjects(B, "arc_is_not_an_arc")
    ch = collections.Counter()
    for s in on:
        if s not in ob:
            ch["not in BASE"] += 1
            continue
        a, b = on[s], ob[s]
        refused_new = rn.get(s, ["", "", ""])[1] == "true" and rn[s][0] == "decided"
        if (a[0], a[1]) == (b[0], b[1]):
            ch["same"] += 1
            continue
        if a[0] == "decided" and b[0] == "decided":
            k = "decided -> other staff"
        elif a[0] == "decided":
            k = "abstained -> decided"
        elif b[0] == "decided":
            k = "decided -> abstained"
        else:
            k = "abstained -> abstained (value)"
        ch[k] += 1
        ch[k + (" [arc refused as a line in NEW]" if refused_new else " [arc kept]")] += 1
        ch["by new reason " + str(a[2])] += 1
    out["owner_changes"] = dict(ch)
    # arc verdict flips that are not owner: refused in NEW but not in BASE
    out["newly_refused"] = sum(1 for s, x in rn.items() if x[0] == "decided" and x[1] == "true"
                               and not (rb.get(s, ["", "", ""])[0] == "decided" and rb.get(s)[1] == "true"))
    return out


def marks(N, B):
    out = {}
    for name, D in (("NEW", N), ("BASE", B)):
        cl = klass(D)
        own = {}
        for s, x in subjects(D, "glyph_owner").items():
            own[s] = dict(outcome=x[0], value=jl(x[1]))

        def eff(s):
            """decided owner; None if the verdict abstained; the filing staff where no contest produced a verdict."""
            o = own.get(s)
            if o is None:
                return "staff/" + "/".join(s.split("/")[1:4])
            return o["value"] if o["outcome"] == "decided" else None
        nan = {s for s, x in subjects(D, "notehead_is_not_a_notehead").items() if x[0] == "decided" and x[1] == "true"}
        by = collections.defaultdict(list)
        for s, (gid, cat) in D["mark_group"].items():
            by[gid].append((s, cat))
        res = collections.Counter()
        for fam in ("notehead", "all"):
            for gid, mem in by.items():
                subs = [s for s, c in mem if fam == "all" or cl.get(s, "").startswith("notehead")]
                if not subs:
                    continue
                if fam == "notehead":
                    subs = [s for s in subs if s not in nan] or []
                    if not subs:
                        continue
                res[f"{fam}: marks"] += 1
                if len(subs) < 2:
                    res[f"{fam}: single-box marks with no staff owning them"] += int(eff(subs[0]) is None)
                    continue
                res[f"{fam}: marks seen 2+ times"] += 1
                res[f"{fam}: extra boxes"] += len(subs) - 1
                ow = {eff(s) for s in subs} - {None}
                k = "one owner" if len(ow) == 1 else ("two or more different owners" if len(ow) > 1 else "no staff owns it")
                res[f"{fam}: 2+ groups, {k}"] += 1
                if len(ow) == 1 and any(eff(s) is None for s in subs):
                    res[f"{fam}: 2+ groups, one owner but some box abstained"] += 1
        out[name] = dict(res)
        out[name]["mark_group_rows"] = len(D["mark_group"])
        out[name]["mark_groups"] = len(by)
    return out


def dots(N, B):
    out = {}
    for name, D in (("NEW", N), ("BASE", B)):
        v = subjects(D, "dot_role")
        c = collections.Counter()
        for s, x in v.items():
            val = jl(x[1])
            role = val.get("role") if isinstance(val, dict) else val
            c[(x[0], x[2], str(role)[:30])] += 1
        out[name] = {f"{a}|{r}|{ro}": n for (a, r, ro), n in c.most_common()}
    vn, vb = subjects(N, "dot_role"), subjects(B, "dot_role")
    ch = collections.Counter()
    ex = collections.defaultdict(list)
    for s in vn:
        a, b = vn[s], vb.get(s)
        if b is None:
            ch["not in BASE"] += 1
            continue
        if a == b:
            ch["same"] += 1
            continue
        ch["role/verdict changed"] += 1
        k = f"{b[0]}:{b[2]} -> {a[0]}:{a[2]}"
        ch[k] += 1
        if len(ex[k]) < 40:
            ex[k].append(s)
    out["role_changes"] = dict(ch)
    out["role_change_examples"] = dict(ex)
    # dot owners: glyph_owner of augmentationDot boxes
    cn, cb = klass(N), klass(B)
    on, ob = subjects(N, "glyph_owner"), subjects(B, "glyph_owner")
    dc = collections.Counter()
    dex = []
    for s, c in cn.items():
        if "ugmentationDot" not in c:
            continue
        a, b = on.get(s), ob.get(s)
        dc["dot boxes"] += 1
        if a is None or b is None:
            dc["no owner verdict in one run"] += 1
            continue
        if (a[0], a[1]) != (b[0], b[1]):
            dc["dot owner changed"] += 1
            dc["  " + b[0] + " -> " + a[0]] += 1
            if len(dex) < 40:
                dex.append(s)
    out["dot_owner_changes"] = dict(dc)
    out["dot_owner_examples"] = dex
    # durations of noteheads (ADJUDICATE verdicts only)
    dn, db = subjects(N, "duration"), subjects(B, "duration")
    res = {}
    for name, DD, D in (("NEW", dn, N), ("BASE", db, B)):
        cl = klass(D)
        c = collections.Counter()
        r = collections.Counter()
        for s, x in DD.items():
            if not cl.get(s, "").startswith("notehead"):
                continue
            c[x[0]] += 1
            r[f"{x[0]}:{x[2]}"] += 1
        res[name] = dict(by_outcome=dict(c), by_reason=dict(r.most_common(10)))
    chg = collections.Counter()
    dexs = []
    cl = klass(N)
    for s, x in dn.items():
        if not cl.get(s, "").startswith("notehead"):
            continue
        y = db.get(s)
        if y is None:
            continue
        if x == y:
            chg["same"] += 1
            continue
        if x[0] != y[0]:
            chg[f"{y[0]} -> {x[0]}"] += 1
        else:
            vx, vy = jl(x[1]), jl(y[1])
            if isinstance(vx, dict) and isinstance(vy, dict) and vx.get("beats") != vy.get("beats"):
                chg["decided both, length differs"] += 1
                chg["   gained a dot" if vx.get("dots", 0) > vy.get("dots", 0) else "   other"] += 1
            else:
                chg["same outcome, reason/detail only"] += 1
        if len(dexs) < 40 and x != y:
            dexs.append(s)
    res["changes"] = dict(chg)
    out["note_durations"] = res
    return out


def verdict_diff(N, B):
    """Per quantity: how many standing verdicts changed (outcome, value or reason), by transition."""
    out = {}
    qs = collections.defaultdict(lambda: [0, 0, 0, collections.Counter(), collections.Counter(), collections.Counter()])
    for k, v in N["allv"].items():
        q, s = k.split("|", 1)
        e = qs[q]
        e[0] += 1
        e[4][v[0]] += 1
        b = B["allv"].get(k)
        if b is None:
            e[1] += 1
            continue
        if b != v:
            e[2] += 1
            e[3][f"{b[0]} -> {v[0]}" if b[0] != v[0] else "same outcome, value/reason differs"] += 1
    for k, v in B["allv"].items():
        q, s = k.split("|", 1)
        qs[q][5][v[0]] += 1
        if k not in N["allv"]:
            qs[q][1] += 1
    for q, (n, miss, ch, tr, on, ob) in sorted(qs.items()):
        if ch or miss:
            out[q] = dict(n_new=n, not_in_both=miss, changed=ch, pct=round(100.0 * ch / n, 2) if n else 0,
                          transitions=dict(tr.most_common(6)), outcomes_new=dict(on), outcomes_base=dict(ob))
    return out


def classes(N, B):
    cn = collections.Counter(c for s, c, b in N["boxes"])
    cb = collections.Counter(c for s, c, b in B["boxes"])
    return {c: (cb.get(c, 0), cn.get(c, 0)) for c in sorted(set(cn) | set(cb)) if cn.get(c, 0) != cb.get(c, 0)}


def main(d, docs):
    d = Path(d)
    NR.main(d, docs)
    summ = {}
    for doc in docs:
        N = json.loads((d / "x" / f"{doc}-{NEWTAG}.json").read_text())
        B = json.loads((d / "x" / f"{doc}-{BASETAG}.json").read_text())
        s = {}
        print("\n" + "=" * 100 + f"\n{doc}")
        s["arcs"] = arcs(N, B)
        print("ARCS", json.dumps(s["arcs"], indent=1))
        s["marks"] = marks(N, B)
        print("MARKS", json.dumps(s["marks"], indent=1))
        s["dots"] = dots(N, B)
        print("DOTS", json.dumps({k: v for k, v in s["dots"].items() if "examples" not in k}, indent=1))
        s["verdict_diff"] = verdict_diff(N, B)
        print("VERDICT DIFF per quantity (changed / n):")
        for q, e in s["verdict_diff"].items():
            print(f"  {q:38s} n={e['n_new']:6d} changed={e['changed']:5d} ({e['pct']}%) missing={e['not_in_both']} {e['transitions']}")
        s["class_counts"] = classes(N, B)
        print("detector class counts that differ (BASE, NEW):", s["class_counts"])
        summ[doc] = s
    (d / "report_day.json").write_text(json.dumps(summ, indent=1, default=str))


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], tuple(a[a.index("--docs") + 1].split(",")) if "--docs" in a else R.DOCS)
