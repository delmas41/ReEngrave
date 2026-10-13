import sys,json,collections; sys.path.insert(0,'.')
from tools.omr.staged.record_io import load_record
def idx(path, st, cls, near=None):
    doc=load_record(path); rec=doc['record'] if 'record' in doc else doc
    out=[]
    for o in rec['observations']:
        if o['quantity']=='glyph_box' and o['subject'].startswith('glyph/'+st+'/0/') and o['value'][0]==cls:
            out.append((o['subject'],o['value']))
    return out
L='out/ab/lit.record.json'; B='out/ab/brah.record.json'
want=[('lit',L,'1/0/0','rest8th','REFUSED: rest8th boxed over the third key flat (bar held before)'),
('lit',L,'1/0/7','rest8th','REFUSED: rest8th boxed over the third key flat (bar held before)'),
('lit',L,'1/0/11','rest8th','REFUSED: rest8th over the third flat, the middle flat never boxed (bridged slot)'),
('lit',L,'3/1/5','rest8th','REFUSED: rest8th boxed over the third key flat'),
('lit',L,'1/0/10','rest8th','CONTROL kept: rest8th 0.3 space past the window edge (flat or rest?)'),
('brah',B,'1/0/3','rest8th','CONTROL kept: rest8th 0.9 space past the window edge'),
('lit',L,'2/1/0','timeSig4','NOT refused (meter digit in key slot): a flat named a 4?'),
('lit',L,'2/1/10','timeSig1','NOT refused (meter digit in key slot): a flat named a 1?'),
('lit',L,'3/0/9','flag8thUp','NOT refused (flag in key slot)'),
('lit',L,'3/0/0','arpeggiato','NOT refused (arpeggiato in key slot)'),
('brah',B,'1/0/13','timeSig1','NOT refused (meter digit in key slot, shattering plate)'),
('brah',B,'1/1/4','timeSig2','NOT refused (meter digit in key slot, shattering plate)')]
tiles=[]
for mv,path,st,cls,why in want:
    c=idx(path,st,cls)
    print(mv,st,cls,[(s.split('/')[-1],v) for s,v in c])
    if c:
        # pick the one in the window: choose first
        tiles.append([mv,c[0][0],why])
# rest8th choice for 1/0/10 near window: pick all printed above manually later
json.dump({'records':{'lit':L,'brah':B},'tiles':tiles},open('out/ab/plan.json','w'),indent=1)
