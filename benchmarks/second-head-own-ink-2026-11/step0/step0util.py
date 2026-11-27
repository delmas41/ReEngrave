import pickle
def sp_at(S,p,y):
    st=pickle.load(open(f"{S}/st{p}.pkl","rb"))
    s=min(st,key=lambda s:0 if s['top']<=y<=s['bot'] else min(abs(y-s['top']),abs(y-s['bot'])))
    return s['sp'], s
