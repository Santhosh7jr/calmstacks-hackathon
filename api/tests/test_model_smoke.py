import unittest
from pathlib import Path
import joblib
import pandas as pd

API_DIR = Path(__file__).resolve().parents[1]
ML_DIR = API_DIR / "ml"
DATASET = ML_DIR / "data" / "processed" / "fragment_dataset.csv"

MODELS = {
    "file_classification": ML_DIR / "models" / "file_classification" / "file_classifier.joblib",
    "corruption_detection": ML_DIR / "models" / "corruption_detection" / "corruption_detector.joblib",
    "recovery_confidence": ML_DIR / "models" / "recovery_confidence" / "recovery_model.joblib",
    "fragment_matching": ML_DIR / "models" / "fragment_matching" / "fragment_matcher.joblib",
    "image_purification": ML_DIR / "models" / "image_purification" / "image_purifier.joblib",
}

class ModelSmokeTests(unittest.TestCase):
    def test_all_bundled_models_load(self):
        for name, path in MODELS.items():
            with self.subTest(name=name):
                self.assertTrue(path.exists(), f"Missing model: {path}")
                loaded = joblib.load(path)
                if isinstance(loaded, dict):
                    self.assertIn("model", loaded)
                    self.assertTrue(hasattr(loaded["model"], "predict"))
                else:
                    self.assertTrue(hasattr(loaded, "predict"))

    def test_fragment_models_predict_on_dataset(self):
        df = pd.read_csv(DATASET)
        base = MODELS["file_classification"]
        loaded = joblib.load(base)
        model = loaded["model"]
        features = loaded["features"]
        X = df[features].fillna(0).head(5)
        predictions = model.predict(X)
        self.assertEqual(len(predictions), 5)

    def test_image_purifier_metadata(self):
        loaded = joblib.load(MODELS["image_purification"])
        self.assertEqual(loaded["patch_size"], 11)
        self.assertEqual(loaded["channels"], 3)
        self.assertGreater(loaded["training_samples"], 10000)

if __name__ == "__main__":
    unittest.main()
