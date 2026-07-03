import { lazy, Suspense, useCallback, useEffect, useRef, useState } from "react";

import { fetchTranscript } from "../api";
import { streamSummarize } from "../utils/summarizeStream";
import { fetchMindmap } from "../utils/mindmapApi";
import {
  clearSummarizeCache,
  loadSummarizeCache,
  saveSummarizeCache,
} from "../utils/summarizeCache";

import ChatPanel from "./ChatPanel";
const MindMapPanel = lazy(() => import("./MindMapPanel"));
import StreamingProgress from "./StreamingProgress";
import StreamingSummaryPanel from "./StreamingSummaryPanel";
import TranscriptPanel from "./TranscriptPanel";
import { useI18n } from "../i18n.jsx";

export default function SummarizeSSESection({
  url,
  hasSubtitles,
  subtitleUncertain,
  preferLang,
  llmReady,
  outputLang,
  onTranslate,
  translating,
  t,
}) {
  const { lang } = useI18n();
  const [activeTab, setActiveTab] = useState("summary");
  const [transcript, setTranscript] = useState(null);
  const [summary, setSummary] = useState(null);
  const [streamingText, setStreamingText] = useState("");
  const [stage, setStage] = useState(null);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState("");
  const [transcriptLoading, setTranscriptLoading] = useState(false);
  const [mindmap, setMindmap] = useState(null);
  const [mindmapMarkdown, setMindmapMarkdown] = useState("");
  const [mindmapLoading, setMindmapLoading] = useState(false);
  const [mindmapError, setMindmapError] = useState("");
  const [chatMessages, setChatMessages] = useState([]);
  const [highlightCueIndex, setHighlightCueIndex] = useState(null);
  const abortRef = useRef(null);
  const mindmapLoadedRef = useRef(false);

  useEffect(() => {
    document.documentElement.classList.toggle("page-scroll-anchor-disabled", streaming);
    return () => {
      document.documentElement.classList.remove("page-scroll-anchor-disabled");
    };
  }, [streaming]);

  const persistSession = useCallback(
    (overrides = {}) => {
      saveSummarizeCache(url, preferLang, {
        transcript,
        summary,
        mindmap,
        mindmapMarkdown,
        chatMessages,
        ...overrides,
      });
    },
    [url, preferLang, transcript, summary, mindmap, mindmapMarkdown, chatMessages],
  );

  useEffect(() => {
    if (!url) return;
    const cached = loadSummarizeCache(url, preferLang);
    if (cached) {
      setTranscript(cached.transcript ?? null);
      setSummary(cached.summary ?? null);
      setMindmap(cached.mindmap ?? null);
      setMindmapMarkdown(cached.mindmapMarkdown ?? "");
      setChatMessages(cached.chatMessages ?? []);
      setStreamingText("");
      mindmapLoadedRef.current = Boolean(cached.mindmapMarkdown);
    }
  }, [url, preferLang]);

  const runSummarize = useCallback(
    async (forceRefresh = false) => {
      if (!llmReady) return;

      setError("");
      setStreaming(true);
      setStage(null);
      setStreamingText("");
      if (forceRefresh) {
        setTranscript(null);
        setSummary(null);
        setMindmap(null);
        setMindmapMarkdown("");
        setChatMessages([]);
        mindmapLoadedRef.current = false;
        clearSummarizeCache(url, preferLang);
      }

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        let latestTranscript = transcript;
        let latestSummary = summary;

        for await (const { event, data } of streamSummarize(url, {
          preferLang,
          outputLang,
          forceRefresh,
          signal: controller.signal,
        })) {
          if (event === "stage") {
            setStage(data);
          } else if (event === "transcript") {
            latestTranscript = data;
            setTranscript(data);
          } else if (event === "summary_delta") {
            setStreamingText((prev) => prev + (data.text || ""));
          } else if (event === "summary") {
            latestSummary = data;
            setSummary(data);
            setStreamingText("");
          } else if (event === "error") {
            throw new Error(data.message || data.code || "Summarize failed");
          } else if (event === "done") {
            break;
          }
        }

        setStage(null);
        saveSummarizeCache(url, preferLang, {
          transcript: latestTranscript,
          summary: latestSummary,
          mindmap: forceRefresh ? null : mindmap,
          mindmapMarkdown: forceRefresh ? "" : mindmapMarkdown,
          chatMessages: forceRefresh ? [] : chatMessages,
        });
        if (forceRefresh) {
          mindmapLoadedRef.current = false;
        }
      } catch (e) {
        if (e.name !== "AbortError") {
          setError(e.message);
        }
      } finally {
        abortRef.current = null;
        setStreaming(false);
        setStage(null);
      }
    },
    [url, preferLang, outputLang, llmReady, transcript, summary, mindmap, mindmapMarkdown, chatMessages],
  );

  const loadMindmap = useCallback(
    async (force = false) => {
      if (!transcript || mindmapLoading) return;
      if (!force && mindmapLoadedRef.current && mindmapMarkdown) return;

      setMindmapError("");
      setMindmapLoading(true);
      try {
        const data = await fetchMindmap(url, {
          summary,
          transcript,
          preferLang,
          outputLang,
        });
        setMindmap(data.mindmap);
        setMindmapMarkdown(data.markdown || "");
        mindmapLoadedRef.current = true;
        persistSession({ mindmap: data.mindmap, mindmapMarkdown: data.markdown || "" });
      } catch (e) {
        setMindmapError(e.message);
      } finally {
        setMindmapLoading(false);
      }
    },
    [transcript, mindmapLoading, mindmapMarkdown, url, summary, preferLang, outputLang, persistSession],
  );

  const handleCancel = () => abortRef.current?.abort();

  const loadTranscript = useCallback(async () => {
    if (transcript || transcriptLoading) return;
    setTranscriptLoading(true);
    setError("");
    try {
      const data = await fetchTranscript(url, preferLang);
      const nextTranscript = {
        title: data.title,
        url,
        lang: data.lang,
        is_auto: data.is_auto,
        duration_sec: data.duration,
        cues: data.cues,
        plain_text: data.plain_text,
        truncated: data.truncated,
        source: data.source,
      };
      setTranscript(nextTranscript);
      persistSession({ transcript: nextTranscript });
    } catch (e) {
      setError(e.message);
    } finally {
      setTranscriptLoading(false);
    }
  }, [transcript, transcriptLoading, url, preferLang, persistSession]);

  const handleCitationClick = useCallback((cite) => {
    setActiveTab("transcript");
    setHighlightCueIndex(cite.cue_index);
  }, []);

  const handleTabChange = async (tabId) => {
    if ((tabId === "mindmap" || tabId === "chat") && !analysisReady) return;
    setActiveTab(tabId);
  };

  const handleChatMessagesChange = useCallback(
    (next) => {
      setChatMessages(next);
      persistSession({ chatMessages: next });
    },
    [persistSession],
  );

  const tabs = [
    { id: "summary", label: t("understanding.tab_summary"), icon: SummaryTabIcon },
    { id: "transcript", label: t("understanding.tab_transcript"), icon: TranscriptTabIcon },
    { id: "mindmap", label: t("understanding.tab_mindmap"), icon: MindmapTabIcon, gated: true },
    { id: "chat", label: t("understanding.tab_chat"), icon: ChatTabIcon, gated: true },
  ];

  const analysisReady = Boolean(transcript || summary);
  const hasResult = transcript || summary || streamingText || streaming;
  const showTabs = hasSubtitles || hasResult || !llmReady;
  const showTranscriptAction = Boolean(hasSubtitles && !transcript && !transcriptLoading);
  const showErrorBanner = Boolean(error);
  const buttonTitle = !llmReady ? t("understanding.btn_disabled_no_llm") : undefined;
  const canGenerateMindmap = Boolean(transcript) && llmReady;

  return (
    <div className="no-page-scroll-anchor mt-6 overflow-hidden rounded-[2rem] border border-white/70 bg-white/80 p-4 shadow-glow backdrop-blur-xl dark:border-white/10 dark:bg-ink-900/70 sm:p-5">
      <div className="relative overflow-hidden rounded-[1.5rem] border border-slate-900/5 bg-gradient-to-br from-ink-950 via-slate-900 to-brand-700 p-5 text-white shadow-2xl shadow-ink-950/20">
        <div className="pointer-events-none absolute right-0 top-0 h-40 w-40 rounded-full bg-accent-500/25 blur-3xl" />
        <div className="pointer-events-none absolute bottom-0 left-10 h-32 w-32 rounded-full bg-neon-400/20 blur-3xl" />
        <div className="relative flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
            <h4 className="flex items-center gap-3 text-lg font-black tracking-tight text-white sm:text-xl">
              <span className="flex h-10 w-10 items-center justify-center rounded-2xl brand-gradient text-white shadow-lg shadow-accent-300/30">
              <SparkIcon />
            </span>
            {t("understanding.title")}
          </h4>
          {!llmReady && (
              <p className="mt-3 flex items-center gap-1.5 text-xs font-bold text-amber-200">
              <WarnIcon />
              {t("understanding.no_llm")}
            </p>
          )}
          {subtitleUncertain && (
              <p className="mt-2 max-w-xl text-xs font-medium leading-relaxed text-amber-100/90">
              {t("understanding.subtitle_uncertain_hint")}
            </p>
          )}
          {!hasSubtitles && !subtitleUncertain && (
              <p className="mt-2 text-xs font-bold text-amber-100">{t("understanding.no_subtitles")}</p>
          )}
        </div>
        <button
          type="button"
          onClick={streaming ? handleCancel : () => runSummarize(!!hasResult)}
          disabled={!llmReady}
          title={buttonTitle}
            className={`flex min-h-12 shrink-0 items-center justify-center gap-2 rounded-2xl px-5 py-3 text-sm font-black transition-all disabled:cursor-not-allowed disabled:opacity-50 ${
            streaming
                ? "border-2 border-white/20 bg-white/10 text-white hover:bg-white/15"
                : "bg-white text-ink-950 shadow-xl shadow-white/10 hover:-translate-y-0.5"
          }`}
        >
          {streaming ? (
            <>
              <Spinner /> {t("understanding.cancel")}
            </>
          ) : hasResult ? (
            <>
              <RefreshIcon /> {t("understanding.reanalyze")}
            </>
          ) : (
            <>
              <SparkIcon /> {t("understanding.one_click")}
            </>
          )}
        </button>
        </div>
      </div>

      {!llmReady && (
        <p className="mt-4 rounded-2xl border border-slate-200/70 bg-slate-50 px-4 py-3 text-xs font-medium text-slate-500 dark:border-white/10 dark:bg-ink-950/50 dark:text-slate-400">{t("result.llm_hint")}</p>
      )}

      {streaming && (
        <div className="mt-4">
          <StreamingProgress stage={stage} lang={lang} t={t} />
        </div>
      )}
      {showErrorBanner && <StatusAlert message={error} />}

      {showTabs && (
        <>
          <div className="mt-4 inline-flex max-w-full flex-wrap gap-1 rounded-2xl border border-slate-200/70 bg-white/80 p-1 shadow-sm dark:border-white/10 dark:bg-ink-950/70">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const active = activeTab === tab.id;
              const disabled = tab.gated && !analysisReady;
              return (
                <button
                  key={tab.id}
                  type="button"
                  disabled={disabled}
                  onClick={() => handleTabChange(tab.id)}
                  title={disabled ? t("understanding.tab_locked_hint") : undefined}
                  className={`flex min-h-11 shrink-0 items-center gap-1.5 rounded-xl px-3 py-2 text-sm font-black transition-all sm:px-4 ${
                    active
                      ? "brand-gradient text-white shadow-lg shadow-accent-200/40"
                      : disabled
                        ? "cursor-not-allowed text-slate-400 opacity-60 dark:text-slate-500"
                        : "text-slate-500 hover:bg-brand-50 hover:text-brand-700 dark:text-slate-400 dark:hover:bg-white/10 dark:hover:text-brand-300"
                  }`}
                >
                  <Icon className={`h-4 w-4 ${active ? "text-white" : "text-slate-400"}`} />
                  {tab.label}
                </button>
              );
            })}
          </div>

          <div className="mt-4 rounded-[1.5rem] border border-slate-200/70 bg-white/70 p-3 shadow-sm backdrop-blur dark:border-white/10 dark:bg-ink-950/50 sm:p-4">
            {activeTab === "summary" && (
              <StreamingSummaryPanel
                summary={summary}
                streamingText={streamingText}
                streaming={streaming}
                stage={stage}
                t={t}
              />
            )}
            {activeTab === "transcript" &&
              (transcriptLoading ? (
                <TranscriptLoadingState t={t} />
              ) : (
                <TranscriptPanel
                  transcript={transcript}
                  highlightCueIndex={highlightCueIndex}
                  t={t}
                  onTranslate={onTranslate}
                  translating={translating}
                  onLoadTranscript={showTranscriptAction ? loadTranscript : undefined}
                  loading={transcriptLoading}
                />
              ))}
            {activeTab === "mindmap" && (
              <Suspense fallback={<TranscriptLoadingState t={t} />}>
                <MindMapPanel
                  markdown={mindmapMarkdown}
                  loading={mindmapLoading}
                  error={mindmapError}
                  onGenerate={() => loadMindmap(true)}
                  canGenerate={canGenerateMindmap}
                  t={t}
                />
              </Suspense>
            )}
            {activeTab === "chat" && (
              <ChatPanel
                url={url}
                transcript={transcript}
                summary={summary}
                preferLang={preferLang}
                outputLang={outputLang}
                messages={chatMessages}
                onMessagesChange={handleChatMessagesChange}
                onCitationClick={handleCitationClick}
                t={t}
              />
            )}
          </div>
        </>
      )}
    </div>
  );
}

