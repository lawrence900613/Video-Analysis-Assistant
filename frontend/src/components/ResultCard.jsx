import { useRef, useState } from "react";
import { DownloadCancelledError, downloadVideo, downloadSubtitles, summarizeVideo, translateSubtitle } from "../api";
import { useI18n } from "../i18n.jsx";
import { formatViews } from "../utils/history.js";
import { formatEta, formatSpeed } from "../utils/progress.js";

export default function ResultCard({ result, url, llmReady, ffmpegAvailable, onDownloadStart, onDownloaded }) {
  const { t, lang } = useI18n();
  const recommended = result.options.find((o) => o.recommended) || result.options[0];
  const [selected, setSelected] = useState(recommended?.id);
  const [subLang, setSubLang] = useState(result.subtitle_langs?.[0] || "");

  const [downloading, setDownloading] = useState(false);
  const [dlProgress, setDlProgress] = useState(null);
  const [dlError, setDlError] = useState("");
  const downloadAbortRef = useRef(null);

  const [subDownloading, setSubDownloading] = useState(false);
  const [subMsg, setSubMsg] = useState("");
  const [subFailed, setSubFailed] = useState(false);

  const [summarizing, setSummarizing] = useState(false);
  const [summary, setSummary] = useState(null);
  const [aiError, setAiError] = useState("");

  const [translating, setTranslating] = useState(false);
  const [trMsg, setTrMsg] = useState("");
  const [trFailed, setTrFailed] = useState(false);

  const optionLabel = (opt) => {
    if (opt.audio_only) return `${t("result.quality_audio")} ${(opt.ext || "").toUpperCase()}`.trim();
    if (opt.height >= 99999) return t("result.quality_best");
    if (opt.height > 0) return `${opt.height}P`;
    return t("result.quality_default");
  };

  // A short, user-friendly quality tier tag (e.g. 4K / 2K / HD) instead of
  // exposing the technical "(merge)" detail.
  const qualityTier = (opt) => {
    if (opt.audio_only || opt.height <= 0 || opt.height >= 99999) return null;
    if (opt.height >= 2160) return "4K";
    if (opt.height >= 1440) return "2K";
    if (opt.height >= 720) return "HD";
    return null;
  };

  const handleDownload = async () => {
    if (downloading) {
      downloadAbortRef.current?.abort();
      return;
    }

    setDlError("");
    setDlProgress(null);
    setDownloading(true);
    const controller = new AbortController();
    downloadAbortRef.current = controller;
    onDownloadStart?.();
    try {
      await downloadVideo(url, selected, {
        onProgress: (p) => setDlProgress(p),
        signal: controller.signal,
      });
      onDownloaded?.();
    } catch (e) {
      if (e instanceof DownloadCancelledError || e.name === "AbortError") {
        return;
      }
      setDlError(e.message);
    } finally {
      if (downloadAbortRef.current === controller) {
        downloadAbortRef.current = null;
      }
      setDownloading(false);
      setDlProgress(null);
    }
  };

  const handleSubDownload = async () => {
    setSubMsg("");
    setSubFailed(false);
    setSubDownloading(true);
    onDownloadStart?.();
    try {
      const { lang: gotLang } = await downloadSubtitles(url, subLang || undefined);
      setSubMsg(`${t("result.subtitle_done")}${gotLang})`);
      onDownloaded?.();
    } catch (e) {
      setSubFailed(true);
      setSubMsg(t("result.subtitle_fail") + e.message);
    } finally {
      setSubDownloading(false);
    }
  };

  const handleSummary = async () => {
    setAiError("");
    setSummary(null);
    setSummarizing(true);
    try {
      const outputLang = lang === "en" ? "English" : "Simplified Chinese";
      const data = await summarizeVideo(url, outputLang);
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
      const target = lang === "en" ? "English" : "Simplified Chinese";
      await translateSubtitle(url, target, subLang || undefined);
      setTrMsg(t("result.translate_done"));
    } catch (e) {
      setTrFailed(true);
      setTrMsg(t("result.translate_fail") + e.message);
    } finally {
      setTranslating(false);
    }
  };

  const viewsLabel = result.view_count != null ? formatViews(result.view_count) : null;
  const showFfmpegWarning =
    !ffmpegAvailable &&
    result.ffmpeg !== true &&
    !result.options?.some((o) => o.needs_merge || o.height >= 99999);

  const progressDetail = () => {
    if (!dlProgress) return t("result.progress_starting");
    if (dlProgress.percent != null) return `${dlProgress.percent}%`;
    if (dlProgress.stage === "processing") return t("result.progress_processing");
    if (dlProgress.stage === "transferring") return t("result.progress_transferring");
    if (dlProgress.stage === "downloading") return t("result.progress_downloading");
    return t("result.progress_indeterminate");
  };

  const progressIndeterminate = dlProgress?.percent == null;
  const speedLabel = formatSpeed(dlProgress?.speed_bps) ?? t("result.progress_unknown");
  const etaLabel = formatEta(dlProgress?.eta_seconds, t) ?? t("result.progress_unknown");

  return (
    <section id="result" className="mx-auto mt-4 max-w-4xl animate-fade-up px-4 sm:px-6">
      <div className="card overflow-hidden p-4 sm:p-6">
        {showFfmpegWarning && (
          <div className="mb-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
            {t("result.ffmpeg_warning")}
          </div>
        )}

        <div className="flex flex-col gap-5 sm:flex-row">
          <div className="relative w-full shrink-0 overflow-hidden rounded-xl bg-slate-100 sm:w-64">
            {result.thumbnail ? (
              <img
                src={result.thumbnail}
                alt={result.title}
                referrerPolicy="no-referrer"
                className="h-44 w-full object-cover sm:h-36"
              />
            ) : (
              <div className="flex h-44 w-full items-center justify-center text-slate-300 sm:h-36">
                {t("result.no_thumb")}
              </div>
            )}
            {result.duration_string && (
              <span className="absolute bottom-2 right-2 rounded bg-black/70 px-1.5 py-0.5 text-xs font-medium text-white">
                {result.duration_string}
              </span>
            )}
          </div>

          <div className="min-w-0 flex-1">
            <h3 className="line-clamp-2 text-lg font-bold text-slate-900">{result.title}</h3>
            <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-500">
              {result.uploader && <span>{result.uploader}</span>}
              {viewsLabel && (
                <span>{viewsLabel} {t("result.views")}</span>
              )}
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

            {result.subtitle_langs?.length > 0 && (
              <div className="mt-3">
                <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-400">
                  {t("result.subtitle_lang")}
                </label>
                <select
                  value={subLang}
                  onChange={(e) => setSubLang(e.target.value)}
                  className="w-full max-w-xs rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 outline-none focus:border-indigo-400 sm:w-auto"
                >
                  {result.subtitle_langs.map((l) => (
                    <option key={l} value={l}>{l}</option>
                  ))}
                </select>
              </div>
            )}

            <div className="mt-4">
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
                {t("result.select_quality")}
              </p>
              <div className="flex flex-wrap gap-2">
                {result.options.map((opt) => (
                  <button
                    key={opt.id}
                    type="button"
                    onClick={() => setSelected(opt.id)}
                    className={`rounded-lg border px-3 py-1.5 text-sm font-medium transition ${
                      selected === opt.id
                        ? "border-indigo-500 bg-indigo-50 text-indigo-700"
                        : "border-slate-200 bg-white text-slate-600 hover:border-indigo-300"
                    }`}
                  >
                    {optionLabel(opt)}
                    {qualityTier(opt) && (
                      <span className="ml-1 rounded bg-indigo-100 px-1 text-[10px] font-bold text-indigo-600">
                        {qualityTier(opt)}
                      </span>
                    )}
                    {opt.filesize && <span className="ml-1 text-xs text-slate-400">{opt.filesize}</span>}
                    {opt.recommended && (
                      <span className="ml-1 rounded bg-amber-100 px-1 text-[10px] font-bold text-amber-600">
                        {t("result.recommend")}
                      </span>
                    )}
                  </button>
                ))}
              </div>
              {result.options.some((o) => o.needs_merge) && (
                <p className="mt-2 text-xs text-slate-400">{t("result.quality_hint")}</p>
              )}
            </div>
          </div>
        </div>

        {/* Download progress */}
        {downloading && (
          <div className="mt-5">
            <div className="mb-1 flex justify-between text-xs text-slate-500">
              <span>{t("result.downloading")}</span>
              <span>{progressDetail()}</span>
            </div>
            <div className="relative h-2 overflow-hidden rounded-full bg-slate-100">
              {progressIndeterminate ? (
                <div className="absolute inset-y-0 w-1/3 animate-progress-indeterminate brand-gradient rounded-full" />
              ) : (
                <div
                  className="brand-gradient h-full rounded-full transition-all duration-300"
                  style={{ width: `${dlProgress.percent}%` }}
                />
              )}
            </div>
            <div className="mt-1 flex justify-between text-xs text-slate-400">
              <span>{t("result.progress_speed")}: {speedLabel}</span>
              <span>{etaLabel}</span>
            </div>
          </div>
        )}

        {/* Primary actions */}
        <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <ActionBtn
            primary
            onClick={handleDownload}
            loading={downloading}
            loadingText={t("result.cancel_download")}
            cancelMode={downloading}
          >
            <DownloadIcon /> {downloading ? t("result.cancel_download") : t("result.download")}
          </ActionBtn>

          {result.has_subtitles && (
            <ActionBtn onClick={handleSubDownload} disabled={subDownloading} loading={subDownloading} loadingText={t("result.downloading_subs")}>
              <SubIcon /> {t("result.download_subs")}
            </ActionBtn>
          )}

          <ActionBtn onClick={handleSummary} disabled={summarizing} loading={summarizing} loadingText={t("result.summarizing")} pro>
            <SparkIcon /> {t("result.ai_summary")}
          </ActionBtn>

          <ActionBtn onClick={handleTranslate} disabled={translating} loading={translating} loadingText={t("result.translating")} pro accent="fuchsia">
            <GlobeIcon /> {t("result.translate")}
          </ActionBtn>
        </div>

        {dlError && <Alert>{dlError}</Alert>}
        {!llmReady && <p className="mt-3 text-center text-xs text-slate-400">{t("result.llm_hint")}</p>}
        {aiError && <Alert>{aiError}</Alert>}
        {subMsg && <StatusMsg failed={subFailed}>{subMsg}</StatusMsg>}
        {trMsg && <StatusMsg failed={trFailed}>{trMsg}</StatusMsg>}

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

      {/* Mobile sticky download bar */}
      <div className="mobile-dock lg:hidden">
        <button
          type="button"
          onClick={handleDownload}
          className={`flex flex-1 items-center justify-center gap-2 rounded-xl py-3 text-sm font-semibold text-white ${
            downloading ? "bg-slate-700 hover:bg-slate-800" : "brand-gradient disabled:opacity-70"
          }`}
        >
          {downloading ? t("result.cancel_download") : t("result.download")}
        </button>
      </div>
    </section>
  );
}

