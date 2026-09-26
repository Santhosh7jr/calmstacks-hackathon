import type { AnalysisResult } from "../types/analysis";

function percent(value: number): string {
  return `${Math.max(0, Math.min(100, value)).toFixed(1)}%`;
}

function MetricCard({
  label,
  value,
  description,
  tone,
}: {
  label: string;
  value: string;
  description: string;
  tone: "teal" | "amber" | "rose";
}) {
  const styles = {
    teal: "border-teal-300/15 bg-teal-300/5 text-teal-300",
    amber: "border-amber-300/15 bg-amber-300/5 text-amber-300",
    rose: "border-rose-300/15 bg-rose-300/5 text-rose-300",
  };

  return (
    <div className={`rounded-2xl border p-5 ${styles[tone]}`}>
      <span className="text-[10px] font-bold uppercase tracking-[0.16em] opacity-70">
        {label}
      </span>
      <strong className="mt-3 block text-3xl font-black tracking-[-0.05em]">
        {value}
      </strong>
      <p className="mt-2 text-xs leading-5 text-slate-500">{description}</p>
    </div>
  );
}

function ProgressBar({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone: "teal" | "rose";
}) {
  const safe = Math.max(0, Math.min(100, value));
  const bar = tone === "teal" ? "bg-teal-300" : "bg-rose-400";

  return (
    <div>
      <div className="mb-2 flex items-center justify-between gap-4 text-xs">
        <span className="font-semibold text-slate-400">{label}</span>
        <span className="font-bold text-slate-200">{percent(safe)}</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-white/10">
        <div
          className={`h-full rounded-full transition-all duration-500 ${bar}`}
          style={{ width: `${safe}%` }}
        />
      </div>
    </div>
  );
}

