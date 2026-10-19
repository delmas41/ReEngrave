"""2.170: the first manifest named its subjects in a dict the judged indexer does not read; rewrite it as a `tiles` list
(n, doc, subject, page_box -- no role, so nothing of the key leaks). usage: fix_manifest_2_170.py MANIFEST.json"""
import json
import sys

p = sys.argv[1]
m = json.load(open(p))
subs = m.pop("subjects", None)
if subs:
    m["tiles"] = [{"n": int(k), "doc": v["doc"], "subject": v["glyph"], "page_box": v["page_box"]}
                  for k, v in sorted(subs.items(), key=lambda kv: int(kv[0]))]
json.dump(m, open(p, "w"), indent=1)
print(len(m.get("tiles") or []), "tiles in manifest")
