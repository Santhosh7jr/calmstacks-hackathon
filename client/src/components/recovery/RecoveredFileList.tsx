type FileRecord = {
  name: string;
  size: string;
  confidence: number;
};

type RecoveredFileListProps = {
  files: FileRecord[];
};

export function RecoveredFileList({ files }: RecoveredFileListProps) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.035] p-5">
      <h3 className="text-sm font-bold text-white">Recovered files</h3>
      <ul className="mt-4 divide-y divide-white/10">
        {files.map((file) => (
          <li key={file.name} className="flex items-center gap-4 py-3 text-sm">
            <span className="min-w-0 flex-1 truncate text-slate-300">
              {file.name}
            </span>
            <small className="text-xs text-slate-500">{file.size}</small>
            <strong className="text-teal-300">{file.confidence}%</strong>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default RecoveredFileList;
