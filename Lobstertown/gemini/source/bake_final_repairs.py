from pathlib import Path
S=Path(__file__).resolve().parent
def edit(file,changes):
    p=S/file
    s=p.read_text(encoding="utf8")
    for a,b in changes:
        assert a in s,(file,a)
        s=s.replace(a,b)
    p.write_text(s,encoding="utf8")

edit("audit_round5.py",[
 ('def sweep(bv,w,d,zmax):','def sweep(bv,w,d,zmax):'),
 ('            samples=[]','            samples=[]\n            faces=set()'),
 ('                        bad+=1','                        bad+=1\n                        faces.add(hit[2])'),
 ('zero_width_grid_edge_ties=seam,samples=samples)','zero_width_grid_edge_ties=seam,samples=samples,backface_polygons=sorted(faces))'),
])
edit("bake_r12.py",[
 ('from separate_legacy import separate,repair_export','from separate_legacy import separate,repair_export\nfrom finish_surface_repairs import trim,add_backings'),
 ('                repair_export(loaded,path,overlaps,kit.overlaps)','                trim(loaded,path,overlaps,kit.overlaps)'),
 ('def verify_audits(out,a):','def verify_audits(out,a,record):'),
 ('        probes[lod]=probe\n        audits[lod]=', '''        if a["reimport"] and any(x["backface_first_hits"] for x in probe.values()):
            path=out/name/(name+suffix+".fbx")
            for _ in range(4):
                ids=sorted({i for r in probe.values() for i in r["backface_polygons"]})
                if not ids:
                    break
                original=core.mesh_stats(body)["triangles"]
                extra=sum(len(body.data.polygons[i].vertices)-2 for i in ids)
                if original+extra+core.mesh_stats(pane)["triangles"]>a["budget"][SUFFIXES.index(suffix)]:
                    break
                add_backings(body,path,ids)
                scans[lod]=windows(out/name,name,suffix,layout)
                body=core.bpy.data.objects[name+suffix]
                pane=core.bpy.data.objects[name+suffix+"_Win"]
                bv,vertices=mesh_bvh(body)
                glow,_=mesh_bvh(pane)
                probe=sweep((bv,glow),w,d,max(v.z for v in vertices))
            count=core.mesh_stats(body)["triangles"]+core.mesh_stats(pane)["triangles"]
            record["lods"][lod]["triangles"]=count
            row=core.mesh_stats(body)
            row["raw_fbx"]=verify_raw(path,row["bounds_m"])
            record["meshes"][name+suffix].update(row)
            if lod=="main":
                record["tris_per_m2"]=round(count/record["envelope_m2"],3)
        probes[lod]=probe
        audits[lod]='''),
 ('probes,audits,scans=verify_audits(out,a)','probes,audits,scans=verify_audits(out,a,rec)'),
])
