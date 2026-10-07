import collections
from tools.omr.staged import record_io

MARGIN = 0.15


def boundary_distance(raw):
    return 0.5 - abs(raw - round(raw))


for name, path in [("Litolff p3", "out/2.44/litolff-p3-arm2.json"),
                    ("Brahms p1", "out/2.44/brahms-p1-arm2.json")]:
    rec = record_io.load_record(path)["record"]
    pos_by_subj = {o["subject"]: o["value"] for o in rec["observations"]
                  if o["quantity"] == "notehead_staff_position"}
    led_abs = {}
    for a in rec["abstentions"]:
        if a["quantity"] == "ledger_printed_position":
            led_abs.setdefault(a["subject"], a["reason"])
    led_obs = {o["subject"] for o in rec["observations"]
              if o["quantity"] == "ledger_printed_position"}

    near_abs_reasons = collections.Counter()
    n_near = 0
    for s, raw in pos_by_subj.items():
        bd = boundary_distance(raw)
        if bd <= MARGIN:
            n_near += 1
            if s in led_abs:
                near_abs_reasons[led_abs[s]] += 1
    print(f"=== {name}: {n_near} near-boundary far heads ===")
    print("  abstain reasons among them:", dict(near_abs_reasons))
