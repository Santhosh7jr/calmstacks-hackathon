import { useState } from "react";
import { Button } from "../components/common/Button";
import { startRecovery } from "../services/recoveryService";
import type { RecoveryResult } from "../types/recovery";

const allowedExtensions = [
  ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tif", ".tiff", ".webp", ".ico",
  ".ppm", ".pgm", ".pbm", ".pnm", ".jp2", ".pdf", ".docx", ".zip",
];

export default function Recover() {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<RecoveryResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const select = (candidate?: File) => {
    setResult(null);
    if (!candidate) return;
    if (!allowedExtensions.some((ext) => candidate.name.toLowerCase().endsWith(ext))) {
      setFile(null);
      setError("Unsupported file type. Upload a supported image, PDF, DOCX, or ZIP file.");
      return;
    }
    setFile(candidate);
    setError("");
  };

  const recover = async () => {
    if (!file) {
      setError("Select a corrupted file first.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const next = await startRecovery(file);
      setResult(next);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Recovery failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="mx-auto max-w-5xl space-y-8">
      <div>
        <p className="mb-4 text-[10px] font-bold uppercase tracking-[0.24em] text-teal-300">RECOVERY ENGINE / 03</p>
        <h1 className="text-5xl font-black tracking-[-0.07em] text-white sm:text-7xl">Recover a file</h1>
        <p className="mt-5 max-w-2xl text-base leading-7 text-slate-400">
          Upload a damaged artifact. RecoverAI uses open-source format-aware recovery: LaMa when its weights are installed, plus forensic image candidate selection, qpdf/pypdf PDF repair, and archive salvage. The original file is never overwritten.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.25fr_.75fr]">
        <label className="group flex min-h-80 cursor-pointer flex-col items-center justify-center rounded-3xl border border-dashed border-teal-300/30 bg-teal-300/[0.035] px-6 text-center transition hover:border-teal-300/70 hover:bg-teal-300/[0.07]">
          <input className="sr-only" type="file" accept={allowedExtensions.join(",")} onChange={(e) => select(e.target.files?.[0])} />
          <span className="mb-5 grid h-16 w-16 place-items-center rounded-2xl bg-teal-300 text-2xl font-black text-slate-950">↻</span>
          <strong className="text-xl font-bold text-white">Choose corrupted file</strong>
          <span className="mt-2 text-sm text-slate-500">The original stays untouched.</span>
          <small className="mt-8 text-[10px] font-bold uppercase tracking-[0.15em] text-slate-600">MAX 50 MB · NON-DESTRUCTIVE SERVER PROCESSING</small>
        </label>

        <div className="rounded-3xl border border-white/10 bg-white/[0.035] p-6">
          <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500">Repair pipeline</p>
          <ol className="mt-6 space-y-5 text-sm">
            {[
              ["01", "Detect", "Reuse the forensic damage assessment."],
              ["02", "Repair", "Use LaMa or a validated forensic image candidate, plus PDF/archive reconstruction."],
              ["03", "Validate", "Analyze the repaired candidate again."],
              ["04", "Export", "Return a new recovered file."],
            ].map(([number, title, text]) => (
              <li key={number} className="flex gap-4">
                <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-white/5 text-[10px] font-black text-teal-300">{number}</span>
                <div><strong className="text-white">{title}</strong><p className="mt-1 leading-5 text-slate-500">{text}</p></div>
              </li>
            ))}
          </ol>
        </div>
      </div>

      {file && (
        <div className="flex flex-col gap-5 rounded-2xl border border-white/10 bg-white/[0.05] p-5 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <strong className="block break-all text-sm font-bold text-white">{file.name}</strong>
            <span className="mt-1 block text-xs text-slate-500">{file.size.toLocaleString()} bytes · {file.type || "unknown MIME type"}</span>
          </div>
          <Button disabled={loading} onClick={recover}>{loading ? "Recovering…" : "Start recovery"}</Button>
        </div>
      )}

      {loading && (
        <div className="rounded-2xl border border-teal-300/20 bg-teal-300/5 p-6">
          <div className="flex items-center justify-between text-sm"><span className="font-semibold text-white">Repairing and validating</span><span className="text-teal-300">working</span></div>
          <div className="mt-4 h-2 overflow-hidden rounded-full bg-white/10"><div className="h-full w-full animate-pulse rounded-full bg-teal-300" /></div>
          <p className="mt-3 text-xs text-slate-500">The backend is generating a candidate and running the forensic analyzer again.</p>
        </div>
      )}

      {error && <div className="rounded-xl border border-rose-300/20 bg-rose-300/10 px-4 py-3 text-sm text-rose-200">{error}</div>}

      {result && (
        <section className="rounded-3xl border border-teal-300/20 bg-teal-300/[0.04] p-6 sm:p-8">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-teal-300">RECOVERY REPORT</p>
              <h2 className="mt-2 text-3xl font-black tracking-[-0.05em] text-white">{result.status === "completed" ? "Recovery candidate ready" : result.status === "completed_partial" ? "Partial recovery candidate ready" : "No repair was needed"}</h2>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">{result.summary}</p>
            </div>
            {result.downloadUrl && <a className="inline-flex shrink-0 items-center justify-center rounded-xl bg-teal-300 px-5 py-3 text-sm font-bold text-slate-950 hover:bg-teal-200" href={result.downloadUrl} download={result.outputFileName}>Download repaired file</a>}
          </div>

          <div className="mt-8 grid gap-4 sm:grid-cols-3">
            <Metric label="Estimated improvement" value={`${result.coverage.toFixed(1)}%`} />
            <Metric label="Output size" value={`${(result.outputSize / 1024 / 1024).toFixed(2)} MB`} />
            <Metric label="Validation" value={result.report?.after?.analysis?.status || "checked"} />
            {result.report?.quality?.pageRetentionPercent != null && <Metric label="Page retention" value={`${result.report.quality.pageRetentionPercent.toFixed(1)}%`} />}
          </div>

          {result.report?.purification ? (
            <div className="mt-7 rounded-2xl border border-teal-300/15 bg-teal-300/5 p-5">
              <p className="text-xs font-bold uppercase tracking-[0.15em] text-teal-200">ML image purification</p>
              <div className="mt-3 grid gap-3 sm:grid-cols-3">
                <Metric label="Pixels purified" value={Number(result.report.purification.pixelsPurified || 0).toLocaleString()} />
                <Metric label="Model patch" value={`${result.report.purification.patchSize || "—"} × ${result.report.purification.patchSize || "—"}`} />
                <Metric label="Passes" value={String(result.report.purification.passes || 0)} />
              </div>
              <p className="mt-3 text-xs leading-5 text-slate-500">The trained model is applied only inside the forensic damage mask. Large regions may additionally use a validated edge-aware fallback.</p>
            </div>
          ) : null}

          {result.report?.methods?.length ? (
            <div className="mt-7 border-t border-white/10 pt-6"><p className="text-xs font-bold uppercase tracking-[0.15em] text-slate-500">Methods applied</p><ul className="mt-3 space-y-2 text-sm text-slate-300">{result.report.methods.map((method: string) => <li key={method}>✓ {method}</li>)}</ul></div>
          ) : null}

          {result.report?.quality?.partial && (
            <div className="mt-6 rounded-xl border border-amber-300/20 bg-amber-300/5 p-4 text-xs leading-5 text-amber-100/80">
              The candidate passed structural validation but is incomplete. Some source content could not be carried into the recovered artifact. Review the warnings before treating it as a complete reconstruction.
            </div>
          )}

          {result.report?.warnings?.length ? (
            <div className="mt-6 rounded-xl border border-amber-300/20 bg-amber-300/5 p-4"><p className="text-xs font-bold uppercase tracking-[0.15em] text-amber-200">Recovery notes</p><ul className="mt-2 space-y-1 text-xs leading-5 text-amber-100/70">{result.report.warnings.map((warning: string) => <li key={warning}>{warning}</li>)}</ul></div>
          ) : null}
        </section>
      )}
    </main>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="rounded-2xl border border-white/10 bg-black/10 p-5"><p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">{label}</p><p className="mt-2 text-2xl font-black text-white">{value}</p></div>;
}
