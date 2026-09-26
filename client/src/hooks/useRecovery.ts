import { useCallback, useState } from "react";
import { startRecovery } from "../services/recoveryService";
import type { RecoveryResult } from "../types/recovery";

export function useRecovery() {
  const [result, setResult] = useState<RecoveryResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const runRecovery = useCallback(async (file: File) => {
    setLoading(true);
    setError("");

    try {
      const nextResult = await startRecovery(file);
      setResult(nextResult);
      return nextResult;
    } catch (caught) {
      const message =
        caught instanceof Error ? caught.message : "Recovery failed.";
      setError(message);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  return { result, loading, error, runRecovery };
}

export default useRecovery;
