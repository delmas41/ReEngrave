"""2.299 retire study: which older key paths FIRE in the flag-OFF run, and would the new reader (same rows) have given the same reading?
    PYTHONPATH=. python3 retire_fires.py OFF.json ON.json [more pairs...]
Counts per plate: staves where `key_header_ink.raise_count` raised (detail.header_ink_slots), staves read by the 2.256b stems (key object
`from_stems` is not on the record: counted by the pieces' src), and for each raise the new reader's answer on the same row.
"""
import collections
import json
import sys

from tools.omr.staged import key_kind_slots as KKS

sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
from census import clef_read, ko_row  # noqa: E402


def main(pairs):
    for off_p, on_p in zip(pairs[0::2], pairs[1::2]):
        off, on = json.load(open(off_p)), json.load(open(on_p))
        c = collections.Counter()
        print("== ", off["plate"])
        for k, v in off["staffs"].items():
            fin = v["key"][0]
            det = fin.get("detail") if isinstance(fin.get("detail"), dict) else {}
            # the verdict chain: the staff's OWN reading is the last (earliest) link, a fill sits on top of it
            own = v["key"][-1]
            od = own.get("detail") if isinstance(own.get("detail"), dict) else {}
            raised = "header_ink_slots" in od or "header_ink_slots" in det
            row = ko_row(v)
            res = KKS.read(row, clef_read(v))
            if raised:
                c["raise_count fired (OFF)"] += 1
                if fin["decider"].startswith("infer"):
                    c["  ... and the staff is still filled by INFER"] += 1
                else:
                    c["  ... and the staff stands READ"] += 1
                fif = KKS.fifths_of(res)
                if fif is not None and fif == (own.get("value") if own.get("value") is not None else fin.get("value")):
                    c["  ... new reader gives the SAME reading on the same row"] += 1
                elif fif is not None:
                    c["  ... new reader READ a DIFFERENT value"] += 1
                else:
                    c["  ... new reader abstains (%s)" % res["why"]] += 1
            if row:
                pcs = row["ko"].get("read_pieces") or []
                if any((p or {}).get("basis") == "stem" for p in pcs):
                    c["staff with a stem-sourced slot"] += 1
        for k, n in sorted(c.items()):
            print("  %-70s %d" % (k, n))


if __name__ == "__main__":
    main(sys.argv[1:])
