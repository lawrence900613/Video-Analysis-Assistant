import SummaryPanel from "./SummaryPanel";

export default function StreamingSummaryPanel({ summary, streamingText, streaming, stage, t }) {
  const isLive = streaming && !summary;
  const isComplete = summary && !streaming;

  return (
    <div
      className={`relative rounded-2xl transition-all duration-500 ${
        isLive
          ? "stream-panel-glow bg-gradient-to-br from-indigo-50/60 via-white to-violet-50/40 p-[1px]"
          : isComplete
            ? "animate-fade-up"
            : ""
      }`}
    >
      <div
        className={`rounded-2xl transition-all duration-500 ${
          isLive ? "bg-white/95 px-4 py-4 sm:px-5 sm:py-5" : ""
        }`}
      >
        {isLive && (
          <div className="mb-4 flex items-center justify-between gap-3">
            <div className="flex items-center gap-2.5">
              <span className="relative flex h-2.5 w-2.5">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-fuchsia-400 opacity-70" />
                <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-fuchsia-500" />
              </span>
              <h5 className="brand-text text-sm font-extrabold tracking-wide sm:text-base">
                {t("understanding.streaming_label")}
              </h5>
            </div>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-indigo-100 bg-indigo-50/80 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-indigo-600">
              <TypingDots />
              {t("understanding.live_badge")}
            </span>
          </div>
        )}

        <SummaryPanel
          summary={summary}
          streamingText={streamingText}
          streaming={streaming}
          stage={stage}
          t={t}
          hideLiveHeader
        />
      </div>
    </div>
  );
}

function TypingDots() {
  return (
    <span className="inline-flex gap-0.5" aria-hidden="true">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="h-1 w-1 rounded-full bg-indigo-500 animate-typing-dot"
          style={{ animationDelay: `${i * 0.15}s` }}
        />
      ))}
    </span>
  );
}
