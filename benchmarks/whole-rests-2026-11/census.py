import json,collections,sys
sys.path.insert(0,".");sys.path.insert(0,"benchmarks/note-loss-funnel-2026-11")
import redbars
S="/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-project-mgmt-pipeline-review-e6581e/77ea0805-f478-4ed7-b4b6-89b2b63b5322/scratchpad/2311/"
SM=json.load(open("benchmarks/lane-report/sample.json"))
out={}
for plate,tag in (("litolff","lit-a"),("brahms","bra-a")):
    f=json.load(open(S+tag+".facts.json"))
    pages=set(SM["plates"][plate]["pages"])
    bars=redbars.run(f,pages)
    cells=collections.defaultdict(list)
    for k,g in f["glyphs"].items():
        p=k.split("/")
        if len(p)==6: cells[(int(p[1]),int(p[2]),int(p[3]),int(p[4]))].append(dict(g,key=k))
    comp=collections.Counter()
    for b in bars:
        key=(b["page"],b["system"],b["staff"],b["cell"])
        ms=[g for g in cells[key] if g["head"] or g["rest"]]
        restish=[g for g in ms if (g["cls"] or "").startswith("rest")]
        nonrest=[g for g in ms if not (g["cls"] or "").startswith("rest")]
        b["n_rest_boxes"]=len(restish); b["n_other_boxes"]=len(nonrest)
        b["marks"]=[(g["cls"],g["fate"]) for g in ms]
        if not ms: c="no_box"
        elif not nonrest: c="rest_boxes_only"
        elif all(g["fate"] not in ("written","written_relocated") for g in nonrest) and restish: c="rest+refused_other"
        elif all(g["fate"] not in ("written","written_relocated") for g in nonrest): c="refused_other_only"
        else: c="has_written_note"
        b["comp"]=c; comp[c]+=1
    print(plate,len(bars),dict(comp))
    out[plate]=bars
json.dump(out,open(sys.argv[1],"w"),default=str)
