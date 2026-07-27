import { afterEach, describe, expect, it } from "vitest";
import "@testing-library/jest-dom/vitest";
import { cleanup, render } from "@testing-library/react";
import { BrutalistSkeleton } from "./BrutalistSkeleton";

afterEach(() => {
  cleanup();
});

describe("BrutalistSkeleton", () => {
  it("line variant uses h-4 w-full sizing", () => {
    const { container } = render(<BrutalistSkeleton variant="line" />);
    const el = container.firstElementChild as HTMLElement;
    expect(el.dataset.variant).toBe("line");
    expect(el.className).toContain("h-4");
    expect(el.className).toContain("w-full");
  });

  it("card variant uses h-24 w-full sizing", () => {
    const { container } = render(<BrutalistSkeleton variant="card" />);
    const el = container.firstElementChild as HTMLElement;
    expect(el.dataset.variant).toBe("card");
    expect(el.className).toContain("h-24");
    expect(el.className).toContain("w-full");
  });

  it("block variant uses h-16 w-full sizing", () => {
    const { container } = render(<BrutalistSkeleton variant="block" />);
    const el = container.firstElementChild as HTMLElement;
    expect(el.dataset.variant).toBe("block");
    expect(el.className).toContain("h-16");
    expect(el.className).toContain("w-full");
  });

  it("circle variant uses h-10 w-10 sizing", () => {
    const { container } = render(<BrutalistSkeleton variant="circle" />);
    const el = container.firstElementChild as HTMLElement;
    expect(el.dataset.variant).toBe("circle");
    expect(el.className).toContain("h-10");
    expect(el.className).toContain("w-10");
  });
});
