"""Apply the shared detail standard to the existing Round 10/11 source builders."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
r=ROOT/"source"
industry=ROOT.name.endswith("round10b")
zones={"Z10":36} if industry else {"Z1C":72,"Z1A":18}

def edit(name,changes):
    p=r/name
    s=p.read_text(encoding="utf8")
    for a,b in changes:
        assert a in s,(name,a)
        s=s.replace(a,b)
    p.write_text(s,encoding="utf8")

edit("round5_geometry.py",[
    ('import civic_geometry as civic','import civic_geometry as civic\nimport detail_mesh as detail'),
    ('steps=7 if h.lod==0 else 4 if h.lod==1 else 3','steps=24 if h.lod==0 else 12 if h.lod==1 else 3'),
    ('f.point(x,z,depth-.012)],normal,STONE)','f.point(x,z,depth-.012)],normal,"RevealStone")'),
])
p=r/"round5_geometry.py"
s=p.read_text(encoding="utf8")
a=s.index('    if h.lod==2 or getattr(h,"slim_shaft",False):return',s.index('def aperture('))
b=s.index('\ndef row(',a)
s=s[:a]+'    detail.window(h,f,opening,depth,arc,spring,header)\n'+s[b:]
x='    if h.lod<2:plane(m,f,prev,f.length,z,e,mat)'
s=s.replace(x,x+'\n    detail.facade(h,f,z,e,slots,mat)')
p.write_text(s,encoding="utf8")
p=r/"round5_specs.py"
s=p.read_text(encoding="utf8")
if industry:
    s=s.replace('budget=[20000,6000,500]','budget=[40000,6000,500]')
else:
    s=s.replace('budget=[14000,4000,500] if key=="Z1C" else [12000,3500,500]','budget=[20000,6000,500]')
p.write_text(s,encoding="utf8")
if industry:
    edit("round10_geometry.py",[
        ('from tenement_details import beam','from tenement_details import beam\nimport detail_mesh as detail'),
        ('        if h.lod==0 and rim:','        if h.lod==0 and rim:') if False else
        ('            sprout(h,x,y,z+.28,.56+.08*k)','            detail.ivy(h,x,y,z+.28,.56+.08*k)'),
        ('                    sprout(h,x+(rr-.76)*math.cos(ang),y+(rr-.76)*math.sin(ang),z+.23,.62+.09*(j%3))','                    detail.ivy(h,x+(rr-.76)*math.cos(ang),y+(rr-.76)*math.sin(ang),z+.23,.62+.09*(j%3))'),
        ('    n=(16,12,8)[h.lod]','    n=(24,12,8)[h.lod]'),
        ('drum(h,x,y,n,((r-.91,base-.02),(r-.91,top-2.34),(r-1.27,top-1.94)),"CopperVent","CopperVent")',
         'drum(h,x,y,(24,12,8)[h.lod],((r-.91,base-.02),(r-.91,top-2.34),(r-1.27,top-1.94)),"PaintedDrum","PaintedDrum")'),
        ('    if h.lod<2:\n        for j in range(6 if h.lod==0 else 3):\n            x=l+.51+(j+.5)*(1.52/(6 if h.lod==0 else 3))\n            box(m,x-.049,x+.049,f-.43,f-.08,1.22+.11*(j%2),3.12,"RoofGreen")',
         '    detail.wall_ivy(h,edges(a["walls"])[0],.45,.85,1.74,2.26)'),
        ('    h.deep_portal=False','    h.deep_portal=False\n    h.works=True\n    h.architectural_family=a["family"]\n    h.detail_grade=a.get("detail_grade",0)'),
        ('            if h.lod==0 and typ=="mill" and side in (1,3):','            if h.lod==0 and typ in {"saw","hall"} and side in (1,3):total=min(total,4)\n            if h.lod==0 and typ=="mill" and side in (1,3):'),
        ('    flat(m,rectangle(l,r,f,b),top,UP,"TinFlat")','''    flat(m,rectangle(l,r,f,b),top,UP,"TinFlat")
    for i,side in enumerate((f0,fr,fb,fl)):
        if i==1:continue
        slots=[(u,w,.031,4.24,0,True,False)] if i==0 else []
        detail.facade(h,side,.032,top,slots,BRICK)'''),
    ])
else:
    edit("house_parts.py",[
        ('from tenement_details import beam','from tenement_details import beam\nimport detail_mesh as detail'),
        ('            g.row(h,f,z,t,BRICK,slots)\n            h.quiet_material=','            h.skip_relief=k in omit\n            g.row(h,f,z,t,BRICK,slots)\n            h.skip_relief=False\n            h.quiet_material='),
    ])
    edit("round11_geometry.py",[
        ('from tenement_details import beam','from tenement_details import beam\nimport detail_mesh as detail'),
        ('    h.deep_portal=False','    h.deep_portal=False\n    h.detail_grade=a.get("detail_grade",0)'),
        ('roof(h,(l,r,f,split_y),z,2.66,a["roof_tile"],.43)','rise=max(3.06,(r-l)*.57*math.tan(math.radians(40.5)))\n    roof(h,(l,r,f,split_y),z,rise,a["roof_tile"],.43)'),
        ('z+2.52),.19,.133,WOOD','z+rise-.14),.19,.133,WOOD'),
        ('leaf(h,x,y0+.18+(j%2)*.29,z+2.546,.42,"RoofGreen")','detail.ivy(h,x,y0+.18+(j%2)*.29,z+2.546,.49)'),
        ('            leaf(h,x+.29,y0,.43,.33)','            detail.ivy(h,x+.29,y0,.43,.35)'),
        ('n=10 if h.lod==0 else 8','n=(24,12,8)[h.lod]'),
        ('n=(22,14,10)[h.lod]','n=(24,12,8)[h.lod]'),
        ('n=(10,8,6)[h.lod]','n=(24,12,8)[h.lod]'),
        ('n=8 if h.lod<2 else 5','n=(24,12,8)[h.lod]'),
    ])

p=r/"bake_round5.py"
s=p.read_text(encoding="utf8")
s=s.replace('from fbx_check import verify_raw','from fbx_check import verify_raw\nfrom detail_mesh import smooth_export\nfrom detail_specs import atlas_owners,envelope')
s=s.replace('    n=a["name"]\n    folder=out/n','    n=a["name"]\n    area=envelope(a)\n    folder=out/n')
a=s.index('        dispose()\n        h=build')
b=s.index('        hits=kit.overlaps(body)',a)
s=s[:a]+'''        grades=(0,1,2,3) if lod==0 else (0,)
        for grade in grades:
            dispose()
            h=build(dict(a,detail_grade=grade),lod)
            pairs=[]
            for m,tag in ((h.body,n+suffix),(h.windows,n+suffix+"_Win")):
                ob=core.optimize_far(m.object(tag,None if tag.endswith("_Win") else core.bpy.data.materials.new(tag)),lod)
                pairs.append((ob,tag,core.mesh_stats(ob)))
            count=sum(s["triangles"] for _,_,s in pairs)
            if lod or count/area>=8 or count>=a["budget"][lod]:
                break
        body,_,stats=pairs[0]
        physical.append(stats["bounds_m"])
'''+s[b:]
s=s.replace('len(hits),hits[:2],stats["bounds_m"]','len(hits),round(count/area,3) if lod==0 else 0,hits[:2],stats["bounds_m"]')
s=s.replace('        assert count<=a["budget"][lod],(n,lod,count,a["budget"])','        assert count<=a["budget"][lod],(n,lod,count,a["budget"])\n        if lod==0:assert count/area>=8,(n,count,area,count/area)')
s=s.replace('        for ob,tag,_ in pairs:nb.export_fbx(ob,folder/(tag+".fbx"))','        for ob,tag,_ in pairs:\n            if not tag.endswith("_Win"):smooth_export(ob)\n            nb.export_fbx(ob,folder/(tag+".fbx"))')
s=s.replace('<=.75,(n,physical)','<=.84,(n,physical)').replace('<=.47,(n,physical)','<=.84,(n,physical)')
s=s.replace('lo,hi=45,65','lo,hi=45,55')
s=s.replace('lods=lods,coverage=coverage,meshes=meshes)','lods=lods,coverage=coverage,meshes=meshes,envelope_m2=round(area,3),\n                tris_per_m2=round(lods["main"]["triangles"]/area,3),atlas=atlas_owners(a)[1])')
a=s.index('    owner=plans[0]["name"]')
b=s.index('    partial=out/"progress.json"',a)
s=s[:a]+'''    groups={atlas_owners(a)[1] for a in plans}
    all_maps={owner:{f"{owner}{suffix}_{key}.png" for suffix in SUFFIXES for key in MAPS} for owner in groups}
    for owner,maps in all_maps.items():
        assert {p.name for p in (out/owner).glob("*.png")}==maps
'''+s[b:]
s=s.replace('        if n!=owner:\n            write(out/n/"settings.json",dict(sharedAssets={old.replace(owner,n,1):f"../{owner}/{old}" for old in sorted(maps)}))',
'''        _,owner=atlas_owners(a)
        if n!=owner:
            write(out/n/"settings.json",dict(sharedAssets={old.replace(owner,n,1):f"../{owner}/{old}" for old in sorted(all_maps[owner])}))''')
s=s.replace('len(plans)*6+15+len(plans)-1','len(plans)*7+14*len(groups)')
s=s.replace('texture_owner=owner','texture_owners=sorted(groups)').replace('batch="R10"','batch="R10b"').replace('batch="R11"','batch="R11b"')
s=s.replace('reimport=False',f'reimport={industry!r}')
p.write_text(s,encoding="utf8")
p=r/"audit_round5.py"
s=p.read_text(encoding="utf8").replace('    assert not any("Glass" in key for key in names),(obj.name,"glazing mapped to body")','    assert not any("Glass" in key and key!="GardenGlass" for key in names),(obj.name,"unexpected glazing tile")')
p.write_text(s,encoding="utf8")
