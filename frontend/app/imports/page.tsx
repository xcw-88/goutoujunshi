"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { api, uploadFile } from "@/lib/api";
import type { Person, UploadedFile } from "@/lib/types";

type Preview = {
  file_id: string;
  format: string;
  total_messages: number;
  senders: string[];
  preview: { sender: string; content: string; timestamp?: string | null }[];
  mapping_required: boolean;
};

export default function ImportsPage() {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [people, setPeople] = useState<Person[]>([]);
  const [fileId, setFileId] = useState("");
  const [preview, setPreview] = useState<Preview | null>(null);
  const [notice, setNotice] = useState("");
  const [completed, setCompleted] = useState(false);

  async function load() {
    const [allFiles, allPeople] = await Promise.all([api<UploadedFile[]>("/api/files"), api<Person[]>("/api/people")]);
    setFiles(allFiles.filter((file) => /\.(txt|md|json|csv)$/i.test(file.original_name)));
    setPeople(allPeople);
  }
  useEffect(() => {
    Promise.all([api<UploadedFile[]>("/api/files"), api<Person[]>("/api/people")])
      .then(([allFiles, allPeople]) => {
        setFiles(allFiles.filter((file) => /\.(txt|md|json|csv)$/i.test(file.original_name)));
        setPeople(allPeople);
      })
      .catch(() => setNotice("无法读取本地文件"));
  }, []);

  async function add(file?: File) {
    if (!file) return;
    const uploaded = await uploadFile(file);
    await load();
    setFileId(uploaded.id);
    setPreview(null);
  }

  async function inspect() {
    if (!fileId) return;
    try {
      setPreview(await api<Preview>("/api/imports/preview", { method: "POST", body: JSON.stringify({ file_id: fileId }) }));
      setCompleted(false);
      setNotice("");
    } catch (reason) { setNotice((reason as Error).message); }
  }

  async function confirm(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      const result = await api<{ conversation_id: string; imported_messages: number }>("/api/imports/confirm", {
        method: "POST",
        body: JSON.stringify({
          file_id: fileId,
          user_sender: form.get("user_sender"),
          object_sender: form.get("object_sender"),
          person_id: form.get("person_id") || null,
          title: form.get("title"),
        }),
      });
      setNotice(`已导入 ${result.imported_messages} 条消息到新对话。`);
      setCompleted(true);
    } catch (reason) { setNotice((reason as Error).message); }
  }

  return (
    <div className="page-wrap">
      <div className="page-heading"><div><span className="eyebrow">Import</span><h1>导入聊天记录</h1><p>先预览，再由你确认谁是用户、谁是对象；系统不会根据昵称、性别或左右位置猜测。</p></div></div>
      <div className="import-steps">
        <section className="surface editor-card">
          <span className="step-number">01</span><h2>选择文件</h2>
          <label className="small-upload">上传 TXT / Markdown / JSON / CSV<input type="file" accept=".txt,.md,.json,.csv" onChange={(event) => { void add(event.target.files?.[0]); event.target.value = ""; }} /></label>
          <label>或选择已上传文件<select value={fileId} onChange={(event) => { setFileId(event.target.value); setPreview(null); }}><option value="">请选择</option>{files.map((file) => <option key={file.id} value={file.id}>{file.original_name}</option>)}</select></label>
          <button className="primary" disabled={!fileId} onClick={inspect}>解析并预览</button>
        </section>
        <section className="surface editor-card preview-panel">
          <span className="step-number">02</span><h2>检查解析结果</h2>
          {preview ? <><div className="preview-meta"><span>{preview.format.toUpperCase()}</span><span>{preview.total_messages} 条</span><span>{preview.senders.length} 位说话人</span></div><div className="transcript-preview">{preview.preview.map((line, index) => <p key={`${line.sender}-${index}`}><strong>{line.sender}</strong><span>{line.content}</span></p>)}</div></> : <div className="empty large">选择文件并预览后，这里会显示前 20 条解析结果。</div>}
        </section>
        <section className="surface editor-card">
          <span className="step-number">03</span><h2>确认说话人映射</h2>
          {preview ? <form className="stack-form" onSubmit={confirm}>
            <label>谁是你？<select name="user_sender" required defaultValue=""><option value="" disabled>请明确选择</option>{preview.senders.map((sender) => <option key={sender}>{sender}</option>)}</select></label>
            <label>谁是对象？<select name="object_sender" required defaultValue=""><option value="" disabled>请明确选择</option>{preview.senders.map((sender) => <option key={sender}>{sender}</option>)}</select></label>
            <label>绑定人物（可选）<select name="person_id"><option value="">暂不绑定</option>{people.map((person) => <option key={person.id} value={person.id}>{person.display_name}</option>)}</select></label>
            <label>对话标题<input name="title" required defaultValue="导入的聊天记录" /></label>
            <button className="primary">确认并创建对话</button>
          </form> : <div className="empty large">完成预览后才能确认映射。</div>}
          {notice && <p className="success-note">{notice}</p>}
          {completed && <Link className="primary-link" href="/">进入对话分析 →</Link>}
        </section>
      </div>
    </div>
  );
}
