import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import SettingsPage from "@/app/settings/page";
import { jsonResponse, mockFetch } from "./helpers";

describe("SettingsPage", () => {
  afterEach(() => { cleanup(); vi.restoreAllMocks(); });

  it("shows only a masked API key", async () => {
    mockFetch(() => jsonResponse({ provider: "openai-compatible", base_url: "https://example.test/v1", model: "test-model", temperature: 0.7, max_tokens: 1200, api_key_configured: true, api_key_masked: "sk--****9F3A" }));
    render(<SettingsPage />);
    expect(await screen.findByDisplayValue("test-model")).toBeInTheDocument();
    expect(screen.getByText(/9F3A/)).toBeInTheDocument();
    expect(screen.queryByText(/secret/)).not.toBeInTheDocument();
  });

  it("switches to Gemini and saves an arbitrary model ID", async () => {
    const fetcher = mockFetch((_url, init) => {
      if (init?.method === "PATCH") {
        const body = JSON.parse(String(init.body));
        return jsonResponse({ provider: "openai-compatible", ...body, api_key_configured: false, api_key_masked: null });
      }
      return jsonResponse({ provider: "openai-compatible", base_url: "https://api.openai.com/v1", model: "gpt-4.1-mini", temperature: 0.7, max_tokens: 1200, api_key_configured: false, api_key_masked: null });
    });
    render(<SettingsPage />);
    await screen.findByDisplayValue("gpt-4.1-mini");
    fireEvent.change(screen.getByLabelText("服务商"), { target: { value: "gemini" } });
    expect(screen.getByDisplayValue("https://generativelanguage.googleapis.com/v1beta/openai")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("模型 ID"), { target: { value: "gemini-my-model" } });
    fireEvent.click(screen.getByRole("button", { name: "保存设置" }));
    await waitFor(() => expect(fetcher).toHaveBeenCalledWith(expect.stringContaining("/api/settings"), expect.objectContaining({ method: "PATCH" })));
    const submitted = JSON.parse(String(fetcher.mock.calls.find((call) => call[1]?.method === "PATCH")?.[1]?.body));
    expect(submitted).toMatchObject({ base_url: "https://generativelanguage.googleapis.com/v1beta/openai", model: "gemini-my-model" });
  });
});
