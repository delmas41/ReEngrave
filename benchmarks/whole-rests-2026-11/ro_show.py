import json, sys
S = "/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-project-mgmt-pipeline-review-e6581e/77ea0805-f478-4ed7-b4b6-89b2b63b5322/scratchpad/"
Q = {"empty_bar_whole_rest", "empty_bar_rest_search", "rest_is_not_a_rest", "duration", "rest", "unread_mark", "glyph_owner", "rest_ink_contact", "event"}
for pl in sys.argv[1:]:
    d = json.load(open(S + "restonly-%s.json" % pl))
    print("#####", pl)
    for c, v in d.items():
        gl = [(g[1].replace("notehead", "nh"), (g[2] or "")[:30]) for g in v["glyphs"] if g[1]]
        print("==", c, v["stratum"], gl)
        for x in v["rows"]:
            if x[2] in Q:
                print("     ", x[1].split("/")[-1] if x[1].startswith("glyph") else "cell", x[2], x[3], x[4], str(x[5])[:60])
