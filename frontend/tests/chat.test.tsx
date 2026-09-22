import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ChatWorkspace } from "@/components/ChatWorkspace";
import { jsonResponse, mockFetch } from "./helpers";

describe("ChatWorkspace", () => {
  afterEach(() => vi.restoreAllMocks());

  it("creates an initial local conversation and shows the safe greeting", async () => {
    mockFetch((url, init) => {
      if (url.endsWith("/api/people")) return jsonResponse([]);
      if (url.endsWith("/api/conversations") && init?.method === "POST") {
        return jsonResponse({ id: "c1", title: "新对话", person_id: null, created_at: "2026-01-01", updated_at: "2026-01-01" }, 201);
      }
      if (url.endsWith("/api/conversations")) return jsonResponse([]);
      throw new Error(`unexpected URL ${url}`);
    });

    render(<ChatWorkspace />);
    expect(screen.getByText(/你好，我是狗头军师/)).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("button", { name: /新对话/ })).toBeEnabled());
    expect(screen.getByPlaceholderText(/讲讲发生了什么/)).toBeInTheDocument();
  });
});

