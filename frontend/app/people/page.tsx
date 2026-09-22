"use client";

import { FormEvent, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Person } from "@/lib/types";

const emptyDraft = { display_name: "", notes: "", status: "unknown", relationshipNotes: "" };

export default function PeoplePage() {
  const [people, setPeople] = useState<Person[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [draft, setDraft] = useState(emptyDraft);
  const [notice, setNotice] = useState("");

  async function load() {
    const items = await api<Person[]>("/api/people");
    setPeople(items);
    if (!selectedId && items[0]) selectPerson(items[0]);
  }

  function selectPerson(person: Person) {
    setSelectedId(person.id);
    setDraft({
      display_name: person.display_name,
      notes: person.notes,
      status: person.relationship_profile?.status ?? "unknown",
      relationshipNotes: person.relationship_profile?.notes ?? "",
    });
    setNotice("");
  }

  useEffect(() => {
    api<Person[]>("/api/people").then((items) => {
      setPeople(items);
      if (items[0]) selectPerson(items[0]);
    }).catch(() => setNotice("无法读取人物列表"));
  }, []);

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const created = await api<Person>("/api/people", {
      method: "POST",
      body: JSON.stringify({ display_name: form.get("display_name"), notes: "" }),
    });
    setPeople((items) => [created, ...items]);
    selectPerson(created);
    event.currentTarget.reset();
  }

  async function save() {
    if (!selectedId || !draft.display_name.trim()) return;
    await api<Person>(`/api/people/${selectedId}`, {
      method: "PATCH",
      body: JSON.stringify({ display_name: draft.display_name, notes: draft.notes }),
    });
    await api(`/api/people/${selectedId}/relationship`, {
      method: "PUT",
      body: JSON.stringify({ status: draft.status, notes: draft.relationshipNotes }),
    });
    setNotice("档案已保存");
    await load();
  }

  async function remove() {
    if (!selectedId || !window.confirm("删除该人物及其记忆？相关会话会保留但解除绑定。")) return;
    await api(`/api/people/${selectedId}`, { method: "DELETE" });
    setSelectedId(null);
    setDraft(emptyDraft);
    await load();
  }

  return (
    <div className="page-wrap">
      <div className="page-heading"><div><span className="eyebrow">Profiles</span><h1>人物与关系</h1><p>分别维护每个对象，避免事件和判断串线。</p></div></div>
      <div className="split-grid">
        <section className="surface">
          <form className="inline-create" onSubmit={create}>
            <input name="display_name" required maxLength={100} placeholder="新人物的代号或称呼" />
            <button className="primary">添加</button>
          </form>
          <div className="record-list">
            {people.map((person) => (
              <button key={person.id} className={person.id === selectedId ? "selected" : ""} onClick={() => selectPerson(person)}>
                <span className="record-avatar">{person.display_name.slice(0, 1)}</span>
                <span><strong>{person.display_name}</strong><small>{person.relationship_profile?.status ?? "未设置关系"}</small></span>
              </button>
            ))}
            {!people.length && <div className="empty">还没有人物档案。</div>}
          </div>
        </section>
        <section className="surface editor-card">
          {selectedId ? (
            <>
              <div className="section-title"><h2>档案详情</h2><button className="danger-link" onClick={remove}>删除人物</button></div>
              <label>称呼<input value={draft.display_name} onChange={(e) => setDraft({ ...draft, display_name: e.target.value })} /></label>
              <label>关系状态
                <select value={draft.status} onChange={(e) => setDraft({ ...draft, status: e.target.value })}>
                  {['unknown', 'friend', 'dating', 'relationship', 'former'].map((item) => <option key={item}>{item}</option>)}
                </select>
              </label>
              <label>人物备注<textarea rows={5} value={draft.notes} onChange={(e) => setDraft({ ...draft, notes: e.target.value })} placeholder="只记录用户明确提供的稳定信息" /></label>
              <label>关系备注<textarea rows={5} value={draft.relationshipNotes} onChange={(e) => setDraft({ ...draft, relationshipNotes: e.target.value })} placeholder="双方共识、现实约束与当前目标" /></label>
              <div className="form-actions"><span className="success-note">{notice}</span><button className="primary" onClick={save}>保存档案</button></div>
            </>
          ) : <div className="empty large">选择或添加一个人物后编辑档案。</div>}
        </section>
      </div>
    </div>
  );
}

