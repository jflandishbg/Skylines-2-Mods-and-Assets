from pathlib import Path
S=Path(__file__).resolve().parent
p=S/"legacy_r12.py"
s=p.read_text(encoding="utf8")
s=s.replace('    tag=h.body.lodkey','    compact=a.get("compact",0)\n    tag=h.body.lodkey')
s=s.replace('if lod<2 and abs(n.z)<.03 and max(v.z for v in p)-min(v.z for v in p)>.64:',
'''if lod<2 and abs(n.z)<.03 and max(v.z for v in p)-min(v.z for v in p)>.64 and (not compact or n.y<-.65):''')
s=s.replace('if lod==0 or (lod==1 and i%2==0):','if (lod==0 and (not compact or n.y<-.35) and (compact<2 or i%2==0)) or (lod==1 and not compact and i%2==0):')
s=s.replace('            h.body.polygon([q+n*.002 for q in p],-n,"GreyBlue")','            if not compact or a["zone_key"]=="Z1B":\n                h.body.polygon([q+n*.002 for q in p],-n,"GreyBlue")')
p.write_text(s,encoding="utf8")

p=S/"finish_surface_repairs.py"
s=p.read_text(encoding="utf8")
s=s.replace('    vertices=[]\n    polys=[]','    vertices=[]\n    index_map={}\n    transform=ob.matrix_world.copy()\n    polys=[]')
s=s.replace('''            idx.append(len(vertices))
            vertices.append(p)''','''            key=tuple(round(x,6) for x in p)
            if key not in index_map:
                index_map[key]=len(vertices)
                vertices.append(p)
            idx.append(index_map[key])''')
s=s.replace('    data.from_pydata(vertices,[],polys)','    data.from_pydata([transform@v for v in vertices],[],polys)')
s=s.replace('    ob.data=data\n    bpy.data.meshes.remove(previous)','    ob.data=data\n    ob.matrix_world.identity()\n    bpy.data.meshes.remove(previous)')
p.write_text(s,encoding="utf8")

p=S/"bake_r12.py"
s=p.read_text(encoding="utf8")
start=s.index('        for grade in ')
end=s.index('            dispose()',start)
s=s[:start]+'''        levels=[0,.5,1,1.12,1.22,1.34,1.45,1.6,1.72,1.86,2.0,2.2,2.45,2.7,3.0] if legacy else [0,1,2,3]
        choices=[(g,c) for g in (levels if not lod else [0]) for c in ([0,1,2] if legacy else [0])]
        skip_grade=None
        for grade,compact in choices:
            if grade==skip_grade:
                continue
'''+s[end:]
s=s.replace('h=build(dict(a,detail_grade=grade),lod)','h=build(dict(a,detail_grade=grade,compact=compact),lod)')
a='''            if not lod:
                if not grade:
                    area=envelope(body)
                if count/area<8 and count<=limits[0] and grade<3:
                    continue
            break'''
b='''            if not lod:
                if not grade and not compact:
                    area=envelope(body)
                if count<=limits[0] and count/area<8:
                    skip_grade=grade
                    continue
            if count<=limits[lod]:
                break'''
assert a in s
s=s.replace(a,b)
a='    measure=meshes[name]["coverage"]'
b='''    for lod,suffix in enumerate(SUFFIXES):
        key=suffix or "main"
        actual=sum(meshes[name+suffix+end]["triangles"] for end in ("","_Win"))
        assert actual<=limits[lod],(name,lod,actual,limits[lod])
        lods[key]["triangles"]=actual
    measure=meshes[name]["coverage"]'''
assert a in s
s=s.replace(a,b)
p.write_text(s,encoding="utf8")