export function Results({ result }: { result: AnalysisResult | null }) {
  if (!result) {
    return (
      <main className="space-y-5">
        <p className="text-[10px] font-bold uppercase tracking-[0.24em] text-teal-300">
          RESULTS / 03
        </p>
        <h1 className="text-5xl font-black tracking-[-0.07em] text-white">
          No analysis result yet
        </h1>
        <p className="max-w-2xl text-base leading-7 text-slate-400">
          Upload a file to generate a structured error-analysis report.
        </p>
      </main>
    );
  }

  const { analysis } = result;
  const assessment = analysis.assessment;
  const recovery = assessment.recovery;
  const healthy = analysis.status === "healthy";
  const suspected = analysis.status === "suspected";

  const headline = healthy
    ? "File passed the current integrity checks"
    : suspected
      ? "Possible damaged region detected"
      : analysis.status === "unsupported"
        ? "File type is not currently supported"
        : "File corruption detected";

  return (
    <main className="space-y-8">
      <div>
        <p className="mb-4 text-[10px] font-bold uppercase tracking-[0.24em] text-teal-300">
          RESULTS / 03
        </p>
        <h1 className="max-w-5xl text-5xl font-black leading-[0.95] tracking-[-0.07em] text-white sm:text-6xl">
          {headline}
        </h1>
        <p className="mt-5 max-w-3xl text-sm leading-7 text-slate-400">
          RecoverAI now separates measured integrity checks from estimated
          damage and recovery potential. Percentages are estimates when the
          original, known-good file is unavailable.
        </p>
      </div>

      <section className="rounded-3xl border border-white/10 bg-white/[0.035] p-5 sm:p-8">
        <div
          className={`mb-8 inline-flex rounded-full border px-3 py-1.5 text-[10px] font-bold uppercase tracking-[0.14em] ${healthy ? "border-teal-300/20 bg-teal-300/10 text-teal-200" : suspected ? "border-amber-300/20 bg-amber-300/10 text-amber-200" : "border-rose-300/20 bg-rose-300/10 text-rose-200"}`}
        >
          {healthy
            ? "✓ VALIDATED"
            : suspected
              ? "⚠ SUSPECTED DAMAGE"
              : analysis.status === "unsupported"
                ? "? UNSUPPORTED"
                : "⚠ CORRUPTION DETECTED"}
        </div>

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <MetricCard
            label="Estimated corrupted"
            value={percent(assessment.corruptionPercent)}
            description="Estimated affected content or decoded region."
            tone={assessment.corruptionPercent === 0 ? "teal" : "amber"}
          />
          <MetricCard
            label="Estimated recoverable"
            value={percent(recovery.recoverablePercent)}
            description="Content the current engine believes can be preserved or salvaged."
            tone="teal"
          />
          <MetricCard
            label="Not recoverable"
            value={percent(recovery.unrecoverablePercent)}
            description="Content that cannot be reconstructed from the supplied file alone."
            tone="rose"
          />
          <MetricCard
            label="Estimate confidence"
            value={recovery.confidence}
            description="Confidence in the percentage estimate, not file authenticity."
            tone="amber"
          />
        </div>

        {assessment.priority && (
          <div className="mt-8 rounded-2xl border border-teal-300/15 bg-teal-300/5 p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-bold text-white">Evidence priority</h3>
                <p className="mt-1 text-xs text-slate-500">Decision-support score based on measured integrity and recovery potential.</p>
              </div>
              <div className="text-right"><strong className="text-2xl font-black text-teal-300">{assessment.priority.score.toFixed(1)}</strong><span className="ml-2 text-xs font-bold uppercase text-slate-500">{assessment.priority.level}</span></div>
            </div>
          </div>
        )}

        <div className="mt-8 rounded-2xl border border-white/10 bg-[#0b1a20] p-5">
          <div className="space-y-5">
            <ProgressBar
              label="Recoverable content"
              value={recovery.recoverablePercent}
              tone="teal"
            />
            <ProgressBar
              label="Not recoverable from this file"
              value={recovery.unrecoverablePercent}
              tone="rose"
            />
          </div>
        </div>

        <div className="mt-8 grid gap-px overflow-hidden rounded-2xl border border-white/10 bg-white/10 sm:grid-cols-2 lg:grid-cols-4">
          <div className="bg-[#0b1a20] p-4">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
              File name
            </span>
            <strong className="mt-2 block break-all text-sm text-white">
              {result.fileName}
            </strong>
          </div>
          <div className="bg-[#0b1a20] p-4">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
              Type
            </span>
            <strong className="mt-2 block text-sm text-white">
              {result.mimeType}
            </strong>
          </div>
          <div className="bg-[#0b1a20] p-4">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
              Size
            </span>
            <strong className="mt-2 block text-sm text-white">
              {result.sizeFormatted}
            </strong>
          </div>
          <div className="bg-[#0b1a20] p-4">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
              Extension
            </span>
            <strong className="mt-2 block text-sm text-white">
              {result.extension}
            </strong>
          </div>
          <div className="bg-[#0b1a20] p-4">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
              Signature
            </span>
            <strong
              className={`mt-2 block text-sm ${result.analysis.signatureValid ? "text-teal-300" : "text-rose-300"}`}
            >
              {result.analysis.signatureValid ? "Valid" : "Invalid"}
            </strong>
          </div>
          <div className="bg-[#0b1a20] p-4">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
              Corruption flag
            </span>
            <strong className={`mt-2 block text-sm ${result.analysis.corrupted ? "text-amber-300" : "text-teal-300"}`}>
              {result.analysis.corrupted ? "Detected" : "Not detected"}
            </strong>
          </div>
          <div className="bg-[#0b1a20] p-4 sm:col-span-2 lg:col-span-2">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
              SHA-256
            </span>
            <strong className="mt-2 block break-all font-mono text-xs text-slate-300">
              {result.sha256}
            </strong>
          </div>
        </div>

        <div className="mt-8 grid gap-4 lg:grid-cols-[1.5fr_1fr]">
          <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-5">
            <h3 className="text-sm font-bold text-white">Forensic summary</h3>
            <p className="mt-3 text-sm leading-6 text-slate-400">
              {healthy
                ? "The file passed the currently implemented format and integrity checks. This does not prove authenticity or guarantee that every possible form of damage is absent."
                : suspected
                  ? "The parser succeeded, but the decoded content contains a strong persistent anomaly. RecoverAI is treating the affected region as suspected damage rather than claiming byte-exact corruption."
                  : "The file failed one or more validation checks. The detailed findings below explain what failed and what portion may still be salvageable."}
            </p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-5">
            <h3 className="text-sm font-bold text-white">Assessment basis</h3>
            <ul className="mt-3 space-y-2 text-sm leading-6 text-slate-400">
              {recovery.basis.map((item) => (
                <li key={item} className="flex gap-2">
                  <span className="text-teal-300">•</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {assessment.findings.length > 0 && (
          <>
            <h2 className="mt-10 text-xl font-bold text-white">
              Damage findings
            </h2>
            <div className="mt-4 space-y-3">
              {assessment.findings.map((finding) => (
                <div
                  key={finding.code}
                  className="rounded-2xl border border-amber-300/15 bg-amber-300/5 p-5"
                >
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <strong className="text-sm font-bold text-white">
                      {finding.code}
                    </strong>
                    <span className="rounded-full border border-amber-300/20 px-2 py-1 text-[9px] font-bold uppercase tracking-[0.12em] text-amber-300">
                      {finding.severity}
                    </span>
                  </div>
                  <p className="mt-3 text-sm leading-6 text-slate-300">
                    {finding.message}
                  </p>
                  {finding.evidence ? (
                    <pre className="mt-4 overflow-x-auto rounded-xl bg-black/20 p-4 font-mono text-xs leading-6 text-slate-500">
                      {JSON.stringify(finding.evidence, null, 2)}
                    </pre>
                  ) : null}
                </div>
              ))}
            </div>
          </>
        )}

        {analysis.ai && (
          <div className="mt-10 rounded-2xl border border-violet-300/15 bg-violet-300/[0.035] p-5">
            <div className="flex items-center justify-between gap-4">
              <div><h2 className="text-xl font-bold text-white">AI advisory signals</h2><p className="mt-1 text-xs text-slate-500">Fragment-trained model output is supporting evidence, not a replacement for parser validation.</p></div>
              <span className="rounded-full bg-white/5 px-3 py-1 text-[10px] font-bold uppercase tracking-wider text-slate-400">{analysis.ai.available ? "available" : "unavailable"}</span>
            </div>
            <div className="mt-5 grid gap-3 md:grid-cols-3">
              {Object.entries(analysis.ai.models).map(([key, value]) => <div key={key} className="rounded-xl bg-black/20 p-4"><span className="block text-[9px] font-bold uppercase tracking-wider text-slate-600">{key}</span><pre className="mt-2 whitespace-pre-wrap break-words text-xs leading-5 text-slate-400">{JSON.stringify(value, null, 2)}</pre></div>)}
            </div>
          </div>
        )}

        <h2 className="mt-10 text-xl font-bold text-white">
          Detailed analysis
        </h2>
        <div className="mt-4 divide-y divide-white/10 overflow-hidden rounded-2xl border border-white/10">
          {Object.entries(result.analysis.details).map(([key, value]) => (
            <div
              key={key}
              className="flex flex-col gap-2 bg-[#0b1a20] px-5 py-4 sm:flex-row sm:items-start sm:justify-between"
            >
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                {key}
              </span>
              <pre className="max-w-full overflow-x-auto whitespace-pre-wrap break-words font-mono text-xs leading-6 text-slate-300">
                {typeof value === "object"
                  ? JSON.stringify(value, null, 2)
                  : String(value)}
              </pre>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}

export default Results;
