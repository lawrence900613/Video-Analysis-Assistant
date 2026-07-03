import { useCallback, useEffect, useRef, useState } from "react";
import { fetchTranscript, streamSummarize } from "../api";
import { clearAnalysisCache, loadAnalysisCache, saveAnalysisCache } from "../utils/analysisCache";
import StreamingProgress from "./StreamingProgress";
import SummaryPanel from "./SummaryPanel";
import TranscriptPanel from "./TranscriptPanel";

export default function UnderstandingSection({
  url,
  hasSubtitles,
  preferLang,
  llmReady,
  outputLang,
  onTranslate,
  translating,
  t,
}) {
  const [activeTab, setActiveTab] = useState("summary");
  const [transcript, setTranscript] = useState(null);
  const [summary, setSummary] = useState(null);
  const [summaryStreamText, setSummaryStreamText] = useState("");
  const [stage, setStage] = useState(null);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState("");
  const [transcriptLoading, setTranscriptLoading] = useState(false);
  const abortRef = useRef(null);

  useEffect(() => {
    if (!url || !hasSubtitles) return;
    const cached = loadAnalysisCache(url, preferLang);
    if (cached) {
      setTranscript(cached.transcript || null);
      setSummary(cached.summary || null);
      setSummaryStreamText("");
    }
  }, [url, preferLang, hasSubtitles]);

  const runAnalysis = useCallback(async (forceRefresh = false) => {
    if (!llmReady || !hasSubtitles) return;

    setError("");
    setStreaming(true);
    setStage(null);
    setSummaryStreamText("");
    if (forceRefresh) {
      clearAnalysisCache(url, preferLang);
      setTranscript(null);
      setSummary(null);
    }
    setActiveTab("summary");

    const controller = new AbortController();
    abortRef.current = controller;

    let sessionTranscript = transcript;
    let sessionSummary = null;
    let streamText = "";

    try {
      for await (const { event, data } of streamSummarize(url, {
        preferLang,
        outputLang,
        forceRefresh,
        signal: controller.signal,
      })) {
        if (event === "stage") {
          setStage(data);
        } else if (event === "transcript") {
          sessionTranscript = data;
          setTranscript(data);
        } else if (event === "summary_delta") {
          streamText += data.text || "";
          setSummaryStreamText(streamText);
        } else if (event === "summary") {
          sessionSummary = data;
          setSummary(data);
          setSummaryStreamText("");
        } else if (event === "error") {
          throw new Error(data.message || data.code || "Analysis failed");
        } else if (event === "done") {
          break;
        }
      }

      if (sessionTranscript || sessionSummary) {
        saveAnalysisCache(url, preferLang, {
          transcript: sessionTranscript,
          summary: sessionSummary,
        });
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
  }, [url, preferLang, outputLang, llmReady, hasSubtitles, transcript]);

  const handleCancel = () => {
    abortRef.current?.abort();
  };

  const handleTabChange = async (tabId) => {
    setActiveTab(tabId);
  };

  const loadTranscript = async () => {
    if (transcript || !hasSubtitles || transcriptLoading) return;
    setTranscriptLoading(true);
    setError("");
    try {
      const data = await fetchTranscript(url, preferLang);
      setTranscript({
        title: data.title,
        url,
        lang: data.lang,
        is_auto: data.is_auto,
        duration_sec: data.duration,
        cues: data.cues,
        plain_text: data.plain_text,
        truncated: data.truncated,
        source: data.source,
      });
    } catch (e) {
      setError(e.message);
    } finally {
      setTranscriptLoading(false);
    }
  };

  const tabs = [
    { id: "summary", label: t("understanding.tab_summary") },
    { id: "transcript", label: t("understanding.tab_transcript") },
  ];

  const hasResult = summary || transcript;

  return (
    <div className="mt-6 rounded-xl border border-indigo-100 bg-gradient-to-br from-indigo-50/40 to-violet-50/30 p-4 sm:p-5">
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h4 className="flex items-center gap-2 text-sm font-bold text-indigo-800">
            <SparkIcon /> {t("understanding.title")}
          </h4>
          {!hasSubtitles && (
            <p className="mt-1 text-xs text-amber-700">{t("understanding.no_subtitles")}</p>
          )}
        </div>
        <button
          type="button"
          onClick={streaming ? handleCancel : () => runAnalysis(!!hasResult)}
          disabled={!hasSubtitles || !llmReady}
          title={!hasSubtitles ? t("understanding.no_subtitles") : undefined}
          className={`flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-50 ${
            streaming
              ? "border-2 border-slate-300 bg-white text-slate-700"
              : "brand-gradient text-white shadow-md shadow-indigo-200"
          }`}
        >
          {streaming ? (
            <>
              <Spinner /> {t("understanding.stop")}
            </>
          ) : hasResult ? (
            <>
              <SparkIcon /> {t("understanding.reanalyze")}
            </>
          ) : (
            <>
              <SparkIcon /> {t("understanding.one_click")}
            </>
          )}
        </button>
      </div>

      {!llmReady && (
        <p className="mb-3 text-xs text-slate-500">{t("result.llm_hint")}</p>
      )}

      {streaming && <StreamingProgress stage={stage} t={t} />}
      {error && (
        <p className="mt-3 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600">{error}</p>
      )}

      {hasSubtitles && (
        <>
          <div className="mt-4 flex gap-1 overflow-x-auto border-b border-indigo-100">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => handleTabChange(tab.id)}
                className={`shrink-0 border-b-2 px-4 py-2 text-sm font-medium transition ${
                  activeTab === tab.id
                    ? "border-indigo-500 text-indigo-700"
                    : "border-transparent text-slate-500 hover:text-indigo-600"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div className="mt-4">
            {activeTab === "summary" && (
              <SummaryPanel
                summary={summary}
                streamingText={summaryStreamText}
                t={t}
              />
            )}
            {activeTab === "transcript" && (
              transcriptLoading ? (
                <div className="py-8 text-center text-sm text-slate-400">{t("understanding.analyzing")}</div>
              ) : (
                <TranscriptPanel
                  transcript={transcript}
                  t={t}
                  onTranslate={onTranslate}
                  translating={translating}
                  onLoadTranscript={loadTranscript}
                  loading={transcriptLoading}
                />
              )
            )}
          </div>
        </>
      )}

      {!hasResult && !streaming && hasSubtitles && llmReady && (
        <p className="text-center text-sm text-slate-400 py-4">{t("understanding.cta_hint")}</p>
      )}
    </div>
  );
}

function SparkIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="currentColor">
      <path d="M9 2l1.5 5L15 8.5 10.5 10 9 15l-1.5-5L3 8.5 7.5 7 9 2zm8 8l.9 2.6 2.6.9-2.6.9L17 17l-.9-2.6-2.6-.9 2.6-.9L17 10z" />
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
