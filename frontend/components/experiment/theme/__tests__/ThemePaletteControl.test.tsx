import { afterEach, describe, expect, it, vi } from "vitest";
import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ThemeConsentDialog } from "../ThemeConsentDialog";
import { ThemePaletteControl } from "../ThemePaletteControl";

afterEach(() => {
  cleanup();
});

async function openControl(props: {
  active: string | null;
  suggested: string | null;
  onSelect: (palette: string | null) => void;
}) {
  render(<ThemePaletteControl {...props} />);
  await userEvent.click(screen.getByRole("button", { name: "Canvas theme" }));
}

describe("ThemePaletteControl", () => {
  it("marks Default as selected when no palette is active", async () => {
    await openControl({ active: null, suggested: null, onSelect: vi.fn() });

    const swatches = screen.getAllByRole("option");
    expect(swatches).toHaveLength(8);
    expect(swatches[0]).toHaveAttribute("aria-selected", "true");
  });

  it("offers the AI suggestion only when one exists", async () => {
    const onSelect = vi.fn();
    await openControl({ active: null, suggested: "emerald", onSelect });

    await userEvent.click(screen.getByText("AI-Suggested"));
    expect(onSelect).toHaveBeenCalledWith("emerald");
  });

  it("hides the AI suggestion when the classifier returned the default", async () => {
    await openControl({
      active: null,
      suggested: "founder-purple",
      onSelect: vi.fn(),
    });
    expect(screen.queryByText("AI-Suggested")).not.toBeInTheDocument();
  });

  it("selects a curated palette from the swatch grid", async () => {
    const onSelect = vi.fn();
    await openControl({ active: "emerald", suggested: null, onSelect });

    await userEvent.click(
      screen.getByTitle("Crimson — Gaming, entertainment, sports"),
    );
    expect(onSelect).toHaveBeenCalledWith("crimson");
  });

  it("reverts to the platform default via null", async () => {
    const onSelect = vi.fn();
    await openControl({ active: "emerald", suggested: null, onSelect });

    await userEvent.click(screen.getByText("Default"));
    expect(onSelect).toHaveBeenCalledWith(null);
  });
});

describe("ThemeConsentDialog", () => {
  it("previews the suggested palette name and hex", () => {
    render(
      <ThemeConsentDialog
        projectName="Funnode"
        paletteName="crimson"
        onAccept={vi.fn()}
        onDecline={vi.fn()}
      />,
    );

    expect(
      screen.getByRole("heading", { name: /Fivvle picked a theme for Funnode/ }),
    ).toBeInTheDocument();
    expect(screen.getByText("Crimson")).toBeInTheDocument();
    expect(screen.getByText(/#B91C1C/)).toBeInTheDocument();
  });

  it("reports accept and decline separately", async () => {
    const onAccept = vi.fn();
    const onDecline = vi.fn();
    render(
      <ThemeConsentDialog
        projectName={null}
        paletteName="emerald"
        onAccept={onAccept}
        onDecline={onDecline}
      />,
    );

    await userEvent.click(screen.getByRole("button", { name: "Use it" }));
    expect(onAccept).toHaveBeenCalledTimes(1);

    await userEvent.click(screen.getByRole("button", { name: "Keep purple" }));
    expect(onDecline).toHaveBeenCalledTimes(1);
  });
});
