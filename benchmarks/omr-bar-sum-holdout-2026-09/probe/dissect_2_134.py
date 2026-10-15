"""ROADMAP 2.134: which held bars hold because of ONE lost or narrowed NOTE, and which
verdict lost it. Reads the held dumps + partitions that held_funnel_2_134.py /
classify_all_2_134.py wrote (nothing re-gathered, nothing re-decided).

A bar is "one lost/narrowed note" here iff its minimal EVIDENCED cause is a single
token in NOTE_TOKENS (a head the record refused or narrowed, whose own value
fills the gap). Chords: a chord's heads share one stem and so one decision; the
shape table says whether it was one head, one chord, or several columns.
Rests (I:*, W, A, R:rest_*), value doubt (B, G), structure (S, V, K) and the
ARITHMETIC tier are reported apart and are NOT counted as lost notes.

    python3 .../dissect_2_134.py <dir> <kind: held|partial> <out.json>
"""
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import classify_held_2_96 as K    # noqa: E402
import classify_held_mvt_2_22 as C    # noqa: E402

D = Path(sys.argv[1])
KIND = sys.argv[2]
OUT = sys.argv[3]
NOTE_TOKENS = {"N", "Y", "O", "P", "Q", "R:too_narrow", "R:clipped_fragment",
               "R:belongs_to_a_nearer_staff", "R:head_cut_piece",
               "U:too_narrow", "U:clipped_fragment", "U:belongs_to_a_nearer_staff"}


def family(tok):
    if tok in NOTE_TOKENS:
        return "NOTE"
    if tok in ("W", "A", "E") or tok.startswith("I:") or tok.startswith(("R:rest", "U:rest")):
        return "REST"
    if tok in ("B", "G"):
        return "VALUE_DOUBT"
    if tok in ("S", "V", "K"):
        return "STRUCTURE"
    if tok == "D":
        return "DOT"
    return "OTHER"


def columns(refs):
    xs = sorted(float(r["page_px"][0]) for r in refs if r.get("page_px"))
    cols = []
    for x in xs:
        if not cols or x - cols[-1] > 60:        # ~1.5 staff spaces at 600 dpi
            cols.append(x)
    return len(cols)


out = {}
for lab in ("lit", "brah"):
    H = json.load(open(D / f"{lab}-{KIND}.json"))
    P = json.load(open(D / f"{lab}-{KIND}-part.json"))
    by = {tuple(b["cell"]): b for b in H["bars"]}
    fam = collections.Counter()
    tok = collections.Counter()
    shape = collections.Counter()
    reason = collections.Counter()
    meter = collections.Counter()
    cands = collections.Counter()
    landing = collections.Counter()
    verdict = collections.Counter()
    cases = []
    for r in P["rows"]:
        if r["tier"] != "evidenced":
            fam[(r["tier"], "")] += 1
            continue
        if "+" in r["cause"]:
            fam[("evidenced compound", "")] += 1
            continue
        t = r["cause"]
        f = family(t)
        fam[("one", f)] += 1
        tok[t] += 1
        if f != "NOTE":
            continue
        b = by[tuple(r["cell"])]
        refs = [x for x in b["refused_in_cell"]
                if x["refusal"] in ("duration_narrowed", "chord_value_undecided",
                                    "too_narrow", "clipped_fragment", "head_cut_piece",
                                    "belongs_to_a_nearer_staff", "no_pitch",
                                    "owner_not_read", "owned_by_another_staff")]
        nar = [x for x in refs if x["refusal"] == "duration_narrowed"]
        use = nar if t == "N" else refs
        nh = len(use)
        nc = columns(use)
        sh = ("1 head" if nh == 1 else
              f"1 chord ({nh} heads)" if nc == 1 else
              f"{nc} columns")
        shape[(t, sh if nh < 4 else "many")] += 1
        for x in use:
            d = x.get("duration") or {}
            verdict[(t, x["refusal"], d.get("outcome"), d.get("reason"))] += 1
            reason[(t, x["refusal"], d.get("reason"))] += 1
            c = d.get("candidates") or []
            if len(c) >= 1:
                sig = tuple(sorted((round(k["value"].get("beats", 0), 3),
                                    k["value"].get("beam_levels", 0)) for k in c))
                cands[(len(c), sig)] += 1
        if t == "N":
            b["_overlap"] = C.voices_overlap(b)
            K.mark_events(b)
            b["_groups"] = K.refusal_groups(b)
            nl = K.n_landings(b, r["T"], kinds=("N",))
            landing[(sh if nh < 4 else "many", "unique" if nl == 1 else f"{nl} ways")] += 1
        sm = (b.get("system_meter") or {}).get("outcome")
        meter[(t, sm, "carried" if (b.get("system_meter") or {}).get("reason") == "carried"
               else (b.get("system_meter") or {}).get("reason"))] += 1
        if t == "N" and nh == 1:
            cases.append({"cell": r["cell"], "measure": r["measure"], "part": r["part"],
                          "T": r["T"], "residual": r["residual"],
                          "head": use[0]["glyph"], "page_px": use[0]["page_px"],
                          "box": use[0]["box"], "reason": (use[0]["duration"] or {}).get("reason"),
                          "cands": [(k["value"]["beats"], k["value"].get("beam_levels"), k["support"])
                                    for k in (use[0]["duration"] or {}).get("candidates") or []],
                          "meter": sm})
    print(f"\n## {lab} {KIND}: {len(P['rows'])} bars classified")
    print("family of the minimal evidenced cause (ONE cause):",
          {f"{a}/{b}": v for (a, b), v in sorted(fam.items(), key=lambda kv: -kv[1])})
    print("single tokens:", dict(tok.most_common(25)))
    print("NOTE shapes:", {f"{a}: {b}": v for (a, b), v in sorted(shape.items(), key=lambda kv: -kv[1])})
    print("NOTE lost by (token, refusal, duration outcome, reason):")
    for k, v in verdict.most_common(14):
        print("  ", v, k)
    print("N: shape x does the record's own candidates land the bar uniquely:",
          {f"{a} / {b}": v for (a, b), v in sorted(landing.items(), key=lambda kv: -kv[1])})
    print("NOTE meter verdict at the system:", {str(k): v for k, v in meter.most_common(8)})
    print("candidate signatures (n, [(beats, beam_levels)]):",
          {str(k): v for k, v in cands.most_common(10)})
    out[lab] = {"fam": {f"{a}/{b}": v for (a, b), v in fam.items()},
                "tok": dict(tok), "single_head_N_cases": cases}
json.dump(out, open(OUT, "w"), indent=1, default=str)
