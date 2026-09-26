export type AnalysisStatus =
  | "healthy"
  | "suspected"
  | "corrupted"
  | "unsupported";

export type RecoveryEstimate = {
  corruptionPercent: number;
  recoverablePercent: number;
  unrecoverablePercent: number;
  confidence: "low" | "medium" | "high" | string;
  basis: string[];
};

export type AnalysisFinding = {
  code: string;
  severity: "info" | "low" | "medium" | "high" | "critical" | string;
  message: string;
  evidence?: Record<string, unknown>;
};

export type AnalysisAssessment = {
  classification: "none" | "suspected" | "confirmed" | "unknown" | string;
  corruptionPercent: number;
  recovery: RecoveryEstimate;
  findings: AnalysisFinding[];
  regions: Array<Record<string, unknown>>;
  priority?: { level: "high" | "medium" | "low" | string; score: number; basis: string[] };
};

export type AnalysisResult = {
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
    assessment: AnalysisAssessment;
    ai?: {
      available: boolean;
      note?: string;
      models: Record<string, unknown>;
    };
  };
};
