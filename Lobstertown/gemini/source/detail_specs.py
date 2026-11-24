"""Envelope quantities and family texture ownership for the detail passes."""
from math import hypot, pi
from pathlib import Path

from round5_specs import make

ROOT=Path(__file__).resolve().parents[1]
INDUSTRY=ROOT.name.endswith("round10b")
PLANS=list(make())
WIDE=list(dict.fromkeys(a["design"] for a in PLANS if a["zone_key"]=="Z1C"))
OWNERS={}

def group(a):
    if INDUSTRY:return a["family"]
    if a["zone_key"]=="Z1A":return "A"
    return "ABCD"[WIDE.index(a["design"])//3]

for entry in PLANS:
    OWNERS.setdefault((entry["zone_key"],group(entry)),entry["name"])

def atlas_owners(a):
    return group(a),OWNERS[(a["zone_key"],group(a))]

def shell(w,d,e,rise=0):
    """Area of the walls, gable ends and sloping roof, excluding the underside."""
    return 2*(w+d)*e + w*rise + 2*hypot(w/2,rise)*d

def envelope(a):
    l,r,f,b=a["walls"]
    w,d=r-l,b-f
    design=a["design"]
    if INDUSTRY:
        x0,x1,y0,y1=a["dock"]
        dock=shell(x1-x0,y1-y0,7.1 if design=="HalleFrigorifique" else 6.15)
        if a["family"]=="A":
            peak={"RedentsTissage":(7.75,2.58,4),"RedentsAteliers":(8.34,3.12,3),
                  "RedentsMenuiserie":(7.57,3.22,5)}[design]
            e,rise,count=peak
            return (2*(w+d)*e+w*rise+(hypot(w/count,rise)+rise)*d*count+dock+20)
        if a["family"]=="B":
            e={"MoulinFilature":21.45,"MoulinImprimerie":17.60,"MoulinChocolat":18.25}[design]
            return shell(w,d,e)+dock+75
        if a["family"]=="C":
            tank={"GazometreBatterie":2*pi*8.41*13.31+pi*8.05**2,"GazometreJardin":0,
                  "GazometreDouble":2*pi*(3.73*7.96+4.32*11.46)+pi*(3.37**2+3.96**2)}[design]
            return shell(w,d,5.55)+dock+tank
        e={"HalleTurbines":10.47,"HalleFonderie":12.18,"HalleFrigorifique":8.40}[design]
        extra={"HalleTurbines":116,"HalleFonderie":132,"HalleFrigorifique":59}[design]
        return shell(w,d,e,2.85)+dock+extra
    e=a["eave_m"]
    style=a["style"]
    rise={"dovecote":1.86,"jetty":3.68,"studio":4.18,"greenhouse":2.08,"camelback":1.84,
          "court":2.35,"clock":4.14,"solar":2.91,"barge":5.70,"bridge":2.41,"porch":2.88}.get(style,0)
    extra={"dovecote":59,"pergola":28,"greenhouse":2.82*d*.67+2.65*d*.67+16,"camelback":56,
           "court":74,"bridge":26,"solar":10}.get(style,0)
    if style=="split":
        return shell(a["left_end"]-l,d,e,2.87)+shell(r-a["right_start"],d,e-.65,2.01)+16
    return shell(w,d,e,rise)+extra
