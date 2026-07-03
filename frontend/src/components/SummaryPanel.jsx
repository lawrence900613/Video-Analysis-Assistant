import { parsePartialSummary } from "../utils/parsePartialSummary";

function TypingCursor() {
  return (
    <span className="ml-0.5 inline-flex items-center gap-1 align-middle">
      <span className="inline-block h-4 w-0.5 animate-pulse bg-gradient-to-b from-indigo-400 to-fuchsia-500" />
    </span>
  );
}

function StreamingMarkdownPreview({ text }) {
  const lines = (text || "").split("\n").filter((_, i, arr) => i < arr.length - 1 || arr[i].trim());

  return (
    <div className="space-y-2 text-sm leading-relaxed text-slate-700">
      {lines.map((line, i) => {
        const trimmed = line.trim();
        if (!trimmed) return <div key={i} className="h-2" />;

        const h1 = trimmed.match(/^#\s+(.+)$/);
        if (h1) {
          return (
            <p key={i} className="text-xs font-semibold uppercase tracking-wide text-indigo-600">
              {h1[1]}
            </p>
          );
        }

        const h2 = trimmed.match(/^##+\s*(?:\[([^\]]+)\]\s*)?(.+)$/);
        if (h2) {
          return (
            <div key={i} className="flex items-baseline gap-2 pt-1">
              {h2[1] && (
                <span className="shrink-0 rounded bg-indigo-100 px-1.5 py-0.5 font-mono text-[10px] text-indigo-600">
                  {h2[1]}
                </span>
              )}
              <span className="font-semibold text-slate-800">{h2[2]}</span>
            </div>
          );
        }

        const bullet = trimmed.match(/^[-*]\s+(.+)$/);
        if (bullet) {
          return (
            <div key={i} className="flex gap-2 pl-1">
              <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-indigo-400" />
              <span>{bullet[1]}</span>
            </div>
          );
        }

        return (
          <p key={i} className="text-slate-600">
            {trimmed}
          </p>
        );
      })}
      <TypingCursor />
    </div>
  );
}

function SummarySections({ summary, streaming, t, showRawPreview, rawText }) {
  const hasContent =
    summary?.tldr ||
    summary?.key_points?.length > 0 ||
    summary?.chapters?.length > 0;

  if (!hasContent) {
    if (streaming && rawText?.trim()) {
      return (
        <div className="rounded-xl border border-indigo-100/80 bg-white/60 p-4 backdrop-blur-sm">
          <StreamingMarkdownPreview text={rawText} />
        </div>
      );
    }

    if (streaming) {
      return (
        <div className="rounded-xl border border-dashed border-indigo-200/80 bg-indigo-50/30 p-5">
          <div className="flex items-center gap-3">
            <ShimmerBlock />
            <div className="flex-1 space-y-2">
              <div className="h-3 w-3/4 animate-pulse rounded bg-indigo-100" />
              <div className="h-3 w-1/2 animate-pulse rounded bg-indigo-100/70" />
              <p className="text-sm text-indigo-600/80">{t("understanding.stage_streaming")}</p>
            </div>
          </div>
        </div>
      );
    }

    return (
      <div className="mx-auto w-full max-w-md rounded-2xl border border-dashed border-indigo-200/70 bg-white/60 px-5 py-6 text-center">
        <p className="text-sm font-semibold text-slate-600">{t("understanding.summary_empty")}</p>
        <p className="mt-1.5 break-words text-xs leading-relaxed text-slate-400">
          {t("understanding.empty_state_hint")}
        </p>
      </div>
    );
  }

  return (
    <div className={`space-y-5 ${streaming ? "animate-fade-up" : ""}`}>
      {summary.tldr && (
        <div className="rounded-xl border border-indigo-100 bg-indigo-50/50 p-4 transition-all duration-300">
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-indigo-600">
            {t("understanding.tldr")}
          </p>
          <p className="text-sm leading-relaxed text-slate-800">
            {summary.tldr}
            {streaming && !summary.key_points?.length && !summary.chapters?.length && <TypingCursor />}
          </p>
        </div>
      )}

      {summary.key_points?.length > 0 && (
        <div className="animate-fade-up">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
            {t("understanding.key_points")}
          </p>
          <ul className="space-y-2">
            {summary.key_points.map((pt, i) => (
              <li key={i} className="flex gap-2 text-sm text-slate-700">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-indigo-400" />
                <span>
                  {pt}
                  {streaming && i === summary.key_points.length - 1 && !summary.chapters?.length && (
                    <TypingCursor />
                  )}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {summary.chapters?.length > 0 && (
        <div className="animate-fade-up">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
            {t("understanding.chapters")}
          </p>
          <div className="space-y-3">
            {summary.chapters.map((ch, i) => (
              <div
                key={i}
                className="rounded-lg border border-slate-100 bg-slate-50/80 px-4 py-3 transition-all duration-300 hover:border-indigo-100 hover:bg-indigo-50/30"
              >
                <div className="flex items-baseline gap-2">
                  {ch.start_label && (
                    <span className="shrink-0 rounded bg-slate-200 px-1.5 py-0.5 font-mono text-xs text-slate-600">
                      {ch.start_label}
                    </span>
                  )}
                  <span className="text-sm font-semibold text-slate-800">{ch.title}</span>
                </div>
                {ch.summary && (
                  <p className="mt-1 text-sm leading-relaxed text-slate-600">
                    {ch.summary}
                    {streaming && i === summary.chapters.length - 1 && <TypingCursor />}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {streaming && showRawPreview && rawText?.trim() && !summary.chapters?.length && (
        <div className="rounded-lg border border-indigo-100/60 bg-white/50 p-3 opacity-80">
          <StreamingMarkdownPreview text={rawText.slice(summary.tldr?.length ? -200 : undefined)} />
        </div>
      )}
    </div>
  );
}

function ShimmerBlock() {
  return (
    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl brand-gradient shadow-md shadow-indigo-200">
      <svg viewBox="0 0 24 24" className="h-5 w-5 animate-pulse text-white" fill="currentColor">
        <path d="M9 2l1.5 5L15 8.5 10.5 10 9 15l-1.5-5L3 8.5 7.5 7 9 2z" />
      </svg>
    </div>
  );
}

export default function SummaryPanel({
  summary,
  streamingText,
  streaming,
  stage,
  t,
  hideLiveHeader = false,
}) {
  if (!summary && !streamingText && !streaming) {
    return (
      <div className="mx-auto w-full max-w-md rounded-2xl border border-dashed border-indigo-200/70 bg-white/60 px-5 py-8 text-center sm:px-6">
        <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-100 to-violet-100 text-indigo-400 shadow-inner">
          <svg viewBox="0 0 24 24" className="h-6 w-6 shrink-0" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path strokeLinecap="round" d="M9 12h6M9 16h4M7 20h10a2 2 0 002-2V8l-2-2H9L7 8v10a2 2 0 002 2z" />
          </svg>
        </div>
        <p className="text-sm font-semibold text-slate-600">{t("understanding.summary_empty")}</p>
        <p className="mt-1.5 break-words text-xs leading-relaxed text-slate-400">
          {t("understanding.empty_state_hint")}
        </p>
      </div>
    );
  }

  const displaySummary =
    summary || (streamingText ? parsePartialSummary(streamingText) : null);

  const waitingForMap =
    streaming &&
    !streamingText &&
    stage?.name &&
    ["fetching_transcript", "chunking", "map"].includes(stage.name);

  const waitingForTokens =
    streaming &&
    !streamingText &&
    stage?.name &&
    ["summarizing", "reducing"].includes(stage.name);

  return (
    <div className="space-y-4">
      {streaming && !summary && !hideLiveHeader && (
        <p className="text-xs font-semibold uppercase tracking-wide text-indigo-600">
          {t("understanding.streaming_label")}
        </p>
      )}

      {waitingForMap && (
        <div className="flex items-center gap-2 rounded-lg bg-indigo-50/60 px-3 py-2 text-sm text-indigo-700">
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-indigo-500" />
          {stage.name === "map" && stage.chunk_current != null
            ? t("understanding.stage_map_progress", {
                current: stage.chunk_current,
                total: stage.chunk_total ?? "?",
              })
            : stage.name === "chunking"
              ? t("understanding.stage_chunking", { total: stage.chunk_total ?? "…" })
              : t("understanding.stage_transcript")}
        </div>
      )}

      {waitingForTokens && (
        <div className="flex items-center gap-2 rounded-lg bg-violet-50/60 px-3 py-2 text-sm text-violet-700">
          <span className="inline-flex gap-0.5">
            {[0, 1, 2].map((i) => (
              <span
                key={i}
                className="h-1 w-1 rounded-full bg-violet-500 animate-typing-dot"
                style={{ animationDelay: `${i * 0.15}s` }}
              />
            ))}
          </span>
          {t("understanding.stage_streaming")}
        </div>
      )}

      <SummarySections
        summary={displaySummary}
        streaming={streaming && !summary}
        rawText={streamingText}
        showRawPreview={false}
        t={t}
      />
    </div>
  );
}
