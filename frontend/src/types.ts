// Mirrors backend/src/proofcheck/models.py and report.py (JSON mode: Decimal and dates are strings).

export type MatchStatus =
  | "verified"
  | "amount_mismatch"
  | "not_in_statement"
  | "outside_period"
  | "duplicate_proof"
  | "unreadable";

export type RosterStatus = "paid" | "partial" | "claimed" | "unpaid";

export interface Receipt {
  source: string;
  utr: string | null;
  amount: string | null;
  payer: string | null;
  paid_on: string | null;
  app: string | null;
  status: "success" | "pending" | "failed" | "unclear";
  method: "ocr+vision" | "ocr_only";
  confidence: "high" | "low";
  issues: string[];
}

export interface StatementTxn {
  row: number;
  posted_on: string;
  amount: string;
  utr: string | null;
  payer: string | null;
  vpa: string | null;
  narration: string;
}

export interface Match {
  receipt: Receipt;
  credit: StatementTxn | null;
  status: MatchStatus;
  note: string;
}

export interface RosterLine {
  name: string;
  due: string;
  received: string;
  status: RosterStatus;
  rows: number[];
  note: string;
}

export interface Report {
  bank: string;
  period_start: string;
  period_end: string;
  matches: Match[];
  counts: Partial<Record<MatchStatus, number>>;
  roster: RosterLine[] | null;
}

export type CheckEvent =
  | { type: "progress"; done: number; total: number; receipt: Receipt }
  | { type: "report"; report: Report };

export interface Health {
  status: string;
  vision: boolean;
  model: string;
}
