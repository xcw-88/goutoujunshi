"use client";

import { FormEvent, useEffect, useState } from "react";
import { api } from "@/lib/api";

type ModelSettings = {
  provider: string;
  base_url: string;
  model: string;
  temperature: number;
  max_tokens: number;
  api_key_configured: boolean;
  api_key_masked: string | null;
};

export default function SettingsPage() {
  const cloud = process.env.NEXT_PUBLIC_CLOUD_MODE === "1";
  const [settings, setSettings] = useState<ModelSettings | null>(null);
  const [notice, setNotice] = useState("");
  useEffect(() => { api<ModelSettings>("/api/settings").then(setSettings).catch(() => setNotice("无法读取设置")); }, []);

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const apiKey = String(form.get("api_key") ?? "").trim();
    const updated = await api<ModelSettings>("/api/settings", {
      method: "PATCH",
      body: JSON.stringify({
        base_url: form.get("base_url"), model: form.get("model"),
        temperature: Number(form.get("temperature")), max_tokens: Number(form.get("max_tokens")),
        ...(apiKey ? { api_key: apiKey } : {}),
      }),
    });
    setSettings(updated);
    if (!cloud) (event.currentTarget.elements.namedItem("api_key") as HTMLInputElement).value = "";
    setNotice(cloud ? "模型参数已保存。API Key 请通过 Worker Secret 管理。" : "设置已保存。API Key 仅保留在当前后端进程内存中。")
  }

  async function clearKey() {
    if (!window.confirm("清除当前进程内的 API Key？")) return;
    setSettings(await api<ModelSettings>("/api/settings", { method: "PATCH", body: JSON.stringify({ clear_api_key: true }) }));
    setNotice("当前进程内的 API Key 已清除。")
  }

  return (
    <div className="page-wrap narrow-page">
      <div className="page-heading"><div><span className="eyebrow">Configuration</span><h1>模型设置</h1><p>连接任意 OpenAI-compatible 接口。配置不会发送到模型服务商，除非你主动开始聊天。</p></div></div>
      <section className="surface settings-card">
        {settings ? <form className="stack-form" onSubmit={save}>
          <div className="setting-status"><span className={settings.api_key_configured ? "status-ok" : "status-warn"}>●</span><div><strong>{settings.provider}</strong><small>{settings.api_key_configured ? `Key 已配置：${settings.api_key_masked}` : "尚未配置 API Key"}</small></div></div>
          <label>Base URL<input name="base_url" type="url" required defaultValue={settings.base_url} /></label>
          <label>Model<input name="model" required defaultValue={settings.model} /></label>
          <div className="two-fields"><label>Temperature<input name="temperature" type="number" min="0" max="2" step="0.1" required defaultValue={settings.temperature} /></label><label>Max tokens<input name="max_tokens" type="number" min="1" max="32768" required defaultValue={settings.max_tokens} /></label></div>
          {cloud ? <p className="field-help">云端 API Key 只通过 GOUTOU_API_KEY Worker Secret 设置，不会写入 D1 或浏览器。</p> : <><label>API Key<input name="api_key" type="password" autoComplete="off" placeholder={settings.api_key_configured ? "留空则保持不变" : "输入 API Key"} /></label><p className="field-help">V1 不把 Key 写入 SQLite 或浏览器存储。重启后端后，如未设置环境变量，需要重新输入。</p></>}
          <div className="form-actions">{!cloud && <button type="button" className="danger-link" onClick={clearKey} disabled={!settings.api_key_configured}>清除 Key</button>}<button className="primary">保存设置</button></div>
          {notice && <span className="success-note">{notice}</span>}
        </form> : <div className="empty large">正在读取设置… {notice}</div>}
      </section>
      <section className="privacy-box"><strong>隐私提示</strong><p>{cloud ? "人物、记忆、对话文字保存在 Cloudflare D1；附件只随当前请求处理，原文件不保存，但图片和附件内容会发送到你配置的模型服务商。导入确认后的聊天文字会保存。部署口令并不等于端到端加密。" : "聊天内容与截图会发送到你配置的模型服务商。请根据服务商条款决定是否提交敏感资料；本应用本身不提供云同步或账号系统。"}</p></section>
    </div>
  );
}
