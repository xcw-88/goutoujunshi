const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000";

export const fileUrl = (id: string) => `${API_BASE}/api/files/${id}/content`;

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
  }
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: response.statusText }));
    throw new ApiError(payload.detail ?? "请求失败", response.status);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export async function streamChat(
  payload: Record<string, unknown>,
  signal: AbortSignal,
  onEvent: (event: string, data: Record<string, unknown>) => void,
): Promise<void> {
  const response = await fetch(`${API_BASE}/api/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal,
  });
  if (!response.ok || !response.body) {
    throw new ApiError("无法开始生成", response.status);
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value, { stream: !done });
    const blocks = buffer.split("\n\n");
    buffer = blocks.pop() ?? "";
    for (const block of blocks) {
      let event = "message";
      let data = "{}";
      for (const line of block.split("\n")) {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        if (line.startsWith("data:")) data = line.slice(5).trim();
      }
      onEvent(event, JSON.parse(data) as Record<string, unknown>);
    }
    if (done) break;
  }
}

export async function uploadFile(file: File): Promise<import("./types").UploadedFile> {
  const body = new FormData();
  body.append("file", file);
  const response = await fetch(`${API_BASE}/api/files`, { method: "POST", body });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: "上传失败" }));
    throw new ApiError(payload.detail ?? "上传失败", response.status);
  }
  return response.json();
}
