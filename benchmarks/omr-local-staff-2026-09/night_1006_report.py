"""night 2026-10-06 read, step 3: NEW (20261006-night-combined) vs BASE (20261004-farhead-all), numbers first.

Reads only the small JSONs `night_1006_extract.py` and `night_1006_replay.py` wrote (and `overnight_1004_truth.py`'s
truth.json; Litolff truth heads are the 41 on page 3, the 3 on page 1 are left out so the set is 41 + 11 = 52).

  python3 night_1006_report.py <dir with x/*.json> [--json out.json]
"""
from __future__ import annotations
import collections, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import offbox_check as C
import overnight_1004_report as R

DOCS = R.DOCS
NEWTAG, BASETAG = "20261006-night-combined", "20261004-farhead-all"
SHORT = {"beethoven5-litolff": "Litolff", "brahms1-breitkopf": "Brahms"}


def pct(a, b):
    return f"{a}/{b} ({100.0 * a / b:.1f}%)" if b else f"{a}/0"


def rkey(s):
    return (s or "?").split(" (")[0].split(" -- ")[0][:60]


def filing_staff(s):
    return "staff/" + "/".join(s.split("/")[1:4])


def far_set(data):
    return {s: g for s, g in data["glyphs"].items() if R.is_far(g) and "geo" in g}


def far_population(name, data, out):
    far = far_set(data)
    dec = {s: g for s, g in far.items() if g.get("np", {}).get("outcome") == "decided"}
    absn = collections.Counter()
    nan = collections.Counter()
    for s, g in far.items():
        np_ = g.get("np") or {}
        if np_.get("outcome") == "decided":
            continue
        lr = (g.get("fh_abs") or {}).get("ledger_reason") or (np_.get("detail") or {}).get("ledger_reason") or np_.get("reason")
        if str(lr).startswith("not_a_note"):
            nan[str(lr)] += 1
        else:
            absn[rkey(lr)] += 1
    adj_nan = sum(1 for g in far.values() if (g.get("nan") or {}).get("outcome") == "decided")
    # a refused head may carry both the reader's refusal and the adjudicator's own not-a-notehead verdict
    both = sum(1 for s, g in far.items() if (g.get("nan") or {}).get("outcome") == "decided"
               and str((g.get("fh_abs") or {}).get("ledger_reason") or "").startswith("not_a_note"))
    n_nan = sum(nan.values())
    out[name] = dict(far=len(far), decided=len(dec), abstained=len(far) - len(dec) - n_nan, not_a_note_refused=n_nan,
                     abstain_by_reason=dict(absn.most_common()), not_a_note_by_reason=dict(nan.most_common()),
                     adjudicate_decided_not_a_notehead_among_far=adj_nan, both=both)
    print(f"  {name}: far heads {len(far)}; decided {len(dec)}; abstained {len(far) - len(dec) - n_nan}; refused as not-a-note {n_nan}"
          " (reader gate)")
    print("     abstained by reason:", dict(absn.most_common(8)))
    if nan:
        print("     not-a-note by why:", dict(nan.most_common()))


def iou(a, b):
    return R.iou(a, b)


