import { useI18n } from "../i18n.jsx";
import { formatViews } from "../utils/history.js";

export default function HistoryPanel({ items, onSelect, onRemove, onClear }) {
  const { t } = useI18n();
  if (!items.length) return null;

  return (
    <section id="history" className="mx-auto mt-8 max-w-4xl px-4 sm:px-6">
      <div className="card p-4 sm:p-5">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-bold text-slate-800">{t("history.title")}</h2>
          <button
            type="button"
            onClick={onClear}
            className="text-xs font-medium text-slate-400 transition hover:text-red-500"
          >
            {t("history.clear")}
          </button>
        </div>
        <ul className="divide-y divide-slate-100">
          {items.map((item) => (
            <li key={item.id} className="flex items-center gap-3 py-3 first:pt-0 last:pb-0">
              <button
                type="button"
                onClick={() => onSelect(item.url)}
                className="flex min-w-0 flex-1 items-center gap-3 text-left transition hover:opacity-80"
              >
                <div className="h-10 w-14 shrink-0 overflow-hidden rounded-lg bg-slate-100">
                  {item.thumbnail ? (
                    <img
                      src={item.thumbnail}
                      alt=""
                      referrerPolicy="no-referrer"
                      className="h-full w-full object-cover"
                    />
                  ) : (
                    <div className="flex h-full w-full items-center justify-center text-[10px] text-slate-300">—</div>
                  )}
                </div>
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-slate-800">{item.title}</p>
                  <p className="text-xs text-slate-400">
                    {item.extractor}
                    {item.view_count != null && ` · ${formatViews(item.view_count)} ${t("history.views")}`}
                  </p>
                </div>
              </button>
              <button
                type="button"
                onClick={() => onRemove(item.id)}
                aria-label={t("history.remove")}
                className="shrink-0 rounded-lg p-1.5 text-slate-400 transition hover:bg-red-50 hover:text-red-500"
              >
                <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
                  <path strokeLinecap="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
