import { describe, expect, it } from "vitest";

import { matchesToCsv } from "../src/csv-export";
import { makeMatch } from "./factories";

describe("matchesToCsv", () => {
  it("writes a header and one row per match", () => {
    const csv = matchesToCsv([makeMatch()]);

    const [header, row] = csv.trim().split("\r\n");
    expect(header).toBe("file,status,payer,amount,utr,statement_row,note");
    expect(row).toBe('a.png,verified,Ramesh Kumar,1500,512345678901,5,"₹1,500 arrived."');
  });

  it("quotes cells containing quotes or commas", () => {
    const csv = matchesToCsv([makeMatch({ note: 'He said "paid", twice' })]);

    expect(csv).toContain('"He said ""paid"", twice"');
  });

  it("neutralises spreadsheet formulas coming from screenshot text", () => {
    const match = makeMatch();
    const csv = matchesToCsv([{ ...match, receipt: { ...match.receipt, payer: "=HYPERLINK(1)" } }]);

    expect(csv).toContain("'=HYPERLINK(1)");
  });
});