def owner_witness(doc, N, B):
    """The ledger-owner witness (reason `ledger_note_first`) in NEW: the heads it decided, and the ones whose owner
    CHANGED against BASE (matched by box), split into moved-with-a-twin vs dropped (no twin box on the new staff)."""
    G = N["glyphs"]
    boxes_by_page_staff = collections.defaultdict(list)
    for s, c, b in N["boxes"]:
        if c.startswith("notehead"):
            boxes_by_page_staff[(R.page_of(s), filing_staff(s))].append((s, b))
    bybox = R.by_page(B["glyphs"])
    cand = {s: g for s, g in G.items() if (g.get("own") or {}).get("reason") == "ledger_note_first" and g["own"]["outcome"] == "decided"}
    kept = 0
    changed = collections.Counter()
    base_had = collections.Counter()
    unmatched = 0
    for s, g in cand.items():
        o = g["own"]
        fs = filing_staff(s)
        box = g.get("box")
        bo = {}
        if box:
            m, v = R.best_match(box, R.page_of(s), bybox)
            if m:
                bo = m[1].get("own") or {}
            else:
                unmatched += 1
        if o["value"] == fs:
            kept += 1
        if bo.get("outcome") == "decided" and bo.get("value") == o["value"]:
            continue                      # BASE already had this owner: the witness only agreed
        if o["value"] == fs:
            changed["to filing staff (BASE: other staff / abstained)"] += 1
            continue
        twin = False
        if box:
            for (s2, b2) in boxes_by_page_staff.get((R.page_of(s), o["value"]), []):
                if s2 != s and iou(box, b2) >= 0.5:
                    twin = True
                    break
        changed["moved off filing staff, twin on new staff" if twin else "moved off filing staff, DROPPED (no twin)"] += 1
        base_had["BASE had filing staff" if bo.get("value") == fs and bo.get("outcome") == "decided" else
                 ("BASE abstained" if bo.get("outcome") == "abstained" else "BASE had another staff / no match")] += 1
    allr = collections.Counter(g["own"]["reason"] for g in G.values() if g.get("own"))
    print(f"  witness (reason ledger_note_first) decided {len(cand)} heads ({kept} on the filing staff); NEW owner differs from BASE on "
          f"{sum(changed.values())}: {dict(changed)}")
    print(f"     for the moved-off ones: {dict(base_had)}; box-unmatched {unmatched}")
    print("     all glyph_owner reasons NEW:", dict(allr.most_common(10)))
    return dict(decided=len(cand), kept_on_filing=kept, changed=dict(changed), base_had=dict(base_had))


def truth_score(doc, N, B, truth):
    t = [h for h in truth[doc] if h["page"] == (3 if doc.startswith("beethoven") else 1)]
    cands = {"NEW": R.by_page(N["glyphs"]), "BASE": R.by_page(B["glyphs"])}
    tal = {n: collections.Counter() for n in ("NEW", "BASE", "GEO")}
    rows = []
    for h in t:
        tt = set(h["truth"])
        row = dict(subject=h["subject"], truth=h["truth"])
        for n in ("NEW", "BASE"):
            m, v = R.best_match(h["box"], h["page"], cands[n])
            if m is None:
                row[n] = ("unmatched", None, None)
                tal[n]["unmatched"] += 1
                continue
            g = m[1]
            dp, gp = R.decided_pos(g), R.geo_pos(g)
            row[n] = (m[0], dp, gp)
            tal[n]["undecided" if dp is None else ("right" if dp in tt else "wrong")] += 1
            if n == "NEW":
                tal["GEO"]["right" if gp in tt else "wrong"] += 1
        rows.append(row)
    print(f"  truth-set far heads n={len(t)}")
    for n in ("NEW", "BASE", "GEO"):
        c = tal[n]
        print(f"    {n:5s} right {c['right']:3d} wrong {c['wrong']:3d} undecided {c['undecided']:3d} unmatched {c['unmatched']:3d}")
    for r in rows:
        a, b = r["NEW"][1], r["BASE"][1]
        if a != b:
            print(f"    NEW!=BASE {r['subject']} truth {r['truth']} NEW {a} (id {r['NEW'][0]}) BASE {b} geometry {r['NEW'][2]}")
    for r in rows:
        if r["NEW"][1] is not None and r["NEW"][1] not in set(r["truth"]):
            print(f"    NEW wrong: {r['subject']} truth {r['truth']} NEW {r['NEW'][1]} geometry {r['NEW'][2]}")
    return dict(n=len(t), tally={k: dict(v) for k, v in tal.items()}, rows=rows)


def rows_for(g, m, grid=False):
    lines = m["lines"] if m and m.get("lines") else None
    if lines is None:
        return None
    return C.Rows(lines) if grid else C.Rows(lines, m["rungs"])


