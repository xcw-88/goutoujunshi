"use client";

import { FormEvent, useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";

type ModelSettings = {
  provider: string;
  base_url: string;
  model: string;
  temperature: number;
  max_tokens: number;
  api_key_configured: boolean;
  api_key_masked: string | null;
};

const PRESETS = {
  openai: { label: "OpenAI", baseUrl: "https://api.openai.com/v1", model: "gpt-4.1-mini", models: ["gpt-4.1-mini", "gpt-4o-mini"] },
  gemini: { label: "Google Gemini", baseUrl: "https://generativelanguage.googleapis.com/v1beta/openai", model: "gemini-3.8-flash", models: ["gemini-3.8-flash", "gemini-3.7-flash"] },
} as const;
type Preset = keyof typeof PRESETS | "custom";

function presetFor(url: string): Preset {
  if (url.replace(/\/+$/, "") === PRESETS.openai.baseUrl) return "openai";
  if (url.replace(/\/+$/, "") === PRESETS.gemini.baseUrl) return "gemini";
  return "custom";
}

function cloudSecretFor(url: string): string {
  try {
    return new URL(url).hostname === "generativelanguage.googleapis.com" ? "GOUTOU_GEMINI_API_KEY" : "GOUTOU_API_KEY";
  } catch {
    return "GOUTOU_API_KEY";
  }
}

export default function SettingsPage() {
  const cloud = process.env.NEXT_PUBLIC_CLOUD_MODE === "1";
  const [settings, setSettings] = useState<ModelSettings | null>(null);
  const [preset, setPreset] = useState<Preset>("openai");
  const [baseUrl, setBaseUrl] = useState("");
  const [model, setModel] = useState("");
  const [notice, setNotice] = useState("");
  useEffect(() => {
    api<ModelSettings>("/api/settings").then((loaded) => {
      setSettings(loaded);
      setPreset(presetFor(loaded.base_url));
      setBaseUrl(loaded.base_url);
      setModel(loaded.model);
    }).catch(() => setNotice("无法读取设置"));
  }, []);

  function selectPreset(value: Preset) {
    setPreset(value);
    setNotice("");
    if (value !== "custom") {
      setBaseUrl(PRESETS[value].baseUrl);
      setModel(PRESETS[value].model);
    }
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const apiKey = String(form.get("api_key") ?? "").trim();
    try {
      const updated = await api<ModelSettings>("/api/settings", {
        method: "PATCH",
        body: JSON.stringify({
          base_url: baseUrl, model,
          temperature: Number(form.get("temperature")), max_tokens: Number(form.get("max_tokens")),
          ...(apiKey ? { api_key: apiKey } : {}),
        }),
      });
      setSettings(updated);
      setPreset(presetFor(updated.base_url));
      if (!cloud) (formElement.elements.namedItem("api_key") as HTMLInputElement).value = "";
      setNotice(cloud
        ? updated.api_key_configured ? "模型已切换，可以开始聊天。" : `模型已保存；请先在 Worker Secret 中设置 ${cloudSecretFor(updated.base_url)}。`
        : "设置已保存。API Key 仅保留在当前后端进程内存中。");
    } catch (error) {
      setNotice(error instanceof ApiError ? `保存失败：${error.message}` : "保存失败，请稍后重试。");
    }
  }

  async function clearKey() {
    if (!window.confirm("清除当前进程内的 API Key？")) return;
    setSettings(await api<ModelSettings>("/api/settings", { method: "PATCH", body: JSON.stringify({ clear_api_key: true }) }));
    setNotice("当前进程内的 API Key 已清除。")
  }

  return (
    <div className="page-wrap narrow-page">
      <div className="page-heading"><div><span className="eyebrow">Configuration</span><h1>模型设置</h1><p>选择服务商或填写自定义 OpenAI-compatible 接口，再输入该服务商支持的模型 ID。只有开始聊天时，内容才会发送给所选服务商。</p></div></div>
      <section className="surface settings-card">
        {settings ? <form className="stack-form" onSubmit={save}>
          <div className="setting-status"><span className={settings.base_url === baseUrl && settings.api_key_configured ? "status-ok" : "status-warn"}>●</span><div><strong>{preset === "custom" ? "自定义兼容接口" : PRESETS[preset].label}</strong><small>{settings.base_url === baseUrl ? settings.api_key_configured ? `Key 已配置：${settings.api_key_masked}` : "尚未配置 API Key" : "切换接口后保存，以检查对应的 Key"}</small></div></div>
          <label>服务商<select value={preset} onChange={(event) => selectPreset(event.target.value as Preset)}><option value="openai">OpenAI</option><option value="gemini">Google Gemini</option><option value="custom">其他兼容接口（自定义）</option></select></label>
          <label>Base URL<input name="base_url" type="url" required value={baseUrl} readOnly={preset !== "custom"} onChange={(event) => setBaseUrl(event.target.value)} /></label>
          <label>模型 ID<input name="model" required value={model} list="model-suggestions" onChange={(event) => setModel(event.target.value)} /></label>
          <datalist id="model-suggestions">{preset !== "custom" && PRESETS[preset].models.map((item) => <option key={item} value={item} />)}</datalist>
          <p className="field-help">可输入任意模型 ID，但模型必须支持聊天接口；处理截图还需要支持图片输入。</p>
          {preset === "gemini" && <p className="field-help">Google 标明 Gemini API 免费层提交内容可能用于改进其产品。发送私人聊天或截图前，请先阅读 <a href="https://ai.google.dev/gemini-api/docs/pricing" target="_blank" rel="noreferrer">Google 定价与数据使用说明</a>。</p>}
          <div className="two-fields"><label>Temperature<input name="temperature" type="number" min="0" max="2" step="0.1" required defaultValue={settings.temperature} /></label><label>Max tokens<input name="max_tokens" type="number" min="1" max="32768" required defaultValue={settings.max_tokens} /></label></div>
          {cloud ? <p className="field-help">当前接口使用 {cloudSecretFor(baseUrl)} Worker Secret；Key 不会写入 D1 或浏览器。切换服务商后请先保存，再检查 Key 状态。</p> : <><label>API Key<input name="api_key" type="password" autoComplete="off" placeholder={settings.api_key_configured ? "留空则保持不变" : "输入 API Key"} /></label><p className="field-help">本地版切换服务商时请换用对应的 Key。V1 不把 Key 写入 SQLite 或浏览器存储；重启后端后，如未设置环境变量，需要重新输入。</p></>}
          <div className="form-actions">{!cloud && <button type="button" className="danger-link" onClick={clearKey} disabled={!settings.api_key_configured}>清除 Key</button>}<button className="primary">保存设置</button></div>
          {notice && <span className="success-note">{notice}</span>}
        </form> : <div className="empty large">正在读取设置… {notice}</div>}
      </section>
      <section className="privacy-box"><strong>隐私提示</strong><p>{cloud ? "人物、记忆、对话文字保存在 Cloudflare D1；附件只随当前请求处理，原文件不保存，但图片和附件内容会发送到你配置的模型服务商。导入确认后的聊天文字会保存。部署口令并不等于端到端加密。" : "聊天内容与截图会发送到你配置的模型服务商。请根据服务商条款决定是否提交敏感资料；本应用本身不提供云同步或账号系统。"}</p></section>
    </div>
  );
}
