import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import PeoplePage from "@/app/people/page";
import { jsonResponse, mockFetch } from "./helpers";

describe("PeoplePage", () => {
  afterEach(() => vi.restoreAllMocks());

  it("shows a person and relationship details", async () => {
    mockFetch(() => jsonResponse([{ id: "p1", display_name: "小王", notes: "同事", created_at: "2026-01-01", updated_at: "2026-01-01", relationship_profile: { id: "r1", person_id: "p1", status: "dating", notes: "约会中", created_at: "2026-01-01", updated_at: "2026-01-01" } }]));
    render(<PeoplePage />);
    expect(await screen.findByText("小王")).toBeInTheDocument();
    expect(screen.getByDisplayValue("dating")).toBeInTheDocument();
    expect(screen.getByDisplayValue("约会中")).toBeInTheDocument();
  });
});

