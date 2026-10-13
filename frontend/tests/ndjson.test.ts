import { describe, expect, it } from "vitest";

import { createLineSplitter } from "../src/ndjson";

describe("createLineSplitter", () => {
  it("returns complete lines and keeps a partial line for the next chunk", () => {
    const split = createLineSplitter();

    expect(split('{"a":1}\n{"b"')).toEqual(['{"a":1}']);
    expect(split(":2}\n")).toEqual(['{"b":2}']);
  });

  it("drops blank lines", () => {
    const split = createLineSplitter();

    expect(split("\n\n{}\n\n")).toEqual(["{}"]);
  });

  it("flushes a trailing line without a newline when the stream ends", () => {
    const split = createLineSplitter();
    split('{"done":true}');

    expect(split("", true)).toEqual(['{"done":true}']);
  });
});
