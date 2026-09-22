import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import MemoryPage from "@/app/memory/page";
import { jsonResponse, mockFetch } from "./helpers";

describe("MemoryPage", () => {
  afterEach(() => vi.restoreAllMocks());

  it("visually preserves hypothesis scope", async () => {
    mockFetch((url) => url.includes("/api/people") ? jsonResponse([]) : jsonResponse([{ id: "m1", person_id: "p1", scope: "hypothesis", key: "intent", value: "可能感兴趣", confidence: "low", source: "assistant_inference", occurred_at: null, created_at: "2026-01-01", updated_at: "2026-01-01" }]));
    render(<MemoryPage />);
    expect(await screen.findByText("可能感兴趣")).toBeInTheDocument();
    expect(screen.getAllByText("hypothesis").some((node) => node.classList.contains("scope-hypothesis"))).toBe(true);
  });
});
