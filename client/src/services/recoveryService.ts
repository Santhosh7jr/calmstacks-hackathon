import type { RecoveryResult } from "../types/recovery";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:5000/api";

export async function startRecovery(file: File): Promise<RecoveryResult> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/recovery/recover`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const data = await response
      .json()
      .catch(() => ({ message: "Recovery failed." }));
    const error = new Error(data.message || "Recovery failed.") as Error & {
      report?: unknown;
    };
    error.report = data.report;
    throw error;
  }

  const blob = await response.blob();
  const reportHeader = response.headers.get("X-Recovery-Report");
  let report: any = null;
  if (reportHeader) {
    try {
      report = JSON.parse(reportHeader);
    } catch {
      report = null;
    }
  }
  const disposition = response.headers.get("Content-Disposition") || "";
  const match = disposition.match(/filename="?([^";]+)"?/i);
  const outputName = match?.[1] || `recovered_${file.name}`;
  const downloadUrl = URL.createObjectURL(blob);

  return {
    fileName: file.name,
    outputFileName: outputName,
    recoveredFiles: 1,
    coverage: Number(report?.recoveryPercent ?? 0),
    status: report?.status === "completed" || report?.status === "completed_partial" ? report.status : "not_needed",
    summary: report?.message || "Recovery completed.",
    report,
    downloadUrl,
    outputSize: blob.size,
  };
}

export default startRecovery;
