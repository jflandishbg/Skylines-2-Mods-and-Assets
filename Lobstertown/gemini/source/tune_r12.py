from pathlib import Path

S=Path(__file__).resolve().parent
def patch(file,rows):
    p=S/file
    s=p.read_text(encoding="utf8")
    for a,b in rows:
        assert a in s,(file,a)
        s=s.replace(a,b)
    p.write_text(s,encoding="utf8")

patch("detail_mesh.py",[
    ('for x,y in divide(l+.019,r-.019,1.04 if industry else .81):','for x,y in divide(l+.019,r-.019,1.35 if getattr(h,"r12",False) else 1.04 if industry else .81):'),
    ('pitch=.78 if industry else .57','pitch=1.24 if getattr(h,"r12",False) else .78 if industry else .57'),
    ('if crown or z<.06:', 'if (crown or z<.06) and not getattr(h,"plain_piers",False):'),
    ('if h.lod==0:\n        for x,y in ((l+.008', 'if h.lod==0 and not getattr(h,"plain_frames",False):\n        for x,y in ((l+.008'),
])
patch("r12_build.py",[
    ('h.window_recess=.355','h.window_recess=.355\n    h.r12=True'),
])
patch("r12_geometry.py",[
    ('min(5,round(face.length/4.15))','min(3,round(face.length/5.2))'),
    ('n=min(n,3)','n=min(n,2)'),
    ('h.finish_cornice=i==levels-1','h.finish_cornice=i==levels-1 and side in (0,2)\n            h.plain_piers=side in (1,3)\n            h.plain_frames=side in (1,3)'),
    ('if roof_kind:\n','h.plain_piers=False\n    h.plain_frames=False\n    if roof_kind:\n'),
    ('if h.lod==2:\n        return\n    block(h.body,face,l+.009','if h.lod==2:\n        return\n    block(h.body,face,l+.009'),
    ('xyz(m,y,z+rise+.026),.061,IRON)','xyz(m+(.095 if x==r else -.095),y,z+rise+.026),.061,IRON)'),
    ('face.point(face.length*.5,top-.71,.11)','face.point(face.length*.5+(-.13 if frac<.5 else .13),top-.71,.11)'),
    ('for x,y in detail.divide(.11,face.length-.11,3.16):','for x,y in detail.divide(.11,face.length-.11,3.16 if h.lod==0 else 4.9 if h.lod==1 else 9.5):'),
    ('if h.lod<2:\n                for z in (3.19,3.44,6.65):','if h.lod==0:\n                for z in (3.19,3.44,6.65):'),
    ('if face.length==r-l and face.out.y<0:', 'if h.lod==2:\n            continue\n        if abs(face.length-(r-l))<.001 and face.out.y<0:'),
    ('3.16,6.98,STONE,(24,12,8)[h.lod])','3.16,6.98,STONE,(24,12,8)[h.lod])'),
    ('def sign(h,a,face,z,u=None,w=None):','def sign(h,a,face,z,u=None,w=None):'),
    ('z+.26,.026,.16,IRON)','z+.26,.19,.232,IRON)'),
    ('"Sign_"+a["design"],.169)','"Sign_"+a["design"],.240)'),
])
patch("r12_flats.py",[
    ('section(h,p,.05,e,4,None,omit=(0,))','section(h,p,.05,e,4,None,omit=(0,))'),
    ('if typ=="ImmeubleBowWindows":\n            for x in (l+3.24,r-3.24):\n                oriel(h,x,f,low,high)','if typ=="ImmeubleBowWindows" and (h.lod<2 or floor==1):\n            for x in (l+3.24,r-3.24):\n                oriel(h,x,f,low,e if h.lod==2 else high)'),
    ('    slab(h,p,z+.08,z+.26,STONE)\n    garden_mat','    slab(h,p,z+.08,z+.26,STONE)\n    if h.lod==2:\n        face=edges(p)[0]\n        face.quad(h.body,.01,face.length-.01,z+.29,t-.31,.002,"GardenGlass")\n        return\n    garden_mat'),
    ('slab(h,p,z+.08,z+.26,STONE)','slab(h,(l+.012,r-.012,f+.012,b-.012),z+.08,z+.26,STONE)'),
    ('cover(h,p,t-.29,"flat",0,"TinGreen")','cover(h,(l-.012,r+.012,f-.012,b+.012),t-.29,"flat",0,"TinGreen")'),
    ('z-.08,z+2.98,BRICK,slots','z-.08,z+2.98,BRICK,slots'),
    ('z=.14+3.2*j','z=.14+3.2*j'),
    ('rail(h,face,.12,face.length-.12,z+.083,.67)','if h.lod<2:\n                rail(h,face,.12,face.length-.12,z+.083,.67, .48 if h.lod==0 else .80)'),
    ('range(4)]\n            h.quiet_panes','range(4)] if h.lod==0 else []\n            h.quiet_panes'),
    ('    n=(24,12,6)[h.lod]','    n=(24,12,4)[h.lod]'),
    ('        beam(h,xyz(*a,top+.85-z/n),xyz(*b,top+.85),.041,IRON)','        if h.lod<2:\n            beam(h,xyz(*a,top+.85-z/n),xyz(*b,top+.85),.041,IRON)'),
])
