from pathlib import Path
p=Path(__file__).resolve().parent/"estate_revision.py"
s=p.read_text(encoding="utf8")
a='''    eaves(h,p,6.65,"SlateBrown")
    wing='''
b='''    eaves(h,p,6.65,"SlateBrown")
    if h.lod<2:
        for side in (1,3):
            f0=edges(roofp)[side]
            peak=.40 if side==1 else .60
            span=f0.length
            def slope(x):
                fraction=x/span
                return 6.69+4.96*(fraction/peak if fraction<peak else (1-fraction)/(1-peak))
            posts=[span*j/(12 if h.lod==0 else 7) for j in range(1,12 if h.lod==0 else 7)]
            block(h.body,f0,.13,span-.13,6.72,6.85,.014,.126,"BrownBrick")
            for x in posts:
                block(h.body,f0,x-.062,x+.062,6.89,slope(x)-.105,.018,.136,"BrownBrick")
            if h.lod==0:
                for u,v in zip(posts[1:],posts[2:]):
                    z=min(slope(u),slope(v))-.23
                    if z>7.31:
                        beam(h,f0.point(u+.11,6.98,.158),f0.point(v-.11,z,.158),.085,"BrownBrick")
    wing='''
assert a in s
p.write_text(s.replace(a,b),encoding="utf8")
