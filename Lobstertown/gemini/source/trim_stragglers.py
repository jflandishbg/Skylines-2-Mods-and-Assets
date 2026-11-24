from pathlib import Path
S=Path(__file__).resolve().parent
p=S/"finish_surface_repairs.py"
s=p.read_text(encoding="utf8")
s+='''\n\ndef remove_hidden_trim(obj,path,hits):
    # Drop small applied slivers only where an existing face covers them.
    faces=raw_faces(obj)
    remove=set()
    for hit in hits:
        small,large=sorted(hit["faces"],key=lambda i:obj.data.polygons[i].area)
        area=obj.data.polygons[small].area
        if area<=.075 and hit["overlap_m2"]>=area*.21:
            remove.add(small)
    if remove:
        replace(obj,[face for i,face in enumerate(faces) if i not in remove])
        export_fbx(obj,path)
    return bool(remove)
'''
p.write_text(s,encoding="utf8")
p=S/"bake_r12.py"
s=p.read_text(encoding="utf8").replace('import trim,add_backings','import trim,add_backings,remove_hidden_trim')
a='''                overlaps=kit.overlaps(core.bpy.context.selected_objects[0])
            if overlaps and legacy'''
b='''                overlaps=kit.overlaps(core.bpy.context.selected_objects[0])
                for _ in range(3):
                    current=core.bpy.context.selected_objects[0]
                    if not overlaps or not remove_hidden_trim(current,path,overlaps):
                        break
                    row=core.validate(path,a)
                    overlaps=kit.overlaps(core.bpy.context.selected_objects[0])
            if overlaps and legacy'''
assert a in s
s=s.replace(a,b)
p.write_text(s,encoding="utf8")
