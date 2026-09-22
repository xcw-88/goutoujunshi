import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import FilesPage from "@/app/files/page";
import { jsonResponse, mockFetch } from "./helpers";

describe("FilesPage", () => {
  afterEach(() => { vi.restoreAllMocks(); vi.unstubAllEnvs(); });

  it("lists local uploads", async () => {
    mockFetch(() => jsonResponse([{ id: "f1", original_name: "chat.txt", stored_name: "safe.txt", mime_type: "text/plain", size: 12, created_at: "2026-01-01" }]));
    render(<FilesPage />);
    expect(await screen.findByText("chat.txt")).toBeInTheDocument();
    expect(screen.getByText(/text\/plain/)).toBeInTheDocument();
  });

  it("does not load a file library in cloud mode", () => {
    vi.stubEnv("NEXT_PUBLIC_CLOUD_MODE", "1");
    const request = vi.spyOn(globalThis, "fetch");
    render(<FilesPage />);
    expect(screen.getByText(/云端不设文件库/)).toBeInTheDocument();
    expect(request).not.toHaveBeenCalled();
  });
});
