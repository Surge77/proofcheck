import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "../src/app";
import { makeMatch, makeReceipt, makeReport } from "./factories";

function ndjsonResponse(events: unknown[]): Response {
  const body = events.map((event) => JSON.stringify(event)).join("\n") + "\n";
  return new Response(body, { status: 200, headers: { "content-type": "application/x-ndjson" } });
}

function mockServer(check: () => Response, vision = true) {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const url = String(input);
    if (url.endsWith("/api/health")) return Response.json({ status: "ok", vision, model: "gemma3:4b" });
    if (url.endsWith("/api/check")) return check();
    throw new Error(`unexpected fetch ${url}`);
  });
}

async function uploadAndCheck() {
  const user = userEvent.setup();
  render(<App />);
  const png = new File(["png"], "a.png", { type: "image/png" });
  const csv = new File(["csv"], "sbi.csv", { type: "text/csv" });
  await user.upload(screen.getByLabelText(/payment screenshots/i), png);
  await user.upload(screen.getByLabelText(/bank statement/i), csv);
  await user.click(screen.getByRole("button", { name: "Check payments" }));
  return user;
}

afterEach(() => vi.restoreAllMocks());

describe("App", () => {
  it("shows the product name and the privacy promise", () => {
    mockServer(() => ndjsonResponse([]));
    render(<App />);

    expect(screen.getByRole("heading", { name: "ProofCheck" })).toBeInTheDocument();
    expect(screen.getByText(/never leaves this computer/i)).toBeInTheDocument();
  });

  it("keeps the check button disabled until screenshots and a statement are chosen", () => {
    mockServer(() => ndjsonResponse([]));
    render(<App />);

    expect(screen.getByRole("button", { name: "Check payments" })).toBeDisabled();
  });

  it("renders the streamed report with a filterable summary", async () => {
    const report = makeReport({
      matches: [makeMatch(), makeMatch({ status: "not_in_statement", note: "Not found." })],
      counts: { verified: 1, not_in_statement: 1 },
    });
    mockServer(() =>
      ndjsonResponse([
        { type: "progress", done: 1, total: 1, receipt: makeReceipt() },
        { type: "report", report },
      ]),
    );

    const user = await uploadAndCheck();

    expect(await screen.findByRole("button", { name: "1 Verified" })).toBeInTheDocument();
    expect(screen.getAllByRole("row")).toHaveLength(3);
    await user.click(screen.getByRole("button", { name: "1 Not in statement" }));
    const rows = screen.getAllByRole("row");
    expect(rows).toHaveLength(2);
    expect(within(rows[1] as HTMLElement).getByText("Not found.")).toBeInTheDocument();
  });

  it("shows the server's message when the check is rejected", async () => {
    mockServer(() => Response.json({ detail: "Could not find the Date column." }, { status: 422 }));

    await uploadAndCheck();

    expect(await screen.findByRole("alert")).toHaveTextContent("Could not find the Date column.");
  });

  it("warns when the vision model is not available", async () => {
    mockServer(() => ndjsonResponse([]), false);
    render(<App />);

    expect(await screen.findByRole("status")).toHaveTextContent(/OCR only/);
  });
});
