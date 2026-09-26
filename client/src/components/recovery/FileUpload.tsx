import type { ChangeEvent } from "react";

type FileUploadProps = {
  onFileSelect: (file: File | null) => void;
  acceptedTypes?: string;
};

export function FileUpload({
  onFileSelect,
  acceptedTypes = ".jpg,.jpeg,.png,.pdf,.docx,.zip",
}: FileUploadProps) {
  const handleChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null;
    onFileSelect(file);
  };

  return (
    <label className="group flex min-h-64 cursor-pointer flex-col items-center justify-center rounded-3xl border border-dashed border-teal-300/30 bg-teal-300/[0.035] px-6 text-center transition hover:border-teal-300/70 hover:bg-teal-300/[0.07]">
      <input
        className="sr-only"
        type="file"
        accept={acceptedTypes}
        onChange={handleChange}
      />
      <span className="mb-4 grid h-14 w-14 place-items-center rounded-2xl bg-teal-300 text-2xl font-black text-slate-950">
        +
      </span>
      <strong className="text-lg font-bold text-white">Drop a file here</strong>
      <span className="mt-2 text-sm text-slate-500">or click to browse</span>
      <small className="mt-6 text-[10px] font-bold uppercase tracking-wider text-slate-600">
        JPG / JPEG / PNG / PDF / DOCX / ZIP
      </small>
    </label>
  );
}

export default FileUpload;
