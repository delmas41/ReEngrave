#!/bin/sh
# 2.119 twins study -- order of commands (cwd = this folder; reads only from /Users/seanjohnson/Desktop/ReEngrave)
S=$(pwd); R=/Users/seanjohnson/Desktop/ReEngrave
git -C $R archive origin/main tools data/dossiers data/hand-truth docs | tar -x -C $S/tree      # main ffb66049 tree, default flags (2.117 + 2.115 ON)
cd $S/tree
nice -n 10 python3 ../extract.py $R/library/_shared-records/beethoven5-litolff-mvt1-whole-20261013-night.record.json 1 ../out/litolff_p1.json
nice -n 10 python3 ../extract.py $R/library/_shared-records/brahms1-breitkopf-mvt1-whole-20261013-night.record.json 0 ../out/brahms_p0.json
cd $S
python3 run_all.py      # truth + matching + fates + pairs -> out/analysis.json
python3 rank.py         # split points -> out/ranking.json, out/analysis_ranked.json
python3 groupstats.py   # medians per split point, bar cascade -> out/groupstats.json
python3 extra.py        # funnel, blue rules, narrowed-notes picture, owner check -> out/extra.json
python3 controls.py     # controls -> out/controls.json
python3 crops.py        # out/crops/sheet_1..5.png + LEGEND.md
