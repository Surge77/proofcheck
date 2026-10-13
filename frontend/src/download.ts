import { matchesToCsv } from "./csv-export";
import type { Match } from "./types";

export function downloadCsv(matches: Match[]): void {
  // BOM so Excel opens the ₹ sign and Indian names as UTF-8.
  const blob = new Blob(["﻿", matchesToCsv(matches)], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "proofcheck-results.csv";
  link.click();
  URL.revokeObjectURL(url);
}