function StatusAlert({ message }) {
  return (
    <div className="mt-4 flex items-start gap-2.5 rounded-2xl border border-red-100 bg-red-50 px-4 py-3 shadow-sm dark:border-red-500/30 dark:bg-red-950/40">
      <WarnIcon className="mt-0.5 text-red-400" />
      <p className="min-w-0 flex-1 break-words text-sm font-medium leading-relaxed text-red-600 dark:text-red-300">{message}</p>
    </div>
  );
}

function TranscriptLoadingState({ t }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-[1.25rem] bg-slate-50/80 py-12 dark:bg-ink-950/40">
      <div className="relative mb-4 flex h-12 w-12 items-center justify-center">
        <span className="absolute inset-0 animate-ping rounded-full bg-brand-200 opacity-40" />
        <span className="relative flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-50 text-brand-600">
          <Spinner />
        </span>
      </div>
      <p className="text-sm font-black text-brand-700">{t("understanding.analyzing")}</p>
      <p className="mt-1 text-xs font-medium text-slate-400">{t("understanding.transcript_loading_hint")}</p>
    </div>
  );
}

function SparkIcon({ className = "h-4 w-4" }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="currentColor">
      <path d="M9 2l1.5 5L15 8.5 10.5 10 9 15l-1.5-5L3 8.5 7.5 7 9 2zm8 8l.9 2.6 2.6.9-2.6.9L17 17l-.9-2.6-2.6-.9 2.6-.9L17 10z" />
    </svg>
  );
}

