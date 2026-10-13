import { MATCH_LABELS, TONE_CLASSES } from "../format";
import type { MatchStatus, Report } from "../types";

interface SummaryBarProps {
  counts: Report["counts"];
  filter: MatchStatus | null;
  onFilter: (status: MatchStatus | null) => void;
}

const ORDER: MatchStatus[] = [
  "verified",
  "not_in_statement",
  "amount_mismatch",
  "duplicate_proof",
  "outside_period",
  "unreadable",
];

export function SummaryBar({ counts, filter, onFilter }: SummaryBarProps) {
  return (
    <div className="flex flex-wrap gap-2" role="group" aria-label="Filter by result">
      {ORDER.filter((status) => (counts[status] ?? 0) > 0).map((status) => {
        const { label, tone } = MATCH_LABELS[status];
        const isActive = filter === status;
        return (
          <button
            key={status}
            type="button"
            aria-pressed={isActive}
            onClick={() => onFilter(isActive ? null : status)}
            className={`rounded-md px-3 py-1.5 text-sm font-medium ring-offset-1 ${TONE_CLASSES[tone]} ${
              isActive ? "ring-2 ring-ink" : ""
            }`}
          >
            {counts[status]} {label}
          </button>
        );
      })}
    </div>
  );
}
