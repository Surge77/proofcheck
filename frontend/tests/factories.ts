import type { Match, Receipt, Report } from "../src/types";

export function makeReceipt(overrides: Partial<Receipt> = {}): Receipt {
  return {
    source: "a.png",
    utr: "512345678901",
    amount: "1500",
    payer: "Ramesh Kumar",
    paid_on: "2026-10-03",
    app: "gpay",
    status: "success",
    method: "ocr+vision",
    confidence: "high",
    issues: [],
    ...overrides,
  };
}

export function makeMatch(overrides: Partial<Match> = {}): Match {
  return {
    receipt: makeReceipt(),
    credit: {
      row: 5,
      posted_on: "2026-10-03",
      amount: "1500",
      utr: "512345678901",
      payer: "RAMESH K",
      vpa: null,
      narration: "UPI/CR/512345678901/RAMESH K",
    },
    status: "verified",
    note: "₹1,500 arrived.",
    ...overrides,
  };
}

export function makeReport(overrides: Partial<Report> = {}): Report {
  return {
    bank: "sbi",
    period_start: "2026-10-01",
    period_end: "2026-10-10",
    matches: [makeMatch()],
    counts: { verified: 1 },
    roster: null,
    ...overrides,
  };
}
