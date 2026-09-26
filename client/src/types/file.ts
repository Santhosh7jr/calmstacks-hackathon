export type SupportedFileType =
  | ".jpg"
  | ".jpeg"
  | ".png"
  | ".gif"
  | ".bmp"
  | ".tif"
  | ".tiff"
  | ".webp"
  | ".ico"
  | ".ppm"
  | ".pgm"
  | ".pbm"
  | ".pnm"
  | ".jp2"
  | ".pdf"
  | ".docx"
  | ".zip";

export type RecoverableFile = {
  id: string;
  name: string;
  size: number;
  status: "recovered" | "partial" | "damaged";
  confidence: number;
};
