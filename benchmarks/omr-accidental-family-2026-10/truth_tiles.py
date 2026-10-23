"""2.201: Sean's answered accidental tiles (2.186b, 2.190, 2.193, 2.199b, 2.203) as one list: plate, page, page-px box, his answer.
The keys/answers are not committed (out/print); they are read from the worktrees that hold them."""
import json, os
W = "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/"
SETS = [
    ("2.186b", W + "start-here-2026-10-21-a8299c/out/print/2.186b-accidentals/"),
    ("2.190", W + "start-here-2026-10-21-a8299c/out/print/2.190-accidental-shape/"),
    ("2.193", W + "start-here-2026-10-21-a8299c/out/print/2.193-missing-naturals/"),
    ("2.199b", W + "lane-2.199/out/lane-report/2.199b/"),
    ("2.203", W + "start-here-2026-10-21-a8299c/out/print/2.203-accidental-decisions/"),
]


def norm(s):
    s = str(s).lower()
    for k in ("natural", "flat", "sharp"):
        if s.startswith(k):
            return k
    if s.startswith("none"):
        return "none"
    return None


def load():
    out = []
    for name, d in SETS:
        ans = {t["tile"]: t for t in json.load(open(d + "answers.json"))["tiles"]}
        key = json.load(open(d + "key.json"))
        key = key if isinstance(key, list) else key.get("tiles", key)
        for k in key:
            a = ans.get(k["tile"])
            if not a or norm(a.get("sean")) is None:
                continue
            out.append(dict(set=name, tile=k["tile"], plate=k["plate"], page=int(k["page"]), box=[float(v) for v in k["box"]],
                            sean=norm(a["sean"]), role=k.get("role") or k.get("population"), key=k))
    return out


if __name__ == "__main__":
    t = load()
    from collections import Counter
    print(len(t), Counter((x["plate"], x["sean"]) for x in t))
    print(sorted(Counter((x["plate"], x["page"]) for x in t).items()))
