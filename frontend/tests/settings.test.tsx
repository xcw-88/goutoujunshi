import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import SettingsPage from "@/app/settings/page";
import { jsonResponse, mockFetch } from "./helpers";

describe("SettingsPage", () => {
  afterEach(() => vi.restoreAllMocks());

  it("shows only a masked API key", async () => {
    mockFetch(() => jsonResponse({ provider: "openai-compatible", base_url: "https://example.test/v1", model: "test-model", temperature: 0.7, max_tokens: 1200, api_key_configured: true, api_key_masked: "sk--****9F3A" }));
    render(<SettingsPage />);
    expect(await screen.findByDisplayValue("test-model")).toBeInTheDocument();
    expect(screen.getByText(/9F3A/)).toBeInTheDocument();
    expect(screen.queryByText(/secret/)).not.toBeInTheDocument();
  });
});

