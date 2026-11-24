from pathlib import Path
S=Path(__file__).resolve().parent
p=S/"bake_r12.py"
s=p.read_text(encoding="utf8")
s=s.replace("from legacy_r12 import build as legacy_build","from legacy_r12 import build as legacy_build\nfrom separate_legacy import separate")
a='                pairs.append((ob,tag,core.mesh_stats(ob)))'
b='''                if legacy and not tag.endswith("_Win"):
                    conflicts=kit.overlaps(ob)
                    if conflicts:
                        if lod==2:
                            # Face indices must correspond to the original loops before dissolve.
                            core.bpy.data.objects.remove(ob,do_unlink=True)
                            ob=m.object(tag,mat)
                            conflicts=kit.overlaps(ob)
                        for attempt in range(3):
                            if not conflicts:
                                break
                            separate(m,ob,conflicts)
                            core.bpy.data.objects.remove(ob,do_unlink=True)
                            ob=m.object(tag,mat)
                            conflicts=kit.overlaps(ob)
                        ob=core.optimize_far(ob,lod)
                pairs.append((ob,tag,core.mesh_stats(ob)))'''
assert a in s
s=s.replace(a,b)
p.write_text(s,encoding="utf8")
