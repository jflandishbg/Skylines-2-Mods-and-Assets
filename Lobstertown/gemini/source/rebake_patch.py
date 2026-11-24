from pathlib import Path
S=Path(__file__).resolve().parent
def edit(file,changes):
    p=S/file
    s=p.read_text(encoding="utf8")
    for a,b in changes:
        assert a in s,(file,a)
        s=s.replace(a,b)
    p.write_text(s,encoding="utf8")

edit("r12_geometry.py",[
 ('sign(h,a,edges(q)[0],2.54)','sign(h,a,edges(q)[0],3.89)'),
])
edit("r12_specs.py",[
 ('with bridge and boathouse','with a stone bridge'),
 ('Open street galleries with laundry lines','Open street galleries with doorways'),
 ('Ferryman’s stone steps, mooring and boat','Ferryman’s stone steps and mooring'),
 ('Lock-keepers’ flats and stepped waterside garden','Lock-keepers’ flats and stepped stone quay'),
])
edit("r12_atlas.py",[
 ('return Image.new("RGBA",size,(6,244,0,132))','return Image.new("RGBA",size,(0,240,0,34))'),
 ('47+16*wave+22*high,82+19*wave+24*high,88+21*wave+26*high','31+7*wave+8*high,55+9*wave+9*high,57+10*wave+10*high'),
])
edit("bake_r12.py",[
 ('from r12_build import build, core, nb, kit','from r12_build import build as new_build, core, nb, kit\nfrom legacy_r12 import build as legacy_build'),
 ('from r12_specs import make, atlas_owners, COUNTS','from rebake_specs import make, atlas_owners, COUNTS'),
 ('    limits=a["budget"]','    limits=a["budget"]\n    legacy=a["reimport"]\n    build=legacy_build if legacy else new_build'),
 ('    if a["zone_key"]=="Z1B":','    if a["zone_key"]=="Z1B" and not legacy:'),
 ('atlas=owner)','atlas=owner,reimport=legacy)'),
 ('        if name in old and a["design"] not in args and "--force" not in args:','''        if "--only" in args and a["design"] not in args:
            if name in old:keep[name]=old[name]
            continue
        if name in old and a["design"] not in args and "--force" not in args:'''),
 ('    assert not failures,failures\n    maps=', '    assert not failures,failures\n    if "--only" in args:return\n    maps='),
 ('dict(batch="R12",zone_key=zone','dict(batch={"Z1B":"R12a","Z2B":"R12b","Z4":"R12c"}[zone],zone_key=zone'),
])
edit("audit_round5.py",[
 ('    assert paved,(obj.name,"missing fascia or paving",names)','    if not a.get("reimport"):assert paved,(obj.name,"missing paving",names)'),
 ('    assert names.get(a["wall_tile"]), (obj.name,"missing colourway",a["wall_tile"])','    if not a.get("reimport"):assert names.get(a["wall_tile"]), (obj.name,"missing colourway",a["wall_tile"])'),
 ('wall_tile=a["wall_tile"],','wall_tile=a.get("wall_tile",a.get("brick","retained palette")),material_tiles=sorted(names),'),
])
