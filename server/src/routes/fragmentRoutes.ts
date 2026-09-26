import { Router, Request, Response, NextFunction } from "express";
import multer from "multer";
import { reconstructWithFlask } from "../services/flask/flaskService";

const router = Router();
const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: 50 * 1024 * 1024, files: 32 },
});

router.post(
  "/reconstruct",
  upload.array("files", 32),
  async (req: Request, res: Response, next: NextFunction) => {
    try {
      const files = (req.files ?? []) as Express.Multer.File[];
      if (!files.length) return res.status(400).json({ message: "Upload at least one fragment." });

      const response = await reconstructWithFlask(
        files.map((file) => ({
          fileName: file.originalname,
          mimeType: file.mimetype,
          buffer: file.buffer,
        })),
        typeof req.body.outputName === "string" ? req.body.outputName : "reconstructed.bin",
      );

      const reportHeader = response.headers["x-reconstruction-report"];
      let report: unknown = undefined;
      if (typeof reportHeader === "string") {
        try { report = JSON.parse(reportHeader); } catch { report = undefined; }
      }

      if (response.status >= 400) {
        let payload: { message?: string } = { message: "Fragment reconstruction failed." };
        try { payload = JSON.parse(Buffer.from(response.data).toString("utf8")); } catch { /* keep default */ }
        return res.status(response.status).json({ ...payload, report });
      }

      res.status(200);
      res.setHeader("Content-Type", response.headers["content-type"] || "application/octet-stream");
      res.setHeader("Content-Disposition", response.headers["content-disposition"] || 'attachment; filename="reconstructed.bin"');
      if (report) res.setHeader("X-Reconstruction-Report", JSON.stringify(report));
      res.setHeader("Access-Control-Expose-Headers", "X-Reconstruction-Report, Content-Disposition");
      return res.send(Buffer.from(response.data));
    } catch (error) {
      return next(error);
    }
  },
);

router.use((error: unknown, _req: Request, res: Response, _next: NextFunction) => {
  const err = error as { code?: string; message?: string; response?: { status?: number; data?: unknown } };
  if (err.code === "LIMIT_FILE_SIZE") return res.status(413).json({ message: "A fragment exceeds the 50 MB upload limit." });
  if (err.code === "LIMIT_FILE_COUNT") return res.status(413).json({ message: "A maximum of 32 fragments can be uploaded." });
  return res.status(err.response?.status ?? 502).json({
    message: err.message || "The Python fragment service is unavailable. Start Flask on port 5001 and try again.",
  });
});

export default router;
