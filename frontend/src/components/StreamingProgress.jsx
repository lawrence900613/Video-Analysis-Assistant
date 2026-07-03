const STAGE_LABELS = {
  zh: {
    fetching_transcript: "获取字幕…",
    summarizing: "生成摘要…",
    chunking: "长视频分块处理…",
    map: "分析片段 {current}/{total}…",
    reducing: "合并摘要…",
  },
  en: {
    fetching_transcript: "Fetching transcript…",
    summarizing: "Generating summary…",
    chunking: "Chunking long video…",
    map: "Analyzing segment {current}/{total}…",
    reducing: "Merging summary…",
  },
};

const STEPS = [
  { id: "transcript", icon: TranscriptIcon },
  { id: "summarize", icon: SparkIcon },
  { id: "done", icon: CheckIcon },
];

function resolveStepIndex(stageName) {
  if (!stageName) return 0;
  if (stageName === "fetching_transcript") return 0;
  if (["chunking", "map", "summarizing", "reducing"].includes(stageName)) return 1;
  return 1;
}

function resolveProgress(stage) {
  if (!stage?.name) return 8;
  if (stage.name === "fetching_transcript") return 18;
  if (stage.name === "chunking") return 38;
  if (stage.name === "map" && stage.chunk_total) {
    const ratio = (stage.chunk_current ?? 0) / stage.chunk_total;
    return 38 + Math.round(ratio * 42);
  }
  if (stage.name === "summarizing") return 78;
  if (stage.name === "reducing") return 92;
  return 55;
}

export default function StreamingProgress({ stage, lang = "zh", t }) {
  const labels = STAGE_LABELS[lang] || STAGE_LABELS.zh;
  const activeStep = resolveStepIndex(stage?.name);
  const progress = resolveProgress(stage);
  const topProgress = Math.min(100, Math.max(0, progress));

  let detail = labels[stage?.name] || labels.summarizing;
  if (stage?.name === "map" && stage.chunk_current != null) {
    detail = detail
      .replace("{current}", String(stage.chunk_current))
      .replace("{total}", String(stage.chunk_total ?? "?"));
  }

  const stepLabels = [
    t?.("understanding.stage_step_transcript") ?? (lang === "zh" ? "获取字幕" : "Fetch transcript"),
    t?.("understanding.stage_step_summarize") ?? (lang === "zh" ? "生成摘要" : "Summarize"),
    t?.("understanding.stage_step_done") ?? (lang === "zh" ? "完成" : "Done"),
  ];

  return (
    <div className="mb-5 overflow-hidden rounded-2xl border border-indigo-100/80 bg-white/90 p-4 shadow-sm shadow-indigo-100/50 dark:border-brand-500/20 dark:bg-ink-900/80 dark:shadow-brand-500/10">
      <div className="relative mb-4">
        <div className="absolute left-[calc(16.666%_-_18px)] right-[calc(16.666%_-_18px)] top-[18px] hidden h-0.5 overflow-hidden rounded-full bg-indigo-100 dark:bg-white/10 sm:block">
          <div
            className="brand-gradient h-full rounded-full transition-all duration-700 ease-out"
            style={{ width: `${topProgress}%` }}
          />
        </div>
        <div className="grid grid-cols-3 gap-3">
        {STEPS.map((step, i) => {
          const Icon = step.icon;
          const isDone = i < activeStep;
          const isActive = i === activeStep;
          const isPending = i > activeStep;

          return (
            <div key={step.id} className="relative z-10 flex min-w-0 flex-col items-center gap-1.5">
                <span
                  className={`relative flex h-9 w-9 shrink-0 items-center justify-center rounded-full transition-all duration-500 ${
                    isDone
                      ? "brand-gradient text-white shadow-md shadow-indigo-200"
                      : isActive
                        ? "bg-indigo-50 text-indigo-600 ring-2 ring-indigo-400 ring-offset-2 dark:bg-brand-500/20 dark:text-brand-300 dark:ring-brand-400 dark:ring-offset-ink-950"
                        : "bg-slate-50 text-slate-400 ring-1 ring-slate-200 dark:bg-white/5 dark:text-slate-500 dark:ring-white/10"
                  }`}
                >
                  {isDone ? (
                    <CheckIcon className="h-4 w-4" />
                  ) : (
                    <Icon className={`h-4 w-4 ${isActive ? "animate-pulse" : ""}`} />
                  )}
                  {isActive && (
                    <span className="absolute -right-0.5 -top-0.5 flex h-2.5 w-2.5">
                      <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-indigo-400 opacity-60" />
                      <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-indigo-500" />
                    </span>
                  )}
                </span>
                <span
                  className={`max-w-[5.5rem] truncate text-center text-[11px] font-semibold leading-tight sm:max-w-none ${
                    isDone ? "text-indigo-600 dark:text-brand-300" : isActive ? "text-indigo-700 dark:text-brand-200" : isPending ? "text-slate-400 dark:text-slate-500" : "text-slate-500 dark:text-slate-400"
                  }`}
                >
                  {stepLabels[i]}
                </span>
            </div>
          );
        })}
        </div>
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between gap-2 text-xs">
          <span className="font-medium text-indigo-700 dark:text-brand-300">{detail}</span>
          <span className="tabular-nums text-slate-400 dark:text-slate-500">{progress}%</span>
        </div>
        <div className="relative h-2 overflow-hidden rounded-full bg-indigo-100/80 dark:bg-white/10">
          <div
            className="brand-gradient relative h-full rounded-full transition-all duration-500 ease-out"
            style={{ width: `${progress}%` }}
          >
            <div className="absolute inset-0 animate-progress-indeterminate bg-gradient-to-r from-transparent via-white/30 to-transparent" />
          </div>
        </div>
      </div>
    </div>
  );
}

function TranscriptIcon({ className = "h-4 w-4" }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="2">
      <path strokeLinecap="round" d="M7 8h10M7 12h6M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H9l-2 2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
    </svg>
  );
}

function SparkIcon({ className = "h-4 w-4" }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="currentColor">
      <path d="M9 2l1.5 5L15 8.5 10.5 10 9 15l-1.5-5L3 8.5 7.5 7 9 2zm8 8l.9 2.6 2.6.9-2.6.9L17 17l-.9-2.6-2.6-.9 2.6-.9L17 10z" />
    </svg>
  );
}

function CheckIcon({ className = "h-4 w-4" }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="2.5">
      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
    </svg>
  );
}
