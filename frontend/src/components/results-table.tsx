import { formatInr, MATCH_LABELS } from "../format";
import type { Match, Receipt } from "../types";
import { Chip } from "./chip";

interface ResultsTableProps {
  /** Final matches, or receipts still being read (shown without a verdict yet). */
  rows: Array<Match | Receipt>;
}

function isMatch(row: Match | Receipt): row is Match {
  return "receipt" in row;
}

export function ResultsTable({ rows }: ResultsTableProps) {
  return (
    <div className="overflow-x-auto rounded-lg border border-line bg-white">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-line text-xs text-muted uppercase">
          <tr>
            <th className="px-3 py-2 font-medium">Screenshot</th>
            <th className="px-3 py-2 font-medium">Paid by</th>
            <th className="px-3 py-2 text-right font-medium">Amount</th>
            <th className="px-3 py-2 font-medium">UPI ref (UTR)</th>
            <th className="px-3 py-2 font-medium">Result</th>
            <th className="px-3 py-2 font-medium">What we found</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => {
            const receipt = isMatch(row) ? row.receipt : row;
            const isLow = receipt.confidence === "low";
            return (
              <tr key={`${receipt.source}-${index}`} className="border-b border-line last:border-0">
                <td className="max-w-40 truncate px-3 py-2" title={receipt.source}>
                  {receipt.source}
                </td>
                <td className="px-3 py-2">{receipt.payer ?? "—"}</td>
                <td className="px-3 py-2 text-right tabular-nums">{formatInr(receipt.amount)}</td>
                <td className="px-3 py-2 font-mono text-xs">{receipt.utr ?? "—"}</td>
                <td className="px-3 py-2">
                  {isMatch(row) ? (
                    <Chip {...MATCH_LABELS[row.status]} />
                  ) : (
                    <span className="text-muted">Read, checking…</span>
                  )}
                </td>
                <td className="px-3 py-2 text-muted">
                  {isMatch(row) ? row.note : null}
                  {isLow && receipt.issues.length > 0 ? (
                    <span className="block text-xs text-warn">Check by hand: {receipt.issues.join(" ")}</span>
                  ) : null}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
