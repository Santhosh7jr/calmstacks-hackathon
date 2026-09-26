import { Button } from "../components/common/Button";
import type { AnalysisResult } from "../types/analysis";

export function Home({
  onOpenUpload,
  onViewResults,
  onOpenRecover,
  result,
}: {
  onOpenUpload: () => void;
  onViewResults: () => void;
  onOpenRecover: () => void;
  result: AnalysisResult | null;
}) {
  const health = result?.analysis.status === "healthy";

  return (
    <main className="space-y-10">
      <div className="grid gap-8 border-b border-white/10 pb-10 xl:grid-cols-[1fr_340px] xl:items-end">
        <div className="max-w-3xl">
          <p className="mb-4 text-[10px] font-bold uppercase tracking-[0.24em] text-teal-300">
            AI-POWERED DIGITAL FORENSICS / 01
          </p>
          <h1 className="text-5xl font-black leading-[0.95] tracking-[-0.07em] text-white sm:text-7xl">
            Recover what matters.
            <br />
            <span className="text-slate-500">Understand what happened.</span>
          </h1>
          <p className="mt-6 max-w-2xl text-base leading-7 text-slate-400">
            RecoverAI analyzes supported files using real file parsers,
            integrity checks, and forensic metadata extraction to separate
            reliable evidence from damaged, incomplete, or suspicious content.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Button onClick={onOpenUpload}>Start analysis →</Button>
            <Button variant="secondary" onClick={onViewResults}>
              View latest results →
            </Button>
            <Button variant="secondary" onClick={onOpenRecover}>
              Recover a file →
            </Button>
          </div>
        </div>
        <div className="rounded-2xl border border-teal-300/15 bg-teal-300/5 p-5">
          <div className="mb-8 flex items-center justify-between text-xs font-bold text-slate-500">
            <span>WORKSPACE STATUS</span>
            <span className="text-teal-300">READY</span>
          </div>
          <div className="mb-2 text-4xl font-black tracking-[-0.06em] text-white">
            {result ? "01" : "00"}
          </div>
          <div className="text-sm text-slate-400">
            {result
              ? "file analyzed in this session"
              : "active analyses in this session"}
          </div>
        </div>
      </div>

      <section className="grid gap-4 md:grid-cols-3">
        <article className="group rounded-2xl border border-white/10 bg-white/[0.035] p-6 transition hover:-translate-y-1 hover:border-teal-300/30">
          <span className="text-xs font-black text-teal-300">
            01 / INTEGRITY
          </span>
          <h3 className="mt-10 text-xl font-bold text-white">File integrity</h3>
          <p className="mt-3 text-sm leading-6 text-slate-500">
            Validate structure, signatures, and parser readability to detect
            tampering or damage.
          </p>
        </article>
        <article className="group rounded-2xl border border-white/10 bg-white/[0.035] p-6 transition hover:-translate-y-1 hover:border-teal-300/30">
          <span className="text-xs font-black text-teal-300">02 / CONTEXT</span>
          <h3 className="mt-10 text-xl font-bold text-white">Metadata</h3>
          <p className="mt-3 text-sm leading-6 text-slate-500">
            Extract facts directly from file headers, document packages, and
            embedded metadata.
          </p>
        </article>
        <article className="group rounded-2xl border border-white/10 bg-white/[0.035] p-6 transition hover:-translate-y-1 hover:border-teal-300/30">
          <span className="text-xs font-black text-teal-300">03 / RISK</span>
          <h3 className="mt-10 text-xl font-bold text-white">
            Corruption detection
          </h3>
          <p className="mt-3 text-sm leading-6 text-slate-500">
            Highlight damaged content, invalid signatures, and recoverability
            estimates with supporting evidence.
          </p>
        </article>
      </section>

      <section className="grid gap-4 lg:grid-cols-[1.3fr_1fr]">
        <div className="rounded-2xl border border-white/10 bg-white/[0.035] p-6">
          <h3 className="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">
            Current signal
          </h3>
          <p className="mt-4 text-lg font-semibold leading-7 text-slate-200">
            {result
              ? health
                ? "This file appears structurally sound and reliable for review."
                : "This file shows signs of corruption or format mismatch and requires caution."
              : "No file uploaded yet. Start a new analysis to generate forensic evidence."}
          </p>
        </div>
        <div className="rounded-2xl border border-white/10 bg-white/[0.035] p-6">
          <h3 className="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">
            Supported evidence
          </h3>
          <p className="mt-4 text-sm leading-6 text-slate-300">
            JPG / JPEG / PNG / GIF / BMP / TIFF / WEBP / PDF / DOCX / ZIP
          </p>
        </div>
      </section>
    </main>
  );
}

export default Home;
