import type { Match } from "./types";

const HEADER = ["file", "status", "payer", "amount", "utr", "statement_row", "note"];

function cell(value: string | number | null): string {
  let text = value === null ? "" : String(value);
  // Payer names come from screenshots strangers send. A cell starting with = + - @
  // would run as a formula when the CSV is opened in Excel, so prefix it with '.
  if (/^[=+\-@\t\r]/.test(text)) text = `'${text}`;
  return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

export function matchesToCsv(matches: Match[]): string {
  const rows = matches.map((m) => [
    m.receipt.source,
    m.status,
    m.receipt.payer,
    m.receipt.amount,
    m.receipt.utr,
    m.credit?.row ?? null,
    m.note,
  ]);
  return [HEADER, ...rows].map((row) => row.map(cell).join(",")).join("\r\n") + "\r\n";
}
