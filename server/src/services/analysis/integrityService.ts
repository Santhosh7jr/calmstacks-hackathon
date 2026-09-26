export function summarizeIntegrity(analysis: Record<string, unknown>) {
  const status = analysis.status === "healthy" ? "healthy" : "damaged";

  return {
    status,
    signatureValid: analysis.signatureValid === true,
    details: analysis.details ?? {},
  };
}
