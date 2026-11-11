"""usage: show_cls.py CLASSIFIED.json -- one line per bar"""
import json
import sys

for r in json.load(open(sys.argv[1])):
    print(r["plate"][:3], "/".join(str(k) for k in r["key"]), "m%s" % r["measure"], "%-9s" % r["family"], "d=%+.2f" % r["delta"], r["why"][:10] if r["why"] else None,
          "2v" if r["two_voice"] else "  ", r["dirs"], "notes", r["notes"])
