import { formatInr, ROSTER_LABELS } from "../format";
import type { RosterLine } from "../types";
import { Chip } from "./chip";

interface RosterTableProps {
  lines: RosterLine[];
}

export function RosterTable({ lines }: RosterTableProps) {
  const paid = lines.filter((line) => line.status === "paid").length;
  return (
    <section className="flex flex-col gap-2">
      <h2 className="text-base font-semibold">
        Who has paid <span className="font-normal text-muted">({paid} of {lines.length})</span>
      </h2>
      <div className="overflow-x-auto rounded-lg border border-line bg-white">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-line text-xs text-muted uppercase">
            <tr>
              <th className="px-3 py-2 font-medium">Name</th>
              <th className="px-3 py-2 text-right font-medium">Due</th>
              <th className="px-3 py-2 text-right font-medium">Received</th>
              <th className="px-3 py-2 font-medium">Status</th>
              <th className="px-3 py-2 font-medium">Note</th>
            </tr>
          </thead>
          <tbody>
            {lines.map((line) => (
              <tr key={line.name} className="border-b border-line last:border-0">
                <td className="px-3 py-2">{line.name}</td>
                <td className="px-3 py-2 text-right tabular-nums">{formatInr(line.due)}</td>
                <td className="px-3 py-2 text-right tabular-nums">{formatInr(line.received)}</td>
                <td className="px-3 py-2">
                  <Chip {...ROSTER_LABELS[line.status]} />
                </td>
                <td className="px-3 py-2 text-muted">{line.note}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
