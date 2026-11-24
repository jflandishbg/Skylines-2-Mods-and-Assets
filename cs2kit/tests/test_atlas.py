"""Unit tests for the declarative rect-packing atlas compiler, Rule 16 gutters, and Rule 27 ControlMask."""
import json
from pathlib import Path
import tempfile
import unittest
from PIL import Image
import numpy as np

import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cs2kit.atlas import MAPS, STEPS, boxes, build_atlas, check_atlas
from cs2kit.config import load_pack


class TestAtlasCompiler(unittest.TestCase):
    def test_rect_packing_and_rule16_rule27_verification(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdir = Path(tmp) / "atlas_test_pack"
            (pdir / "designs").mkdir(parents=True)
            atlas_spec = {
                "sizes": {"main": 512, "_LOD1": 256, "_LOD2": 128},
                "gutter_px_main": 16,
                "tiles": [
                    {"key": "PaintWall", "kind": "flat_paint", "color": [180, 180, 180], "px": [128, 128], "metres": [2.0, 2.0], "tint_channel": 1, "lift_target_rgb": [236, 234, 228]},
                    {"key": "BoardBatten", "kind": "board_batten", "nboard": 8, "px": [128, 128], "metres": [2.4, 2.4], "tint_channel": 0},
                    {"key": "TrimWhite", "kind": "flat_paint", "color": [226, 225, 219], "px": [64, 64], "metres": [3.0, 3.0], "tint_channel": "B"},
                    {"key": "Stucco", "kind": "stucco", "color": [210, 200, 185], "px": [128, 64], "metres": [2.0, 1.0]},
                    {"key": "RoofSeam", "kind": "standing_seam", "color": [84, 114, 98], "px": [128, 128], "metres": [2.4, 2.4]},
                ],
                "signs": [
                    {"key": "Sign_TestShop", "text": "TEST SHOP", "board": [30, 50, 40], "ink": [220, 200, 140], "metres": [3.0, 0.58], "px": [128, 32]}
                ],
            }
            (pdir / "atlas.json").write_text(json.dumps(atlas_spec), encoding="utf-8")
            pack_json = {
                "pack_id": "atlas_test",
                "title": "Atlas Test",
                "prefix": "NA_AT",
                "zones": {"ZL1": {"game_name": "Z", "kind": "residential", "module": "m", "default_lots": [[1, 2]]}},
                "roster": [],
            }
            (pdir / "pack.json").write_text(json.dumps(pack_json), encoding="utf-8")

            pack = load_pack(pdir)
            out = build_atlas(pack)
            self.assertTrue((out / "atlas_layout.json").exists())
            self.assertTrue((out / "atlas_preview.png").exists())

            for _, suf, dim in (("main", "", 512), ("_LOD1", "_LOD1", 256), ("_LOD2", "_LOD2", 128)):
                for mp in MAPS:
                    with Image.open(out / f"ATLAS{suf}_{mp}.png") as im:
                        self.assertEqual(im.size, (dim, dim))

            errs = check_atlas(pack)
            self.assertEqual(errs, [], errs)

            # Verify Rule 27 base lift on PaintWall
            lay = json.loads((out / "atlas_layout.json").read_text(encoding="utf-8"))
            b = boxes(lay["lods"]["main"], 512)["PaintWall"]
            with Image.open(out / "ATLAS_BaseColor.png") as base_im:
                base_arr = np.asarray(base_im.convert("RGB"))
            mean_rgb = base_arr[b[1] : b[3], b[0] : b[2]].mean(axis=(0, 1))
            self.assertGreater(mean_rgb[0], 230.0)
            self.assertGreater(mean_rgb[1], 228.0)

            # Verify 4-pixel alignment so LOD2 boxes are exact integers
            for k, cell in lay["lods"]["main"].items():
                x0 = round(cell["uv"][0] * 512)
                x1 = round(cell["uv"][2] * 512)
                y0 = round((1.0 - cell["uv"][3]) * 512)
                y1 = round((1.0 - cell["uv"][1]) * 512)
                self.assertEqual(x0 % 4, 0, k)
                self.assertEqual(x1 % 4, 0, k)
                self.assertEqual(y0 % 4, 0, k)
                self.assertEqual(y1 % 4, 0, k)


if __name__ == "__main__":
    unittest.main()
