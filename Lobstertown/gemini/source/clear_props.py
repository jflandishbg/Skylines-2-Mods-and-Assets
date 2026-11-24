from pathlib import Path
S=Path(__file__).resolve().parent
p=S/"rebake_specs.py"
s=p.read_text(encoding="utf8")
a=s.index('    gates=[ent["position_lot_m"]')
b=s.index('    while len(rows)<6:',a)
s=s[:a]+'''    gates=[ent.get("gate_lot_m",ent["position_lot_m"])[0]
           for ent in a.get("active_entrances",[]) if ent.get("street_path",True) and "position_lot_m" in ent]
    if a["design"]=="VillaMurHabite":
        gates=[12.1]
    rows=rear+[prop("tree",w-2.25,d-5.2,2.45,2.45,4.6),prop("tree",w*.46,d-4.1,2.1,2.1,3.8)]
    left=.60
    for gate in sorted(gates or [w*.5]):
        right=min(w-.60,gate-1.26)
        if right-left>.90:
            rows.append(prop("hedge",(left+right)/2,1.23,right-left,.49,.78))
        left=max(left,gate+1.26)
    if w-.60-left>.90:
        right=w-.60
        rows.append(prop("hedge",(left+right)/2,1.23,right-left,.49,.78))
'''+s[b:]
s=s.replace('rows.append(prop("hedge",w-.67,d-5.1,.48,3.1,.65))',
'''rows.append(prop("hedge",.65 if len(rows)%2==0 else w-.65,d-6.4,.48,2.2,.65))''')
p.write_text(s,encoding="utf8")
p=S/"publish_rebake.py"
s=p.read_text(encoding="utf8")
s=s.replace('covered_windows=covered,exterior_backface_hits=back)', '''covered_windows=covered,exterior_backface_hits=back,
                minor_trim_ties={a["name"]:{k:v["minor_trim_ties"] for k,v in a["lods"].items() if v.get("minor_trim_ties")}
                                 for a in manifest["assets"] if any(v.get("minor_trim_ties") for v in a["lods"].values())})''')
s=s.replace('    (dest/"READ-ME-FIRST.md").write_text(text,encoding="utf8")', '''    if checks["minor_trim_ties"]:
        text+="\nThe QA summary lists any remaining small coplanar trim intersections in retained models.\n"
    text+="\nThe retained buildings preserve their original architectural massing. Secondary openings and distance proxies retain source joinery where deepening would cut through the old wall or exceed the mesh budget.\n"
    (dest/"READ-ME-FIRST.md").write_text(text,encoding="utf8")'''.replace('text+="\nThe','text+="\\nThe').replace('models.\n"','models.\\n"').replace('budget.\n"','budget.\\n"'))
p.write_text(s,encoding="utf8")
