import { useI18n } from "../i18n.jsx";

const PLATFORMS = ["YouTube", "Bilibili", "Douyin", "Twitch", "TikTok", "X / Twitter", "Instagram"];

export default function Hero({ url, setUrl, onParse, loading, error, flowStep = 1 }) {
  const { t } = useI18n();
  const steps = t("hero.steps");
  const trustItems = t("hero.trust_items");

  const handleSubmit = (e) => {
    e.preventDefault();
    onParse();
  };

  return (
    <section id="home" className="mesh-grid relative overflow-hidden pb-14 pt-12 sm:pt-20">
      <div className="pointer-events-none absolute left-1/2 top-10 h-80 w-80 -translate-x-1/2 rounded-full bg-neon-400/20 blur-3xl" />
      <div className="pointer-events-none absolute right-0 top-28 h-72 w-72 rounded-full bg-accent-400/20 blur-3xl" />

      <div className="relative mx-auto grid max-w-6xl items-center gap-10 px-4 sm:px-6 lg:grid-cols-[1.05fr_0.95fr]">
        <div className="text-center lg:text-left">
          <div className="mb-5 inline-flex animate-fade-up items-center gap-2 rounded-full border border-white/80 bg-white/75 px-4 py-2 text-xs font-black uppercase tracking-[0.16em] text-brand-700 shadow-sm backdrop-blur">
            <span className="flex h-2.5 w-2.5 rounded-full bg-emerald-400 shadow-lg shadow-emerald-300" />
            {t("hero.badge")}
          </div>

          <h1 className="animate-fade-up text-4xl font-black leading-[0.98] tracking-[-0.05em] text-ink-950 sm:text-6xl lg:text-7xl">
            {t("hero.title_pre")}
            <span className="brand-text">{t("hero.title_highlight")}</span>
            {t("hero.title_post")}
          </h1>

          <p className="mx-auto mt-6 max-w-2xl animate-fade-up text-base leading-8 text-slate-600 sm:text-lg lg:mx-0">
            {t("hero.sub_1")}
            <span className="font-black text-ink-950">{t("hero.sub_ai")}</span>
            {t("hero.sub_2")}
            <span className="font-black text-ink-950">{t("hero.sub_translate")}</span>
            {t("hero.sub_3")}
          </p>

          <form
            onSubmit={handleSubmit}
            className="search-box mx-auto mt-8 flex max-w-2xl animate-fade-scale flex-col gap-3 p-2 sm:flex-row sm:items-center lg:mx-0"
          >
            <div className="flex flex-1 items-center gap-3 px-3 py-2.5 sm:py-0">
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-brand-50 text-brand-600">
                <LinkIcon />
              </span>
              <input
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder={t("hero.placeholder")}
                className="w-full bg-transparent text-sm font-medium text-slate-800 outline-none placeholder:text-slate-400"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="premium-button flex items-center justify-center gap-2 sm:min-w-40"
            >
              {loading ? (
                <>
                  <Spinner /> {t("hero.parsing")}
                </>
              ) : (
                <>
                  {t("hero.parse")} <ArrowIcon />
                </>
              )}
            </button>
          </form>

          {error && (
            <p className="mx-auto mt-4 max-w-2xl rounded-2xl border border-red-100 bg-red-50 px-4 py-3 text-sm font-medium text-red-600 lg:mx-0">
              {error}
            </p>
          )}

          <div className="mt-6 grid animate-fade-up gap-3 sm:grid-cols-3">
            {trustItems.map((item) => (
              <div key={item.value} className="rounded-2xl border border-white/80 bg-white/65 p-4 text-left shadow-sm backdrop-blur">
                <p className="text-xl font-black text-ink-950">{item.value}</p>
                <p className="mt-1 text-xs font-bold uppercase tracking-[0.12em] text-slate-400">{item.label}</p>
              </div>
            ))}
          </div>
        </div>

        <HeroPreview t={t} />
      </div>

      <div className="relative mx-auto mt-8 flex max-w-6xl flex-wrap items-center justify-center gap-2 px-4 text-xs font-bold text-slate-500 sm:px-6">
        {PLATFORMS.map((p) => (
          <span key={p} className="rounded-full border border-white/80 bg-white/65 px-3 py-1.5 shadow-sm backdrop-blur">{p}</span>
        ))}
      </div>
    </section>
  );
}

function HeroPreview({ t }) {
  const previewItems = t("hero.preview_items");

  return (
    <div className="premium-panel relative animate-fade-scale overflow-hidden p-4 sm:p-5">
      <div className="absolute right-6 top-6 h-24 w-24 rounded-full bg-neon-400/20 blur-2xl" />
      <div className="dark-panel relative overflow-hidden p-5">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-xs font-black uppercase tracking-[0.22em] text-neon-300">{t("hero.preview_badge")}</p>
            <h2 className="mt-2 text-2xl font-black tracking-tight">{t("hero.preview_title")}</h2>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/10 px-3 py-2 text-right">
            <p className="text-lg font-black text-neon-300">3m</p>
            <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-white/50">{t("hero.preview_saved")}</p>
          </div>
        </div>

        <div className="mt-5 space-y-3">
          {previewItems.map((item, index) => (
            <div key={item.title} className="rounded-2xl border border-white/10 bg-white/[0.07] p-4 backdrop-blur">
              <div className="flex items-center justify-between gap-3">
                <span className="text-sm font-black">{item.title}</span>
                <span className="rounded-full bg-white/10 px-2 py-1 text-[10px] font-black uppercase tracking-[0.12em] text-neon-300">
                  {item.tag}
                </span>
              </div>
              <div className="mt-3 h-2 overflow-hidden rounded-full bg-white/10">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-neon-400 via-brand-400 to-accent-400"
                  style={{ width: `${82 - index * 14}%` }}
                />
              </div>
            </div>
          ))}
        </div>

      </div>
    </div>
  );
}

function LinkIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2">
      <path strokeLinecap="round" strokeLinejoin="round" d="M13.19 8.688a4.5 4.5 0 011.242 7.244l-4.5 4.5a4.5 4.5 0 01-6.364-6.364l1.757-1.757" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M10.81 15.312a4.5 4.5 0 01-1.242-7.244l4.5-4.5a4.5 4.5 0 016.364 6.364l-1.757 1.757" />
    </svg>
  );
}

function ArrowIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2.5">
      <path strokeLinecap="round" strokeLinejoin="round" d="M5 12h14m-6-6l6 6-6 6" />
    </svg>
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
