import unittest
from io import BytesIO
from pathlib import Path
import zipfile

from recoverai_core.recovery.engine import recover_file

ROOT = Path(__file__).resolve().parents[1]


class RecoveryTests(unittest.TestCase):
    def test_incomplete_docx_recovery_is_rejected(self):
        from recoverai_core.recovery.engine import RecoveryFailure

        output = BytesIO()
        with zipfile.ZipFile(output, "w") as archive:
            archive.writestr("[Content_Types].xml", "<Types/>")

        with self.assertRaises(RecoveryFailure) as context:
            recover_file("incomplete.docx", output.getvalue(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

        self.assertEqual(context.exception.report["status"], "failed")
        self.assertEqual(context.exception.report["after"]["analysis"]["status"], "corrupted")

    def test_structurally_damaged_decodable_png_is_reencoded(self):
        from PIL import Image
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "damaged.png"
            Image.new("RGB", (128, 128), (20, 80, 140)).save(path, "PNG")
            data = bytearray(path.read_bytes())
            data[-5] ^= 255

        result = recover_file(path.name, bytes(data), "image/png")
        self.assertEqual(result.report["status"], "completed")
        self.assertEqual(result.report["after"]["analysis"]["status"], "healthy")

    def test_structurally_damaged_rgba_png_preserves_alpha(self):
        from PIL import Image
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "transparent.png"
            source = Image.new("RGBA", (32, 32), (20, 80, 140, 37))
            source.save(path, "PNG")
            data = bytearray(path.read_bytes())
            data[-5] ^= 255

        result = recover_file(path.name, bytes(data), "image/png")
        with Image.open(BytesIO(result.data)) as repaired:
            self.assertEqual(repaired.mode, "RGBA")
            self.assertEqual(repaired.getpixel((0, 0))[3], 37)

    def test_structurally_damaged_animated_png_preserves_frames(self):
        from PIL import Image
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "animated.png"
            first = Image.new("RGBA", (16, 16), (255, 0, 0, 255))
            second = Image.new("RGBA", (16, 16), (0, 0, 255, 255))
            output = BytesIO()
            first.save(output, "PNG", save_all=True, append_images=[second], duration=[100, 200], loop=0)
            data = bytearray(output.getvalue())
            data[-5] ^= 255

        result = recover_file(path.name, bytes(data), "image/png")
        with Image.open(BytesIO(result.data)) as repaired:
            self.assertEqual(repaired.n_frames, 2)
            repaired.seek(1)
            self.assertEqual(repaired.getpixel((0, 0))[:3], (0, 0, 255))

    def test_visual_jpeg_recovery(self):
        path = Path('/mnt/data/images.jpg')
        if not path.exists():
            self.skipTest('visual test image is not available')
        result = recover_file(path.name, path.read_bytes(), 'image/jpeg')
        self.assertEqual(result.report['status'], 'completed')
        self.assertTrue(result.data)
        self.assertEqual(result.report['after']['analysis']['status'], 'healthy')
        self.assertLessEqual(
            result.report['after']['analysis']['assessment']['corruptionPercent'],
            result.report['before']['analysis']['assessment']['corruptionPercent'],
        )

    def test_truncated_jpeg_salvage(self):
        path = Path('/mnt/data/corrupted_test_image.jpg')
        if not path.exists():
            self.skipTest('truncated image is not available')
        result = recover_file(path.name, path.read_bytes(), 'image/jpeg')
        self.assertEqual(result.report['status'], 'completed')
        self.assertEqual(result.report['after']['analysis']['status'], 'healthy')

    def test_docx_reconstruction(self):
        path = Path('/mnt/data/corrupted_test_document.docx')
        if not path.exists():
            self.skipTest('corrupted docx is not available')
        result = recover_file(path.name, path.read_bytes(), 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        self.assertEqual(result.report['status'], 'completed')
        self.assertEqual(result.report['after']['analysis']['status'], 'healthy')


    def test_pdf_xref_reconstruction(self):
        path = ROOT / 'tests' / 'fixtures' / 'corrupted_xref_test.pdf'
        if not path.exists():
            self.skipTest('corrupted PDF recovery fixture is not available')
        result = recover_file(path.name, path.read_bytes(), 'application/pdf')
        self.assertEqual(result.report['status'], 'completed')
        self.assertEqual(result.report['after']['analysis']['status'], 'healthy')
        self.assertIn('xref/trailer', ' '.join(result.report['methods']))

        from pypdf import PdfReader
        reader = PdfReader(BytesIO(result.data))
        self.assertEqual(len(reader.pages), 4)
        text = '\n'.join((page.extract_text() or '') for page in reader.pages)
        self.assertIn('RECOVERAI-TEST-2026', text)

    def test_interior_image_damage_is_repaired_by_candidate_selection(self):
        path = ROOT / 'tests' / 'fixtures' / 'damaged_visual.png'
        result = recover_file(path.name, path.read_bytes(), 'image/png')
        before = result.report['before']['analysis']['assessment']['corruptionPercent']
        after = result.report['after']['analysis']['assessment']['corruptionPercent']
        self.assertEqual(result.report['status'], 'completed')
        self.assertEqual(result.report['after']['analysis']['status'], 'healthy')
        self.assertLess(after, before)
        self.assertTrue(any('candidate selected by post-repair forensic score' in m for m in result.report['methods']))


if __name__ == '__main__':
    unittest.main()
