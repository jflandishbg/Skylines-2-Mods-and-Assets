# Plan a safe retirement: which folders + loose files can go to the Recycle Bin without breaking any surviving asset.
# Texture files are NEVER recycled: surfaces point at them by an id this script can't decode, and a retired
# design can be the texture owner for survivors (R11: MercerMansardPair owns 30 surviving Z1C surfaces).
# usage: python retire_plan.py <list-of-names.txt> <out-plan.txt>
import os, re, sys, collections
I = r"C:\Users\<you>\AppData\LocalLow\Colossal Order\Cities Skylines II\ImportedData\47e9fcd660d2d72a"
retire = set(l.strip() for l in open(sys.argv[1], encoding="utf-8") if l.strip())
loose = [f for f in os.listdir(I) if os.path.isfile(os.path.join(I, f)) and not f.endswith(".cid")]
gid = {}                                   # guid hex -> loose file
for f in loose:
    c = os.path.join(I, f + ".cid")
    if os.path.exists(c): gid[open(c).read().strip().lower()] = f
def patterns(h):                           # raw bytes and .NET Guid byte order
    b = bytes.fromhex(h)
    net = b[3::-1] + b[5:3:-1] + b[7:5:-1] + b[8:]
    return (b, net)
pat = {}
for h, f in gid.items():
    for p in patterns(h): pat[p] = f
def refs_of(data):
    out = set()
    for h in set(re.findall(rb"[0-9a-f]{32}", data)):
        f = gid.get(h.decode())
        if f: out.add(f)
    if b"\x00" in data[:4096] or not data.lstrip().startswith(b"{"):   # binary: look for 16-byte guids
        for p, f in pat.items():
            if p in data: out.add(f)
    return out
edges = {}
for f in loose:
    if f.endswith((".Surface",)):
        edges[f] = refs_of(open(os.path.join(I, f), "rb").read())
    else: edges[f] = set()
roots = collections.defaultdict(set)       # asset folder -> loose files its prefabs reference
for d in os.listdir(I):
    p = os.path.join(I, d)
    if not os.path.isdir(p): continue
    for f in os.listdir(p):
        if f.endswith(".Prefab"): roots[d] |= refs_of(open(os.path.join(p, f), "rb").read())
def closure(start):
    seen, st = set(), list(start)
    while st:
        f = st.pop()
        if f in seen: continue
        seen.add(f); st.extend(edges.get(f, ()))
    return seen
keep = set().union(*(closure(r) for d, r in roots.items() if d not in retire))
gone = set().union(*(closure(roots[d]) for d in retire if d in roots))
shared = gone & keep
recycle = sorted(gone - keep)
prefix_orphans = sorted(f for f in loose if not f.endswith('.Texture') and any(f.startswith(n + "_") or f.startswith(n + " ") for n in retire) and f not in keep and f not in gone)
print("retire folders", len(retire), "missing", [n for n in retire if n not in roots])
print("loose referenced only by retirees", len(recycle), "| shared with survivors (kept)", len(shared), "| unreferenced orphans by name", len(prefix_orphans))
print("shared sample", sorted(shared)[:6])
print("total kept refs", len(keep), "of", len(loose))
with open(sys.argv[2], "w", encoding="utf-8") as o:
    for n in sorted(retire): o.write(os.path.join(I, n) + "\n")
    for f in recycle + prefix_orphans:
        o.write(os.path.join(I, f) + "\n")
        if os.path.exists(os.path.join(I, f + ".cid")): o.write(os.path.join(I, f + ".cid") + "\n")
