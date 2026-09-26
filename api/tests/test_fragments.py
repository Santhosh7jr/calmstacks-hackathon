import io
import sys
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "ml" / "venv" / "Lib" / "site-packages"))

from recoverai_core.recovery.fragments import reconstruct_fragments
from run import app


class FragmentReconstructionTests(unittest.TestCase):
    def test_known_pdf_fragments_are_reordered_and_revalidated(self):
        source = Path(__file__).resolve().parents[1] / "ml" / "data" / "raw" / "pdf" / "file-sample_150kB.pdf"
        data = source.read_bytes()
        third = len(data) // 3
        chunks = [data[:third], data[third : third * 2], data[third * 2 :]]

        result = reconstruct_fragments(
            [("fragment-0.bin", chunks[0]), ("fragment-1.bin", chunks[1]), ("fragment-2.bin", chunks[2])],
            "candidate.pdf",
        )

        self.assertEqual(result["data"], data)
        self.assertEqual(result["report"]["validation"]["analysis"]["status"], "healthy")
        self.assertEqual(result["report"]["orderedFragments"], ["fragment-0.bin", "fragment-1.bin", "fragment-2.bin"])

    def test_fragment_http_endpoint_returns_candidate_and_report(self):
        client = app.test_client()
        response = client.post(
            "/api/fragments/reconstruct",
            data={
                "files": [
                    (io.BytesIO(b"%PDF-1.7\n"), "a.bin"),
                    (io.BytesIO(b"%%EOF\n"), "b.bin"),
                ],
                "outputName": "candidate.pdf",
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.headers.get("X-Reconstruction-Report"))


if __name__ == "__main__":
    unittest.main()
