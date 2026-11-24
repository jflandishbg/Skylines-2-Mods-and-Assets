import os, json, re, collections, sys
G = "C:/Users/<you>/CS2Planner/Lobstertown/GPT_INBOX/"
ID = "C:/Users/<you>/AppData/LocalLow/Colossal Order/Cities Skylines II/ImportedData/47e9fcd660d2d72a/"
installed = {d for d in os.listdir(ID) if os.path.isdir(ID+d)}
bad = re.compile(r"grass|ivy|leaf|foliage|\bplant\b|planting|planter|vine|moss|crate|bench|laundry|boat|fern|flower|water|canal|basin|bassin|pool|pond|bed\b", re.I)
for r in sys.argv[1:]:
    base = G+(r if r.startswith("20") else "2026-11-11_"+r)+"/"
    for imp in sorted(d for d in os.listdir(base) if d.startswith("import_")):
        ip = base+imp+"/"
        names = sorted(d for d in os.listdir(ip) if os.path.isdir(ip+d))
        same = [n for n in names if n in installed]
        print(f"== {r} {imp}: {len(names)} folders, {len(same)} same-name, {len(names)-len(same)} new: {[n for n in names if n not in installed][:4]}")
        owners = 0; broken = 0
        for n in names:
            fs = os.listdir(ip+n)
            if len([f for f in fs if f.endswith('.fbx')]) != 6: print("  FBX count", n)
            if any(f.endswith('.png') for f in fs): owners += 1
            sp = ip+n+"/settings.json"
            if os.path.exists(sp):
                for k,v in json.load(open(sp,encoding="utf-8")).get("sharedAssets",{}).items():
                    if not os.path.exists(os.path.normpath(ip+n+"/"+v)): broken += 1
        print(f"  atlas owners {owners}, broken links {broken}")
        a = json.load(open(ip+"audit.json", encoding="utf-8")) if os.path.exists(ip+"audit.json") else {}
        tiles = set()
        for n,v in a.items():
            if isinstance(v, dict):
                for lod,x in v.items():
                    if isinstance(x, dict): tiles.update(x.get("material_tiles",[]))
        print("  FLAG tiles:", [t for t in tiles if bad.search(t)], "| tiles", len(tiles))
    q = json.load(open(base+"qa-summary.json", encoding="utf-8"))
    print("  qa:", {k: q[k] for k in q if k in ("registrations","same_name","new","triangles","density_min","density_median","covered_windows")})
    d = json.load(open(base+"designs.json", encoding="utf-8"))["designs"]
    pk = collections.Counter(p['kind'] for x in d for p in x.get('props',[]))
    print("  designs", len(d), "props", dict(pk), "min/lot", min(len(x.get('props',[])) for x in d),
          "hh", dict(collections.Counter(x.get('households') for x in d)), "access", dict(collections.Counter(x.get('access') for x in d)),
          "product", dict(collections.Counter(x.get('product') for x in d if x.get('product'))))
    print("  retire:", open(base+"RETIREMENT-LIST.md",encoding="utf-8").read().count("`NA_"))
