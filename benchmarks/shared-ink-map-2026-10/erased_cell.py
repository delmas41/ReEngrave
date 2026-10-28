"""ROADMAP 2.202 cause study: re-cut ONE cell (same code as the gather) and draw `image_no_staff` with the stroke boxes (left) beside `binary` with the staff lines (right).
usage: erased_cell.py PLATE PAGE SYSTEM STAFF CELL OUT.png   (the stroke map reads the LEFT panel; a beam lying on a staff line is thinned there)."""
import json,sys
sys.path.insert(0,'.')
import cv2, numpy as np
from tools.omr.staged import pipeline, gather as G, stroke_map as S
LIB="/Users/seanjohnson/Desktop/ReEngrave/library/"
PDF={"litolff":LIB+"editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf","brahms":LIB+"editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
plate,page,sysi,st,cell=sys.argv[1],int(sys.argv[2]),int(sys.argv[3]),int(sys.argv[4]),int(sys.argv[5]); out=sys.argv[6]
pws,cells=pipeline.prepare_pages(PDF[plate],[page],dpi=600)[0]
loc=G.gather_geometry(G.Log(),pws)
c=next(c for c in cells if loc.get(c.staff_index)==(sysi,st) and c.measure_index==cell)
g=G._cell_grid(c)
r=S.map_strokes(c.image_no_staff,g[1]*2,c.staff_line_ys_canonical,c.binary)
a=cv2.cvtColor(c.image_no_staff,cv2.COLOR_GRAY2BGR); b=cv2.cvtColor(c.binary if c.binary.ndim==2 else c.binary[:,:,0],cv2.COLOR_GRAY2BGR) if True else None
print(c.image_no_staff.shape,c.binary.shape,c.binary.dtype,c.binary.max())
for s in r.strokes:
    x,y,w,h=s.box; cv2.rectangle(a,(x,y),(x+w,y+h),(0,0,255) if s.kind=='vertical' else (255,0,0),2)
# staff line positions
for y in c.staff_line_ys_canonical: cv2.line(b,(0,int(y)),(b.shape[1],int(y)),(0,200,0),1)
cv2.imwrite(out,np.hstack([cv2.resize(a,None,fx=0.35,fy=0.35),cv2.resize(b,None,fx=0.35,fy=0.35)]))
