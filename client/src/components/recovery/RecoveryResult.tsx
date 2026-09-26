type RecoveryResultProps = {
  fileName: string;
  recoveredCount: number;
  integrityScore: number;
};

export function RecoveryResult({
  fileName,
  recoveredCount,
  integrityScore,
}: RecoveryResultProps) {
  return (
    <div className="rounded-2xl border border-teal-300/20 bg-teal-300/5 p-5">
      <h3 className="text-sm font-bold text-teal-100">Recovery summary</h3>
      <p className="mt-3 text-sm leading-6 text-slate-300">
        {fileName} yielded {recoveredCount} recovered files with an integrity
        score of {integrityScore}%.
      </p>
    </div>
  );
}

export default RecoveryResult;
