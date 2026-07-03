import { useCallback, useEffect, useRef, useState } from "react";

import { streamChat } from "../utils/chatStream";

const AUTO_SCROLL_THRESHOLD_PX = 48;

function formatCueTime(sec) {
  if (sec == null) return "?:??";
  const s = Math.floor(sec);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const ss = s % 60;
  if (h) return `${h}:${String(m).padStart(2, "0")}:${String(ss).padStart(2, "0")}`;
  return `${m}:${String(ss).padStart(2, "0")}`;
}

export default function ChatPanel({
  url,
  transcript,
  summary,
  preferLang,
  outputLang,
  messages,
  onMessagesChange,
  onCitationClick,
  t,
}) {
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const [error, setError] = useState("");
  const abortRef = useRef(null);
  const messagesRef = useRef(null);
  const shouldAutoScrollRef = useRef(true);

  useEffect(() => {
    document.documentElement.classList.toggle("page-scroll-anchor-disabled", streaming);
    return () => {
      document.documentElement.classList.remove("page-scroll-anchor-disabled");
    };
  }, [streaming]);

  useEffect(() => {
    const container = messagesRef.current;
    if (!container) return;
    if (!shouldAutoScrollRef.current) return;
    container.scrollTop = container.scrollHeight;
  }, [messages, streamingText, streaming]);

  const handleMessagesScroll = useCallback(() => {
    const container = messagesRef.current;
    if (!container) return;
    const distanceFromBottom = container.scrollHeight - container.scrollTop - container.clientHeight;
    shouldAutoScrollRef.current = distanceFromBottom <= AUTO_SCROLL_THRESHOLD_PX;
  }, []);

  const sendMessage = useCallback(async () => {
    const text = input.trim();
    if (!text || streaming || !transcript) return;

    setError("");
    setInput("");
    const userMsg = { role: "user", content: text, created_at: new Date().toISOString() };
    const nextMessages = [...messages, userMsg];
    onMessagesChange(nextMessages);

    const controller = new AbortController();
    abortRef.current = controller;
    setStreaming(true);
    setStreamingText("");

    try {
      let answerText = "";
      let citations = [];

      for await (const { event, data } of streamChat(url, {
        messages: nextMessages,
        transcript,
        summary,
        preferLang,
        outputLang,
        signal: controller.signal,
      })) {
        if (event === "answer_delta") {
          answerText += data.text || "";
          setStreamingText(answerText);
        } else if (event === "answer") {
          answerText = data.answer || answerText;
          citations = data.citations || [];
        } else if (event === "error") {
          throw new Error(data.message || data.code || "Chat failed");
        } else if (event === "done") {
          break;
        }
      }

      onMessagesChange([
        ...nextMessages,
        {
          role: "assistant",
          content: answerText,
          citations,
          created_at: new Date().toISOString(),
        },
      ]);
      setStreamingText("");
    } catch (e) {
      if (e.name !== "AbortError") {
        setError(e.message);
      }
    } finally {
      abortRef.current = null;
      setStreaming(false);
    }
  }, [
    input,
    streaming,
    transcript,
    messages,
    url,
    summary,
    preferLang,
    outputLang,
    onMessagesChange,
  ]);

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  if (!transcript) {
    return (
      <p className="py-8 text-center text-sm text-slate-400">{t("understanding.chat_need_transcript")}</p>
    );
  }

  return (
    <div className="flex flex-col">
      <div
        ref={messagesRef}
        onScroll={handleMessagesScroll}
        className="mb-3 max-h-[420px] min-h-[280px] overflow-y-auto rounded-xl border border-indigo-100/80 bg-slate-50/40 p-3"
      >
        {messages.length === 0 && !streaming && (
          <div className="flex h-full min-h-[240px] flex-col items-center justify-center text-center">
            <p className="text-sm font-semibold text-slate-700">{t("understanding.chat_empty_title")}</p>
            <p className="mt-1.5 max-w-sm text-xs text-slate-500">{t("understanding.chat_empty_hint")}</p>
          </div>
        )}

        <div className="space-y-3">
          {messages.map((msg, idx) => (
            <MessageBubble
              key={`${msg.role}-${idx}-${msg.created_at || idx}`}
              message={msg}
              onCitationClick={onCitationClick}
            />
          ))}

          {streaming && streamingText && (
            <MessageBubble message={{ role: "assistant", content: streamingText, streaming: true }} />
          )}

          {streaming && !streamingText && (
            <div className="flex items-center gap-2 text-xs text-indigo-500">
              <TypingDots /> {t("understanding.chat_thinking")}
            </div>
          )}
        </div>
      </div>

      {error && (
        <p className="mb-2 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-600">{error}</p>
      )}

      <div className="flex gap-2">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={streaming}
          rows={2}
          placeholder={t("understanding.chat_placeholder")}
          className="min-h-11 flex-1 resize-none rounded-xl border border-indigo-100 bg-white px-3 py-2.5 text-sm outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100 disabled:opacity-60"
        />
        <button
          type="button"
          onClick={sendMessage}
          disabled={streaming || !input.trim()}
          className="min-h-11 shrink-0 self-end rounded-xl brand-gradient px-4 py-2.5 text-sm font-semibold text-white shadow-md shadow-indigo-200 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {streaming ? t("understanding.chat_sending") : t("understanding.chat_send")}
        </button>
      </div>
    </div>
  );
}

function MessageBubble({ message, onCitationClick }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed ${
          isUser
            ? "brand-gradient text-white shadow-md shadow-indigo-200"
            : "border border-indigo-100/80 bg-white text-slate-700 shadow-sm"
        }`}
      >
        <p className="whitespace-pre-wrap break-words">{message.content}</p>
        {message.streaming && <span className="ml-0.5 inline-block animate-pulse text-indigo-400">▍</span>}

        {!isUser && message.citations?.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1.5 border-t border-indigo-50 pt-2">
            {message.citations.map((cite, i) => (
              <button
                key={`${cite.cue_index}-${i}`}
                type="button"
                onClick={() => onCitationClick?.(cite)}
                className="rounded-md bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-600 hover:bg-indigo-100"
                title={cite.quote}
              >
                [{formatCueTime(cite.start_sec)}]
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function TypingDots() {
  return (
    <span className="inline-flex gap-0.5">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="h-1.5 w-1.5 animate-bounce rounded-full bg-indigo-400"
          style={{ animationDelay: `${i * 150}ms` }}
        />
      ))}
    </span>
  );
}