def offbox(doc, N, B, rn, rb, truth):
    out = {}
    for name, D, M in (("NEW", N, rn), ("BASE", B, rb)):
        far = far_set(D)
        dec = {s: g for s, g in far.items() if g.get("np", {}).get("outcome") == "decided" and "box" in g}
        H = M["heads"]
        rep = {s: g for s, g in dec.items() if H.get(s, {}).get("repro")}
        res = {}
        for label, grid in (("reader's measured rows", False), ("grid rows (reader-independent)", True)):
            on_r = on_g = n = 0
            for s, g in rep.items():
                rows = rows_for(g, H[s], grid)
                if rows is None:
                    continue
                n += 1
                on_r += C.passes(int(round(float(g["np"]["value"]))), g["box"], rows)
                on_g += C.passes(R.geo_pos(g), g["box"], rows)
            res[label] = dict(n=n, reader_on=on_r, geometry_on=on_g)
        # decided answers split by whether the reader's rows exist for them at all
        res["decided"] = len(dec)
        res["replayed_ok"] = len(rep)
        out[name] = res
        print(f"  {name}: decided far heads {len(dec)}; replay reproduced the record on {pct(len(rep), len(dec))} (census on those)")
        for label in ("reader's measured rows", "grid rows (reader-independent)"):
            r = res[label]
            print(f"     [{label}] reader ON {pct(r['reader_on'], r['n'])}   geometry ON {pct(r['geometry_on'], r['n'])}")
    # same heads in both runs: decided + replayed in NEW and in BASE (matched by box), measured rows
    bb = R.by_page(B["glyphs"])
    cnt = collections.Counter()
    for s_, g in far_set(N).items():
        if g.get("np", {}).get("outcome") != "decided" or "box" not in g or not rn["heads"].get(s_, {}).get("repro"):
            continue
        m, v = R.best_match(g["box"], R.page_of(s_), bb)
        if not m or R.decided_pos(m[1]) is None or not rb["heads"].get(m[0], {}).get("repro"):
            continue
        rN, rB = rows_for(g, rn["heads"][s_]), rows_for(m[1], rb["heads"][m[0]])
        if rN is None or rB is None:
            continue
        cnt["n"] += 1
        pn, pbv = R.decided_pos(g), R.decided_pos(m[1])
        cnt["new_on"] += C.passes(pn, g["box"], rN)
        cnt["base_on"] += C.passes(pbv, m[1]["box"], rB)
        cnt["same_answer"] += (pn == pbv)
    print(f"  SAME HEADS decided in both (n={cnt['n']}): NEW ON {pct(cnt['new_on'], cnt['n'])}  BASE ON {pct(cnt['base_on'], cnt['n'])}; same answer {pct(cnt['same_answer'], cnt['n'])}")
    out["common"] = dict(cnt)
    # CONTROL: the truth references under the same rows; a shifted reference must be flagged
    t = [h for h in truth[doc] if h["page"] == (3 if doc.startswith("beethoven") else 1)]
    for name, D, M in (("NEW", N, rn), ("BASE", B, rb)):
        cand = R.by_page(D["glyphs"])
        H = M["heads"]
        ok = fl1 = fl2 = nref = 0
        cross = collections.Counter()
        for h in t:
            m, v = R.best_match(h["box"], h["page"], cand)
            if m is None or not H.get(m[0], {}).get("repro"):
                continue
            g = m[1]
            rows = rows_for(g, H[m[0]])
            if rows is None:
                continue
            nref += 1
            tt = h["truth"][0]
            ok += C.passes(tt, g["box"], rows)
            fl1 += (not C.passes(tt - 1, g["box"], rows)) and (not C.passes(tt + 1, g["box"], rows))
            dp = R.decided_pos(g)
            if dp is not None:
                cross[("reader " + ("right" if dp in set(h["truth"]) else "wrong"), "ON" if C.passes(dp, g["box"], rows) else "OFF")] += 1
        print(f"  CONTROL {name}: truth references with measured rows n={nref}: references PASS {pct(ok, nref)}; "
              f"both +-1 shifts FLAGGED {pct(fl1, nref)}; reader right/wrong x ON/OFF {dict(cross)}")
        out[name]["control"] = dict(n=nref, ref_pass=ok, both_shift_flagged=fl1, cross={str(k): v for k, v in cross.items()})
    return out


