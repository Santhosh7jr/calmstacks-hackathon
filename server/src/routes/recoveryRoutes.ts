import { Router, Request, Response, NextFunction } from "express";
import multer from "multer";
import { recoverWithFlask } from "../services/flask/flaskService";

const router = Router();
const upload = multer({ storage: multer.memoryStorage(), limits: { fileSize: 50 * 1024 * 1024 } });

router.post("/recover", upload.single("file"), async (req: Request, res: Response, next: NextFunction) => {
  try {
    if (!req.file) return res.status(400).json({ message: "Please upload a file." });

    const response = await recoverWithFlask(req.file.originalname, req.file.mimetype, req.file.buffer);
    const reportHeader = response.headers["x-recovery-report"];
    let report: unknown = undefined;
    if (typeof reportHeader === "string") {
      try { report = JSON.parse(reportHeader); } catch { report = undefined; }
    }

    if (response.status >= 400) {
      let payload: any = { message: "Recovery failed." };
      try { payload = JSON.parse(Buffer.from(response.data).toString("utf8")); } catch { /* keep default */ }
      return res.status(response.status).json({ ...payload, report });
    }

    res.status(200);
    res.setHeader("Content-Type", response.headers["content-type"] || req.file.mimetype || "application/octet-stream");
    res.setHeader("Content-Disposition", response.headers["content-disposition"] || `attachment; filename="recovered_${req.file.originalname}"`);
    if (report) res.setHeader("X-Recovery-Report", JSON.stringify(report));
    return res.send(Buffer.from(response.data));
  } catch (error) {
    return next(error);
  }
});

router.use((error: unknown, _req: Request, res: Response, _next: NextFunction) => {
  const err = error as { code?: string; message?: string; response?: { status?: number; data?: any } };
  if (err.code === "LIMIT_FILE_SIZE") return res.status(413).json({ message: "File is too large. Maximum size is 50 MB." });
  return res.status(err.response?.status ?? 502).json({
    message: err.message || "The Python recovery service is unavailable. Start Flask on port 5001 and try again.",
  });
});

export default router;
