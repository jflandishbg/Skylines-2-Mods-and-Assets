"""Unit tests for pack config, palette resolution, preflight gate, and dynamic staging owner promotion."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest

import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cs2kit.config import ConfigError, expand_roster, load_pack, validate_pack_hygiene
from cs2kit.preflight import run_preflight
from cs2kit.runner import stage_run


DEMO_PACK = ROOT / "packs" / "demo_pack"


class TestConfigAndPreflight(unittest.TestCase):
    def test_demo_pack_loads_and_passes_preflight(self):
        pack = load_pack(DEMO_PACK)
        assets = expand_roster(pack)
        self.assertEqual(len(assets), 6)
        names = [a.name for a in assets]
        self.assertIn("NA_DMDemoRowBrick_L1_1x2", names)
        self.assertIn("NA_DMDemoCornerLeftCorner_L1_2x3", names)
        self.assertIn("NA_DMTownHall", names)
        corner = next(a for a in assets if a.design == "DemoCornerLeftCorner")
        self.assertEqual(corner.access, "LeftCorner")
        self.assertEqual(corner.party_walls, ("right",))

        res = run_preflight(pack)
        self.assertEqual(res["failed"], 0, res)
        self.assertEqual(res["passed"], 6)
        self.assertLess(res["elapsed_s"], 5.0)

    def test_preflight_catches_intentional_violations(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdir = Path(tmp) / "bad_pack"
            shutil.copytree(DEMO_PACK, pdir, ignore=shutil.ignore_patterns("runs", "imports", "atlas_build"))
            # Add a test design file exercising multiple violations
            bad_py = pdir / "designs" / "bad_designs.py"
            bad_py.write_text(
                '''from cs2kit.kit import Mesh, finish, wall, style, gable_roof
from cs2kit.mesh import party

def build(lod, W=1, D=2, **variant):
    case = variant["case"]
    m, g = Mesh(), Mesh()
    if case == "oob":
        m.facing([(-4.5, -8.0, 0.0), (4.0, -8.0, 0.0), (4.0, -8.0, 4.0), (-4.5, -8.0, 4.0)], (0, -1, 0), "Brick074")
        finish(m, g)
    elif case == "open_roof":
        from cs2kit.mesh import roof_check
        t = Mesh()
        t.facing([(-3.0, -7.0, 4.0), (3.0, -7.0, 4.0), (3.0, 7.0, 4.0), (-3.0, 7.0, 4.0)], (0, 0, 1), "SlateDark")
        roof_check(m, t, "open test roof")
        finish(m, g)
    elif case == "setback":
        m.facing([(-3.5, -4.0, 0.0), (3.5, -4.0, 0.0), (3.5, -4.0, 4.0), (-3.5, -4.0, 4.0)], (0, -1, 0), "Brick074")
        finish(m, g)
    elif case == "rhythm":
        st = style(6.5, [(0.0, 6.5, "Brick074")], [(0.9, 1.0, 2.7), (0.9, 3.8, 5.4)], plinth=None, corners=False, frieze=0.2)
        # Bays spaced too far apart (> 2.5x width)
        wall(m, g, st, (-3.9, -7.0), (3.9, -7.0), "-", "-", [-2.8, 2.8], lod, door=(-2.8, 1.0, 2.7), waive={"balance": "test"})
        finish(m, g)
    elif case == "unknown_mat":
        m.facing([(-3.5, -7.0, 0.0), (3.5, -7.0, 0.0), (3.5, -7.0, 4.0), (-3.5, -7.0, 4.0)], (0, -1, 0), "NoSuchMaterial")
        finish(m, g)
''',
                encoding="utf-8",
            )
            pjson = json.loads((pdir / "pack.json").read_text(encoding="utf-8"))
            pjson["zones"]["ZI1"] = {"game_name": "Ind", "kind": "green_industry", "module": "bad_designs", "default_lots": [[1, 2]]}
            pjson["roster"] = [
                {"design": "BadOob", "zone_key": "ZL1", "module": "bad_designs", "lots": [[1, 2]], "params": {"case": "oob"}},
                {"design": "BadRoof", "zone_key": "ZL1", "module": "bad_designs", "lots": [[1, 2]], "params": {"case": "open_roof"}},
                {"design": "BadSetback", "zone_key": "ZL1", "module": "bad_designs", "lots": [[1, 2]], "params": {"case": "setback"}},
                {"design": "BadRhythm", "zone_key": "ZL1", "module": "bad_designs", "lots": [[1, 2]], "params": {"case": "rhythm"}},
                {"design": "BadMat", "zone_key": "ZL1", "module": "bad_designs", "lots": [[1, 2]], "params": {"case": "unknown_mat"}},
                {"design": "BadRightCorner", "zone_key": "ZL1", "module": "rowhouse", "lots": [[1, 2]], "access": "RightCorner"},
                {"design": "BadInd", "zone_key": "ZI1", "module": "bad_designs", "lots": [[1, 2]], "params": {"case": "rhythm"}},
            ]
            (pdir / "pack.json").write_text(json.dumps(pjson), encoding="utf-8")

            pack = load_pack(pdir)
            res = run_preflight(pack)
            self.assertEqual(res["failed"], 7)
            self.assertTrue(any("exceed lot" in e for e in res["assets"]["NA_DMBadOob_L1_1x2"]["errors"]))
            self.assertTrue(any("Rule 15" in e for e in res["assets"]["NA_DMBadRoof_L1_1x2"]["errors"]))
            self.assertTrue(any("Rule 29" in e for e in res["assets"]["NA_DMBadSetback_L1_1x2"]["errors"]))
            self.assertTrue(any("Rule 2" in e for e in res["assets"]["NA_DMBadRhythm_L1_1x2"]["errors"]))
            self.assertTrue(any("NoSuchMaterial" in e for e in res["assets"]["NA_DMBadMat_L1_1x2"]["errors"]))
            self.assertTrue(any("RightCorner is forbidden" in e for e in res["assets"]["NA_DMBadRightCorner_L1_1x2"]["errors"]))
            self.assertTrue(any("missing 'product'" in e for e in res["assets"]["NA_DMBadInd_L1_1x2"]["errors"]))

    def test_dynamic_atlas_owner_promotion_on_stage(self):
        """When asset #0 is excluded from staging, asset #1 becomes the 15-PNG atlas owner."""
        with tempfile.TemporaryDirectory() as tmp:
            pdir = Path(tmp) / "stage_pack"
            shutil.copytree(DEMO_PACK, pdir, ignore=shutil.ignore_patterns("runs", "imports", "atlas_build"))
            atlas_dir = pdir / "atlas_build"
            atlas_dir.mkdir(parents=True, exist_ok=True)
            for suf in ("", "_LOD1", "_LOD2"):
                for mp in ("BaseColor", "Normal", "MaskMap", "ControlMask", "Emissive"):
                    (atlas_dir / f"ATLAS{suf}_{mp}.png").write_bytes(b"png")

            run_dir = pdir / "runs" / "2026-11-23_000001"
            assets_names = ["NA_DMAlpha_L1_1x2", "NA_DMBeta_L1_1x3", "NA_DMGamma_L1_2x3"]
            for n in assets_names:
                ad = run_dir / n
                ad.mkdir(parents=True, exist_ok=True)
                (ad / f"{n}.fbx").write_bytes(b"fbx")
                (ad / f"{n}_Win.fbx").write_bytes(b"fbx")

            manifest = {
                "pack_id": "demo_pack",
                "assets": [
                    {"name": "NA_DMAlpha_L1_1x2", "design": "Alpha", "zone_key": "ZL1", "lot": [1, 2]},
                    {"name": "NA_DMBeta_L1_1x3", "design": "Beta", "zone_key": "ZL1", "lot": [1, 3]},
                    {"name": "NA_DMGamma_L1_2x3", "design": "Gamma", "zone_key": "ZL1", "lot": [2, 3]},
                ],
                "asset_specs": {n: {"name": n} for n in assets_names},
            }
            (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            # Reject Alpha (the first building), approve Beta and Gamma
            review = {
                "pack_id": "demo_pack",
                "run": run_dir.name,
                "designs": [
                    {"zone_key": "ZL1", "design": "Alpha", "assets": ["NA_DMAlpha_L1_1x2"], "verdict": "REDO"},
                    {"zone_key": "ZL1", "design": "Beta", "assets": ["NA_DMBeta_L1_1x3"], "verdict": "PASS"},
                    {"zone_key": "ZL1", "design": "Gamma", "assets": ["NA_DMGamma_L1_2x3"], "verdict": "PASS"},
                ],
            }
            (run_dir / "REVIEW.json").write_text(json.dumps(review), encoding="utf-8")

            pack = load_pack(pdir)
            dst = stage_run(pack, run_dir)
            self.assertFalse((dst / "NA_DMAlpha_L1_1x2").exists())
            # Beta must now own the 15 PNGs and Gamma must point to Beta
            beta_pngs = list((dst / "NA_DMBeta_L1_1x3").glob("*.png"))
            self.assertEqual(len(beta_pngs), 15)
            self.assertFalse((dst / "NA_DMBeta_L1_1x3" / "settings.json").exists())
            gamma_pngs = list((dst / "NA_DMGamma_L1_2x3").glob("*.png"))
            self.assertEqual(len(gamma_pngs), 0)
            settings = json.loads((dst / "NA_DMGamma_L1_2x3" / "settings.json").read_text(encoding="utf-8"))
            self.assertEqual(len(settings["sharedAssets"]), 15)
            self.assertTrue(all(v.startswith("../NA_DMBeta_L1_1x3/NA_DMBeta_L1_1x3") for v in settings["sharedAssets"].values()))


if __name__ == "__main__":
    unittest.main()
