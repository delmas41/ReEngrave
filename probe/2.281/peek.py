import json, sys, collections
p = sys.argv[1]
rec = json.load(open(p))
print(rec.keys())
V = [v for v in rec['verdicts'] if 'page_arc' in str(v.get('quantity'))]
print(len(V), collections.Counter(v['quantity'] for v in V))
v = V[0]
print(list(v.keys()))
print(json.dumps(v, default=str)[:1500])
O = [o for o in rec['observations'] if o['quantity'] == 'page_arc']
print(len(O), json.dumps(O[0], default=str)[:1200])
