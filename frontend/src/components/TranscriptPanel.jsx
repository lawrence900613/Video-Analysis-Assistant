import { useEffect, useMemo, useRef, useState } from "react";

function formatCueTime(sec) {
  if (sec == null) return "?:??";
  const s = Math.floor(sec);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const ss = s % 60;
  if (h) return `${h}:${String(m).padStart(2, "0")}:${String(ss).padStart(2, "0")}`;
  return `${m}:${String(ss).padStart(2, "0")}`;
}

export default function TranscriptPanel({
  transcript,
  t,
  onTranslate,
  translating,
  highlightCueIndex,
  onLoadTranscript,
  loading,
}) {
  const [search, setSearch] = useState("");
  const listRef = useRef(null);
  const cues = transcript?.cues || [];

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return cues;
    return cues.filter((c) => c.text.toLowerCase().includes(q));
  }, [cues, search]);

  useEffect(() => {
    if (highlightCueIndex == null) return;
    const container = listRef.current;
    const target = container?.querySelector(`[data-cue-index="${highlightCueIndex}"]`);
    if (!container || !target) return;
    container.scrollTop = target.offsetTop - container.clientHeight / 2 + target.clientHeight / 2;
  }, [highlightCueIndex, filtered]);

  if (!transcript) {
    return (
      <div className="mx-auto w-full max-w-md rounded-2xl border border-indigo-100/80 bg-white/70 px-5 py-6 text-center shadow-sm shadow-indigo-100/30">
        <p className="text-sm font-semibold text-slate-700">{t("understanding.transcript_empty_title")}</p>
        <p className="mt-1.5 text-xs leading-relaxed text-slate-500">
          {t("understanding.transcript_empty_hint")}
        </p>
        {onLoadTranscript && (
          <button
            type="button"
            onClick={onLoadTranscript}
            disabled={loading}
            className="mt-4 inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-indigo-200 bg-white px-4 py-2 text-sm font-semibold text-indigo-600 transition hover:border-indigo-300 hover:bg-indigo-50 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loading && <Spinner />}
            {loading ? t("understanding.transcript_loading_short") : t("understanding.load_transcript")}
          </button>
        )}
      </div>
    );
  }

  return (
    <div>
      <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center">
        <input
          type="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder={t("understanding.search_transcript")}
          className="min-h-11 flex-1 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-indigo-400"
        />
        {onTranslate && (
          <button
            type="button"
            onClick={onTranslate}
            disabled={translating}
            className="min-h-11 shrink-0 rounded-lg border border-fuchsia-200 px-3 py-2 text-sm font-medium text-fuchsia-600 hover:border-fuchsia-400 disabled:opacity-60"
          >
            {translating ? t("result.translating") : t("result.translate")}
          </button>
        )}
      </div>

      {transcript.truncated && (
        <p className="mb-2 text-xs text-amber-600">{t("understanding.truncated_hint")}</p>
      )}

      <div ref={listRef} className="max-h-96 overflow-y-auto rounded-xl border border-slate-100 bg-slate-50/50">
        {filtered.length === 0 ? (
          <p className="py-6 text-center text-sm text-slate-400">{t("understanding.no_search_results")}</p>
        ) : (
          <ul className="divide-y divide-slate-100">
            {filtered.map((cue) => (
              <li
                key={cue.index}
                id={`cue-${cue.index}`}
                data-cue-index={cue.index}
                className={`flex gap-3 px-3 py-2 text-sm hover:bg-white/80 ${
                  highlightCueIndex === cue.index ? "bg-indigo-100/80 ring-1 ring-inset ring-indigo-300" : ""
                }`}
              >
                <span className="shrink-0 font-mono text-xs text-indigo-500 pt-0.5">
                  [{formatCueTime(cue.start_sec)}]
                </span>
                <span className="text-slate-700">{cue.text}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
      <p className="mt-2 text-xs text-slate-400">
        {t("understanding.cue_count", { shown: filtered.length, total: cues.length })}
      </p>
    </div>
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
