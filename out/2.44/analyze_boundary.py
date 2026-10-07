import statistics
from tools.omr.staged import record_io

for name, path in [("Litolff p3", "out/2.44/litolff-p3-arm.json"),
                    ("Brahms p1", "out/2.44/brahms-p1-arm.json")]:
    rec = record_io.load_record(path)["record"]
    far_subjects = set()
    for o in rec["observations"]:
        if o["quantity"] == "ledger_printed_position":
            far_subjects.add(o["subject"])
    for a in rec["abstentions"]:
        if a["quantity"] == "ledger_printed_position":
            far_subjects.add(a["subject"])
    pos_by_subj = {o["subject"]: o["value"] for o in rec["observations"]
                  if o["quantity"] == "notehead_staff_position"}
    dists = []
    for s in far_subjects:
        raw = pos_by_subj.get(s)
        if raw is None:
            continue
        bd = 0.5 - abs(raw - round(raw))
        dists.append(bd)
    dists.sort()
    print(f"=== {name}: n={len(dists)} ===")
    print(" min/median/max:", dists[0], statistics.median(dists), dists[-1])
    for thr in (0.05, 0.1, 0.15, 0.2, 0.25, 0.3):
        n = sum(1 for d in dists if d <= thr)
        print(f"  <= {thr}: {n} ({100*n/len(dists):.1f}%)")
