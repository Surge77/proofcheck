import { useState, type FormEvent } from "react";

import type { CheckInput } from "../api";
import { FilePicker } from "./file-picker";

interface UploadFormProps {
  isBusy: boolean;
  onSubmit: (input: CheckInput) => void;
}

export function UploadForm({ isBusy, onSubmit }: UploadFormProps) {
  const [screenshots, setScreenshots] = useState<File[]>([]);
  const [statement, setStatement] = useState<File[]>([]);
  const [roster, setRoster] = useState<File[]>([]);
  const statementFile = statement[0];
  const canSubmit = !isBusy && screenshots.length > 0 && statementFile !== undefined;

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!canSubmit || !statementFile) return;
    onSubmit({ screenshots, statement: statementFile, roster: roster[0] ?? null });
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-3">
      <div className="grid gap-3 sm:grid-cols-3">
        <FilePicker
          label="Payment screenshots"
          hint="GPay, PhonePe, Paytm… drop them all here"
          accept="image/*"
          multiple
          files={screenshots}
          onChange={setScreenshots}
        />
        <FilePicker
          label="Bank statement"
          hint="CSV or Excel export (SBI, HDFC, ICICI, Kotak)"
          accept=".csv,.xls,.xlsx,.ods"
          files={statement}
          onChange={setStatement}
        />
        <FilePicker
          label="Who owes what (optional)"
          hint="CSV with name, amount"
          accept=".csv"
          files={roster}
          onChange={setRoster}
        />
      </div>
      <div>
        <button
          type="submit"
          disabled={!canSubmit}
          className="rounded-md bg-brand px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-40"
        >
          {isBusy ? "Checking…" : "Check payments"}
        </button>
      </div>
    </form>
  );
}
