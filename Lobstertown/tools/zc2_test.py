import subprocess
R={
"TidewaterCasino":dict(storeys=4,promenade=True,roofs="gm",turret="both",spire=(1,1),towers=(("l",2,"hipl"),("r",2,"hipl")),base="Greystone",wall="ShingleSilver",gable_mat="ShingleGrey",roof_mat="SlateGreen",door="Oxblood"),
"SeaBathhouse":dict(storeys=3,promenade=False,roofs="g",turret="both",back="store",lantern=True,base="Rubble",wall="ClapSage",gable_mat="ShingleSilver",roof_mat="TinOxide",door="GreyBlue"),
"DancePavilion":dict(storeys=3,promenade=True,roofs="mmg",turret="both",lantern=True,wall="ShingleGrey",gable_mat="ShingleSilver",roof_mat="SlateDark",door="Oxblood"),
"BathingHotel":dict(storeys=5,promenade=True,roofs="g",turret="l",towers=(("c",2,"hip"),),back="store",base="Greystone",wall="Clapboard",gable_mat="ShingleGrey",roof_mat="SlateGreen",door="Black"),
}
for n,v in R.items():
    for W,D in [(4,4),(4,5),(5,5),(6,6)]:
        o=subprocess.run(["python3","-I","dry.py","src","boardwalk",repr(dict(v,W=W,D=D))],capture_output=True,text=True)
        t=[l for l in (o.stdout+o.stderr).splitlines() if "WAIVED" not in l]
        print(n,W,D,t[0] if t and "lod 0 ok" in t[0] else "FAIL "+" | ".join(t[-2:]))
