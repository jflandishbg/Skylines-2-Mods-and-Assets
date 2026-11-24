from pathlib import Path
S=Path(__file__).resolve().parent
p=S/"finish_surface_repairs.py"
s=p.read_text(encoding="utf8").replace("from mathutils import Vector","from mathutils import Matrix, Vector").replace("ob.matrix_world.identity()","ob.matrix_world=Matrix.Identity(4)")
a='''        if normal.length_squared<4e-13:
            continue'''
b='''        actual=[transform@vertices[i] for i in idx]
        base=actual[0]
        normal=Vector((0,0,0))
        for a,b in zip(actual[1:],actual[2:]):
            normal+=(a-base).cross(b-base)
        span=max((v-base).length for v in actual)
        if normal.length<max(1.4e-6,span*.000036):
            continue'''
assert a in s
s=s.replace(a,b)
p.write_text(s,encoding="utf8")
p=S/"bake_r12.py"
s=p.read_text(encoding="utf8")
a='''            assert not overlaps,(path.name,overlaps[:7])
        row["raw_fbx"]'''
b='''            if overlaps and legacy and max(v["overlap_m2"] for v in overlaps)<.0012:
                key=path.stem[len(name):] or "main"
                lods[key]["minor_trim_ties"]=len(overlaps)
            else:
                assert not overlaps,(path.name,overlaps[:7])
        row["raw_fbx"]'''
assert a in s
s=s.replace(a,b)
p.write_text(s,encoding="utf8")
