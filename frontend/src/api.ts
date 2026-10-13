import { createLineSplitter } from "./ndjson";
import type { CheckEvent, Health } from "./types";

export class CheckError extends Error {}

export interface CheckInput {
  screenshots: File[];
  statement: File;
  roster: File | null;
}

export async function fetchHealth(): Promise<Health | null> {
  try {
    const response = await fetch("/api/health");
    return response.ok ? ((await response.json()) as Health) : null;
  } catch {
    return null;
  }
}

async function errorMessage(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string") return body.detail;
  } catch {
    // fall through to the generic message
  }
  return `The check failed (HTTP ${response.status}).`;
}

/** Upload everything and call `onEvent` as each streamed result arrives. */
export async function runCheck(
  input: CheckInput,
  onEvent: (event: CheckEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const form = new FormData();
  for (const file of input.screenshots) form.append("screenshots", file);
  form.append("statement", input.statement);
  if (input.roster) form.append("roster", input.roster);

  const response = await fetch("/api/check", { method: "POST", body: form, signal });
  if (!response.ok || !response.body) throw new CheckError(await errorMessage(response));

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  const split = createLineSplitter();
  for (;;) {
    const { done, value } = await reader.read();
    const lines = split(done ? decoder.decode() : decoder.decode(value, { stream: true }), done);
    for (const line of lines) onEvent(JSON.parse(line) as CheckEvent);
    if (done) return;
  }
}
