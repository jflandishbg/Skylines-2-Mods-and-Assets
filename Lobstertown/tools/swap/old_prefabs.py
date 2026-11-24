# After the author imports same-name rebakes, CS2 leaves the OLD prefabs beside the new ones in each asset folder.
# Lists the old Prefab/.cid/.bak files (older than the cutoff) for the given 1_READY folders.
# usage: python old_prefabs.py "2026-11-11 15:50" out.txt 1_READY_A 1_READY_B ...
# (the folders may be in generator/imports or generator/imports/2_DONE)
import os, sys, datetime, collections
I = r"C:\Users\<you>\AppData\LocalLow\Colossal Order\Cities Skylines II\ImportedData\47e9fcd660d2d72a"
G = r"C:\Users\<you>\CS2Planner\Lobstertown\generator\imports"
cut = datetime.datetime.strptime(sys.argv[1], "%Y-%m-%d %H:%M").timestamp()
out_path = sys.argv[2]
def where(s):
    for p in (os.path.join(G, s), os.path.join(G, "2_DONE", s)):
        if os.path.isdir(p): return p
    raise SystemExit("not found: " + s)
names = [d for s in sys.argv[3:] for d in os.listdir(where(s)) if d.startswith("NA_")]
out, bad, kinds = [], [], collections.Counter()
for n in names:
    p = os.path.join(I, n)
    if not os.path.isdir(p): bad.append(("missing", n)); continue
    pre = [f for f in os.listdir(p) if f.endswith(".Prefab")]
    old = [f for f in pre if os.path.getmtime(os.path.join(p, f)) < cut]
    new = [f for f in pre if f not in old]
    kinds[(len(old), len(new))] += 1
    if len(new) != 4 or len(old) not in (0, 4): bad.append((n, len(old), len(new)))
    for f in old:
        for x in (f, f + ".cid", f + ".bak"):
            if os.path.exists(os.path.join(p, x)): out.append(os.path.join(p, x))
print("(old,new) per folder:", dict(kinds)); print("bad", bad[:10]); print("files", len(out))
open(out_path, "w", encoding="utf-8").write("\n".join(out) + "\n")
