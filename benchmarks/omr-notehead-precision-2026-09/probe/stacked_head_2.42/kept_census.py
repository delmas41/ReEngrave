import sys
from collections import defaultdict
sys.path.insert(0, ".")
from tools.omr.staged import record_io


def main(path):
    new = record_io.load_record(path)["record"]
    refused = {v["subject"] for v in new["verdicts"]
              if v["quantity"] == "notehead_is_not_a_notehead"
              and v["reason"] == "stacked_head_duplicate"}
    groups = defaultdict(list)
    for o in new["observations"]:
        if o["quantity"] != "stacked_head_fit":
            continue
        d = o["detail"] or {}
        key = (d.get("stem"), d.get("side"), o["value"][1])
        groups[key].append(o)

    kept_inks = []
    for key, members in groups.items():
        if len(members) <= 1:
            continue
        for m in members:
            if m["subject"] not in refused:
                kept_inks.append((m["subject"], (m["detail"] or {}).get("ink")))

    n_total = len(kept_inks)
    n_real = sum(1 for _, i in kept_inks if i is not None and i > 0.5)
    print(f"{path}: contested-slot keepers = {n_total}, ink>0.5 = {n_real}")
    low = [(s, i) for s, i in kept_inks if i is None or i <= 0.5]
    print("low/none:", low)


if __name__ == "__main__":
    main(sys.argv[1])
