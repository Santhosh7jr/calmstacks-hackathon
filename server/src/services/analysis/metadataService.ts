export function getMetadataSummary(metadata: Record<string, unknown>) {
  return Object.entries(metadata).map(([key, value]) => ({ key, value }));
}
