import { useCallback, useState } from "react";
import { analyzeFile } from "../services/analysisService";
import type { AnalysisResult } from "../types/analysis";

export function useAnalysis() {
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const runAnalysis = useCallback(async (file: File) => {
    setLoading(true);
    setError("");

    try {
      const nextResult = await analyzeFile(file);
      setResult(nextResult);
      return nextResult;
    } catch (caught) {
      const message =
        caught instanceof Error ? caught.message : "Analysis failed.";
      setError(message);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  return { result, loading, error, runAnalysis };
}

export default useAnalysis;
