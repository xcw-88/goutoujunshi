"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ReactNode, useState } from "react";

const nav = [
  ["/", "对话", "✦"],
  ["/people", "人物", "◎"],
  ["/memory", "记忆", "◇"],
  ["/files", "文件", "▧"],
  ["/imports", "导入", "⇣"],
  ["/settings", "设置", "⚙"],
];

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  async function logout() {
    try {
      const response = await fetch("/api/auth/logout", { method: "POST", credentials: "same-origin" });
      if (!response.ok && response.status !== 401) throw new Error("logout failed");
      window.dispatchEvent(new Event("goutou:logout"));
    } catch {
      window.alert("退出失败，请检查网络后重试。");
    }
  }

  return (
    <div className="app-shell">
      <header className="mobile-header">
        <button className="icon-button" onClick={() => setOpen((value) => !value)} aria-label="切换导航">
          ☰
        </button>
        <span className="brand-mark small">狗</span>
        <strong>狗头军师</strong>
      </header>
      {open && <button className="nav-backdrop" aria-label="关闭导航" onClick={() => setOpen(false)} />}
      <aside className={`sidebar ${open ? "sidebar-open" : ""}`}>
        <div className="brand">
          <span className="brand-mark">狗</span>
          <div><strong>狗头军师</strong><small>你的关系决策助手</small></div>
        </div>
        <nav>
          {nav.filter(([href]) => process.env.NEXT_PUBLIC_CLOUD_MODE !== "1" || href !== "/files").map(([href, label, icon]) => (
            <Link
              key={href}
              href={href}
              onClick={() => setOpen(false)}
              className={pathname === href ? "active" : ""}
            >
              <span>{icon}</span>{label}
            </Link>
          ))}
        </nav>
        <div className="privacy-note"><span>●</span> {process.env.NEXT_PUBLIC_CLOUD_MODE === "1" ? "聊天文字保存在 D1；附件不保留" : "数据仅保存在本机"}</div>
        {process.env.NEXT_PUBLIC_CLOUD_MODE === "1" && <button className="sidebar-logout" onClick={() => void logout()}>退出登录</button>}
      </aside>
      <main className="main-content">{children}</main>
    </div>
  );
}
