import type { AnalysisResult } from "../types/analysis";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:5000/api";

export async function analyzeFile(file: File): Promise<AnalysisResult> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/analysis/analyze`, {
    method: "POST",
    body: formData,
  });

  const data = (await response.json().catch(() => ({
    message: "Invalid server response.",
  }))) as Partial<AnalysisResult> & { message?: string };

  if (!response.ok) {
    throw new Error(data.message || "File analysis failed.");
  }

  return data as AnalysisResult;
}

export default analyzeFile;
