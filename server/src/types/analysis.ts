export type AnalysisStatus = "healthy" | "suspected" | "corrupted" | "unsupported";

export type AnalysisResponse = {
  fileName: string;
  extension: string;
  mimeType: string;
  size: number;
  sizeFormatted: string;
  sha256: string;
  analysis: {
    status: AnalysisStatus;
    corrupted: boolean;
    signatureValid: boolean;
    details: Record<string, unknown>;
    assessment: {
      classification: string;
      corruptionPercent: number;
      recovery: {
        corruptionPercent: number;
        recoverablePercent: number;
        unrecoverablePercent: number;
        confidence: string;
        basis: string[];
      };
      findings: Array<Record<string, unknown>>;
      regions: Array<Record<string, unknown>>;
    };
  };
};
