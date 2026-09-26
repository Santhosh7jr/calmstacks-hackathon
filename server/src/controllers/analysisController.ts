import type { NextFunction, Request, Response } from "express";
import { analyzeWithFlask } from "../services/flask/flaskService";

export async function analyzeFileController(
  req: Request,
  res: Response,
  next: NextFunction,
) {
  try {
    if (!req.file) {
      return res.status(400).json({ message: "Please upload a file." });
    }

    const result = await analyzeWithFlask(
      req.file.originalname,
      req.file.mimetype,
      req.file.buffer,
    );

    return res.status(200).json(result);
  } catch (error) {
    return next(error);
  }
}
