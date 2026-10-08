"""ROADMAP 2.58d -- replay `adjudicate_glyph_owner` + `reconcile_group_owners` over a 10-07 day record, with and without the
stem witness (`OMR_STEM_OWNER`), through the real harness. GATHER+ADJUDICATE only; nothing written back.

  python3 benchmarks/omr-local-staff-2026-09/stem_owner_replay.py <litolff|brahms> <extract.pkl> <stems.json> <out.json>

ARMS on ONE tree (CLAUDE.md §6b): OFF = this branch with the flag off (the 2.58c group rule, no stem), ON = the stem
witness read. CONTROL (can fail): OFF must reproduce the record's own `glyph_owner` verdicts head for head.
"""
import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import stem_owner_lib as L  # noqa: E402
from tools.omr.staged.adjudicators import ownership as OWN  # noqa: E402
from tools.omr.staged.record import Q, Subject  # noqa: E402

#: Sean's confirmed owner answers (DECISIONS 2026-10-06..08), owner staff key per head subject.
CONFIRMED = {
    "litolff": {
        "glyph/14/0/10/4/4": "staff/14/0/10", "glyph/4/1/10/5/4": "staff/4/1/9", "glyph/14/0/10/8/3": "staff/14/0/10",
        "glyph/15/1/0/6/14": "staff/15/1/1", "glyph/12/1/3/10/0": "staff/12/1/3", "glyph/12/0/1/8/11": "staff/12/0/2",
        "glyph/10/1/8/9/6": "staff/10/1/9",
    },
    "brahms": {
        "glyph/2/1/0/2/9": "staff/2/1/1", "glyph/2/0/13/0/10": "staff/2/0/12", "glyph/10/1/2/2/21": "staff/10/1/3",
        "glyph/24/1/3/6/1": "staff/24/1/3", "glyph/7/0/6/5/13": "staff/7/0/5",
        "glyph/11/0/11/8/18": "staff/11/0/10", "glyph/13/1/8/2/4": "staff/13/1/9",
    },
}
COUNT_PAGE = {"litolff": 3, "brahms": 1}


def final_owner(log, s):
    v = log.verdict(Q.GLYPH_OWNER, Subject.from_key(s))
    return (v.outcome.value, v.value, v.reason) if v is not None else None


def main(tag, pkl, stems_json, out):
    data = L.load(pkl)
    heads = list(L.contested(data))
    stems = json.load(open(stems_json))
    rec = L.record_owner_verdicts(data)
    log0 = L.build_log(data)
    off = L.run_owner(log0, heads, False)
    census_off = OWN.reconcile_group_owners(log0)
    ctrl = [h for h in heads if h in rec]
    same = sum(1 for h in ctrl if (off[h][0], off[h][1], off[h][2]) == rec[h])
    print(f"CONTROL OFF vs record: {same}/{len(ctrl)} identical", flush=True)
    log1 = L.build_log(data, stems=stems)
    on = L.run_owner(log1, heads, True)
    census_on = OWN.reconcile_group_owners(log1)
    res = {"tag": tag, "control": [same, len(ctrl)], "census_off": census_off, "census_on": census_on, "heads": {}}
    for h in heads:
        res["heads"][h] = dict(rec=rec.get(h), off=off[h][:3], on=on[h][:3], off_final=final_owner(log0, h),
                               on_final=final_owner(log1, h), stem=stems.get(h, {}).get("direction"),
                               on_detail=(on[h][3].get("stem") or None),
                               on_flags={k: on[h][3].get(k) for k in ("stem_agrees", "stem_owner", "ledger_owner", "against")})
    json.dump(res, open(out, "w"), default=str)
    ch = collections.Counter()
    for h, r in res["heads"].items():
        if r["off"][:2] != r["on"][:2]:
            ch[(r["off"][2], r["on"][2])] += 1
    print("head-level changes (off reason -> on reason):")
    for k, n in ch.most_common():
        print(f"  {n:5d} {k}")
    print("census off", census_off)
    print("census on ", census_on)
    bad = []
    for h, want in CONFIRMED[tag].items():
        r = res["heads"].get(h)
        got = r["on_final"][1] if r and r["on_final"] else None
        base = r["off_final"][1] if r and r["off_final"] else None
        if r is None:
            print("CONFIRMED head not contested in this record:", h)
            continue
        flag = "OK " if got == want else "BAD"
        print(flag, h, "want", want, "off", base, "on", got, r["on"][2])
        if got != want:
            bad.append(h)
    print("confirmed owners broken by the stem witness:", bad)


if __name__ == "__main__":
    main(*sys.argv[1:5])
