import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from recoverai_core import analyze_file


class ImageEngineTests(unittest.TestCase):
    def test_natural_noise_is_not_marked_corrupt(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "noise.jpg"
            pixels = np.random.default_rng(7).integers(
                0, 256, size=(512, 768, 3), dtype=np.uint8
            )
            Image.fromarray(pixels, "RGB").save(path, "JPEG", quality=90)
            result = analyze_file(path.name, path.read_bytes(), "image/jpeg")

        self.assertEqual(result["analysis"]["status"], "healthy")
        self.assertEqual(result["analysis"]["assessment"]["corruptionPercent"], 0.0)

    def test_healthy_png_passes_crc_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "healthy.png"
            Image.new("RGB", (128, 128), (30, 80, 140)).save(path, "PNG")
            result = analyze_file(path.name, path.read_bytes(), "image/png")

        self.assertEqual(result["analysis"]["status"], "healthy")
        self.assertEqual(result["analysis"]["details"]["pngStructure"]["crcErrors"], 0)

    def test_supplied_visual_damage_is_localized(self):
        path = Path("/mnt/data/images.jpg")
        if not path.exists():
            self.skipTest("No supplied visual-corruption sample is available")

        result = analyze_file(path.name, path.read_bytes(), "image/jpeg")
        analysis = result["analysis"]
        self.assertEqual(analysis["status"], "suspected")
        self.assertGreater(analysis["assessment"]["corruptionPercent"], 20.0)
        self.assertLess(analysis["assessment"]["corruptionPercent"], 50.0)
        self.assertTrue(analysis["assessment"]["regions"])


if __name__ == "__main__":
    unittest.main()
