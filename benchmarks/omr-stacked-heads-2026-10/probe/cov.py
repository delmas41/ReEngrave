import json,sys
def row(path):
    c=json.load(open(path)); w=c["written"]; b=c["bars_held_out_sum"]; pb=c.get("partial_bars") or {}
    nn=c.get("notes_not_written") or {}
    return {"written_notes":w.get("notes"),"guessed_notes":w.get("guessed_notes"),"rests":w.get("rests"),
            "bars_held_out":b.get("bars"),"of_bars_with_events":b.get("of_bars_with_events"),"noteheads_in_held_bars":b.get("noteheads_and_rests"),
            "partial_bars":{k:v for k,v in pb.items() if k not in("bars",)} if isinstance(pb,dict) else pb,
            "notes_not_written_total":c.get("notes_not_written_total"),
            "stacked_dup":(nn.get("not_a_notehead:stacked_head_duplicate") if isinstance(nn,dict) else None)}
for a,bp in zip(sys.argv[1::2],sys.argv[2::2]):
    print(a,json.dumps(row(bp),default=str))
