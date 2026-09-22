"use client";

import { useEffect, useState } from "react";
import { api, fileUrl, uploadFile } from "@/lib/api";
import type { UploadedFile } from "@/lib/types";

function formatSize(size: number) {
  return size < 1024 * 1024 ? `${Math.ceil(size / 1024)} KB` : `${(size / 1024 / 1024).toFixed(1)} MB`;
}

export default function FilesPage() {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [notice, setNotice] = useState("");

  async function load() { setFiles(await api<UploadedFile[]>("/api/files")); }
  useEffect(() => { api<UploadedFile[]>("/api/files").then(setFiles).catch(() => setNotice("无法读取文件")); }, []);

  async function add(file?: File) {
    if (!file) return;
    try {
      await uploadFile(file);
      setNotice("文件仅保存在本机 data/uploads。")
      await load();
    } catch (reason) { setNotice((reason as Error).message); }
  }

  async function remove(file: UploadedFile) {
    if (!window.confirm(`删除 ${file.original_name}？`)) return;
    await api(`/api/files/${file.id}`, { method: "DELETE" });
    await load();
  }

  return (
    <div className="page-wrap">
      <div className="page-heading"><div><span className="eyebrow">Local files</span><h1>文件与截图</h1><p>支持 PNG、JPG、WEBP、TXT、Markdown、JSON 和 CSV，单文件最大 20 MB。</p></div></div>
      <label className="upload-zone">
        <input type="file" accept=".png,.jpg,.jpeg,.webp,.txt,.md,.json,.csv" onChange={(event) => { void add(event.target.files?.[0]); event.target.value = ""; }} />
        <span className="upload-icon">＋</span><strong>选择本地文件</strong><small>文件名会被替换为安全 UUID；不会上传到本应用以外的位置。</small>
      </label>
      {notice && <p className="success-note center">{notice}</p>}
      <section className="file-grid">
        {files.map((file) => (
          <article className="file-card" key={file.id}>
            {file.mime_type.startsWith("image/") ? <img src={fileUrl(file.id)} alt={file.original_name} /> : <div className="file-type">{file.original_name.split(".").pop()?.toUpperCase()}</div>}
            <div><strong>{file.original_name}</strong><small>{formatSize(file.size)} · {file.mime_type}</small></div>
            <div className="file-actions"><a href={fileUrl(file.id)} target="_blank" rel="noreferrer">查看</a><button className="danger-link" onClick={() => remove(file)}>删除</button></div>
          </article>
        ))}
        {!files.length && <div className="empty large">还没有本地文件。</div>}
      </section>
    </div>
  );
}
