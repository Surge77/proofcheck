import { useId, useState, type DragEvent } from "react";

interface FilePickerProps {
  label: string;
  hint: string;
  accept: string;
  multiple?: boolean;
  files: File[];
  onChange: (files: File[]) => void;
}

export function FilePicker({ label, hint, accept, multiple = false, files, onChange }: FilePickerProps) {
  const id = useId();
  const [isOver, setIsOver] = useState(false);

  function onDrop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setIsOver(false);
    const dropped = Array.from(event.dataTransfer.files);
    onChange(multiple ? dropped : dropped.slice(0, 1));
  }

  const summary =
    files.length === 0 ? hint : files.length === 1 ? files[0]?.name : `${files.length} files selected`;

  return (
    <label
      htmlFor={id}
      onDragOver={(event) => {
        event.preventDefault();
        setIsOver(true);
      }}
      onDragLeave={() => setIsOver(false)}
      onDrop={onDrop}
      className={`flex cursor-pointer flex-col gap-1 rounded-lg border border-dashed p-4 transition-colors ${
        isOver ? "border-brand bg-white" : "border-line bg-white hover:border-muted"
      }`}
    >
      <span className="text-sm font-medium">{label}</span>
      <span className={`truncate text-sm ${files.length ? "text-ink" : "text-muted"}`}>{summary}</span>
      <input
        id={id}
        type="file"
        accept={accept}
        multiple={multiple}
        className="sr-only"
        onChange={(event) => onChange(Array.from(event.target.files ?? []))}
      />
    </label>
  );
}
