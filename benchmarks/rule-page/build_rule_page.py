"""Build docs/ink-rules.md -- THE RULE PAGE (ROADMAP 2.207).  STAGED path, reads only.

Sean, 2026-10-26: "The main point of our current process is to make sure all ink is accounted for one time -
our previous pass had a lot of rules - some really good and some to deal with ink erasure and double counting
boxes and ink. I don't want to lose context of the big picture or to fall into scope creep or forget what we
have learned."

    python3 benchmarks/rule-page/build_rule_page.py            # print the page
    python3 benchmarks/rule-page/build_rule_page.py --write    # write docs/ink-rules.md
    python3 benchmarks/rule-page/build_rule_page.py --check    # exit 1 if the committed page is stale
    python3 benchmarks/rule-page/count_fires.py REC OUT.json   # (slow) re-count the firing tables from a record

DERIVED, NOT RE-LISTED (CLAUDE: derive it, don't re-list it).  What the CODE gives:
  * every decision in `adjudicate.REGISTRY` and its declared closed `reasons` vocabulary (the harness raises
    `UndeclaredReason` on any other), with the module and function that owns it;
  * every EVALUATE rule (`evaluate.RULES`) and INFER rule (`infer.RULES`);
  * the post-passes `adjudicate.run` calls after a decision, and every staged/ module that is not one of those.
  * how often each fires: `fires-litolff.json` / `fires-brahms.json`, streamed (ijson) from the
    20261022-night whole-movement records by `count_fires.py` -- every verdict, by (decider, outcome, reason).
What a HUMAN gives, and only that: `rule_kinds.py` -- what the rule means and which KIND it is.  A rule the code
declares and `rule_kinds.py` does not name is printed as UNSURE; a name there that the code no longer has fails
`tools/omr/tests/test_ink_rules_page.py`.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

import rule_kinds as K  # noqa: E402

PAGE = ROOT / "docs" / "ink-rules.md"
RECORDS = {"L": "beethoven5-litolff-mvt1-whole-20261022-night", "B": "brahms1-breitkopf-mvt1-whole-20261022-night"}
KIND_WORD = {"A": "CONVENTION", "B": "ERASURE", "C": "DOUBLE-COUNT", "D": "OTHER", "U": "UNSURE"}


# ----------------------------------------------------------------------------------------------- derived
def code_inventory():
    """{'decisions': [(name, quantity, module, function, reasons)], 'evaluate': [...], 'infer': [...], 'modules': set}"""
    from tools.omr.staged import adjudicate as A, evaluate as E, infer as I
    A._ensure_decisions()
    E._ensure_rules()
    I._ensure_rules()
    decisions = []
    for quantity, s in sorted(A.REGISTRY.items(), key=lambda kv: (kv[1].fn.__module__, kv[0])):
        decisions.append(dict(name=s.name, quantity=quantity, module=s.fn.__module__.split(".")[-1],
                              function=s.fn.__name__, reasons=list(s.reasons), stub=s.stub))
    evaluate = [dict(name=r.fn.__name__, cause=r.cause, effect=r.effect, module=r.fn.__module__.split(".")[-1])
                for r in E.RULES]
    infer = [dict(name=r.inference.value, target=r.target, module=r.fn.__module__.split(".")[-1]) for r in I.RULES]
    staged = ROOT / "tools" / "omr" / "staged"
    files = sorted(p.name for p in staged.glob("*.py")) + sorted("adjudicators/" + p.name for p in (staged / "adjudicators").glob("*.py"))
    return dict(decisions=decisions, evaluate=evaluate, infer=infer, files=files)


def load_fires():
    """{plate: {(decider, reason): {'n': int, 'refused': int}}}  from the committed count files."""
    out = {}
    for plate, tag in (("L", "litolff"), ("B", "brahms")):
        d = json.load(open(HERE / f"fires-{tag}.json"))
        agg = collections.defaultdict(lambda: collections.Counter())
        for r in d["rows"]:
            c = agg[(r["decider"], r["reason"])]
            c["n"] += r["n"]
            if r["outcome"] == "decided" and r["value"] is True:
                c["refused"] += r["n"]
        out[plate] = agg
        out[plate + "_meta"] = {k: d[k] for k in ("verdicts_total", "superseded")}
    return out


def explode(entries):
    """(quantity, reason) -> entry, checking no reason is claimed twice."""
    m = {}
    for e in entries:
        for r in e.reasons.split(","):
            key = (e.quantity, r.strip())
            if key in m:
                raise SystemExit(f"rule_kinds.py names {key} twice")
            m[key] = e
    return m


# ----------------------------------------------------------------------------------------------- rows
def fmt_n(x):
    return f"{x:,}"


def fires_cell(fires, decider, reasons):
    parts = []
    for plate in ("L", "B"):
        n = sum(fires[plate].get((decider, r), {}).get("n", 0) for r in reasons)
        parts.append(fmt_n(n))
    return " / ".join(parts)


def fires_sum(fires, decider, reasons, plate):
    return sum(fires[plate].get((decider, r), {}).get("n", 0) for r in reasons)


def build():
    inv = code_inventory()
    fires = load_fires()
    by_key = explode(K.RULES)
    rows = []                       # one dict per page row
    unclassified = []
    seen_keys = set()
    decider_of = {}
    for d in inv["decisions"]:
        decider_of[d["quantity"]] = d
        groups = collections.OrderedDict()
        for r in d["reasons"]:
            if r == K.STUB_REASON:
                continue
            e = by_key.get((d["quantity"], r))
            seen_keys.add((d["quantity"], r))
            if e is None:
                groups.setdefault(None, []).append(r)
            else:
                groups.setdefault(e, []).append(r)
        for e, rs in groups.items():
            if e is not None:
                pass
            if e is None:
                unclassified.append((d, rs))
                rows.append(dict(family="unclassified", kind="U", name="NOT YET CLASSIFIED", meaning="the code declares this exit and rule_kinds.py does not name it",
                                 evidence="-", fate="open", d=d, reasons=rs, unclassified=True, order=10**6))
            else:
                rows.append(dict(family=e.family, kind=e.kind, name=e.name, meaning=e.meaning, evidence=e.evidence, fate=e.fate,
                                 d=d, reasons=rs, unclassified=False, order=K.RULES.index(e)))
    stale = sorted(k for k in by_key if k not in seen_keys)
    rows.sort(key=lambda r: r["order"])
    return inv, fires, rows, stale


def kind_letter(kind):
    return kind[0] if kind and kind[0] in "ABCDU" else kind


def render():
    inv, fires, rows, stale = build()
    # ---- counts -------------------------------------------------------------------------------
    rule_rows = [r for r in rows if r["kind"] not in ("ok",)]
    per_kind_reasons = collections.Counter()
    per_kind_fires = {"L": collections.Counter(), "B": collections.Counter()}
    for r in rule_rows:
        k = kind_letter(r["kind"])
        per_kind_reasons[k] += len(r["reasons"])
        for plate in ("L", "B"):
            per_kind_fires[plate][k] += fires_sum(fires, r["d"]["name"], r["reasons"], plate)
    # EVALUATE / INFER / passes / modules
    extra = []
    ev_fires = lambda name, plate: sum(v["n"] for (dec, rea), v in fires[plate].items() if dec == name)
    for ev in inv["evaluate"]:
        t = K.EVALUATE_RULES.get(ev["name"])
        extra.append(("EVALUATE", ev["name"], ev["module"] + "." + ev["name"], t, f"{ev['cause']} -> {ev['effect']}",
                      ev_fires(ev["name"], "L"), ev_fires(ev["name"], "B")))
    for inf in inv["infer"]:
        t = K.INFER_RULES.get(inf["name"])
        extra.append(("INFER", inf["name"], inf["module"] + "." + inf["name"], t, f"-> {inf['target']}",
                      ev_fires("infer:" + inf["name"], "L"), ev_fires("infer:" + inf["name"], "B")))
    for name, t in K.PASSES.items():
        extra.append(("ADJUDICATE post-pass", name, "adjudicate.run -> " + name, t, "", ev_fires(name, "L"), ev_fires(name, "B")))
    registered_files = {("adjudicators/" + d["module"] + ".py") for d in inv["decisions"]} | \
                       {(d["module"] + ".py") for d in inv["decisions"]}
    mods = []
    for f in inv["files"]:
        base = f.split("/")[-1]
        if f in K.MODULES:
            mods.append((f, K.MODULES[f]))
        elif f in registered_files or base in K.INFRA:
            continue
        else:
            mods.append((f, None))
    for kind_src in (extra,):
        for stage, name, code, t, note, l, b in kind_src:
            k = kind_letter(t[1]) if t else "U"
            per_kind_reasons[k] += 1
            per_kind_fires["L"][k] += l
            per_kind_fires["B"][k] += b
    for f, t in mods:
        per_kind_reasons[kind_letter(t[1]) if t else "U"] += 1
    ok_count = sum(len(r["reasons"]) for r in rows if r["kind"] == "ok")
    n_stub = len(inv["decisions"])
    n_reasons = sum(len(d["reasons"]) for d in inv["decisions"])
    total_rules = sum(per_kind_reasons.values())

    L = []
    a = L.append
    a("# The rule page: every old rule, its kind and its fate")
    a("")
    a("*Generated by `benchmarks/rule-page/build_rule_page.py` (ROADMAP 2.207). Do not edit by hand: the list of rules is read out of the code, "
      "the meaning and kind of each is in `benchmarks/rule-page/rule_kinds.py`, and `tools/omr/tests/test_ink_rules_page.py` fails if the two drift apart. "
      "Fires are counts of every verdict on the 20261022-night whole-movement records (Litolff Beethoven 5 mvt 1 / Brahms 1 Breitkopf mvt 1), "
      "from `fires-litolff.json` / `fires-brahms.json`.*")
    a("")
    a("**Why this page exists.** Sean, 2026-10-26: *\"The main point of our current process is to make sure all ink is accounted for one time - our previous pass "
      "had a lot of rules - some really good and some to deal with ink erasure and double counting boxes and ink. I don't want to lose context of the big picture "
      "or to fall into scope creep or forget what we have learned.\"* (DECISIONS 2026-10-26.)")
    a("")
    a("## Summary")
    a("")
    kinds = ["A", "B", "C", "D", "U"]
    a(f"1. **{total_rules} rule exits** are sorted ({n_reasons} declared reasons on {len(inv['decisions'])} decisions, less {ok_count} positive exits and {n_stub} stubs, "
      f"plus {len(extra)} EVALUATE/INFER/post-pass rules and {len(mods)} guard modules): "
      + ", ".join(f"**{per_kind_reasons[k]} {KIND_WORD[k]}** ({k})" for k in kinds) + ".")
    a("2. **Fires** (Litolff / Brahms verdicts, all stages): "
      + "; ".join(f"{KIND_WORD[k]} {fmt_n(per_kind_fires['L'][k])} / {fmt_n(per_kind_fires['B'][k])}" for k in kinds)
      + ". A fire is a verdict, not a note lost: most OTHER fires are bookkeeping (\"nothing to decide here\").")
    a("3. **The conventions the new path must carry** are the A rows below. The ones that fire most: "
      + ", ".join(top_conventions(rule_rows, fires)) + ".")
    a("4. **The workarounds that fire most** (B, C): " + ", ".join(top_workarounds(rule_rows, fires, extra)) + ".")
    a(f"5. **{per_kind_reasons['U']} rules are UNSURE** (section at the end): I would not guess a kind for them. "
      "Not enumerated one by one: the GATHER ink readers in `gather.py` (15k lines; the ~22 that read the erased raster are listed in 2.206 FINDINGS s2, "
      "the ~500 that re-measure ink in the 2.194 plan), the detector, and EXPORT.")
    a("")
    a("**How to read a row.** *kind*: A convention (keep) / B erasure workaround (retires with 2.206, the staff-eraser fix) / C double-count workaround (retires with 2.205 stroke ownership, "
      "or landed with 2.186 one-ink-one-mark / 2.201 accidental family) / D other (the sub-kind says what: honesty = a rule-8 \"cannot tell\" exit; bookkeeping = nothing to decide here; "
      "passthrough = an earlier refusal handed on; cutoff = a number measured on our two plates, which may only NARROW; lookup = catalog/roster/lexicon; infer = INFER, always blue) / U unsure. "
      "*code* is `decision function`: `reason, reason` (the module is in the heading). *fires* is Litolff / Brahms. "
      "*fate*: kept / retires with 2.206 / retires with 2.205 / landed (2.186-2.201) / open. A fate that says \"measure after the fix\" is a prediction from the cause, "
      "not a measurement: the rule is retired only when the three measures say so.")
    a("")
    a("Counts are of declared exits, not of distinct ink mistakes: one B rule and one C rule can act on the same bar.")
    a("")

    # ---- families -------------------------------------------------------------------------------
    fam_rows = collections.defaultdict(list)
    for r in rows:
        fam_rows[r["family"]].append(r)
    for fam in K.FAMILIES + ["unclassified"]:
        frows = fam_rows.get(fam, [])
        if not frows:
            continue
        a(f"## {fam.capitalize() if fam != 'unclassified' else 'UNCLASSIFIED (the code declares it, rule_kinds.py does not)'}")
        a("")
        rules = [r for r in frows if r["kind"] != "ok"]
        oks = [r for r in frows if r["kind"] == "ok"]
        a("| rule | kind | plain meaning | code | fires L / B | evidence | fate |")
        a("|---|---|---|---|---|---|---|")
        for r in rules:
            d = r["d"]
            code = f"`{d['name']}` ({d['module']}): " + ", ".join(f"`{x}`" for x in r["reasons"])
            a(f"| {r['name']} | {r['kind']} | {cell(r['meaning'])} | {code} | {fires_cell(fires, d['name'], r['reasons'])} | {cell(r['evidence'])} | {cell(r['fate'])} |")
        if oks:
            a("")
            a("Positive exits (the rule answered; not counted as rules): " + "; ".join(
                f"`{r['d']['name']}`: " + ", ".join(f"`{x}`" for x in r["reasons"]) + f" ({fires_cell(fires, r['d']['name'], r['reasons'])})" for r in oks) + ".")
        a("")

    # ---- EVALUATE / INFER / passes -------------------------------------------------------------
    a("## EVALUATE rules, INFER rules and post-passes")
    a("")
    a("What a settled fact FORCES (EVALUATE), what is merely MOST LIKELY and written blue (INFER), and the passes `adjudicate.run` runs after a decision. "
      "Fires are the verdicts each wrote.")
    a("")
    a("| stage | rule | kind | plain meaning | code | fires L / B | evidence | fate |")
    a("|---|---|---|---|---|---|---|---|")
    for stage, name, code, t, note, l, b in extra:
        if t:
            fam, kind, meaning, evid, fate = t
        else:
            kind, meaning, evid, fate = "U", "NOT YET CLASSIFIED", "-", "open"
        a(f"| {stage} | {name} | {kind} | {cell(meaning)} | `{code}`{' (' + note + ')' if note else ''} | {fmt_n(l)} / {fmt_n(b)} | {cell(evid)} | {cell(fate)} |")
    a("")
    a("## Guard modules (readers and guards that are not a registered decision)")
    a("")
    a("Files under `tools/omr/staged/` and `tools/omr/staged/adjudicators/` that hold a reader or a guard but are not a registered decision. "
      "Plumbing, derived checks, the exporter, `gather.py` and the stage drivers are not rules and are not listed.")
    a("")
    a("| module | kind | plain meaning | evidence | fate |")
    a("|---|---|---|---|---|")
    for f, t in mods:
        if t:
            fam, kind, meaning, evid, fate = t
        else:
            kind, meaning, evid, fate = "U", "NOT YET CLASSIFIED", "-", "open"
        a(f"| `{f}` | {kind} | {cell(meaning)} | {cell(evid)} | {cell(fate)} |")
    a("")

    # ---- unsure ---------------------------------------------------------------------------------
    a("## Unsure: for Sean")
    a("")
    a("I could not tell the kind of these from the code and the docs, and did not guess. Each is a question about WHY the rule fires, which one crop or one measurement answers.")
    a("")
    unsure = [r for r in rows if kind_letter(r["kind"]) == "U"]
    for r in unsure:
        d = r["d"]
        a(f"- **{r['name']}** (`{d['name']}`: " + ", ".join(f"`{x}`" for x in r["reasons"]) + f"; fires {fires_cell(fires, d['name'], r['reasons'])}): {r['meaning']}. Fate: {r['fate']}.")
    for stage, name, code, t, note, l, b in extra:
        if not t or kind_letter(t[1]) == "U":
            a(f"- **{name}** ({stage}): not classified.")
    for f, t in mods:
        if not t or kind_letter(t[1]) == "U":
            a(f"- **`{f}`**: " + (t[2] if t else "not classified") + ".")
    a("")
    a("## How this page stays true")
    a("")
    a("`python3 -m pytest tools/omr/tests/test_ink_rules_page.py` regenerates the list from the code and fails if a declared reason, EVALUATE/INFER rule or guard module is missing from "
      "this page, if `rule_kinds.py` names something the code no longer has, or if the committed page differs from a fresh build. To add a rule: declare it in the code, add a line to "
      "`rule_kinds.py` (or leave it and it prints as UNSURE), run `build_rule_page.py --write`. To refresh the fire counts after an overnight: run `count_fires.py` on each record "
      "and commit the two small JSON files. A lane that retires a rule says so by changing its fate here, in the same commit (CLAUDE rule 9: no restating anywhere else).")
    a("")
    a(f"Fire-count source: {fires['L_meta']['verdicts_total']:,} Litolff and {fires['B_meta']['verdicts_total']:,} Brahms verdicts "
      f"({fires['L_meta']['superseded']:,} / {fires['B_meta']['superseded']:,} later superseded by EVALUATE or INFER; they still count as a firing of the rule that wrote them).")
    return "\n".join(L) + "\n", stale


def cell(s):
    return str(s).replace("|", "/").replace("\n", " ")


def top_conventions(rule_rows, fires, n=7):
    sc = []
    for r in rule_rows:
        if kind_letter(r["kind"]) == "A" and not r["unclassified"]:
            tot = fires_sum(fires, r["d"]["name"], r["reasons"], "L") + fires_sum(fires, r["d"]["name"], r["reasons"], "B")
            sc.append((tot, r["name"]))
    sc.sort(reverse=True)
    seen, out = set(), []
    for tot, name in sc:
        if name in seen or name.startswith("a human's"):
            continue
        seen.add(name)
        out.append(f"{name} ({fmt_n(tot)})")
        if len(out) == n:
            break
    return out


def top_workarounds(rule_rows, fires, extra, n=6):
    sc = []
    for r in rule_rows:
        if kind_letter(r["kind"]) in "BC" and not r["unclassified"]:
            tot = fires_sum(fires, r["d"]["name"], r["reasons"], "L") + fires_sum(fires, r["d"]["name"], r["reasons"], "B")
            sc.append((tot, f"{r['name']} [{kind_letter(r['kind'])}]"))
    sc.sort(reverse=True)
    return [f"{name} ({fmt_n(t)})" for t, name in sc[:n]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    text, stale = render()
    if stale:
        print("rule_kinds.py names rules the code no longer declares:", stale, file=sys.stderr)
    if args.write:
        PAGE.write_text(text)
        print(f"wrote {PAGE} ({len(text.splitlines())} lines)")
    elif args.check:
        ok = PAGE.exists() and PAGE.read_text() == text and not stale
        print("fresh" if ok else "STALE")
        sys.exit(0 if ok else 1)
    else:
        print(text)


if __name__ == "__main__":
    main()
