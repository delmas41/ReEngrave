import json, sys, collections
base = "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-ac21680e67803326a/benchmarks/claim-once-audit-2026-11/out/"
KINDS = ["head","ledger","accidental","dot","rest","arc","hairpin","stem","beam","flag","word_dynamic","mark","bracket","barline","clef_key_meter"]
for plate in ("brahms", "litolff"):
    d = json.load(open(base + plate + "/readout.json"))
    t = d["total"]
    sp = t["state_px"]
    mark_ink = t["ink_px"] - sp["staff_line"]
    print("\n### %s pages %s  mark ink (staff lines out) %d px" % (plate, d["pages"], mark_ink))
    one = sp["one"]; tw = sp["twin"]; cs = sp["contested_settled"]; co = sp["contested_open"]
    unc = mark_ink - one - tw - cs - co
    print("overall (share of mark ink): one owner %.1f%%  twin %.1f%%  contested settled %.1f%% open %.1f%%  unclaimed/other %.1f%%" % tuple(100.0 * x / mark_ink for x in (one, tw, cs, co, unc)))
    un = {k: v for k, v in sp.items() if k.startswith(("unclaimed", "refused", "residue", "weak", "debris", "outside"))}
    print("unclaimed classes (share of mark ink):", ", ".join("%s %.1f%%" % (k, 100.0 * v / mark_ink) for k, v in sorted(un.items(), key=lambda x: -x[1])))
    # per kind: one, twin, contested participation
    cp = collections.Counter(); cpo = collections.Counter()
    for pair, px in t["contested_by_pair"].items():
        ks, state = pair.split("|")
        for k in ks.split("+"):
            (cpo if state == "open" else cp)[k] += px
    print("%-15s %9s %9s %9s %9s %9s" % ("kind", "one px", "twin px", "cont.set", "cont.open", "any claim"))
    for k in KINDS:
        print("%-15s %9d %9d %9d %9d %9d" % (k, t["one_by_kind"].get(k, 0), t["twin_by_kind"].get(k, 0), cp[k], cpo[k], t["claimed_px_by_kind"].get(k, 0)))
    print("top contested pairs:")
    for k, v in sorted(t["contested_by_pair"].items(), key=lambda x: -x[1])[:12]:
        print("  %8d %.2f%%  %s" % (v, 100.0 * v / mark_ink, k))
    print("register-claimed px by kind (area/trace):", t["register_px_by_kind"])
