import { useI18n } from "../i18n.jsx";

const PLATFORMS = ["YouTube", "Bilibili", "Douyin", "Twitch", "TikTok", "X / Twitter", "Instagram"];

export default function Hero({ url, setUrl, onParse, loading, error, flowStep = 1 }) {
  const { t } = useI18n();
  const steps = t("hero.steps");

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
          className="search-box mx-auto mt-8 flex max-w-2xl animate-fade-up flex-col gap-3 sm:flex-row sm:items-center sm:gap-0"
        >
          <div className="flex flex-1 items-center gap-2 px-4 py-3 sm:py-0">
            <svg viewBox="0 0 24 24" className="h-5 w-5 shrink-0 text-slate-400" fill="none" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M13.19 8.688a4.5 4.5 0 011.242 7.244l-4.5 4.5a4.5 4.5 0 01-6.364-6.364l1.757-1.757" />
              <path strokeLinecap="round" strokeLinejoin="round" d="M10.81 15.312a4.5 4.5 0 01-1.242-7.244l4.5-4.5a4.5 4.5 0 016.364 6.364l-1.757 1.757" />
            </svg>
            <input
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder={t("hero.placeholder")}
              className="w-full bg-transparent text-sm text-slate-800 outline-none placeholder:text-slate-400"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="brand-gradient mx-2 mb-2 flex items-center justify-center gap-2 rounded-xl px-8 py-3 text-sm font-semibold text-white shadow-lg shadow-indigo-200 transition hover:scale-[1.02] disabled:cursor-not-allowed disabled:opacity-70 sm:mb-0 sm:rounded-lg sm:px-6 sm:py-2.5"
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

        {/* Flow steps */}
        <div className="mx-auto mt-8 flex max-w-2xl flex-wrap items-center justify-center gap-2 animate-fade-up">
          {steps.map((step, i) => (
            <div key={step} className="flex items-center gap-2">
              <span
                className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold ${
                  i < flowStep ? "brand-gradient text-white" : "bg-white text-slate-500 ring-1 ring-slate-200"
                }`}
              >
                {i + 1}
              </span>
              <span className="text-xs font-medium text-slate-500">{step}</span>
              {i < steps.length - 1 && (
                <svg viewBox="0 0 24 24" className="mx-1 hidden h-4 w-4 text-slate-300 sm:block" fill="none" stroke="currentColor" strokeWidth="2">
                  <path strokeLinecap="round" d="M9 5l7 7-7 7" />
                </svg>
              )}
            </div>
          ))}
        </div>

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
