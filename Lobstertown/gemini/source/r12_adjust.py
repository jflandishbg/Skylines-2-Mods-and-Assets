from pathlib import Path
S=Path(__file__).resolve().parent

def patch(f,rows):
    p=S/f
    t=p.read_text(encoding="utf8")
    for a,b in rows:
        assert a in t,(f,a)
        t=t.replace(a,b)
    p.write_text(t,encoding="utf8")

patch("bake_r12.py",[
    ('    roof_polys=[]','    roof_polys=[]\n    normals=ob.matrix_world.to_3x3().inverted().transposed()'),
    ('if poly.normal.z<.20','if (normals@poly.normal).normalized().z<.20'),
    ('        probes,audits,scans=verify_audits(out,a)','        try:\n            probes,audits,scans=verify_audits(out,a)\n        except Exception as exc:\n            failures.append((name,str(exc)))\n            print("AUDIT_ERROR",name,type(exc).__name__,str(exc),flush=True)\n            continue'),
])
patch("detail_mesh.py",[
    ('and abs(f.out.x)>.5:', 'and f.out.y>-.5:'),
])
patch("r12_flats.py",[
    ('    section(h,p,.05,e,4,None,omit=(0,))','    h.plain_frames=True\n    section(h,p,.05,e,4,None,omit=(0,))'),
    ('    n=(24,12,8)[h.lod]\n    curve=', '    n=(24,12,8)[h.lod]\n    curve='),
    ('        f.quad(h.body,0,f.length,z+.088,z+.63,0,"TinGreen")','        f.quad(h.body,0,f.length,z+.088,z+.63,0,"TinGreen")'),
    ('if k%(2 if h.lod==0 else 3)==0:', 'if h.lod<2 and k%(3 if h.lod==0 else 4)==0:'),
    ('if h.lod<2:\n            block(h.body,f,.005,f.length-.005,z+1.61,z+1.67,.008,.043,IRON)','if h.lod==0 and k%2==0:\n            f.quad(h.body,.003,f.length-.003,z+1.61,z+1.65,.016,IRON)'),
    ('h.finish_cornice=floor==3\n        g.row','h.finish_cornice=floor==3\n        h.skip_relief=typ=="ImmeubleBowWindows"\n        g.row'),
    ('g.row(h,front,low,high,BRICK,slots)\n        if typ==','g.row(h,front,low,high,BRICK,slots)\n        h.skip_relief=False\n        if typ=='),
    ('    if typ!="ImmeubleImprimeur":\n        sign', '''    if typ=="ImmeubleBowWindows" and h.lod==0:
        for x in (.36,front.length-.36):
            detail.bevel(h.body,front,x-.15,x+.15,top+.08,e-.28,.012,.115,BRICK)
        detail.bevel(h.body,front,.15,front.length-.15,e-.26,e-.13,.013,.282,STONE,shadow=True)
    if typ!="ImmeubleImprimeur":
        sign'''),
])
patch("r12_geometry.py",[
    ('h.plain_frames=side in (1,3)','h.plain_frames=side in (1,3) or (h.compact_trim and side==2)'),
])
