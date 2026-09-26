import unittest
from io import BytesIO

from PIL import Image

from run import app


class ApiRouteTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        image = BytesIO()
        Image.new("RGB", (16, 16), (20, 80, 140)).save(image, "PNG")
        self.image_data = image.getvalue()

    def _upload(self, path):
        return self.client.post(
            path,
            data={"file": (BytesIO(self.image_data), "sample.png", "image/png")},
            content_type="multipart/form-data",
        )

    def test_health_endpoint(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["status"], "ok")

    def test_analysis_supports_documented_and_frontend_paths(self):
        for path in ("/api/analyze", "/api/analyze/analyze"):
            with self.subTest(path=path):
                response = self._upload(path)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json["analysis"]["status"], "healthy")

    def test_recovery_supports_documented_and_frontend_paths(self):
        for path in ("/api/recovery", "/api/recovery/recover"):
            with self.subTest(path=path):
                response = self._upload(path)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.mimetype, "image/png")
                self.assertIsNotNone(response.headers.get("X-Recovery-Report"))


if __name__ == "__main__":
    unittest.main()