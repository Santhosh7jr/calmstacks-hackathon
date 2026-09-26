import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from recoverai_core import analyze_file
from recoverai_core.recovery.engine import recover_file


class PurificationModelTests(unittest.TestCase):
    def test_trained_model_repairs_localized_uniform_image_damage(self):
        source = Path(__file__).resolve().parents[1] / "ml" / "data" / "raw" / "images" / "file_example_JPG_100kB.jpg"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "damaged.png"
            image = Image.open(source).convert("RGB").resize((512, 342))
            draw = ImageDraw.Draw(image)
            draw.rectangle((180, 100, 300, 180), fill=(0, 0, 0))
            image.save(path, "PNG")

            before = analyze_file(path.name, path.read_bytes(), "image/png")
            self.assertEqual(before["analysis"]["status"], "suspected")
            self.assertTrue(before["analysis"]["assessment"]["regions"])

            result = recover_file(path.name, path.read_bytes(), "image/png")

        self.assertEqual(result.report["status"], "completed")
        self.assertEqual(result.report["after"]["analysis"]["status"], "healthy")
        self.assertIsNotNone(result.report["purification"])
        self.assertEqual(result.report["purification"]["model"], "image_purifier")
        self.assertGreater(result.report["purification"]["pixelsPurified"], 0)
        self.assertIn("Trained ML image purification model", " ".join(result.report["methods"]))


if __name__ == "__main__":
    unittest.main()