function ActionBtn({ children, onClick, disabled, loading, loadingText, cancelMode, primary, pro, accent }) {
  const border = accent === "fuchsia" ? "border-fuchsia-200 text-fuchsia-600 hover:border-fuchsia-400" : "border-indigo-200 text-indigo-600 hover:border-indigo-400";
  const cancelStyles = cancelMode
    ? "border-2 border-slate-300 bg-white text-slate-700 hover:border-slate-400 hover:bg-slate-50"
    : primary
      ? "brand-gradient text-white shadow-lg shadow-indigo-200 hover:scale-[1.02]"
      : `border-2 bg-white ${border}`;
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`flex items-center justify-center gap-2 rounded-xl px-4 py-3 text-sm font-semibold transition disabled:opacity-70 ${cancelStyles}`}
    >
      {loading ? (
        <>
          {!cancelMode && <Spinner />} {loadingText}
        </>
      ) : (
        <>
          {children}
          {pro && <ProBadge />}
        </>
      )}
    </button>
  );
}

function Alert({ children }) {
  return <p className="mt-3 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600">{children}</p>;
}

function StatusMsg({ children, failed }) {
  return (
    <p className={`mt-3 rounded-xl px-4 py-3 text-sm ${failed ? "bg-red-50 text-red-600" : "bg-emerald-50 text-emerald-600"}`}>
      {children}
    </p>
  );
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

function SubIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
      <path strokeLinecap="round" d="M7 8h10M7 12h6M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H9l-2 2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
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
