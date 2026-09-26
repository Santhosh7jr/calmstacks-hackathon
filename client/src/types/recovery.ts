export type RecoveryStatus = "queued" | "running" | "completed" | "completed_partial" | "failed" | "not_needed";

export type RecoveryResult = {
  fileName: string;
  outputFileName: string;
  recoveredFiles: number;
  coverage: number;
  status: RecoveryStatus;
  summary: string;
  report: any;
  downloadUrl: string;
  outputSize: number;
};
