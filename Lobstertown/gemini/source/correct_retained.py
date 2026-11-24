from pathlib import Path
S=Path(__file__).resolve().parent
p=S/"legacy_r12.py"
s=p.read_text(encoding="utf8")
s=s.replace('if grade>=2:', 'if grade>1:')
s=s.replace('for u,v in detail.divide(lo,hi,.58 if grade==2 else .38):','for u,v in detail.divide(lo,hi,.61 if grade<2 else .46):')
s=s.replace('if v-u>.19 and has_wall((u+v)/2,z+.68):','if v-u>.19 and abs(math.sin(u*493.8+z*173.1+side*231.7))<min(1,(grade-1)*.65) and has_wall((u+v)/2,z+.68):')
s=s.replace('if grade:\n                                    for zz,zt', 'if grade>=.5:\n                                    for zz,zt')
s=s.replace('.62 if grade==1 else .43 if grade==2 else .29','.75 if grade<1 else .57 if grade<2 else .36')
a='''        elif lod<2:
            h.body.polygon([q+n*.006 for q in p],n,"GreyBlue")'''
b='''        elif lod<2:
            h.body.polygon([q+n*.006 for q in p],n,"GreyBlue")
            h.body.polygon([q+n*.002 for q in p],-n,"GreyBlue")'''
assert a in s
s=s.replace(a,b)
p.write_text(s,encoding="utf8")

p=S/"bake_r12.py"
s=p.read_text(encoding="utf8")
s=s.replace('from separate_legacy import separate','from separate_legacy import separate,repair_export')
s=s.replace('for grade in ([0,1,2,3] if lod==0 else [0]):','for grade in (([0,.5,1,1.22,1.45,1.72,2.0,2.45,3.0] if legacy else [0,1,2,3]) if lod==0 else [0]):')
a='''        row=core.validate(path,a)
        row["raw_fbx"]=verify_raw(path,row["bounds_m"])
        if not path.stem.endswith("_Win"):
            overlaps=kit.overlaps(core.bpy.context.selected_objects[0])
            assert not overlaps,(path.name,overlaps[:7])
        meshes[path.stem]=row'''
b='''        row=core.validate(path,a)
        if not path.stem.endswith("_Win"):
            loaded=core.bpy.context.selected_objects[0]
            overlaps=kit.overlaps(loaded)
            if legacy and overlaps:
                repair_export(loaded,path,overlaps,kit.overlaps)
                row=core.validate(path,a)
                overlaps=kit.overlaps(core.bpy.context.selected_objects[0])
            assert not overlaps,(path.name,overlaps[:7])
        row["raw_fbx"]=verify_raw(path,row["bounds_m"])
        meshes[path.stem]=row'''
assert a in s
s=s.replace(a,b)
p.write_text(s,encoding="utf8")
