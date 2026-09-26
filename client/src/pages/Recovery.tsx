import { useState } from "react";
import { Button } from "../components/common/Button";
import { analyzeFile } from "../services/analysisService";
import type { AnalysisResult } from "../types/analysis";

const allowedExtensions = [
  ".jpg",
  ".jpeg",
  ".png",
  ".gif",
  ".bmp",
  ".tif",
  ".tiff",
  ".webp",
  ".ico",
  ".ppm",
  ".pgm",
  ".pbm",
  ".pnm",
  ".jp2",
  ".pdf",
  ".docx",
  ".zip",
];

export function Recovery({
  onShowResults,
}: {
  onShowResults: (result: AnalysisResult) => void;
}) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleFileSelect = (file?: File) => {
    if (!file) {
      setSelectedFile(null);
      return;
    }

    const name = file.name.toLowerCase();
    const isSupported = allowedExtensions.some((extension) =>
      name.endsWith(extension),
    );

    if (!isSupported) {
      setSelectedFile(null);
      setError(
        "Unsupported file type. Please upload JPG, PNG, PDF, DOCX, or ZIP.",
      );
      return;
    }

    setSelectedFile(file);
    setError("");
  };

  const handleAnalyze = async () => {
    if (!selectedFile) {
      setError("Please select a file first.");
      return;
    }

    setIsLoading(true);
    setError("");

    try {
      const result = await analyzeFile(selectedFile);
      onShowResults(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "File analysis failed.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="mx-auto max-w-4xl space-y-8">
      <div>
        <p className="mb-4 text-[10px] font-bold uppercase tracking-[0.24em] text-teal-300">
          LIVE FILE ANALYSIS / 02
        </p>
        <h1 className="text-5xl font-black tracking-[-0.07em] text-white sm:text-7xl">
          Upload a file
        </h1>
        <p className="mt-5 max-w-2xl text-base leading-7 text-slate-400">
          RecoverAI inspects the uploaded file at the byte level and reports
          measured integrity checks plus evidence-backed estimates of damage and recoverability.
        </p>
      </div>

      <label className="group flex min-h-80 cursor-pointer flex-col items-center justify-center rounded-3xl border border-dashed border-teal-300/30 bg-teal-300/[0.035] px-6 text-center transition hover:border-teal-300/70 hover:bg-teal-300/[0.07]">
        <input
          className="sr-only"
          type="file"
          accept={allowedExtensions.join(",")}
          onChange={(event) => handleFileSelect(event.target.files?.[0])}
        />
        <span className="mb-5 grid h-16 w-16 place-items-center rounded-2xl bg-teal-300 text-2xl font-black text-slate-950 shadow-lg shadow-teal-950/30">
          +
        </span>
        <strong className="text-xl font-bold text-white">
          Drop a file here
        </strong>
        <span className="mt-2 text-sm text-slate-500">
          or click to browse from your device
        </span>
        <small className="mt-8 text-[10px] font-bold uppercase tracking-[0.15em] text-slate-600">
          JPG · JPEG · PNG · GIF · BMP · TIFF · WEBP · ICO · PDF · DOCX · ZIP
        </small>
      </label>

      {error ? (
        <div className="rounded-xl border border-rose-300/20 bg-rose-300/10 px-4 py-3 text-sm text-rose-200">
          {error}
        </div>
      ) : null}

      {selectedFile ? (
        <div className="flex flex-col gap-5 rounded-2xl border border-white/10 bg-white/[0.05] p-5 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <strong className="block break-all text-sm font-bold text-white">
              {selectedFile.name}
            </strong>
            <span className="mt-1 block text-xs text-slate-500">
              {selectedFile.size.toLocaleString()} bytes ·{" "}
              {selectedFile.type || "unknown mime type"}
            </span>
          </div>
          <Button disabled={isLoading} onClick={handleAnalyze}>
            {isLoading ? "Analyzing…" : "Analyze file"}
          </Button>
        </div>
      ) : null}
    </main>
  );
}

export default Recovery;
