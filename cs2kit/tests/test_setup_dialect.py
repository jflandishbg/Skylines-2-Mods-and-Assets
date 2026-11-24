"""Sandboxed unit tests for CS2 .Prefab JSON dialect, --pre-import archival, setup patching, and .loc/icon dressing."""
import json
from pathlib import Path
import struct
import tempfile
import unittest
from PIL import Image

import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cs2kit.setup import load_prefab, pre_import_cleanup, save_prefab, setup_pack


SAMPLE_ZONE_PREFAB = """{
    "$id": 0,
    "$type": "0|Game.Prefabs.ZonePrefab, Game",
    "name": "Demo Mixed Street",
    "components": {
        "$id": 1,
        "$type": "1|System.Collections.Generic.List`1[[Game.Prefabs.ComponentBase, Game]], mscorlib",
        "$rlength": 1,
        "$rcontent": [
            {
                "$id": 2,
                "$type": "2|Game.Prefabs.ZoneProperties, Game",
                "name": "ZoneProperties",
                "active": true,
                "m_AllowedSold": {
                    "$id": 3,
                    "$type": "3|Game.Economy.ResourceInEditor[], Game",
                    "$rlength": 2,
                    "$rcontent": [
                        4,
                        3
                    ]
                }
            }
        ]
    }
}"""


def _sample_building_prefab(name: str) -> str:
    return json.dumps(
        {
            "$id": 0,
            "$type": "0|Game.Prefabs.BuildingPrefab, Game",
            "name": name,
            "m_LotWidth": 1,
            "m_LotDepth": 1,
            "m_AccessType": 0,
            "components": {
                "$id": 1,
                "$type": "1|System.Collections.Generic.List`1[[Game.Prefabs.ComponentBase, Game]], mscorlib",
                "$rlength": 1,
                "$rcontent": [
                    {
                        "$id": 2,
                        "$type": "2|Game.Prefabs.UIObject, Game",
                        "name": "UIObject",
                        "active": True,
                        "m_Icon": "",
                    }
                ],
            },
        },
        indent=4,
    )


def _sample_mesh_prefab(name: str) -> str:
    return json.dumps(
        {
            "$id": 0,
            "$type": "0|Game.Prefabs.RenderPrefab, Game",
            "name": name + " Mesh",
            "components": {
                "$id": 1,
                "$type": "1|System.Collections.Generic.List`1[[Game.Prefabs.ComponentBase, Game]], mscorlib",
                "$rlength": 0,
                "$rcontent": [],
            },
        },
        indent=4,
    )


