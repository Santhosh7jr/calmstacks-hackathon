import { ProgressBar } from "../common/ProgressBar";

type RecoveryProgressProps = {
  progress: number;
  status: string;
};

export function RecoveryProgress({ progress, status }: RecoveryProgressProps) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.035] p-5">
      <h3 className="mb-5 text-sm font-bold text-white">{status}</h3>
      <ProgressBar value={progress} label="Recovery status" />
    </div>
  );
}

export default RecoveryProgress;
