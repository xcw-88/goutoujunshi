import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MarkdownMessage } from "@/components/MarkdownMessage";

describe("MarkdownMessage", () => {
  it("renders markdown without interpreting raw model HTML", () => {
    const { container } = render(<MarkdownMessage content={"**建议** <script>alert(1)</script>"} />);
    expect(screen.getByText("建议")).toBeInTheDocument();
    expect(container.querySelector("script")).toBeNull();
    expect(container.textContent).toContain("<script>alert(1)</script>");
  });
});

