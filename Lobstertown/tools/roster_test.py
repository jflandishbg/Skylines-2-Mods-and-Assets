import subprocess,sys
R={
"MansardRow":dict(roof="mansard",wall="BuffBrick",upper="bays",hood="cap",roof_mat="Slate",door="Green",storeys=4),
"QuadDecker":dict(roof="flat",cornice="bracket",storeys=5,wall="Brick074",door="Black"),
"BayTenement":dict(roof="flat",cornice="corbel",upper="bays",wall="BrownBrick",door="Oxblood",storeys=4),
"GraniteBase":dict(roof="flat",cornice="corbel",base="granite",quoins=True,wall="Brick094",hood="pediment",storeys=5,door="GreyBlue"),
"CorniceBlock":dict(roof="flat",cornice="bracket",hood="pediment",wall="BuffBrick",door="Green",storeys=4,quoins=True),
"ShingleMansard":dict(roof="mansard",wall="ShingleGrey",upper="bays",roof_mat="SlateGreen",door="GreyBlue",storeys=4),
"HarbourLeftCorner":dict(corner=True,roof="flat",cornice="bracket",wall="Brick074",hood="cap",door="Oxblood",storeys=5),
}
for n,v in R.items():
    for W,D in ([(2,4),(2,6)] if "Corner" in n else [(1,4),(1,6),(2,4),(2,6)]):
        kw=dict(v,W=W,D=D)
        o=subprocess.run(["python3","-I","dry.py","src","harbourhill",repr(kw)],capture_output=True,text=True)
        t=[l for l in (o.stdout+o.stderr).splitlines() if "WAIVED" not in l]
        print(n,W,D,t[0] if t and "lod 0 ok" in t[0] else "FAIL "+" | ".join(t[-3:]))
