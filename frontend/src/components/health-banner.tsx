import type { Health } from "../types";

interface HealthBannerProps {
  /** undefined while loading, null when the backend is unreachable */
  health: Health | null | undefined;
}

export function HealthBanner({ health }: HealthBannerProps) {
  if (health === undefined || health?.vision) return null;
  const message =
    health === null
      ? "Can't reach the ProofCheck server. Start it with `uv run proofcheck`."
      : `The local vision model (${health.model}) isn't running, so results will use OCR only and be marked for checking. Start Ollama and run \`ollama pull ${health.model}\`.`;
  return (
    <p role="status" className="rounded-md bg-warn-soft px-4 py-3 text-sm text-warn">
      {message}
    </p>
  );
}