class TestSetupDialectAndSandbox(unittest.TestCase):
    def test_fstrref_and_inline_vector_roundtrip(self):
        raw = """{
    "$id": 0,
    "$type": "0|Game.Prefabs.Test, Game",
    "m_Ref": $fstrref:"CID:abc123",
    "m_Color": {
        "$type": "1|UnityEngine.Color, UnityEngine.CoreModule",
        0.5,
        0.25,
        0.1,
        1
    }
}"""
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "test.Prefab"
            p.write_text(raw, encoding="utf-8")
            doc = load_prefab(p)
            self.assertEqual(doc["m_Ref"], "@@FSTR@@CID:abc123")
            self.assertEqual(doc["m_Color"]["@@VALS@@"], [0.5, 0.25, 0.1, 1])
            save_prefab(p, doc, dry_run=False)
            self.assertTrue(Path(str(p) + ".bak").exists())
            saved = p.read_text(encoding="utf-8")
            self.assertIn('$fstrref:"CID:abc123"', saved)
            self.assertIn("0.5, 0.25, 0.1, 1", saved)

    def test_pre_import_archiver_and_manifest_setup(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            imp = root / "ImportedData"
            bkp = root / "backups"
            ready = root / "1_READY_demo"
            thumbs = root / "thumbs"
            imp.mkdir()
            bkp.mkdir()
            ready.mkdir()
            thumbs.mkdir()

            # Create stale ImportedData files for RowHouse (to be archived) and keep Unrelated untouched
            hx = "0123456789abcdef0123456789abcdef"
            stale_files = [
                f"NA_DMDemoRowBrick_L1_1x2_{hx}.Prefab",
                f"NA_DMDemoRowBrick_L1_1x2_{hx}.Prefab.cid",
                f"NA_DMDemoRowBrick_L1_1x2_{hx}.Prefab.bak",
                f"NA_DMDemoRowBrick_L1_1x2 Mesh_{hx}.Prefab",
                f"NA_DMDemoRowBrick_L1_1x2_en-US.loc",
            ]
            for sf in stale_files:
                (imp / sf).write_text("old", encoding="utf-8")
            (imp / f"NA_DMOtherUnrelated_L1_1x2_{hx}.Prefab").write_text("keep", encoding="utf-8")

            (ready / "IMPORT-LIST.txt").write_text("NA_DMDemoRowBrick_L1_1x2\n", encoding="utf-8")
            arch = pre_import_cleanup(ready, imp, bkp, "demo_pack", dry_run=False)
            self.assertEqual(arch["matched"], len(stale_files))
            for sf in stale_files:
                self.assertFalse((imp / sf).exists())
            self.assertTrue((imp / f"NA_DMOtherUnrelated_L1_1x2_{hx}.Prefab").exists())

            # Now populate fresh ImportedData with ZonePrefabs + fresh building/mesh prefabs
            (imp / f"ZoneMixed_{hx}.Prefab").write_text(SAMPLE_ZONE_PREFAB, encoding="utf-8")
            (imp / f"ZoneMixed_{hx}.Prefab.cid").write_text("zone-cid-mixed", encoding="utf-8")
            (imp / f"ZoneRes_{hx}.Prefab").write_text(
                SAMPLE_ZONE_PREFAB.replace("Demo Mixed Street", "Demo Brick Rows"), encoding="utf-8"
            )
            (imp / f"ZoneRes_{hx}.Prefab.cid").write_text("zone-cid-res", encoding="utf-8")
            (imp / f"ZoneInd_{hx}.Prefab").write_text(
                SAMPLE_ZONE_PREFAB.replace("Demo Mixed Street", "Demo Cannery"), encoding="utf-8"
            )
            (imp / f"ZoneInd_{hx}.Prefab.cid").write_text("zone-cid-ind", encoding="utf-8")

            b_res = f"NA_DMDemoRowBrick_L1_1x2_{hx}.Prefab"
            m_res = f"NA_DMDemoRowBrick_L1_1x2 Mesh_{hx}.Prefab"
            b_mix = f"NA_DMDemoMixedBakery_L1_1x3_{hx}.Prefab"
            b_ind = f"NA_DMDemoCannery_L1_2x4_{hx}.Prefab"
            (imp / b_res).write_text(_sample_building_prefab("NA_DMDemoRowBrick_L1_1x2"), encoding="utf-8")
            (imp / m_res).write_text(_sample_mesh_prefab("NA_DMDemoRowBrick_L1_1x2"), encoding="utf-8")
            (imp / b_mix).write_text(_sample_building_prefab("NA_DMDemoMixedBakery_L1_1x3"), encoding="utf-8")
            (imp / b_ind).write_text(_sample_building_prefab("NA_DMDemoCannery_L1_2x4"), encoding="utf-8")

            Image.new("RGBA", (64, 64), (10, 20, 30, 255)).save(thumbs / "NA_DMDemoRowBrick_L1_1x2.png")

            manifest = {
                "pack_id": "demo_pack",
                "prefix": "NA_DM",
                "variation_group": "Demo",
                "colour_random": [2, 4, 5],
                "assets": {
                    "NA_DMDemoRowBrick_L1_1x2": {
                        "name": "NA_DMDemoRowBrick_L1_1x2",
                        "design": "DemoRowBrick",
                        "zone_key": "ZL1",
                        "zone_kind": "residential",
                        "game_zone": "Demo Brick Rows",
                        "lot": [1, 2],
                        "level": 1,
                        "access": "Front",
                        "households": 2,
                        "display_name": "Harbour Brick Rowhouse",
                        "description": "Nice brick rowhouse.",
                        "colour_sets": [[[1.0, 1.0, 1.0], [0.9, 0.8, 0.7], [0.95, 0.95, 0.95]]],
                    },
                    "NA_DMDemoMixedBakery_L1_1x3": {
                        "name": "NA_DMDemoMixedBakery_L1_1x3",
                        "design": "DemoMixedBakery",
                        "zone_key": "ZM1",
                        "zone_kind": "mixed",
                        "game_zone": "Demo Mixed Street",
                        "lot": [1, 3],
                        "level": 1,
                        "access": "Front",
                        "households": 3,
                        "display_name": "Harbour Bakery Block",
                        "description": "",
                    },
                    "NA_DMDemoCannery_L1_2x4": {
                        "name": "NA_DMDemoCannery_L1_2x4",
                        "design": "DemoCannery",
                        "zone_key": "ZI1",
                        "zone_kind": "green_industry",
                        "game_zone": "Demo Cannery",
                        "lot": [2, 4],
                        "level": 1,
                        "access": "Front",
                        "households": 0,
                        "product": "Food",
                        "space_multiplier": 8,
                        "display_name": "Harbour Cannery",
                        "description": "",
                    },
                },
            }

            res = setup_pack(manifest, imp, thumb_dirs=[thumbs], dry_run=False)
            self.assertEqual(len(res["updated_buildings"]), 3)
            self.assertEqual(res["updated_meshes"], ["NA_DMDemoRowBrick_L1_1x2"])
            self.assertEqual(res["missing_zones"], [])

            # Check residential prefab
            d_res = json.loads((imp / b_res).read_text(encoding="utf-8").replace('$fstrref:"', '"@@FSTR@@'))
            self.assertEqual(d_res["m_LotWidth"], 1)
            self.assertEqual(d_res["m_LotDepth"], 2)
            bp_res = next(c for c in d_res["components"]["$rcontent"] if c["name"] == "BuildingProperties")
            self.assertEqual(bp_res["m_ResidentialProperties"], 2)
            ui_res = next(c for c in d_res["components"]["$rcontent"] if c["name"] == "UIObject")
            self.assertTrue(ui_res["m_Icon"].startswith("assetdb://global/"))

            # Check mixed prefab inherited m_AllowedSold from Demo Mixed Street
            d_mix = json.loads((imp / b_mix).read_text(encoding="utf-8").replace('$fstrref:"', '"@@FSTR@@'))
            bp_mix = next(c for c in d_mix["components"]["$rcontent"] if c["name"] == "BuildingProperties")
            self.assertEqual(bp_mix["m_ResidentialProperties"], 3)
            self.assertEqual(bp_mix["m_AllowedSold"]["$rcontent"], [4, 3])

            # Check green industry prefab restricted to Food [4]
            d_ind = json.loads((imp / b_ind).read_text(encoding="utf-8").replace('$fstrref:"', '"@@FSTR@@'))
            bp_ind = next(c for c in d_ind["components"]["$rcontent"] if c["name"] == "BuildingProperties")
            self.assertEqual(bp_ind["m_ResidentialProperties"], 0)
            self.assertEqual(bp_ind["m_AllowedManufactured"]["$rcontent"], [4])
            self.assertEqual(bp_ind["m_SpaceMultiplier"], 8)

            # Check ColorProperties written on mesh prefab (parsed via load_prefab for CS2 inline Color structs)
            d_mesh = load_prefab(imp / m_res)
            cp = next(c for c in d_mesh["components"]["$rcontent"] if c["name"] == "ColorProperties")
            self.assertEqual(cp["m_VariationGroups"]["$rcontent"][0]["m_Name"], "Demo")

            # Check .loc file created
            loc_bytes = (imp / "NA_DMDemoRowBrick_L1_1x2_en-US.loc").read_bytes()
            self.assertIn(b"Harbour Brick Rowhouse", loc_bytes)
            self.assertTrue((imp / "NA_DMDemoRowBrick_L1_1x2_en-US.loc.cid").exists())


if __name__ == "__main__":
    unittest.main()
