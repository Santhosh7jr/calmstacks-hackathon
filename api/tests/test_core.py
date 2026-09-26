import unittest
from pathlib import Path

from recoverai_core import analyze_file


class RecoverAICoreTests(unittest.TestCase):
    def test_healthy_jpeg(self) -> None:
        from PIL import Image
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "healthy.jpg"
            Image.new("RGB", (64, 64), (120, 120, 120)).save(path, "JPEG")
            result = analyze_file(path.name, path.read_bytes(), "image/jpeg")

        analysis = result["analysis"]
        self.assertEqual(analysis["status"], "healthy")
        self.assertEqual(analysis["assessment"]["corruptionPercent"], 0.0)
        self.assertEqual(
            analysis["assessment"]["recovery"]["recoverablePercent"],
            100.0,
        )

    def test_visual_jpeg_damage_is_flagged(self) -> None:
        path = Path("/mnt/data/images.jpg")
        if not path.exists():
            self.skipTest("No supplied visual-corruption sample is available")

        result = analyze_file(path.name, path.read_bytes(), "image/jpeg")
        analysis = result["analysis"]

        self.assertEqual(analysis["status"], "suspected")
        self.assertGreater(analysis["assessment"]["corruptionPercent"], 0)
        self.assertLess(
            analysis["assessment"]["recovery"]["recoverablePercent"],
            100,
        )

    def test_corrupted_docx_is_detected(self) -> None:
        path = Path("/mnt/data/corrupted_test_document.docx")
        if not path.exists():
            self.skipTest("No DOCX corruption sample is available")

        result = analyze_file(path.name, path.read_bytes(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        self.assertEqual(result["analysis"]["status"], "corrupted")
        self.assertTrue(result["analysis"]["assessment"]["findings"])

    def test_corrupted_pdf_is_detected(self) -> None:
        path = Path("/mnt/data/corrupted_test_document.pdf")
        if not path.exists():
            self.skipTest("No PDF corruption sample is available")

        result = analyze_file(path.name, path.read_bytes(), "application/pdf")
        self.assertEqual(result["analysis"]["status"], "corrupted")
        self.assertTrue(result["analysis"]["assessment"]["findings"])


if __name__ == "__main__":
    unittest.main()
