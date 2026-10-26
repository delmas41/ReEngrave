import sys,glob,os
from PIL import Image
d=sys.argv[1]; per=int(sys.argv[2]) if len(sys.argv)>2 else 5
fs=sorted(glob.glob(os.path.join(d,'c*.png')))
W=1500
for s in range(0,len(fs),per):
    ims=[]
    for f in fs[s:s+per]:
        im=Image.open(f); r=W/im.width; im=im.resize((W,max(1,int(im.height*r)))); 
        if im.height>420: im=im.resize((int(W*420/im.height),420))
        ims.append(im)
    H=sum(i.height+8 for i in ims); sh=Image.new('RGB',(W,H),'white'); y=0
    for i in ims: sh.paste(i,(0,y)); y+=i.height+8
    sh.save(os.path.join(d,'sheet_%d.png'%(s//per)))
print('ok')
