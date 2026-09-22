import { afterEach, describe, expect, it, vi } from "vitest";
import { streamChat } from "@/lib/api";

describe("cloud chat transport", () => {
  afterEach(() => { vi.restoreAllMocks(); vi.unstubAllEnvs(); });

  it("sends selected files in one request without calling the file library", async () => {
    vi.stubEnv("NEXT_PUBLIC_CLOUD_MODE", "1");
    const response = new Response("event: done\ndata: {\"message_id\":\"m1\"}\n\n", {
      headers: { "Content-Type": "text/event-stream" },
    });
    const request = vi.spyOn(globalThis, "fetch").mockResolvedValue(response);
    const events: string[] = [];
    const file = new File(["temporary text"], "notes.txt", { type: "text/plain" });
    await streamChat({ conversation_id: "c1", message: "help", file_ids: [] }, new AbortController().signal,
      (event) => events.push(event), [file]);
    expect(events).toContain("done");
    expect(request).toHaveBeenCalledTimes(1);
    const [url, init] = request.mock.calls[0];
    expect(String(url)).toContain("/api/chat/stream");
    expect(init?.body).toBeInstanceOf(FormData);
    expect((init?.body as FormData).get("files")).toBe(file);
    expect(init?.headers).toBeUndefined();
  });
});
