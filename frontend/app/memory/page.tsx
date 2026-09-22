"use client";

import { FormEvent, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Memory, Person } from "@/lib/types";

const scopes = ["user", "object", "relationship", "event", "hypothesis"] as const;

export default function MemoryPage() {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [people, setPeople] = useState<Person[]>([]);
  const [scope, setScope] = useState<string>("");
  const [personId, setPersonId] = useState<string>("");
  const [notice, setNotice] = useState("");

  async function load() {
    const params = new URLSearchParams();
    if (scope) params.set("scope", scope);
    if (personId) params.set("person_id", personId);
    setMemories(await api<Memory[]>(`/api/memories?${params}`));
  }

  useEffect(() => {
    Promise.all([api<Memory[]>("/api/memories"), api<Person[]>("/api/people")])
      .then(([memoryList, personList]) => { setMemories(memoryList); setPeople(personList); })
      .catch(() => setNotice("无法读取记忆"));
  }, []);

  useEffect(() => {
    const params = new URLSearchParams();
    if (scope) params.set("scope", scope);
    if (personId) params.set("person_id", personId);
    api<Memory[]>(`/api/memories?${params}`).then(setMemories).catch(() => setNotice("无法读取记忆"));
  }, [scope, personId]);

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const selectedScope = String(form.get("scope"));
    const source = selectedScope === "hypothesis" ? "assistant_inference" : "user_explicit";
    await api("/api/memories", {
      method: "POST",
      body: JSON.stringify({
        person_id: selectedScope === "user" ? null : form.get("person_id"),
        scope: selectedScope,
        key: form.get("key"),
        value: form.get("value"),
        source,
        confidence: selectedScope === "hypothesis" ? "medium" : null,
      }),
    });
    setNotice("记忆已添加；推测仍保持为 hypothesis。")
    event.currentTarget.reset();
    await load();
  }

  async function remove(id: string) {
    await api(`/api/memories/${id}`, { method: "DELETE" });
    await load();
  }

  async function clearVisible() {
    if (!window.confirm(personId ? "清空当前人物的全部记忆？" : "清空全部记忆？此操作不可撤销。")) return;
    if (personId) await api(`/api/memories/person/${personId}`, { method: "DELETE" });
    else await api("/api/memories?confirm=true", { method: "DELETE" });
    await load();
  }

  return (
    <div className="page-wrap">
      <div className="page-heading"><div><span className="eyebrow">Memory</span><h1>长期记忆</h1><p>事实、事件与模型推测始终分层保存，随时可以删除。</p></div><button className="danger-link" onClick={clearVisible}>清空{personId ? "当前人物" : "全部"}</button></div>
      <div className="memory-grid">
        <section className="surface">
          <div className="filter-row">
            <select value={personId} onChange={(e) => setPersonId(e.target.value)}><option value="">全部人物</option>{people.map((person) => <option key={person.id} value={person.id}>{person.display_name}</option>)}</select>
            <select value={scope} onChange={(e) => setScope(e.target.value)}><option value="">全部类型</option>{scopes.map((item) => <option key={item}>{item}</option>)}</select>
          </div>
          <div className="memory-list">
            {memories.map((memory) => (
              <article key={memory.id}>
                <div><span className={`scope scope-${memory.scope}`}>{memory.scope}</span><strong>{memory.key}</strong></div>
                <p>{memory.value}</p>
                <footer><span>{people.find((person) => person.id === memory.person_id)?.display_name ?? "用户档案"}{memory.confidence ? ` · ${memory.confidence}` : ""}</span><button className="danger-link" onClick={() => remove(memory.id)}>删除</button></footer>
              </article>
            ))}
            {!memories.length && <div className="empty large">当前筛选下没有记忆。</div>}
          </div>
        </section>
        <section className="surface editor-card compact">
          <h2>手动添加</h2>
          <form onSubmit={create} className="stack-form">
            <label>类型<select name="scope" required defaultValue="event">{scopes.map((item) => <option key={item}>{item}</option>)}</select></label>
            <label>人物<select name="person_id"><option value="">请选择（user 类型除外）</option>{people.map((person) => <option key={person.id} value={person.id}>{person.display_name}</option>)}</select></label>
            <label>字段<input name="key" required maxLength={64} placeholder="如 stage / invitation" /></label>
            <label>内容<textarea name="value" required maxLength={200} rows={4} /></label>
            <button className="primary">添加记忆</button>
            <span className="success-note">{notice}</span>
          </form>
        </section>
      </div>
    </div>
  );
}
