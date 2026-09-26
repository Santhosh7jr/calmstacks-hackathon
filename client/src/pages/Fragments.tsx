import { useState } from "react";
import { Button } from "../components/common/Button";
import { reconstructFragments } from "../services/fragmentService";
import type { FragmentReport } from "../services/fragmentService";

export default function Fragments() {
  const [files, setFiles] = useState<File[]>([]);
  const [outputName, setOutputName] = useState("reconstructed.bin");
  const [report, setReport] = useState<FragmentReport | null>(null);
  const [downloadUrl, setDownloadUrl] = useState("");
  const [downloadName, setDownloadName] = useState("reconstructed.bin");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const submit = async () => {
    if (!files.length) return setError("Select at least one fragment.");
    setLoading(true);
    setError("");
    try {
      const result = await reconstructFragments(files, outputName);
      setReport(result.report);
      setDownloadUrl(result.downloadUrl);
      setDownloadName(result.outputName);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Fragment reconstruction failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="mx-auto max-w-6xl space-y-8">
      <div>
        <p className="mb-4 text-[10px] font-bold uppercase tracking-[0.24em] text-teal-300">FRAGMENT LAB / 04</p>
        <h1 className="text-5xl font-black tracking-[-0.07em] text-white sm:text-7xl">Match. Order. Reconstruct.</h1>
        <p className="mt-5 max-w-3xl text-base leading-7 text-slate-400">
          Upload fragments from the same suspected artifact. RecoverAI combines the trained fragment matcher with deterministic byte-continuity signals, proposes an order, concatenates the bytes, and validates the candidate separately.
        </p>
      </div>

      <section className="grid gap-6 lg:grid-cols-[1.15fr_.85fr]">
        <label className="flex min-h-72 cursor-pointer flex-col items-center justify-center rounded-3xl border border-dashed border-teal-300/30 bg-teal-300/[0.035] px-6 text-center hover:border-teal-300/70">
          <input className="sr-only" type="file" multiple onChange={(event) => setFiles(Array.from(event.target.files || []))} />
          <span className="mb-5 grid h-16 w-16 place-items-center rounded-2xl bg-teal-300 text-2xl font-black text-slate-950">+</span>
          <strong className="text-xl font-bold text-white">Choose fragments</strong>
          <span className="mt-2 text-sm text-slate-500">Up to 32 fragments · 50 MB total request limit</span>
        </label>

        <div className="rounded-3xl border border-white/10 bg-white/[0.035] p-6">
          <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500">Output</p>
          <input value={outputName} onChange={(event) => setOutputName(event.target.value)} className="mt-4 w-full rounded-xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-white outline-none focus:border-teal-300/40" placeholder="reconstructed.pdf" />
          <Button className="mt-4 w-full" disabled={loading || !files.length} onClick={submit}>{loading ? "Reconstructing…" : "Build candidate"}</Button>
          {files.length > 0 && <p className="mt-4 text-xs text-slate-500">{files.length} fragment{files.length === 1 ? "" : "s"} selected.</p>}
        </div>
      </section>

      {files.length > 0 && (
        <section className="rounded-3xl border border-white/10 bg-white/[0.035] p-6">
          <h2 className="text-sm font-bold text-white">Selected fragments</h2>
          <div className="mt-4 grid gap-2 md:grid-cols-2 xl:grid-cols-3">
            {files.map((file) => <div key={`${file.name}-${file.size}`} className="rounded-xl bg-black/20 px-4 py-3 text-xs text-slate-300"><span className="block truncate">{file.name}</span><span className="mt-1 block text-slate-600">{file.size.toLocaleString()} bytes</span></div>)}
          </div>
        </section>
      )}

      {error && <div className="rounded-xl border border-rose-300/20 bg-rose-300/10 px-4 py-3 text-sm text-rose-200">{error}</div>}

      {report && (
        <section className="space-y-6 rounded-3xl border border-teal-300/20 bg-teal-300/[0.04] p-6 sm:p-8">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div><p className="text-[10px] font-bold uppercase tracking-[0.2em] text-teal-300">RECONSTRUCTION REPORT</p><h2 className="mt-2 text-3xl font-black text-white">Candidate assembled</h2><p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">{report.message}</p></div>
            {downloadUrl && <a className="inline-flex rounded-xl bg-teal-300 px-5 py-3 text-sm font-bold text-slate-950" href={downloadUrl} download={downloadName}>Download candidate</a>}
          </div>
          <div className="grid gap-4 sm:grid-cols-3">
            <Metric label="Match confidence" value={`${report.matchConfidencePercent.toFixed(1)}%`} />
            <Metric label="Validation" value={report.validation?.analysis?.status || "checked"} />
            <Metric label="Output size" value={`${(report.outputSize / 1024).toFixed(1)} KB`} />
          </div>
          <div><p className="text-xs font-bold uppercase tracking-[0.15em] text-slate-500">Proposed order</p><ol className="mt-3 space-y-2">{report.orderedFragments.map((name, index) => <li key={`${name}-${index}`} className="rounded-xl bg-black/20 px-4 py-3 text-xs text-slate-300"><span className="mr-3 text-teal-300">{String(index + 1).padStart(2, "0")}</span>{name}</li>)}</ol></div>
          {report.edges.length > 0 && <div><p className="text-xs font-bold uppercase tracking-[0.15em] text-slate-500">Ordering evidence</p><div className="mt-3 space-y-2">{report.edges.map((edge) => <div key={`${edge.from}-${edge.to}`} className="rounded-xl border border-white/5 bg-black/20 p-4 text-xs"><div className="flex justify-between gap-4"><span className="truncate text-slate-300">{edge.from} → {edge.to}</span><strong className="text-teal-300">{edge.score.toFixed(1)}%</strong></div><div className="mt-2 text-slate-600">ML {edge.signals.ml.toFixed(1)}% · overlap {edge.signals.overlap.toFixed(1)}%</div></div>)}</div></div>}
        </section>
      )}
    </main>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="rounded-2xl border border-white/10 bg-black/10 p-5"><p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">{label}</p><p className="mt-2 text-2xl font-black text-white">{value}</p></div>;
}