function RefreshIcon({ className = "h-4 w-4" }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="2">
      <path strokeLinecap="round" d="M4 4v5h5M20 20v-5h-5" />
      <path strokeLinecap="round" d="M20 9A8 8 0 006.34 6.34M4 15a8 8 0 0013.66 2.66" />
    </svg>
  );
}

function SummaryTabIcon({ className = "h-4 w-4" }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="2">
      <path strokeLinecap="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2" />
      <rect x="9" y="3" width="6" height="4" rx="1" />
      <path strokeLinecap="round" d="M9 12h6M9 16h4" />
    </svg>
  );
}

function TranscriptTabIcon({ className = "h-4 w-4" }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="2">
      <path strokeLinecap="round" d="M7 8h10M7 12h6M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H9l-2 2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
    </svg>
  );
}

function MindmapTabIcon({ className = "h-4 w-4" }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="5" r="2" />
      <circle cx="5" cy="19" r="2" />
      <circle cx="19" cy="19" r="2" />
      <path strokeLinecap="round" d="M12 7v4M12 11l-7 6M12 11l7 6" />
    </svg>
  );
}

function ChatTabIcon({ className = "h-4 w-4" }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="2">
      <path strokeLinecap="round" d="M8 10h8M8 14h5" />
      <path strokeLinecap="round" d="M21 12a8 8 0 01-8 8H7l-4 3V12a8 8 0 018-8h2a8 8 0 018 8z" />
    </svg>
  );
}

function WarnIcon({ className = "" }) {
  return (
    <svg viewBox="0 0 24 24" className={`h-4 w-4 shrink-0 ${className}`.trim()} fill="none" stroke="currentColor" strokeWidth="2">
      <path strokeLinecap="round" d="M12 9v4M12 17h.01" />
      <path strokeLinecap="round" d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
    </svg>
  );
}

function Spinner() {
  return (
    <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  );
}
