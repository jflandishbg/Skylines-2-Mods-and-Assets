import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import round11_geometry as g
from round5_specs import make

a=next(a for a in make() if a["design"]=="MaisonSolaire" and a["lot"][1]==3)
h=g.build(a,0)
ob=h.body.object("Solaire")
hits=g.kit.overlaps(ob)
tiles=g.nb.LAYOUT["lods"]["main"]
for entry in hits[:8]:
    for i in entry["faces"]:
        f=ob.data.polygons[i]
        u,v=ob.data.uv_layers.active.data[f.loop_indices[0]].uv
        name=next((k for k,rec in tiles.items() if rec["uv"][0]-.00001<=u<=rec["uv"][2]+.00001 and rec["uv"][1]-.00001<=v<=rec["uv"][3]+.00001),"?")
        print(i,name,[tuple(round(x,4) for x in ob.data.vertices[j].co) for j in f.vertices])
