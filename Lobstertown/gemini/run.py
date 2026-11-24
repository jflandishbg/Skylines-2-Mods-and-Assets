"""Gemini building runner (Claude, 2026-11-13).

  python run.py NA_PdDMaisonDuQuai_L1_1x3 [more names]   bake, audit, preview, report  ->  runs/<stamp>/REPORT.md
  python run.py --stage runs/<stamp>                      after the author approves: copy to generator/imports, register zones

Each name is a Gemini script saved as scripts/<name>.py (see ../GEMINI_BUILDING_TEMPLATE.md).
"""
import sys, os, subprocess, shutil, json, re, datetime
from pathlib import Path

G = Path(__file__).resolve().parent
NF = G.parent
BLENDER = r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"

def blender(script, *args, env=None, log=None):
    r = subprocess.run([BLENDER, "-b", "--python-exit-code", "2", "--python", str(G / "source" / script), "--", *map(str, args)],
                       cwd=G, env=env, capture_output=True, text=True, encoding="utf8", errors="replace")
    if log: Path(log).write_text(r.stdout + "\n--- stderr ---\n" + r.stderr, encoding="utf8")
    return r.returncode, r.stdout

def precheck(name):
    p = G / "scripts" / f"{name}.py"
    if not p.exists(): return [f"no script at scripts/{name}.py"]
    t = p.read_text(encoding="utf8"); bad = []
    if not re.search(r"^def build\(\s*lod", t, re.M): bad.append("no `def build(lod)` function")
    if not re.search(r'^ZONE\s*=\s*["\']Z\w+["\']', t, re.M): bad.append('no `ZONE = "Z1A"` line (the zone key)')
    if not re.fullmatch(r"NA_(?:PdD|LT)[A-Za-z]+_L1_\dx\d", name): bad.append("file name must look like NA_LTCaptainsGable_L1_1x3")
    for word in ("import os", "subprocess", "urllib", "requests", "socket", "shutil", "open("):
        if word in t: bad.append(f"the script uses `{word}`; building scripts may only use bpy, bmesh, mathutils and math")
    try: compile(t, str(p), "exec")
    except SyntaxError as e: bad.append(f"Python syntax error on line {e.lineno}: {e.msg}")
    return bad

