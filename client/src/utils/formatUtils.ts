export function formatTimestamp(value: string | number | Date): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Unknown";
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

export function scoreToPercent(value: number): string {
  return `${Math.min(Math.max(value, 0), 100).toFixed(0)}%`;
}
