import json, sys
for i, it in enumerate(json.load(open(sys.argv[1]))):
    d = it["d"]
    print(i, it["sub"], it["reason"], "cert/poss=%s/%s" % (d.get("levels_certain"), d.get("levels_possible")), "stems=%s" % d.get("stems_attached"),
          "bfs=%s" % it.get("bfs"), "cv=%s yolo=%s kept=%s" % (d.get("cv_beams"), d.get("yolo_beams"), d.get("yolo_kept")), "nbi=%s far=%s nb=%s side=%s" % (d.get("beams_not_by_ink"), d.get("beams_far_side"), d.get("beams_neighbour_staff"), d.get("beam_side")))
