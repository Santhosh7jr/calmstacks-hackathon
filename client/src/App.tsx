import { useState } from "react";
import Home from "./pages/Home";
import Recovery from "./pages/Recovery";
import Recover from "./pages/Recover";
import Results from "./pages/Results";
import Fragments from "./pages/Fragments";
import type { AnalysisResult } from "./types/analysis";

type Page = "dashboard" | "recovery" | "recover" | "fragments" | "results";

const navItems: Array<{ label: string; page: Page }> = [
  { label: "Dashboard", page: "dashboard" },
  { label: "Analyze", page: "recovery" },
  { label: "Recover", page: "recover" },
  { label: "Fragments", page: "fragments" },
  { label: "Results", page: "results" },
];

export default function App() {
  const [page, setPage] = useState<Page>("dashboard");
  const [result, setResult] = useState<AnalysisResult | null>(null);

  const handleAnalyze = (nextResult: AnalysisResult) => {
    setResult(nextResult);
    setPage("results");
  };

  return (
    <div className="min-h-screen bg-[#071116] text-slate-100 selection:bg-teal-300 selection:text-slate-950">
      <div className="flex min-h-screen">
        <aside className="hidden w-72 shrink-0 flex-col border-r border-white/10 bg-[#09171d] px-5 py-7 lg:flex">
          <button
            className="mb-12 flex items-center gap-3 text-left"
            onClick={() => setPage("dashboard")}
          >
            <span className="grid h-10 w-10 place-items-center rounded-xl bg-teal-300 text-sm font-black text-slate-950 shadow-[0_0_28px_rgba(94,234,212,0.22)]">
              R
            </span>
            <span className="text-xl font-black tracking-[-0.06em]">
              Recover<span className="text-teal-300">AI</span>
            </span>
          </button>

          <div className="mb-4 px-3 text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500">
            Workspace
          </div>

          <nav className="space-y-1.5">
            {navItems.map((item, index) => (
              <button
                key={item.label}
                className={`group flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left text-sm font-semibold transition ${page === item.page ? "bg-teal-300 text-slate-950 shadow-lg shadow-teal-950/20" : "text-slate-400 hover:bg-white/5 hover:text-white"}`}
                onClick={() => setPage(item.page)}
              >
                <span
                  className={`grid h-7 w-7 place-items-center rounded-lg text-[10px] font-black ${page === item.page ? "bg-slate-950/10" : "bg-white/5 text-slate-500 group-hover:text-teal-300"}`}
                >
                  {String(index + 1).padStart(2, "0")}
                </span>
                {item.label}
              </button>
            ))}
          </nav>

          <div className="mt-auto rounded-2xl border border-teal-300/15 bg-teal-300/5 p-4">
            <div className="mb-3 flex items-center gap-2 text-xs font-bold text-teal-200">
              <span className="h-2 w-2 rounded-full bg-teal-300 shadow-[0_0_10px_#5eead4]" />
              Analysis engine online
            </div>
            <p className="text-xs leading-5 text-slate-500">
              Error analysis and recovery processing is ready for a new file.
            </p>
          </div>
        </aside>

        <div className="min-w-0 flex-1">
          <header className="sticky top-0 z-10 flex items-center justify-between border-b border-white/10 bg-[#071116]/90 px-5 py-4 backdrop-blur-xl sm:px-8 lg:px-10">
            <div className="flex items-center gap-3 lg:hidden">
              <span className="grid h-8 w-8 place-items-center rounded-lg bg-teal-300 text-xs font-black text-slate-950">
                R
              </span>
              <span className="font-black tracking-[-0.05em]">
                Recover<span className="text-teal-300">AI</span>
              </span>
            </div>

            <div className="hidden text-xs font-medium text-slate-500 sm:block">
              Digital forensics /{" "}
              <span className="text-slate-300">
                {navItems.find((item) => item.page === page)?.label}
              </span>
            </div>

            <div className="ml-auto flex items-center gap-3 text-xs font-semibold text-slate-400">
              <span className="h-2 w-2 rounded-full bg-teal-300" />
              System operational
            </div>
          </header>

          <nav className="flex gap-1 overflow-x-auto border-b border-white/5 bg-[#09171d] px-5 py-2 lg:hidden">
            {navItems.map((item) => (
              <button
                key={item.label}
                className={`whitespace-nowrap rounded-lg px-3 py-2 text-xs font-semibold ${page === item.page ? "bg-teal-300 text-slate-950" : "text-slate-500"}`}
                onClick={() => setPage(item.page)}
              >
                {item.label}
              </button>
            ))}
          </nav>

          <main className="mx-auto max-w-[1440px] px-5 py-8 sm:px-8 sm:py-12 lg:px-12">
            {page === "dashboard" && (
              <Home
                onOpenUpload={() => setPage("recovery")}
                onViewResults={() => setPage("results")}
                onOpenRecover={() => setPage("recover")}
                result={result}
              />
            )}

            {page === "recovery" && (
              <Recovery onShowResults={handleAnalyze} />
            )}

            {page === "recover" && <Recover />}

            {page === "fragments" && <Fragments />}

            {page === "results" && <Results result={result} />}

          </main>
        </div>
      </div>
    </div>
  );
}
