/**
 * Split a streamed NDJSON body into whole lines. Network chunks can end mid-line,
 * so the unfinished tail is kept until the next chunk (or flushed at the end).
 */
export function createLineSplitter(): (chunk: string, isLast?: boolean) => string[] {
  let pending = "";
  return (chunk, isLast = false) => {
    const parts = (pending + chunk).split("\n");
    pending = isLast ? "" : (parts.pop() ?? "");
    return parts.map((line) => line.trim()).filter((line) => line.length > 0);
  };
}
