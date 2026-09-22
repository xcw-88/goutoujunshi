"use client";

import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { api, streamChat, uploadFile } from "@/lib/api";
import type { Conversation, Message, Person, UploadedFile } from "@/lib/types";
import { MarkdownMessage } from "@/components/MarkdownMessage";

const greeting: Message = {
  id: "greeting",
  role: "assistant",
  content: "你好，我是狗头军师。你可以直接讲发生了什么，我会先帮你稳住情绪，再一起分清事实、推测和下一步。",
  created_at: new Date(0).toISOString(),
};

export function ChatWorkspace() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [people, setPeople] = useState<Person[]>([]);
  const [current, setCurrent] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([greeting]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState("");
  const [attachments, setAttachments] = useState<UploadedFile[]>([]);
  const abortRef = useRef<AbortController | null>(null);

  const refreshLists = useCallback(async () => {
    const [conversationList, personList] = await Promise.all([
      api<Conversation[]>("/api/conversations"),
      api<Person[]>("/api/people"),
    ]);
    setConversations(conversationList);
    setPeople(personList);
    return conversationList;
  }, []);

  const openConversation = useCallback(async (id: string) => {
    const detail = await api<Conversation>(`/api/conversations/${id}`);
    setCurrent(detail);
    setMessages(detail.messages?.length ? detail.messages : [greeting]);
  }, []);

  const newConversation = useCallback(async () => {
    const created = await api<Conversation>("/api/conversations", {
      method: "POST",
      body: JSON.stringify({}),
    });
    setCurrent(created);
    setMessages([greeting]);
    setConversations((items) => [created, ...items]);
  }, []);

  useEffect(() => {
    let active = true;
    Promise.all([
      api<Conversation[]>("/api/conversations"),
      api<Person[]>("/api/people"),
    ])
      .then(async ([conversationList, personList]) => {
        if (!active) return;
        setConversations(conversationList);
        setPeople(personList);
        if (conversationList[0]) {
          const detail = await api<Conversation>(`/api/conversations/${conversationList[0].id}`);
          if (!active) return;
          setCurrent(detail);
          setMessages(detail.messages?.length ? detail.messages : [greeting]);
        } else {
          const created = await api<Conversation>("/api/conversations", {
            method: "POST",
            body: JSON.stringify({}),
          });
          if (!active) return;
          setCurrent(created);
          setConversations([created]);
        }
      })
      .catch(() => {
        if (active) setError("无法连接本地后端，请确认服务已启动。");
      });
    return () => {
      active = false;
    };
  }, []);

  async function bindPerson(personId: string) {
    if (!current) return;
    const updated = await api<Conversation>(`/api/conversations/${current.id}`, {
      method: "PATCH",
      body: JSON.stringify(personId ? { person_id: personId } : { unbind_person: true }),
    });
    setCurrent({ ...current, person_id: updated.person_id });
  }

  async function submit(event?: FormEvent, override?: string) {
    event?.preventDefault();
    const message = (override ?? input).trim();
    const regenerating = override !== undefined;
    if (!message || streaming || !current) return;
    setInput("");
    setError("");
    setStreaming(true);
    const optimisticUser: Message = {
      id: `user-${Date.now()}`,
      role: "user",
      content: message,
      created_at: new Date().toISOString(),
    };
    const optimisticAssistant: Message = {
      id: `assistant-${Date.now()}`,
      role: "assistant",
      content: "",
      created_at: new Date().toISOString(),
    };
    setMessages((items) => {
      const withoutGreeting = items.filter((item) => item.id !== "greeting");
      if (!regenerating) return [...withoutGreeting, optimisticUser, optimisticAssistant];
      const lastUserIndex = withoutGreeting.findLastIndex((item) => item.role === "user");
      return [...withoutGreeting.slice(0, lastUserIndex + 1), optimisticAssistant];
    });
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      await streamChat(
        {
          conversation_id: current.id,
          person_id: current.person_id,
          message,
          file_ids: attachments.map((file) => file.id),
          regenerate: regenerating,
        },
        controller.signal,
        (type, data) => {
          if (type === "delta") {
            setMessages((items) => items.map((item) =>
              item.id === optimisticAssistant.id
                ? { ...item, content: item.content + String(data.content ?? "") }
                : item,
            ));
          }
          if (type === "done" && data.message_id) {
            setMessages((items) => items.map((item) =>
              item.id === optimisticAssistant.id ? { ...item, id: String(data.message_id) } : item,
            ));
          }
          if (type === "error") throw new Error(String(data.detail ?? "生成失败"));
        },
      );
      await refreshLists();
      setAttachments([]);
    } catch (reason) {
      if ((reason as Error).name !== "AbortError") setError((reason as Error).message);
      setMessages((items) => items.filter((item) => item.id !== optimisticAssistant.id || item.content));
    } finally {
      setStreaming(false);
      abortRef.current = null;
    }
  }

  const lastUserMessage = [...messages].reverse().find((message) => message.role === "user")?.content;

  async function attach(file: File | undefined) {
    if (!file) return;
    try {
      const uploaded = await uploadFile(file);
      setAttachments((items) => [...items, uploaded].slice(-8));
    } catch (reason) {
      setError((reason as Error).message);
    }
  }

  return (
    <div className="chat-layout">
      <section className="conversation-panel">
        <button className="primary full" onClick={newConversation}>＋ 新对话</button>
        <div className="panel-label">最近对话</div>
        <div className="conversation-list">
          {conversations.map((conversation) => (
            <button
              key={conversation.id}
              className={current?.id === conversation.id ? "selected" : ""}
              onClick={() => openConversation(conversation.id)}
            >
              <span>{conversation.title}</span>
              <small>{conversation.person_id ? people.find((p) => p.id === conversation.person_id)?.display_name : "普通咨询"}</small>
            </button>
          ))}
        </div>
      </section>
      <section className="chat-main">
        <header className="chat-header">
          <div><h1>{current?.title ?? "新对话"}</h1><p>事实与推测分开，建议由你决定</p></div>
          <label className="person-picker">当前人物
            <select value={current?.person_id ?? ""} onChange={(event) => bindPerson(event.target.value)}>
              <option value="">不绑定人物</option>
              {people.map((person) => <option key={person.id} value={person.id}>{person.display_name}</option>)}
            </select>
          </label>
        </header>
        <div className="message-scroll" aria-live="polite">
          {messages.map((message) => (
            <article key={message.id} className={`message ${message.role}`}>
              <div className="avatar">{message.role === "user" ? "你" : "狗"}</div>
              <div className="bubble">
                {message.content ? <MarkdownMessage content={message.content} /> : <span className="typing">正在思考…</span>}
                {message.role === "assistant" && message.content && (
                  <button className="text-button" onClick={() => navigator.clipboard.writeText(message.content)}>复制</button>
                )}
              </div>
            </article>
          ))}
        </div>
        {error && <div className="error-banner">{error}</div>}
        <div className="composer-wrap">
          {lastUserMessage && !streaming && (
            <button className="text-button regenerate" onClick={() => submit(undefined, lastUserMessage)}>↻ 重新生成</button>
          )}
          {!!attachments.length && <div className="attachment-row">{attachments.map((file) => <span key={file.id}>{file.original_name}<button type="button" aria-label={`移除 ${file.original_name}`} onClick={() => setAttachments((items) => items.filter((item) => item.id !== file.id))}>×</button></span>)}</div>}
          <form className="composer" onSubmit={submit}>
            <label className="attach-button" title="添加截图或文件">＋<input type="file" accept=".png,.jpg,.jpeg,.webp,.txt,.md,.json,.csv" onChange={(event) => { void attach(event.target.files?.[0]); event.target.value = ""; }} /></label>
            <textarea
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  void submit();
                }
              }}
              placeholder="讲讲发生了什么，或粘贴对话…"
              rows={2}
            />
            {streaming ? (
              <button type="button" className="stop" onClick={() => abortRef.current?.abort()}>■ 停止</button>
            ) : (
              <button type="submit" className="send" disabled={!input.trim()}>↑</button>
            )}
          </form>
          <small className="composer-note">Enter 发送 · Shift + Enter 换行 · AI 建议仅供参考</small>
        </div>
      </section>
    </div>
  );
}
