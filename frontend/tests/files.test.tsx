import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import FilesPage from "@/app/files/page";
import { jsonResponse, mockFetch } from "./helpers";

describe("FilesPage", () => {
  afterEach(() => vi.restoreAllMocks());

  it("lists local uploads", async () => {
    mockFetch(() => jsonResponse([{ id: "f1", original_name: "chat.txt", stored_name: "safe.txt", mime_type: "text/plain", size: 12, created_at: "2026-01-01" }]));
    render(<FilesPage />);
    expect(await screen.findByText("chat.txt")).toBeInTheDocument();
    expect(screen.getByText(/text\/plain/)).toBeInTheDocument();
  });
});
