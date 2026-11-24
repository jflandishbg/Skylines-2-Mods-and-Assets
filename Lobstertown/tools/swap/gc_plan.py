# Retirement + orphan plan: folders to retire (names file, may be empty) and the old Geometry/Surface files the
# rebaked names no longer use. Never lists .Texture files. Run AFTER old prefabs are recycled.
# usage: python gc_plan.py retire_names.txt plan_out.txt 1_READY_A 1_READY_B ...
import os, sys, runpy
here = os.path.dirname(os.path.abspath(__file__))
folders = sys.argv[3:]
sys.argv = ["retire_plan.py", sys.argv[1], sys.argv[2]]
g = runpy.run_path(os.path.join(here, "retire_plan.py"), run_name="rp")
I = g["I"]; keep = g["keep"]; loose = g["loose"]
G = r"C:\Users\<you>\CS2Planner\Lobstertown\generator\imports"
def where(s):
    for p in (os.path.join(G, s), os.path.join(G, "2_DONE", s)):
        if os.path.isdir(p): return p
    raise SystemExit("not found: " + s)
names = [d for s in folders for d in os.listdir(where(s)) if d.startswith("NA_")]
orph = sorted(f for f in loose if not f.endswith(".Texture") and f not in keep and any(f.startswith(n + "_") for n in names))
print("rebake orphans (old geometry/surfaces)", len(orph))
with open(sys.argv[2], "a", encoding="utf-8") as o:
    for f in orph:
        o.write(os.path.join(I, f) + "\n")
        if os.path.exists(os.path.join(I, f + ".cid")): o.write(os.path.join(I, f + ".cid") + "\n")