def sheet(folder, out):
    from PIL import Image, ImageDraw
    shots = sorted((folder / "preview").glob("*.png"))
    if not shots: return False
    W, H, cols = 600, 400, 3
    rows = (len(shots) + cols - 1) // cols
    img = Image.new("RGB", (W * cols, H * rows), "white"); dr = ImageDraw.Draw(img)
    for i, p in enumerate(shots):
        x, y = (i % cols) * W, (i // cols) * H
        img.paste(Image.open(p).convert("RGB").resize((W, H)), (x, y))
        dr.rectangle((x, y, x + 200, y + 18), fill="black"); dr.text((x + 5, y + 3), p.stem[2:], fill="white")
    img.save(out); return True

def facing(n):
    x, y, z = map(float, n.split(","))
    return "up" if z > .7 else "down" if z < -.7 else "the street" if y < -.7 else "the rear" if y > .7 else "right" if x > .7 else "left" if x < -.7 else "sideways"

def plain(err):
    """Turn a bake assertion into words the author and Gemini can act on."""
    m = re.search(r"\('(\w+?)(_LOD\d)?(_Win)?\.fbx', '([XYZ]) bounds', \[([-\d., ]+)\], \[([-\d., ]+)\]\)", err)
    if m:
        lo = [float(x) for x in m[5].split(",")]; hi = [float(x) for x in m[6].split(",")]
        k = "XYZ".index(m[4]); lod = m[2][-1] if m[2] else "0"
        what = {0: "sideways past the side lot lines", 1: "past the front or rear lot line", 2: "below the ground"}[k]
        return (f"LOD{lod}{' glass' if m[3] else ''} sticks out {what}: it runs {'xyz'[k]} {lo[k]} to {hi[k]}. "
                "The lot runs x ±4·W and y ±4·D (front at y = -4·D); keep 0.05 m inside the front and 0.25 m inside the sides and rear. "
                "Check cornices, dentils, sills, eaves and balconies: anything that projects counts.")
    m = re.search(r"\('(\w+)', (\d), (\d+), \[(\d+), (\d+), (\d+)\]\)", err)
    if m: return f"LOD{m[2]} has {int(m[3]):,} triangles; the limit is {int(m[3+int(m[2])+1]):,}"
    m = re.search(r"\('(\w+)', (\d+), ([\d.]+)\)", err)
    if m: return f"too plain: {int(m[2]):,} triangles over {float(m[3]):.0f} m² of surface = {int(m[2])/float(m[3]):.1f} per m²; needs at least 8 (add window reveals, sills, cornices, trim)"
    pts = re.findall(r"'overlap_m2': ([\d.]+), 'normal': \[([-\d., ]+)\], 'point': \[([-\d., ]+)\]", err)
    if pts:
        lod = re.search(r"\('[^']+', (\d)", err)
        where = "; ".join("at x {:.2f}, y {:.2f}, z {:.2f} (faces facing {})".format(*map(float, q.split(",")), facing(n)) for _, n, q in pts[:5])
        return (f"LOD{lod[1] if lod else '?'}: {len(pts)}+ places where two faces lie in the same plane and overlap, so they would flicker in game: "
                f"{where}. Move one of each pair at least 0.003 m off the other, or cut the hidden face away.")
    return err[:400]

def run(names):
    import subprocess, sys
    subprocess.run([sys.executable, str(G / "source" / "lt_atlas.py"), "--check"], check=True)   # rule 16
    stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    out = G / "runs" / stamp; out.mkdir(parents=True, exist_ok=True)
    rows = {}
    ok = []
    for n in names:
        bad = precheck(n)
        rows[n] = dict(fail=bad[:])
        if bad: continue
        (out / n).mkdir(exist_ok=True)
        ok.append(n)
    lt = [n for n in ok if n.startswith("NA_LT")]       # Lobstertown: one shared texture set, owned by the first
    for n in ok:
        if n.startswith("NA_LT") and n != lt[0]:
            continue
        for f in (G / "atlas_template").glob("TEMPLATE*.png"):
            shutil.copy2(f, out / n / f.name.replace("TEMPLATE", n))
    if ok:
        env = dict(os.environ, GEMINI_NAMES=",".join(ok), GEMINI_OUT=str(out))
        code, log = blender("bake_r12.py", "GEMINI", "--force", env=env, log=out / "bake-log.txt")
        for line in log.splitlines():
            m = re.match(r"(ASSET_ERROR|AUDIT_ERROR) (\S+) (\w+) (.*)", line)
            if m and m[2] in rows: rows[m[2]]["fail"] += [x for x in (plain(y) for y in m[4].split(" || ")) if x not in rows[m[2]]["fail"]]
        if "BAKE_COMPLETE" not in log and not any(rows[n]["fail"] for n in ok):
            for n in ok: rows[n]["fail"].append("the bake stopped early; see bake-log.txt (Claude will read it)")
        baked = [n for n in ok if not rows[n]["fail"]]
        if baked:
            blender("audit_gemini.py", out, *baked, log=out / "audit-log.txt")
            aud = json.loads((out / "audit-gemini.json").read_text(encoding="utf8")) if (out / "audit-gemini.json").exists() else {}
            for n in baked:
                rows[n].update({k: v for k, v in aud.get(n, {}).items() if k != "fail"})
                rows[n]["fail"] += aud.get(n, {}).get("fail", ["audit did not run"])
                blender("preview_gemini.py", out, n, log=out / n / "preview-log.txt")
                rows[n]["sheet"] = sheet(out / n, out / f"{n}_preview.png")
                if not rows[n]["fail"]: review_form(out, n, rows[n])
    report(out, rows)
    print("REPORT", out / "REPORT.md")
    return out

CHECKLIST = [
    "One composition: blocks touch or overlap with no slits; wings share the cornice or step down a full storey",
    "Grounded: porticos, pavilions and bays stand on walls that reach the ground, with an entrance below",
    "Every side the camera sees has windows and trim (only declared party walls may be bare)",
    "Roofs meet cleanly: no slivers, gaps, or pile-up of heights",
    "Hierarchy reads: base, main floors, roof; the front door is obvious",
    "Reads as its style from the street (as named at the top of the script)",
    "Far views (LOD1, LOD2) keep the outline and roofline",
    "the author's rules: one building, no props, water, benches or spires; broad top",
]

def review_form(out, n, r):
    """The architecture review: Claude fills this in from the preview sheet. --stage refuses anything not marked PASS."""
    facts = f"height {r.get('height_m')} m, roof eaves at {r.get('roof_levels_m')} m, slits {r.get('gaps_m2')} m², lot covered {r.get('occupied_pct')}%"
    L = [f"# Design review: {n}", "", f"Filled in by Claude from `{n}_preview.png` before anything is staged. Measured: {facts}.", "",
         "| # | Check | Result | Notes |", "| --- | --- | --- | --- |"]
    L += [f"| {i} | {c} | | |" for i, c in enumerate(CHECKLIST, 1)]
    L += ["", "Verdict: PENDING", "", "Reasons:", ""]
    p = out / f"{n}_REVIEW.md"
    if not p.exists(): p.write_text("\n".join(L), encoding="utf8")

def reviewed(run_dir, n):
    p = run_dir / f"{n}_REVIEW.md"
    return p.exists() and re.search(r"^Verdict:\s*PASS\b", p.read_text(encoding="utf8"), re.M) is not None

def report(out, rows):
    L = [f"# Gemini building run {out.name}", ""]
    for n, r in rows.items():
        L += [f"## {n}: {'PASS' if not r['fail'] else 'FAIL'}", ""]
        if r.get("sheet"): L += [f"Preview: `{n}_preview.png` (street level on all sides, aerial, far LODs).", ""]
        if not r["fail"]: L += [f"Design review: `{n}_REVIEW.md` (must say PASS before staging).", ""]
        for k, label in (("height_m", "Height"), ("front_m", "Front wall from the lot front (m)"), ("occupied_pct", "Lot covered (%)"),
                         ("roof_levels_m", "Roof eave heights (m)"), ("gaps_m2", "Slits between blocks (m²)")):
            if k in r: L.append(f"- {label}: {r[k]}")
        if r["fail"]:
            L += ["", "**Problems:**"] + [f"- {x}" for x in r["fail"]]
            L += ["", "**Paste this back to Gemini:**", "", "```",
                  f"Your script for {n} was run in Blender and checked. Please fix these and send the whole script again:"]
            L += [f"- {x}" for x in r["fail"]]
            L += ["Keep everything else the same. Re-check Parts 1 and 2 of the brief before answering.", "```"]
        L.append("")
    (out / "REPORT.md").write_text("\n".join(L), encoding="utf8")

def stage(run_dir):
    run_dir = Path(run_dir).resolve()
    rows = json.loads((run_dir / "audit-gemini.json").read_text(encoding="utf8"))
    man = json.loads((run_dir / "manifest.json").read_text(encoding="utf8"))
    good = [a for a in man["assets"] if not rows.get(a["name"], {}).get("fail")]
    unreviewed = [a["name"] for a in good if not reviewed(run_dir, a["name"])]
    if unreviewed: print("NOT STAGED (design review not PASS):", ", ".join(unreviewed))
    good = [a for a in good if a["name"] not in unreviewed]
    assert good, "nothing passed both the checks and the design review in this run"
    dst = NF / "generator/imports" / f"1_READY_GEMINI_{run_dir.name}_{len(good)}"
    dst.mkdir(exist_ok=True)
    for a in good:
        src = run_dir / a["name"]
        shared = (src / "settings.json").exists()      # textures come from the batch owner: ship no PNGs of its own
        pats = ("preview", "*-log.txt") + (("*.png",) if shared else ())
        if shared:
            owner = json.loads((src / "settings.json").read_text(encoding="utf8"))["sharedAssets"]
            owner = next(iter(owner.values())).split("/")[1]
            assert owner in [b["name"] for b in good], f"{a['name']} shares textures with {owner}, which is not staged"
        if not (dst / a["name"]).exists(): shutil.copytree(src, dst / a["name"], ignore=shutil.ignore_patterns(*pats))
    (dst / "IMPORT-LIST.txt").write_text("\n".join(a["name"] for a in good) + "\n", encoding="utf8")
    # setup finds each building's zone in GPT_INBOX/**/designs.json
    reg = NF / "GPT_INBOX/gemini/designs.json"; reg.parent.mkdir(exist_ok=True)
    d = json.loads(reg.read_text(encoding="utf8")) if reg.exists() else dict(project="Paris on the Delaware", batch="GEMINI", designs=[])
    keep = {x["name"]: x for x in d["designs"]}
    specs = {}
    sys.path.insert(0, str(G / "source"))
    from gemini_specs import entry
    for a in good:
        e = entry(G / "scripts" / (a["name"] + ".py"))
        keep[a["name"]] = dict(name=a["name"], design=e["design"], zone_key=e["zone_key"], households=e["households"], lot=e["lot"])
        if e.get("product"):                                  # green industry: setup restricts the building to it
            keep[a["name"]]["product"] = e["product"]
    d["designs"] = list(keep.values())
    reg.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf8")
    print("STAGED", dst)

if __name__ == "__main__":
    a = sys.argv[1:]
    if not a: print(__doc__); sys.exit(1)
    if a[0] == "--stage": stage(a[1])
    else: run(a)
