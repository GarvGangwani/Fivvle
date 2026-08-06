import { afterEach, describe, expect, it } from "vitest";
import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { PanelHeader } from "./PanelHeader";

afterEach(() => {
  cleanup();
});

describe("PanelHeader", () => {
  it("default variant renders the title", () => {
    render(<PanelHeader title="Metrics + verdict" phaseLabel="SIGNAL" />);
    expect(
      screen.getByRole("heading", { name: "Metrics + verdict" }),
    ).toBeInTheDocument();
    expect(screen.getByText("SIGNAL")).toBeInTheDocument();
  });

  it("minimal variant renders a hairline with no title chrome", () => {
    const { container } = render(<PanelHeader variant="minimal" />);
    expect(screen.queryByRole("heading")).not.toBeInTheDocument();
    const hairline = container.querySelector('[role="presentation"]');
    expect(hairline).toBeTruthy();
    expect(hairline?.className).toContain("border-b-[1px]");
  });

  it("renders badge and actions slot children", () => {
    render(
      <PanelHeader
        title="Insight report"
        badge={<span>Publish #2</span>}
        actions={<button type="button">Regenerate</button>}
      />,
    );
    expect(screen.getByText("Publish #2")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Regenerate" }),
    ).toBeInTheDocument();
  });
});
