export function detectFileType(fileName: string): string {
  const extension = fileName.includes(".")
    ? fileName.split(".").pop()?.toLowerCase()
    : "unknown";
  return extension || "unknown";
}
