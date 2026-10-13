import type { MatchStatus, RosterStatus } from "./types";

const INR = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  minimumFractionDigits: 0,
  maximumFractionDigits: 2,
});

export function formatInr(amount: string | null): string {
  if (amount === null) return "—";
  const value = Number(amount);
  return Number.isFinite(value) ? INR.format(value) : amount;
}

export type Tone = "ok" | "warn" | "bad" | "muted";

export const MATCH_LABELS: Record<MatchStatus, { label: string; tone: Tone }> = {
  verified: { label: "Verified", tone: "ok" },
  amount_mismatch: { label: "Amount differs", tone: "bad" },
  not_in_statement: { label: "Not in statement", tone: "bad" },
  duplicate_proof: { label: "Duplicate", tone: "bad" },
  outside_period: { label: "Outside dates", tone: "warn" },
  unreadable: { label: "Unreadable", tone: "warn" },
};

export const ROSTER_LABELS: Record<RosterStatus, { label: string; tone: Tone }> = {
  paid: { label: "Paid", tone: "ok" },
  partial: { label: "Part paid", tone: "warn" },
  claimed: { label: "Claimed only", tone: "bad" },
  unpaid: { label: "Unpaid", tone: "muted" },
};

export const TONE_CLASSES: Record<Tone, string> = {
  ok: "bg-ok-soft text-ok",
  warn: "bg-warn-soft text-warn",
  bad: "bg-bad-soft text-bad",
  muted: "bg-line text-muted",
};
