import unittest
from pathlib import Path

from recoverai_core.recovery.fragments import reconstruct_fragments
from recoverai_core.recovery.engine import recover_file


class RuntimeCompletionTests(unittest.TestCase):
    def test_fragment_filename_sequence_reconstructs_shuffled_fragments(self):
        original = b"%PDF-1.7\n" + (b"RecoverAI forensic evidence block. " * 500)
        size = len(original)
        cuts = [0, size // 4, size // 2, (size * 3) // 4, size]
        chunks = [original[cuts[i]:cuts[i + 1]] for i in range(4)]
        shuffled = [(f"evidence_fragment_{i:04d}.bin", chunks[i]) for i in (2, 0, 3, 1)]

        result = reconstruct_fragments(shuffled, "reconstructed.bin")

        self.assertEqual(
            result["report"]["orderingMethod"],
            "filename-sequence-hint",
        )
        self.assertEqual(result["data"], original)

    def test_pdf_xref_fixture_produces_validated_candidate(self):
        path = Path(__file__).parent / "fixtures" / "corrupted_xref_test.pdf"
        result = recover_file(path.name, path.read_bytes(), "application/pdf")

        self.assertIn(result.report["status"], {"completed", "completed_partial"})
        self.assertTrue(result.report["changed"])
        self.assertEqual(result.report["after"]["analysis"]["status"], "healthy")
        self.assertIn("ai", result.report)


if __name__ == "__main__":
    unittest.main()
