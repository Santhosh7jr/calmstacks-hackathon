export type RecoveryStatus = "queued" | "running" | "completed" | "failed";

export type RecoveryTask = {
  id: string;
  status: RecoveryStatus;
  progress: number;
  message: string;
};
