from pathlib import Path
S=Path(__file__).resolve().parent
def patch(file,rows):
    p=S/file
    s=p.read_text(encoding="utf8")
    for a,b in rows:
        assert a in s,(file,a)
        s=s.replace(a,b)
    p.write_text(s,encoding="utf8")

patch("r12_build.py",[
 ('h.r12=True','h.r12=True\n    h.quiet_counter=0\n    h.compact_trim=a["zone_key"]=="Z2B" or a["design"]=="Familistere"\n    h.hotel=design_is_hotel=a["design"]=="HotelMeublePort"'),
])
patch("r12_geometry.py",[
 ('for x in (p[0]+.65,(p[0]+p[1])/2,p[1]-.65):','for x in ((p[0]+.65,p[1]-.65) if h.lod==2 else (p[0]+.65,(p[0]+p[1])/2,p[1]-.65)):'),
 ('            lit={s[0] for j,s in enumerate(candidates)\n                 if (j+side+i)%3==0 and (not h.estate or i==levels-1 and side in (0,2))}', 
  '            lit={s[0] for j,s in enumerate(candidates)\n                 if (h.quiet_counter+j+1)%3==0 and (not h.estate or i==levels-1 and side in (0,2))}\n            h.quiet_counter+=len(candidates)\n            if h.hotel:\n                lit={candidates[0][0]} if side==0 and i==1 and candidates else set()'),
 ('h.quiet_panes={s[0] for s in candidates}-lit','h.quiet_panes={s[0] for s in slots}-lit'),
 ('if h.lod==2 and slots:', 'if h.lod==2 and slots:'),
])
patch("detail_mesh.py",[
 ('    industry=getattr(h,"works",False)\n    span=f.length', 
  '''    industry=getattr(h,"works",False)
    if getattr(h,"compact_trim",False) and abs(f.out.x)>.5:
        from round5_geometry import block
        if z<.08:
            for l,r in gaps(slots,.08,f.length-.08,z+.025,z+.60,.15):
                block(m,f,l,r,z+.027,z+.60,.011,.162,"StoneBase")
        block(m,f,.12,f.length-.12,t-.19,t-.10,.019,.217,STONE)
        for l,r in gaps(slots,.20,f.length-.20,z+.69,t-.32,.24):
            if r-l>.34:
                u=(l+r)*.5
                block(m,f,u-.13,u+.13,z+.72,t-.27,.016,.09,mat)
        return
    span=f.length'''),
])
patch("round5_geometry.py",[
 ('    if not door and u in getattr(h,"quiet_panes",()):', '    if (not door or getattr(h,"r12",False)) and u in getattr(h,"quiet_panes",()):'),
])
patch("r12_flats.py",[
 ('b+.093),e+.005,e+.24','b+.093),e+.017,e+.24'),
 ('cover(h,(l-.012,r+.012,f-.012,b+.012),t-.29,"flat",0,"TinGreen")','cover(h,(l-.012,r+.012,f-.012,b+.012),t-.316,"flat",0,"TinGreen")'),
 ('h.quiet_panes={s[0] for s in slots if not s[5]}','h.quiet_panes={s[0] for s in slots}'),
 ('h.quiet_panes={s[0] for i,s in enumerate(slots) if (i+floor)%3}','h.quiet_panes={s[0] for i,s in enumerate(slots) if (i+floor)%3}\n        if h.lod==2 and floor==2:\n            h.quiet_panes.discard(slots[0][0])'),
])
patch("bake_r12.py",[
 ('    keep={}\n    groups=set()', '    keep={}\n    failures=[]\n    groups=set()'),
 ('        rec=asset(out,a)','        try:\n            rec=asset(out,a)\n        except Exception as exc:\n            failures.append((name,str(exc)))\n            print("ASSET_ERROR",name,type(exc).__name__,str(exc),flush=True)\n            continue'),
 ('    maps={p.relative_to(out)','    assert not failures,failures\n    maps={p.relative_to(out)'),
])
