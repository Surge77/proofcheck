import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { App } from "../src/app";

describe("App", () => {
  it("shows the product name and the privacy promise", () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: "ProofCheck" })).toBeInTheDocument();
    expect(screen.getByText(/never leaves this computer/i)).toBeInTheDocument();
  });
});
