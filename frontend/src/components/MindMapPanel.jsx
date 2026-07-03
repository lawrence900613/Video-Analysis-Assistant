import { useEffect, useRef } from "react";

import { Markmap } from "markmap-view";
import { Transformer } from "markmap-lib";

const BRAND_COLORS = ["#6366f1", "#7c3aed", "#8b5cf6", "#a855f7", "#818cf8"];

export default function MindMapPanel({
  markdown,
  loading,
  error,
  onGenerate,
  canGenerate,
  t,
}) {
  const svgRef = useRef(null);
  const markmapRef = useRef(null);

  useEffect(() => {
    if (!markdown || !svgRef.current) return;

    const transformer = new Transformer();
    const { root } = transformer.transform(markdown);

    if (!markmapRef.current) {
      markmapRef.current = Markmap.create(svgRef.current, {
        autoFit: true,
        duration: 400,
        paddingX: 18,
        color: (node) => BRAND_COLORS[node.state?.depth % BRAND_COLORS.length],
      });
    }

    markmapRef.current.setData(root);
    markmapRef.current.fit();
  }, [markdown]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-16">
        <div className="relative mb-4 flex h-12 w-12 items-center justify-center">
          <span className="absolute inset-0 animate-ping rounded-full bg-indigo-200 opacity-40" />
          <span className="relative flex h-12 w-12 items-center justify-center rounded-xl bg-indigo-50 text-indigo-500">
            <Spinner />
          </span>
        </div>
        <p className="text-sm font-medium text-indigo-700">{t("understanding.mindmap_loading")}</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-red-100 bg-red-50 px-4 py-6 text-center">
        <p className="text-sm text-red-600">{error}</p>
        {canGenerate && (
          <button
            type="button"
            onClick={onGenerate}
            className="mt-4 rounded-lg border border-indigo-200 bg-white px-4 py-2 text-sm font-semibold text-indigo-600 hover:bg-indigo-50"
          >
            {t("understanding.mindmap_retry")}
          </button>
        )}
      </div>
    );
  }

  if (!markdown) {
    return (
      <div className="rounded-xl border border-dashed border-indigo-200/70 bg-white/60 px-5 py-10 text-center">
        <p className="text-sm font-semibold text-slate-700">{t("understanding.mindmap_empty_title")}</p>
        <p className="mt-1.5 text-xs text-slate-500">{t("understanding.mindmap_empty_hint")}</p>
        {canGenerate && (
          <button
            type="button"
            onClick={onGenerate}
            className="mt-5 inline-flex items-center gap-2 rounded-xl brand-gradient px-4 py-2 text-sm font-semibold text-white shadow-md shadow-indigo-200"
          >
            <SparkIcon /> {t("understanding.mindmap_generate")}
          </button>
        )}
      </div>
    );
  }

  return (
    <div>
      <div className="mb-3 flex items-center justify-between gap-2">
        <p className="text-xs text-slate-500">{t("understanding.mindmap_hint")}</p>
        {canGenerate && (
          <button
            type="button"
            onClick={onGenerate}
            disabled={loading}
            className="shrink-0 rounded-lg border border-indigo-200 px-3 py-1.5 text-xs font-medium text-indigo-600 hover:bg-indigo-50 disabled:opacity-50"
          >
            {t("understanding.mindmap_regenerate")}
          </button>
        )}
      </div>
      <div className="overflow-hidden rounded-xl border border-indigo-100/80 bg-gradient-to-br from-indigo-50/30 via-white to-violet-50/20">
        <svg ref={svgRef} className="h-[420px] w-full" />
      </div>
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

function Spinner() {
  return (
    <svg className="h-5 w-5 animate-spin" viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  );
}
