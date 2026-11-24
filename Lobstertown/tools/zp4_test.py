import subprocess
R={
"UCourt":dict(layout="U",wall="ShingleGrey",office_wall="Clapboard",roof_mat="SlateDark",door="Green"),
"LCourt":dict(layout="L",wall="ShingleSilver",office_wall="ClapSage",roof_mat="TinOxide",door="Oxblood"),
"DoubleRow":dict(layout="R",wall="Clapboard",office_wall="ShingleGrey",roof_mat="SlateGreen",door="GreyBlue"),
"GambrelCourt":dict(layout="U",roof="gambrel",wall="ShingleSilver",office_wall="Clapboard",roof_mat="SlateDark",door="Black"),
"RubbleCourt":dict(layout="L",wall="Rubble",office_wall="ShingleGrey",base=None,roof_mat="SlateGreen",door="Oxblood"),
"OfficeCourt":dict(layout="R",roof="gambrel",wall="ClapSage",office_wall="Rubble",roof_mat="TinOxide",door="GreyBlue"),
}
import sys
sys.path.insert(0,"src/lt_designs")
from courtplan import plan
for n,v in R.items():
    for W,D in [(3,5),(4,5),(4,6)]:
        o=subprocess.run(["python3","-I","dry.py","src","motorcourt",repr(dict(v,W=W,D=D))],capture_output=True,text=True)
        t=[l for l in (o.stdout+o.stderr).splitlines() if "WAIVED" not in l]
        print(n,W,D,"hh",plan(v["layout"],W,D)["hh"],t[0] if t and "lod 0 ok" in t[0] else "FAIL "+" | ".join(t[-2:])[:300])
