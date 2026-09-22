"use client";

import { FormEvent, ReactNode, useEffect, useState } from "react";

const cloud = process.env.NEXT_PUBLIC_CLOUD_MODE === "1";

export function CloudAuthGate({ children }: { children: ReactNode }) {
  const [authenticated, setAuthenticated] = useState(!cloud);
  const [checking, setChecking] = useState(cloud);
  const [password, setPassword] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    if (!cloud) return;
    fetch("/api/auth/session", { credentials: "same-origin", cache: "no-store" })
      .then(async (response) => response.ok && (await response.json()).authenticated === true)
      .then(setAuthenticated)
      .catch(() => setNotice("无法连接云端服务，请稍后重试。"))
      .finally(() => setChecking(false));
    const expired = () => { setAuthenticated(false); setNotice("会话已过期，请重新登录。"); };
    const loggedOut = () => { setAuthenticated(false); setNotice(""); };
    window.addEventListener("goutou:unauthorized", expired);
    window.addEventListener("goutou:logout", loggedOut);
    return () => {
      window.removeEventListener("goutou:unauthorized", expired);
      window.removeEventListener("goutou:logout", loggedOut);
    };
  }, []);

  if (!cloud) return <>{children}</>;
  if (checking) return <div className="cloud-login"><div className="surface cloud-login-card">正在验证会话…</div></div>;
  if (authenticated) return <>{children}</>;

  async function login(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setNotice("");
    try {
      const response = await fetch("/api/auth/login", {
        method: "POST", credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password }),
      });
      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: "登录失败" }));
        throw new Error(error.detail ?? "登录失败");
      }
      setPassword("");
      setAuthenticated(true);
    } catch (error) {
      setNotice((error as Error).message);
    }
  }

  return <div className="cloud-login"><form className="surface cloud-login-card stack-form" onSubmit={login}>
    <span className="brand-mark">狗</span><h1>登录狗头军师</h1>
    <p>这是你的私人云端空间。请输入部署时设置的访问口令。</p>
    <label>访问口令<input type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required /></label>
    <button className="primary" type="submit">登录</button>
    {notice && <span role="alert" className="success-note">{notice}</span>}
  </form></div>;
}
