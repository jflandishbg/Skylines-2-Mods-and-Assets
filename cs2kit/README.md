# cs2kit — Standalone CS2 Asset Pack Engine

A fast, pack-agnostic Python + Blender 5.2 pipeline for building, checking, previewing, staging, and configuring **Cities: Skylines II** procedural building packs.

Designed from lessons learned in *New France* and *Lobstertown*:
- **Zero hardcoded pack logic:** everything about a pack lives in `pack.json` and `atlas.json` (zones, budgets, lot sizes, party-wall behavior, palette swatches, CC0 scans, procedural tiles, and signboards).
- **2-second pure-Python preflight:** tests an entire pack's rules (Rules 1–10, Rule 15 closed roofs, Rule 29 street setback, lot bounds `±2 mm`, planar faces, missing lots/corners) before ever launching Blender.
- **Declarative rect-packing atlas compiler:** packs scans + procedural textures + signboards onto `4096² / 2048² / 1024²` across 5 CS2 maps with Rule 16 continuous gutters and Rule 27 `ControlMask` tint channels.
- **Single-pass parallel Blender bake + audit + persistent batch previews:** exports 6 FBXs per asset, validates and audits in one import pass, renders 9 views + automatic 512×512 transparent service thumbnails in one persistent Blender session per worker, and builds zone comparison contact sheets (`front`, `rear`, `aerial`, `allsizes`).
- **Safe staging & setup:** dynamically promotes the first passing+approved asset as texture owner, writes `.loc` display names for all assets, archives stale `ImportedData` duplicates via `--pre-import`, and patches CS2 prefabs from explicit `zone.kind`.

---

## Quick Start (Windows PowerShell)

```powershell
$py = "C:\Users\<you>\AppData\Local\Programs\Python\Python313\python.exe"

# 1. Compile and verify the 5-map texture atlas (4096 / 2048 / 1024)
& $py -m cs2kit atlas packs/demo_pack
& $py -m cs2kit atlas packs/demo_pack --check

# 2. Pure-Python preflight (< 2 seconds, no Blender)
& $py -m cs2kit preflight packs/demo_pack

# 3. Parallel Blender bake + audit + EEVEE previews + zone contact sheets
& $py -m cs2kit bake packs/demo_pack --workers 2

# 4. Review & approve designs, then stage into imports/1_READY_*
& $py -m cs2kit review packs/demo_pack --run <stamp> --approve-all --note "Approved"
& $py -m cs2kit stage packs/demo_pack --run <stamp>

# 5. Pre-import cleanup & prefab setup (game closed)
& $py -m cs2kit setup packs/demo_pack --pre-import packs/demo_pack/imports/1_READY_... --dry-run
& $py -m cs2kit setup packs/demo_pack --pre-import packs/demo_pack/imports/1_READY_...
```

## Starting a New Pack

```powershell
& $py -m cs2kit init-pack packs/my_new_pack --id my_new_pack --title "My New Pack" --prefix NA_MN
& $py -m cs2kit atlas packs/my_new_pack
& $py -m cs2kit preflight packs/my_new_pack
```

See [PACK_SPEC_GUIDE.md](PACK_SPEC_GUIDE.md) for the full `pack.json`, `atlas.json`, and design module reference.
