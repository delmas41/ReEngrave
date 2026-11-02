"""Every record row on given subjects in the r3 2-page ON gather (read-only)."""
import json, sys
R = "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a54c2f8bd7e5bd469/out/2.248-r3/" + __import__("os").environ.get("RUN","far2") + "/work/%s.on.gathered.record.json"
plate = sys.argv[1]; subs = sys.argv[2:]
r = json.load(open(R % plate)); r = r.get("record", r)
print(list(r.keys()))
def short(x):
    s = json.dumps(x, default=str)
    return s if len(s) < 700 else s[:700] + "..."
for s in subs:
    print("=" * 30, s)
    for k in ("observations", "abstentions", "verdicts"):
        for o in r.get(k, []):
            if o.get("subject") == s:
                print(k[:3], short(o))
