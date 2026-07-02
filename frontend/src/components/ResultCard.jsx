import { useState } from "react";
import { downloadVideo, summarizeVideo, translateSubtitle } from "../api";
import { useI18n } from "../i18n.jsx";

export default function ResultCard({ result, url, llmReady }) {
  const { t, lang } = useI18n();
  const recommended = result.options.find((o) => o.recommended) || result.options[0];
  const [selected, setSelected] = useState(recommended?.id);

  const [downloading, setDownloading] = useState(false);
  const [dlError, setDlError] = useState("");

  const [summarizing, setSummarizing] = useState(false);
  const [summary, setSummary] = useState(null);
  const [aiError, setAiError] = useState("");

  const [translating, setTranslating] = useState(false);
  const [trMsg, setTrMsg] = useState("");
  const [trFailed, setTrFailed] = useState(false);

  const optionLabel = (opt) => {
    if (opt.audio_only) return `${t("result.quality_audio")} ${(opt.ext || "").toUpperCase()}`.trim();
    if (opt.height >= 99999) return t("result.quality_best");
    if (opt.height > 0) return `${opt.height}P` + (opt.needs_merge ? ` ${t("result.quality_merge")}` : "");
    return t("result.quality_default");
  };

  const handleDownload = async () => {
    setDlError("");
    setDownloading(true);
    try {
      await downloadVideo(url, selected);
    } catch (e) {
      setDlError(e.message);
    } finally {
      setDownloading(false);
    }
  };

  const handleSummary = async () => {
    setAiError("");
    setSummary(null);
    setSummarizing(true);
    try {
      const data = await summarizeVideo(url);
      setSummary(data);
    } catch (e) {
      setAiError(e.message);
    } finally {
      setSummarizing(false);
    }
  };

  const handleTranslate = async () => {
    setTrMsg("");
    setTrFailed(false);
    setTranslating(true);
    try {
      const target = lang === "en" ? "English" : "简体中文";
      await translateSubtitle(url, target);
      setTrMsg(t("result.translate_done"));
    } catch (e) {
      setTrFailed(true);
      setTrMsg(t("result.translate_fail") + e.message);
    } finally {
      setTranslating(false);
    }
  };

  return (
    <section className="mx-auto mt-4 max-w-4xl animate-fade-up px-4 sm:px-6">
      <div className="card overflow-hidden p-4 sm:p-6">
        <div className="flex flex-col gap-5 sm:flex-row">
          {/* 封面 */}
          <div className="relative w-full shrink-0 overflow-hidden rounded-xl bg-slate-100 sm:w-64">
            {result.thumbnail ? (
              <img src={result.thumbnail} alt={result.title} className="h-40 w-full object-cover sm:h-36" />
            ) : (
              <div className="flex h-40 w-full items-center justify-center text-slate-300 sm:h-36">
                {t("result.no_thumb")}
              </div>
            )}
            {result.duration_string && (
              <span className="absolute bottom-2 right-2 rounded bg-black/70 px-1.5 py-0.5 text-xs font-medium text-white">
                {result.duration_string}
              </span>
            )}
          </div>

          {/* 信息 */}
          <div className="min-w-0 flex-1">
            <h3 className="line-clamp-2 text-lg font-bold text-slate-900">{result.title}</h3>
            <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-500">
              {result.uploader && <span>{result.uploader}</span>}
              {result.extractor && (
                <span className="rounded-full bg-indigo-50 px-2 py-0.5 font-medium text-indigo-600">
                  {result.extractor}
                </span>
              )}
              {result.has_subtitles && (
                <span className="rounded-full bg-emerald-50 px-2 py-0.5 font-medium text-emerald-600">
                  {t("result.has_subtitles")}
                </span>
              )}
            </div>

            {/* 清晰度选择 */}
            <div className="mt-4">
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
                {t("result.select_quality")}
              </p>
              <div className="flex flex-wrap gap-2">
                {result.options.map((opt) => (
                  <button
                    key={opt.id}
                    onClick={() => setSelected(opt.id)}
                    className={`rounded-lg border px-3 py-1.5 text-sm font-medium transition ${
                      selected === opt.id
                        ? "border-indigo-500 bg-indigo-50 text-indigo-700"
                        : "border-slate-200 bg-white text-slate-600 hover:border-indigo-300"
                    }`}
                  >
                    {optionLabel(opt)}
                    {opt.filesize && <span className="ml-1 text-xs text-slate-400">{opt.filesize}</span>}
                    {opt.recommended && (
                      <span className="ml-1 rounded bg-amber-100 px-1 text-[10px] font-bold text-amber-600">
                        {t("result.recommend")}
                      </span>
                    )}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* 操作区 */}
        <div className="mt-6 flex flex-col gap-3 sm:flex-row">
          <button
            onClick={handleDownload}
            disabled={downloading}
            className="brand-gradient flex flex-1 items-center justify-center gap-2 rounded-xl px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-indigo-200 transition hover:scale-[1.02] disabled:opacity-70"
          >
            {downloading ? <><Spinner /> {t("result.downloading")}</> : <><DownloadIcon /> {t("result.download")}</>}
          </button>

          <button
            onClick={handleSummary}
            disabled={summarizing}
            className="flex flex-1 items-center justify-center gap-2 rounded-xl border-2 border-indigo-200 bg-white px-6 py-3 text-sm font-semibold text-indigo-600 transition hover:border-indigo-400 disabled:opacity-70"
          >
            {summarizing ? <><Spinner /> {t("result.summarizing")}</> : <><SparkIcon /> {t("result.ai_summary")}</>}
            <ProBadge />
          </button>

          <button
            onClick={handleTranslate}
            disabled={translating}
            className="flex flex-1 items-center justify-center gap-2 rounded-xl border-2 border-fuchsia-200 bg-white px-6 py-3 text-sm font-semibold text-fuchsia-600 transition hover:border-fuchsia-400 disabled:opacity-70"
          >
            {translating ? <><Spinner /> {t("result.translating")}</> : <><GlobeIcon /> {t("result.translate")}</>}
            <ProBadge />
          </button>
        </div>

        {dlError && <Alert>{dlError}</Alert>}
        {!llmReady && <p className="mt-3 text-center text-xs text-slate-400">{t("result.llm_hint")}</p>}
        {aiError && <Alert>{aiError}</Alert>}
        {trMsg && (
          <p className={`mt-3 rounded-xl px-4 py-3 text-sm ${trFailed ? "bg-red-50 text-red-600" : "bg-emerald-50 text-emerald-600"}`}>
            {trMsg}
          </p>
        )}

        {/* AI 总结结果 */}
        {summary && (
          <div className="mt-5 rounded-xl border border-indigo-100 bg-gradient-to-br from-indigo-50/60 to-fuchsia-50/40 p-5">
            <div className="mb-2 flex items-center gap-2 text-sm font-bold text-indigo-700">
              <SparkIcon /> {t("result.summary_title")}
              <span className="ml-auto text-xs font-normal text-slate-400">
                {t("result.sub_lang")}{summary.lang}{summary.is_auto ? t("result.auto") : ""}
              </span>
            </div>
            <div className="whitespace-pre-wrap text-sm leading-relaxed text-slate-700">{summary.summary}</div>
          </div>
        )}
      </div>
    </section>
  );
}

function Alert({ children }) {
  return <p className="mt-3 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600">{children}</p>;
}

function ProBadge() {
  return (
    <span className="rounded bg-gradient-to-r from-amber-400 to-orange-500 px-1.5 py-0.5 text-[10px] font-bold text-white">
      PRO
    </span>
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

function DownloadIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
    </svg>
  );
}

function SparkIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="currentColor">
      <path d="M9 2l1.5 5L15 8.5 10.5 10 9 15l-1.5-5L3 8.5 7.5 7 9 2zm8 8l.9 2.6 2.6.9-2.6.9L17 17l-.9-2.6-2.6-.9 2.6-.9L17 10z" />
    </svg>
  );
}

function GlobeIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="9" />
      <path strokeLinecap="round" d="M3 12h18M12 3c2.5 2.7 2.5 15.3 0 18M12 3c-2.5 2.7-2.5 15.3 0 18" />
    </svg>
  );
}
