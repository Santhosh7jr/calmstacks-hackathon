const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:5000/api";

export type AnalysisResult = {
  fileName: string;
  extension: string;
  mimeType: string;
  size: number;
  sizeFormatted: string;
  sha256: string;
  analysis: {
    status: "healthy" | "suspected" | "corrupted" | "unsupported";
    corrupted: boolean;
    signatureValid: boolean;
    details: Record<string, unknown>;
    assessment: {
      classification: string;
      corruptionPercent: number;
      recovery: {
        corruptionPercent: number;
        recoverablePercent: number;
        unrecoverablePercent: number;
        confidence: string;
        basis: string[];
      };
      findings: Array<Record<string, unknown>>;
      regions: Array<Record<string, unknown>>;
    };
  };
};

export async function analyzeFile(file: File): Promise<AnalysisResult> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/analysis/analyze`, {
    method: "POST",
    body: formData,
  });

  const data = await response
    .json()
    .catch(() => ({ message: "Invalid server response." }));
  if (!response.ok) throw new Error(data.message || "File analysis failed.");
  return data;
}
