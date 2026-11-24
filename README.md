# Skylines 2 Mods and Assets

Tools, mods and procedural building packs for **Cities: Skylines II**, built with Blender and Python. Everything here is open source under the MIT license.

## What's inside

| Folder | What it is |
|---|---|
| `Lobstertown/` | A Maine shingle-style building pack (about 930 buildings across residential, commercial, industrial, office and service zones, plus landmarks). Python scripts drive Blender to model, bake, check and stage the assets. Start with `Lobstertown/BRIEF.md` and `Lobstertown/gemini/RULEBOOK.md`. |
| `cs2kit/` | A pack-agnostic rewrite of the Lobstertown pipeline: `pack.json` and `atlas.json` describe a pack, then preflight, atlas, bake, review, stage and setup commands do the rest. See `cs2kit/README.md`. |
| `InterchangeStudio/` | A C# mod for building highway interchanges and ramps. |
| `WaterfrontAuto/` | A C# mod for waterfront road layouts. |
| `tools/RouterTest/` | A small C# test harness for the road routing code. |
| `cascadian_league/` | Notes for a related project. |
| `docs/` | Older notes (ClaudePlanner, a read-only city planning mod). |

## What's not here

Generated meshes, textures, FBX files, Blender bake output, import backups, decompiled game code and copies of the game's DLLs. These are large, rebuildable, or belong to their owners. Paths in the scripts that point at a Windows user folder read `C:\Users\<you>`; change them to match your machine.

## Requirements

Windows, Cities: Skylines II with the modding toolchain, Blender 5.x, Python 3.13, and the .NET SDK for the C# mods. Mod projects expect game assemblies from your own game install.

## License and credits

Code and documents are MIT licensed (see `LICENSE`). Cities: Skylines II and its assets belong to Colossal Order and Paradox Interactive. A few scripts read data from the game or reference prefab names from it; see `NOTICE.md`. Much of this work was written with AI coding assistants (Claude, Gemini and GPT).
