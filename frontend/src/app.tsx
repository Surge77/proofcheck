import { useEffect, useRef, useState } from "react";

import { CheckError, fetchHealth, runCheck, type CheckInput } from "./api";
import { HealthBanner } from "./components/health-banner";
import { ResultsTable } from "./components/results-table";
import { RosterTable } from "./components/roster-table";
import { SummaryBar } from "./components/summary-bar";
import { UploadForm } from "./components/upload-form";
import { downloadCsv } from "./download";
import type { Health, MatchStatus, Receipt, Report } from "./types";

type CheckState =
  | { kind: "idle" }
  | { kind: "running"; done: number; total: number; receipts: Receipt[] }
  | { kind: "done"; report: Report }
  | { kind: "error"; message: string };

export function App() {
  const [health, setHealth] = useState<Health | null | undefined>(undefined);
  const [state, setState] = useState<CheckState>({ kind: "idle" });
  const [filter, setFilter] = useState<MatchStatus | null>(null);
  const controller = useRef<AbortController | null>(null);

  useEffect(() => {
    let isMounted = true;
    fetchHealth().then((result) => {
      if (isMounted) setHealth(result);
    });
    return () => {
      isMounted = false;
      controller.current?.abort();
    };
  }, []);

  async function check(input: CheckInput) {
    controller.current?.abort();
    controller.current = new AbortController();
    setFilter(null);
    setState({ kind: "running", done: 0, total: input.screenshots.length, receipts: [] });
    try {
      await runCheck(
        input,
        (event) => {
          if (event.type === "progress") {
            setState((prev) =>
              prev.kind === "running"
                ? { ...prev, done: event.done, total: event.total, receipts: [...prev.receipts, event.receipt] }
                : prev,
            );
          } else {
            setState({ kind: "done", report: event.report });
          }
        },
        controller.current.signal,
      );
    } catch (error: unknown) {
      if (error instanceof DOMException && error.name === "AbortError") return;
      const message = error instanceof CheckError ? error.message : "Lost the connection to ProofCheck.";
      setState({ kind: "error", message });
    }
  }

  const report = state.kind === "done" ? state.report : null;
  const visible = report?.matches.filter((m) => filter === null || m.status === filter) ?? [];

  return (
    <div className="min-h-screen">
      <header className="border-b border-line bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
          <h1 className="text-lg font-semibold tracking-tight">ProofCheck</h1>
          <p className="text-sm text-muted">Your statement never leaves this computer.</p>
        </div>
      </header>

      <main className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-6">
        <HealthBanner health={health} />
        <UploadForm isBusy={state.kind === "running"} onSubmit={check} />

        {state.kind === "running" ? (
          <section className="flex flex-col gap-3" aria-live="polite">
            <p className="text-sm">
              Reading screenshot {Math.min(state.done + 1, state.total)} of {state.total}…
            </p>
            <progress className="h-2 w-full accent-brand" value={state.done} max={state.total} />
            {state.receipts.length > 0 ? <ResultsTable rows={state.receipts} /> : null}
          </section>
        ) : null}

        {state.kind === "error" ? (
          <p role="alert" className="rounded-md bg-bad-soft px-4 py-3 text-sm text-bad">
            {state.message}
          </p>
        ) : null}

        {report ? (
          <section className="flex flex-col gap-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-sm text-muted">
                {report.bank.toUpperCase()} statement, {report.period_start} to {report.period_end}
              </p>
              <button
                type="button"
                onClick={() => downloadCsv(report.matches)}
                className="rounded-md border border-line bg-white px-3 py-1.5 text-sm"
              >
                Export CSV
              </button>
            </div>
            <SummaryBar counts={report.counts} filter={filter} onFilter={setFilter} />
            <ResultsTable rows={visible} />
            {report.roster ? <RosterTable lines={report.roster} /> : null}
          </section>
        ) : null}
      </main>
    </div>
  );
}
