import { useI18n } from "../i18n.jsx";

const PLATFORMS = ["YouTube", "哔哩哔哩", "抖音", "Threads", "TikTok", "X / Twitter", "Instagram"];

export default function Hero({ url, setUrl, onParse, loading, error }) {
  const { t } = useI18n();

  const handleSubmit = (e) => {
    e.preventDefault();
    onParse();
  };

  return (
    <section id="home" className="relative overflow-hidden pt-16 pb-10 sm:pt-24">
      <div className="mx-auto max-w-3xl px-4 text-center sm:px-6">
        <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-indigo-100 bg-white/70 px-4 py-1.5 text-xs font-medium text-indigo-600 shadow-sm animate-fade-up">
          <span className="flex h-2 w-2 rounded-full bg-emerald-500" />
          {t("hero.badge")}
        </div>

        <h1 className="animate-fade-up text-4xl font-extrabold leading-tight tracking-tight text-slate-900 sm:text-6xl">
          {t("hero.title_pre")}
          <br className="sm:hidden" />
          <span className="brand-text">{t("hero.title_highlight")}</span>
          {t("hero.title_post")}
        </h1>

        <p className="mx-auto mt-5 max-w-xl animate-fade-up text-base text-slate-500 sm:text-lg">
          {t("hero.sub_1")}
          <span className="font-semibold text-slate-700">{t("hero.sub_ai")}</span>
          {t("hero.sub_2")}
          <span className="font-semibold text-slate-700">{t("hero.sub_translate")}</span>
          {t("hero.sub_3")}
        </p>

        <form
          onSubmit={handleSubmit}
          className="mx-auto mt-8 flex max-w-2xl animate-fade-up flex-col gap-3 sm:flex-row sm:items-center sm:gap-2 sm:rounded-full sm:bg-white sm:p-2 sm:shadow-xl sm:shadow-indigo-100 sm:ring-1 sm:ring-slate-100"
        >
          <div className="flex flex-1 items-center gap-2 rounded-full bg-white px-4 py-3 shadow-lg ring-1 ring-slate-100 sm:shadow-none sm:ring-0">
            <svg viewBox="0 0 24 24" className="h-5 w-5 shrink-0 text-slate-400" fill="none" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M13.19 8.688a4.5 4.5 0 011.242 7.244l-4.5 4.5a4.5 4.5 0 01-6.364-6.364l1.757-1.757" />
              <path strokeLinecap="round" strokeLinejoin="round" d="M10.81 15.312a4.5 4.5 0 01-1.242-7.244l4.5-4.5a4.5 4.5 0 016.364 6.364l-1.757 1.757" />
            </svg>
            <input
              type="text"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder={t("hero.placeholder")}
              className="w-full bg-transparent text-sm text-slate-800 outline-none placeholder:text-slate-400"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="brand-gradient flex items-center justify-center gap-2 rounded-full px-8 py-3 text-sm font-semibold text-white shadow-lg shadow-indigo-200 transition hover:scale-[1.03] disabled:cursor-not-allowed disabled:opacity-70"
          >
            {loading ? (
              <>
                <Spinner /> {t("hero.parsing")}
              </>
            ) : (
              t("hero.parse")
            )}
          </button>
        </form>

        {error && (
          <p className="mx-auto mt-4 max-w-xl rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600">
            {error}
          </p>
        )}

        <div className="mt-6 flex flex-wrap items-center justify-center gap-x-5 gap-y-2 text-xs text-slate-400">
          {PLATFORMS.map((p) => (
            <span key={p} className="font-medium">{p}</span>
          ))}
        </div>
      </div>
    </section>
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
