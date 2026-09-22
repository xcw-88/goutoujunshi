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
          {nav.map(([href, label, icon]) => (
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
        <div className="privacy-note"><span>●</span> 数据仅保存在本机</div>
      </aside>
      <main className="main-content">{children}</main>
    </div>
  );
}

