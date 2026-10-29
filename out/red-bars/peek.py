import json, sys
R = json.load(open(sys.argv[1]))
b = R['bars_written_red']['bars_list'][0]
print({k: v for k, v in b.items() if k != 'rows'})
print(b['rows'][:3])
pb = R['partial_bars']
print({k: v for k, v in pb.items() if k != 'bars'})
print(pb['bars'][0])
print([k for k in R.keys()][:80])
