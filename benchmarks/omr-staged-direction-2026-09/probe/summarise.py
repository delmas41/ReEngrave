"""Per-document figures for FINDINGS: the family row, the census, the balance.

⚠️ REACH IS `direction_arm.py`'s JOB AND IS NOT REPEATED HERE. What this adds
is the COVERAGE view -- and one number in it is wrong in a way worth printing
beside it: `cv_glyphs` counts this family's OBSERVATIONS, which are the words
the LEXICON ACCEPTED, while the family's ink is the CANDIDATES the CV
proposed. On these documents that is 2 against 42 and 10 against 56.
"""
from __future__ import annotations

import collections
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

from tools.omr.staged import export as SX                     # noqa: E402
from tools.omr.staged.record import Q                         # noqa: E402


def one(name: str, path: str) -> None:
    r = json.loads(pathlib.Path(path).read_text())
    _xml, rep = SX.to_musicxml(r)
    cov = SX.coverage(r, rep["written"])
    row = {x["family"]: x for x in cov["families"]}["direction"]

    obs = [o for o in r["record"]["observations"]
           if o["quantity"] == Q.DIRECTION_WORD]
    refs = [a for a in r["record"]["abstentions"]
            if a["quantity"] == Q.DIRECTION_WORD]
    cand_ref = [a for a in refs if str(a["subject"]).startswith("glyph/")]
    per_page = collections.Counter(
        str(o["subject"]).split("/")[1] for o in obs + cand_ref)
    acc_page = collections.Counter(
        str(o["subject"]).split("/")[1] for o in obs)

    print(f"--- {name} ---")
    print("  provenance      :", (r.get("provenance") or {}).get("commit"),
          "dirty=", (r.get("provenance") or {}).get("dirty"))
    print("  candidates/page :", dict(sorted(per_page.items())))
    print("  accepted/page   :", dict(sorted(acc_page.items())))
    print("  family row      :",
          {k: row[k] for k in ("status", "detector_glyphs", "cv_glyphs",
                               "ink_rows", "decided", "written")})
    print("  ⚠️ cv_glyphs is the ACCEPTED count, not the ink: "
          f"{row['cv_glyphs']} against {len(obs) + len(cand_ref)} candidates")
    print("  census unaccounted:", cov["status_census"]["unaccounted"],
          "balanced:", cov["status_census"]["balanced"])
    print("  decided_and_unwritten:", rep["decided_and_unwritten"])
    print("  main balance    :", rep["balance"]["balanced"])
    print("  direction_balance:", rep["direction_balance"])
    print("  counters        : direction_words="
          f"{rep['written'].get('direction_words')} "
          f"dynamics={rep['written'].get('dynamics')}")


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        name, _sep, path = arg.partition("=")
        one(name, path or name)
