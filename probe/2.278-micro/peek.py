import sys, json, collections
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from load import load, BRAHMS
d, R = load(BRAHMS)
xs=[o for o in R.observations if o["quantity"]=="beam_stem_levels"]
print(len(xs)); print(json.dumps(xs[100])[:1200])
print(collections.Counter(str(o["value"]) for o in xs).most_common(8))
