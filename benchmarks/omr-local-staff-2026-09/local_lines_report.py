"""lane-local-staff-lines: the counts, per document, from `local_lines_audit.py`'s JSON.
  python3 local_lines_report.py <audit.json> [<audit.json> ...]"""
import collections, json, sys


def main(paths):
    for p in paths:
        d = json.load(open(p))
        rows = d["rows"]
        c = collections.Counter()
        ex = collections.defaultdict(list)
        for r in rows:
            c["far_heads"] += 1
            of = [v["old_flag"] for v in r["cand"].values()]
            nf = [v["new_flag"] for v in r["cand"].values()]
            own = r["cand"][r["own"]]
            for ck, v in r["cand"].items():
                c["fits"] += 1
                c["old_flagged"] += bool(v["old_flag"])
                c["new_flagged"] += bool(v["new_flag"])
                c["old_" + str(v["old_flag"])] += 1
                c["new_" + str(v["new_flag"])] += 1
                c["new_" + str(v["why"])] += bool(v["new_flag"])
                c["fit_with_fallback_line"] += bool(v["fallback"] and v["new"] is not None)
            c["heads_old_flagged_any"] += any(of)
            c["heads_old_flagged_own"] += bool(own["old_flag"])
            c["heads_new_flagged_any"] += any(nf)
            if "old" in r:
                c["replayed"] += 1
                # an answer RESTS on a flagged fit: the position was read against the own staff's old lines (flagged),
                # the owner witness read toward either candidate's old lines
                pos_rests = bool(own["old_flag"]) and r["recorded"] is not None
                own_rests = any(of) and r["old"]["word"] not in ("unread",) and r["old"]["owner"] is not None
                c["decided_pos_rests_on_flagged"] += pos_rests
                c["owner_answer_rests_on_flagged"] += own_rests
                c["owner_answer_total"] += (r["old"]["owner"] is not None)
                c["pos_changed"] += (r["old"]["pos"] != r["new"]["pos"])
                c["owner_changed"] += ((r["old"]["owner"], r["old"]["word"]) != (r["new"]["owner"], r["new"]["word"]))
                c["pos_decided_to_abstain"] += (r["old"]["pos"] is not None and r["new"]["pos"] is None)
                c["pos_abstain_to_decided"] += (r["old"]["pos"] is None and r["new"]["pos"] is not None)
                c["pos_value_to_value"] += (r["old"]["pos"] is not None and r["new"]["pos"] is not None
                                            and r["old"]["pos"] != r["new"]["pos"])
                c["repro"] += bool(r.get("repro"))
            c["decided_far_heads"] += (r["recorded"] is not None)
        print("==", d["doc"])
        for k in sorted(c):
            print("  %-34s %d" % (k, c[k]))


if __name__ == "__main__":
    main(sys.argv[1:])
