import { useEffect, useRef, useState } from "react";
import { DownloadCancelledError, downloadVideo, downloadSubtitles, translateSubtitle } from "../api";
import { useI18n } from "../i18n.jsx";
import { formatViews } from "../utils/history.js";
import { formatEta, formatSpeed } from "../utils/progress.js";
import { pickDefaultSubtitleLang } from "../utils/subtitleLang.js";
import SummarizeSSESection from "./SummarizeSSESection";

export default function ResultCard({ result, url, llmReady, ffmpegAvailable, onDownloadStart, onDownloaded }) {
  const { t, lang } = useI18n();
  const recommended = result.options.find((o) => o.recommended) || result.options[0];
  const [selected, setSelected] = useState(recommended?.id);
  const [subLangManual, setSubLangManual] = useState(false);
  const [subLang, setSubLang] = useState(() =>
    pickDefaultSubtitleLang(result.subtitle_langs, lang),
  );

  useEffect(() => {
    setSubLangManual(false);
    setSubLang(pickDefaultSubtitleLang(result.subtitle_langs, lang));
  }, [url]);

  useEffect(() => {
    if (!subLangManual) {
      setSubLang(pickDefaultSubtitleLang(result.subtitle_langs, lang));
    }
  }, [lang, result.subtitle_langs, subLangManual]);

  const [downloading, setDownloading] = useState(false);
  const [dlProgress, setDlProgress] = useState(null);
  const [dlError, setDlError] = useState("");
  const downloadAbortRef = useRef(null);

  const [subDownloading, setSubDownloading] = useState(false);
  const [subMsg, setSubMsg] = useState("");
  const [subFailed, setSubFailed] = useState(false);

  const [translating, setTranslating] = useState(false);
  const [trMsg, setTrMsg] = useState("");
  const [trFailed, setTrFailed] = useState(false);

  const outputLang = lang === "en" ? "English" : "Simplified Chinese";

  const optionLabel = (opt) => {
    if (opt.audio_only) return `${t("result.quality_audio")} ${(opt.ext || "").toUpperCase()}`.trim();
    if (opt.height >= 99999) return t("result.quality_best");
    if (opt.height > 0) return `${opt.height}P`;
    return t("result.quality_default");
  };

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

  const handleTranslate = async () => {
    setTrMsg("");
    setTrFailed(false);
    setTranslating(true);
    try {
      await translateSubtitle(url, outputLang, subLang || undefined);
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
  const resultFlowSteps = t("hero.steps");
  const resultFlowStep = downloading ? 4 : 3;

  return (
    <section id="result" className="mx-auto mt-6 max-w-6xl animate-fade-up px-4 sm:px-6">
      <div className="premium-panel overflow-hidden p-4 sm:p-6">
        {showFfmpegWarning && (
          <div className="mb-4 rounded-2xl border border-amber-200 bg-amber-50/90 px-4 py-3 text-sm font-medium text-amber-800">
            {t("result.ffmpeg_warning")}
          </div>
        )}

        {/* Header */}
        <div className="grid gap-5 lg:grid-cols-[22rem_1fr]">
          <div className="dark-panel relative min-h-full overflow-hidden p-3">
            <div className="relative overflow-hidden rounded-[1.35rem] bg-slate-900">
            {result.thumbnail ? (
              <img
                src={result.thumbnail}
                alt={result.title}
                referrerPolicy="no-referrer"
                  className="h-56 w-full object-cover"
              />
            ) : (
                <div className="flex h-56 w-full items-center justify-center text-slate-500">
                {t("result.no_thumb")}
              </div>
            )}
            {result.duration_string && (
                <span className="absolute bottom-3 right-3 rounded-full bg-black/75 px-3 py-1 text-xs font-black text-white backdrop-blur">
                {result.duration_string}
              </span>
            )}
            </div>
            <div className="p-3">
              <p className="text-[11px] font-black uppercase tracking-[0.18em] text-neon-300">{t("result.section_download")}</p>
              <h3 className="mt-2 line-clamp-2 text-xl font-black leading-snug text-white">{result.title}</h3>
              <div className="mt-3 flex flex-wrap items-center gap-2 text-xs font-bold text-white/65">
                {result.uploader && <span>{result.uploader}</span>}
                {viewsLabel && <span>{viewsLabel} {t("result.views")}</span>}
              </div>
            </div>
          </div>

          <div className="min-w-0 rounded-[1.5rem] border border-slate-200/70 bg-white/75 p-5 shadow-sm">
            <div className="flex flex-wrap items-center gap-2">
              {result.extractor && (
                <span className="rounded-full bg-brand-50 px-3 py-1 text-xs font-black uppercase tracking-[0.12em] text-brand-700">
                  {result.extractor}
                </span>
              )}
              {result.has_subtitles && (
                <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-black uppercase tracking-[0.12em] text-emerald-600">
                  {t("result.has_subtitles")}
                </span>
              )}
            </div>

            <ResultFlow steps={resultFlowSteps} currentStep={resultFlowStep} label={t("result.workflow")} />

            {/* Section A: Download */}
            <div className="mt-5">
              <p className="mb-3 text-xs font-black uppercase tracking-[0.18em] text-slate-400">
                {t("result.select_quality")}
              </p>

          {result.subtitle_langs?.length > 0 && (
            <div className="mb-4">
                  <label className="mb-1 block text-xs font-black uppercase tracking-[0.16em] text-slate-400">
                {t("result.subtitle_lang")}
              </label>
              <select
                value={subLang}
                onChange={(e) => {
                  setSubLangManual(true);
                  setSubLang(e.target.value);
                }}
                    className="w-full max-w-xs rounded-2xl border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 outline-none transition focus:border-brand-400 focus:ring-4 focus:ring-brand-100 sm:w-auto"
              >
                {result.subtitle_langs.map((l) => (
                  <option key={l} value={l}>{l}</option>
                ))}
              </select>
            </div>
          )}

          <div>
            <div className="flex flex-wrap gap-2">
              {result.options.map((opt) => (
                <button
                  key={opt.id}
                  type="button"
                  onClick={() => setSelected(opt.id)}
                      className={`rounded-2xl border px-3 py-2 text-sm font-bold transition ${
                    selected === opt.id
                          ? "border-brand-500 bg-brand-50 text-brand-700 shadow-sm shadow-brand-100"
                          : "border-slate-200 bg-white text-slate-600 hover:border-brand-300 hover:text-brand-700"
                  }`}
                >
                  {optionLabel(opt)}
                  {qualityTier(opt) && (
                        <span className="ml-1 rounded-full bg-brand-100 px-1.5 py-0.5 text-[10px] font-black text-brand-700">
                      {qualityTier(opt)}
                    </span>
                  )}
                  {opt.filesize && <span className="ml-1 text-xs text-slate-400">{opt.filesize}</span>}
                  {opt.recommended && (
                        <span className="ml-1 rounded-full bg-amber-100 px-1.5 py-0.5 text-[10px] font-black text-amber-700">
                      {t("result.recommend")}
                    </span>
                  )}
                </button>
              ))}
            </div>
            {result.options.some((o) => o.needs_merge) && (
                  <p className="mt-2 text-xs font-medium text-slate-400">{t("result.quality_hint")}</p>
            )}
          </div>

          {downloading && (
                <div className="mt-5 rounded-2xl border border-brand-100 bg-brand-50/60 p-4">
                  <div className="mb-2 flex justify-between text-xs font-bold text-slate-500">
                <span>{t("result.downloading")}</span>
                <span>{progressDetail()}</span>
              </div>
                  <div className="relative h-2.5 overflow-hidden rounded-full bg-white">
                {progressIndeterminate ? (
                  <div className="absolute inset-y-0 w-1/3 animate-progress-indeterminate brand-gradient rounded-full" />
                ) : (
                  <div
                    className="brand-gradient h-full rounded-full transition-all duration-300"
                    style={{ width: `${dlProgress.percent}%` }}
                  />
                )}
              </div>
                  <div className="mt-2 flex justify-between text-xs font-medium text-slate-400">
                <span>{t("result.progress_speed")}: {speedLabel}</span>
                <span>{etaLabel}</span>
              </div>
            </div>
          )}

              <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
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

            {result.has_subtitles && (
              <ActionBtn onClick={handleTranslate} disabled={translating} loading={translating} loadingText={t("result.translating")} pro accent="fuchsia">
                <GlobeIcon /> {t("result.translate")}
              </ActionBtn>
            )}
          </div>

          {dlError && <Alert>{dlError}</Alert>}
          {subMsg && <StatusMsg failed={subFailed}>{subMsg}</StatusMsg>}
          {trMsg && <StatusMsg failed={trFailed}>{trMsg}</StatusMsg>}
            </div>
        </div>
        </div>

        {/* Section B: AI Understanding */}
        <SummarizeSSESection
          url={url}
          hasSubtitles={result.has_subtitles || result.subtitle_uncertain}
          subtitleUncertain={result.subtitle_uncertain}
          preferLang={subLang || undefined}
          llmReady={llmReady}
          outputLang={outputLang}
          onTranslate={result.has_subtitles ? handleTranslate : undefined}
          translating={translating}
          t={t}
        />
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

function ResultFlow({ steps, currentStep, label }) {
  return (
    <div className="mt-5 rounded-[1.25rem] border border-brand-100 bg-gradient-to-r from-brand-50 via-white to-accent-100/40 p-3">
      <div className="mb-3 flex items-center justify-between">
        <p className="text-xs font-black uppercase tracking-[0.16em] text-brand-700">{label}</p>
        <p className="text-xs font-black text-slate-400">{currentStep}/{steps.length}</p>
      </div>
      <div className="mb-3 h-2 overflow-hidden rounded-full bg-white shadow-inner">
        <div
          className="h-full rounded-full bg-gradient-to-r from-neon-400 via-brand-500 to-accent-500 transition-all duration-500"
          style={{ width: `${Math.min(100, (currentStep / steps.length) * 100)}%` }}
        />
      </div>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {steps.map((step, index) => {
          const done = index + 1 < currentStep;
          const active = index + 1 === currentStep;
          return (
            <div
              key={step}
              className={`rounded-2xl border px-3 py-2 ${
                active
                  ? "border-brand-300 bg-white shadow-sm shadow-brand-100"
                  : done
                    ? "border-emerald-100 bg-emerald-50"
                    : "border-slate-200 bg-white/70"
              }`}
            >
              <div className="flex items-center gap-2">
                <span
                  className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-black ${
                    active
                      ? "brand-gradient text-white"
                      : done
                        ? "bg-emerald-500 text-white"
                        : "bg-slate-100 text-slate-400"
                  }`}
                >
                  {done ? "✓" : index + 1}
                </span>
                <span className={`text-xs font-black leading-tight ${active ? "text-brand-700" : done ? "text-emerald-700" : "text-slate-400"}`}>
                  {step}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ActionBtn({ children, onClick, disabled, loading, loadingText, cancelMode, primary, pro, accent }) {
  const border = accent === "fuchsia"
    ? "border-accent-200 text-accent-600 hover:border-accent-400 hover:bg-accent-50"
    : "border-brand-200 text-brand-700 hover:border-brand-400 hover:bg-brand-50";
  const cancelStyles = cancelMode
    ? "border-2 border-slate-300 bg-white text-slate-700 hover:border-slate-400 hover:bg-slate-50"
    : primary
      ? "brand-gradient text-white shadow-lg shadow-accent-200/50 hover:-translate-y-0.5"
      : `border-2 bg-white ${border}`;
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`flex items-center justify-center gap-2 rounded-2xl px-4 py-3 text-sm font-black transition disabled:opacity-70 ${cancelStyles}`}
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
  return <p className="mt-3 rounded-2xl border border-red-100 bg-red-50 px-4 py-3 text-sm font-medium text-red-600">{children}</p>;
}

function StatusMsg({ children, failed }) {
  return (
    <p className={`mt-3 rounded-2xl border px-4 py-3 text-sm font-medium ${failed ? "border-red-100 bg-red-50 text-red-600" : "border-emerald-100 bg-emerald-50 text-emerald-600"}`}>
      {children}
    </p>
  );
}

function ProBadge() {
  return (
    <span className="rounded-full bg-gradient-to-r from-amber-400 to-orange-500 px-2 py-0.5 text-[10px] font-black text-white">
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

function GlobeIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="9" />
      <path strokeLinecap="round" d="M3 12h18M12 3c2.5 2.7 2.5 15.3 0 18M12 3c-2.5 2.7-2.5 15.3 0 18" />
    </svg>
  );
}