def census(doc, N, B):
    out = {}
    for name, D in (("NEW", N), ("BASE", B)):
        c = D["census"]
        far = far_set(D)
        G = D["glyphs"]
        own_all = c["glyph_owner"]["outcome"]
        own_nonfar = collections.Counter(g["own"]["outcome"] for s, g in G.items() if g.get("own") and s not in far)
        own_far = collections.Counter(g["own"]["outcome"] for s, g in G.items() if g.get("own") and s in far)
        clef = collections.Counter(v["outcome"] for v in D["clef"].values())
        meter = collections.Counter(v["outcome"] for v in D["meter"].values())
        out[name] = dict(noteheads=c["noteheads_gathered"], far=len(far), owner_all=own_all, owner_nonfar=dict(own_nonfar),
                         owner_far=dict(own_far), clef=dict(clef), meter=dict(meter),
                         np=c["notehead_position"]["outcome"], nan=c["notehead_is_not_a_notehead"]["outcome"])
    for k in ("noteheads", "far", "owner_all", "owner_nonfar", "owner_far", "np", "nan", "clef", "meter"):
        print(f"  {k:12s} NEW {out['NEW'][k]}   BASE {out['BASE'][k]}")
    # per-staff clef and per-system meter: same subject, same answer?
    cn, cb = N["clef"], B["clef"]
    diff = [s for s in cn if s in cb and (cn[s]["outcome"], cn[s]["value"]) != (cb[s]["outcome"], cb[s]["value"])]
    mn, mb = N["meter"], B["meter"]
    mdiff = [s for s in mn if s in mb and (mn[s]["outcome"], mn[s]["value"]) != (mb[s]["outcome"], mb[s]["value"])]
    print(f"  clef verdicts: staves in both {len(set(cn) & set(cb))}; changed {len(diff)} {diff[:6]}")
    print(f"  meter verdicts: systems in both {len(set(mn) & set(mb))}; changed {len(mdiff)} {mdiff[:6]}")
    out["clef_changed"] = diff
    out["meter_changed"] = mdiff
    # >2% flags outside the far-head population
    flags = []

    def chk(label, a, b):
        if b and abs(a - b) / b > 0.02:
            flags.append((label, a, b))
    chk("noteheads gathered", out["NEW"]["noteheads"], out["BASE"]["noteheads"])
    for k in ("decided", "abstained"):
        chk(f"owner {k} (non-far heads)", out["NEW"]["owner_nonfar"].get(k, 0), out["BASE"]["owner_nonfar"].get(k, 0))
        chk(f"clef {k}", out["NEW"]["clef"].get(k, 0), out["BASE"]["clef"].get(k, 0))
        chk(f"meter {k}", out["NEW"]["meter"].get(k, 0), out["BASE"]["meter"].get(k, 0))
    print("  FLAGS (>2% change outside the far-head population):", flags or "none")
    out["flags"] = flags
    return out


def main(d, out_json=None, docs=DOCS):
    d = Path(d)
    truth = json.loads((d / "x" / "truth.json").read_text())
    summ = {}
    for doc in docs:
        N = json.loads((d / "x" / f"{doc}-{NEWTAG}.json").read_text())
        B = json.loads((d / "x" / f"{doc}-{BASETAG}.json").read_text())
        short = SHORT[doc].lower()
        rn = json.loads((d / "x" / f"rep_new_{short}.json").read_text())
        rb = json.loads((d / "x" / f"rep_base_{short}.json").read_text())
        print("=" * 100)
        print(f"{doc}: NEW {N['src'].split('/')[-1]}  BASE {B['src'].split('/')[-1]}")
        print(" replay controls:", "NEW", rn["stats"], "BASE", rb["stats"])
        s = {}
        print("\n1. FAR HEADS")
        far_population("NEW", N, s)
        far_population("BASE", B, s)
        print("   owner changes, ledger-owner witness (NEW):")
        s["owner_witness"] = owner_witness(doc, N, B)
        print("\n2. OFF-BOX CHECK (Sean's rule) on decided far heads")
        s["offbox"] = offbox(doc, N, B, rn, rb, truth)
        print("\n3. TRUTH SET")
        s["truth"] = truth_score(doc, N, B, truth)
        print("\n4. WHOLE-RECORD SANITY (GATHER+ADJUDICATE)")
        s["census"] = census(doc, N, B)
        summ[doc] = s
    if out_json:
        Path(out_json).write_text(json.dumps(summ, indent=1, default=str))


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], a[a.index("--json") + 1] if "--json" in a else None,
         tuple(a[a.index("--docs") + 1].split(",")) if "--docs" in a else DOCS)
