from pathlib import Path
p=Path(__file__).resolve().parent/"legacy_r12.py"
s=p.read_text(encoding="utf8")
s=s.replace('and max(p.z for p in points)>.17','')
s=s.replace('        if side in (1,3) and a["access"]!="Front" and not grade:\n            continue\n','')
a='''                                if grade>1:
                                    for k in range(1,grade+2):
                                        sill=z+.86+(t-z-1.53)*k/(grade+2)
                                        detail.bevel(h.body,ff,c-.14,c+.14,sill-.036,sill+.038,.094,.128,"Dressed")'''
b='''                                if grade:
                                    for zz,zt in detail.divide(z+.87,t-.70,.62 if grade==1 else .43 if grade==2 else .29):
                                        if has_wall(c,(zz+zt)/2):
                                            detail.bevel(h.body,ff,c-.148,c+.148,zz+.021,zt-.025,.096,.144,"Dressed")
            if grade>=2:
                for lo,hi in detail.gaps(row,left,right,z+.57,z+.79,.25):
                    for u,v in detail.divide(lo,hi,.58 if grade==2 else .38):
                        if v-u>.19 and has_wall((u+v)/2,z+.68):
                            detail.bevel(h.body,ff,u+.018,v-.018,z+.585,z+.754,.027,.073,"Dressed")'''
assert a in s
s=s.replace(a,b)
a='''    for i,(p,uv,n) in enumerate(good):
        if i in candidates:
            h.windows._add(p,uv)
        elif lod<2:
            h.body.polygon([q+n*.006 for q in p],n,"GreyBlue")
        if lod==0 or (lod==1 and i%2==0):
            window_bar(h,p,n,raw)
    if lod==0:
        relief_for_wall(h,a,walls,[(p,n) for p,_,n in good],raw,a.get("detail_grade",0))
    return h'''
b='''    for i,(p,uv,n) in enumerate(good):
        if lod==0 or (lod==1 and i%2==0):
            window_bar(h,p,n,raw)
    if lod==0:
        relief_for_wall(h,a,walls,[(p,n) for p,_,n in good],raw,a.get("detail_grade",0))
    if lod<2:
        vertices=[Vector(v) for v in h.body.vertices]
        tree=BVHTree.FromPolygons(vertices,h.body.faces)
        allowed={"Iron","TinGreen","Black","Green","Mustard","TinOxide"}
        def clear(p,n):
            mid=midpoint(p)
            samples=[mid]+[mid.lerp(q,.54) for q in p]+[mid.lerp((x+y)/2,.71) for x,y in zip(p,p[1:]+p[:1])]
            blocked=0
            for point in samples:
                hit,norm,index,dist=tree.ray_cast(point+n*.012,n,1.188)
                if hit is None or norm.dot(n)<.94 or tile(h.body.uvs[index],target) in allowed:
                    continue
                outside=tree.ray_cast(point+n*180,-n,180)[0]
                if outside is not None and (outside-hit).length<=.018:
                    blocked+=1
            return blocked<2
        candidates=[j for j in candidates if clear(good[j][0],good[j][2])]
        if not candidates:
            candidates=[j for j,(p,uv,n) in enumerate(good) if clear(p,n)][:1]
    for i,(p,uv,n) in enumerate(good):
        if i in candidates:
            h.windows._add(p,uv)
        elif lod<2:
            h.body.polygon([q+n*.006 for q in p],n,"GreyBlue")
    return h'''
assert a in s
s=s.replace(a,b)
p.write_text(s,encoding="utf8")
p=p.with_name("bake_r12.py")
s=p.read_text(encoding="utf8").replace('for attempt in range(3):','for attempt in range(7):').replace('and "--force" not in args:','and "--force" not in args and not ("--redo-legacy" in args and a["reimport"]):')
p.write_text(s,encoding="utf8")
p=p.with_name("separate_legacy.py")
s=p.read_text(encoding="utf8").replace('slot*.00075','slot*.00118')
p.write_text(s,encoding="utf8")
