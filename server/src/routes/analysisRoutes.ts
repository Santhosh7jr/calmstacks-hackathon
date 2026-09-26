import { Router, Request, Response, NextFunction } from "express";
import multer from "multer";
import { analyzeWithFlask } from "../services/flask/flaskService";

const router = Router();
const allowed = new Set([
  ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tif", ".tiff",
  ".webp", ".ico", ".ppm", ".pgm", ".pbm", ".pnm", ".jp2",
  ".pdf", ".docx", ".zip",
]);

const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: 50 * 1024 * 1024 },
});

router.post(
  "/analyze",
  upload.single("file"),
  async (req: Request, res: Response, next: NextFunction) => {
    try {
      if (!req.file) {
        return res.status(400).json({ message: "Please upload a file." });
      }

      const extension = req.file.originalname.includes(".")
        ? `.${req.file.originalname.split(".").pop()?.toLowerCase()}`
        : "";

      if (!allowed.has(extension)) {
        return res.status(400).json({
          message:
            "Unsupported file type. Supported files: JPG, JPEG, PNG, GIF, BMP, TIFF, WEBP, ICO, PPM, PGM, PBM, PNM, JP2, PDF, DOCX, and ZIP.",
        });
      }

      const result = await analyzeWithFlask(
        req.file.originalname,
        req.file.mimetype,
        req.file.buffer,
      );

      return res.status(200).json(result);
    } catch (error: unknown) {
      return next(error);
    }
  },
);

router.use((error: unknown, _req: Request, res: Response, _next: NextFunction) => {
  const err = error as {
    response?: { status?: number; data?: { message?: string } };
    code?: string;
    message?: string;
  };

  if (err.code === "LIMIT_FILE_SIZE") {
    return res.status(413).json({ message: "File is too large. Maximum size is 50 MB." });
  }

  const status = err.response?.status ?? 502;
  const message =
    err.response?.data?.message ??
    "The Python analysis service is unavailable. Start Flask on port 5001 and try again.";

  return res.status(status).json({ message });
});

export default router;
