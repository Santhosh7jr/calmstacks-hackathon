export type FragmentReport = {
  status: string;
  message: string;
  fragmentCount: number;
  orderedFragments: string[];
  matchConfidencePercent: number;
  edges: Array<{
    from: string;
    to: string;
    score: number;
    signals: Record<string, number>;
  }>;
  outputSha256: string;
  outputSize: number;
  validation: {
    analysis?: {
      status?: string;
      assessment?: { corruptionPercent?: number; recovery?: { recoverablePercent?: number } };
    };
  };
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:5000/api";

export async function reconstructFragments(files: File[], outputName = "reconstructed.bin") {
  const form = new FormData();
  for (const file of files) form.append("files", file);
  form.append("outputName", outputName);

  const response = await fetch(`${API_BASE_URL}/fragments/reconstruct`, {
    method: "POST",
    body: form,
  });

  if (!response.ok) {
    const data = await response.json().catch(() => ({ message: "Fragment reconstruction failed." }));
    throw new Error(data.message || "Fragment reconstruction failed.");
  }

  const blob = await response.blob();
  const header = response.headers.get("X-Reconstruction-Report");
  const report = header ? JSON.parse(header) as FragmentReport : null;
  return {
    report,
    downloadUrl: URL.createObjectURL(blob),
    outputName: response.headers.get("Content-Disposition")?.match(/filename="?([^";]+)"?/i)?.[1] || `reconstructed_${outputName}`,
    outputSize: blob.size,
  };
}
