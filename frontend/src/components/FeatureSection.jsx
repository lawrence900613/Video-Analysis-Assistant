import { useI18n } from "../i18n.jsx";

const ICONS = [
  <path key="i" strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />,
  <path key="i" strokeLinecap="round" strokeLinejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178zM15 12a3 3 0 11-6 0 3 3 0 016 0z" />,
  <path key="i" strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />,
  <path key="i" strokeLinecap="round" strokeLinejoin="round" d="M10.5 21l5.25-11.25L21 21m-9-3h7.5M3 5.621a48.474 48.474 0 016-.371m0 0c1.12 0 2.233.038 3.334.114M9 5.25V3m3.334 2.364C11.176 10.658 7.69 15.08 3 17.502" />,
  <path key="i" strokeLinecap="round" strokeLinejoin="round" d="M12 21a9 9 0 100-18 9 9 0 000 18zm0 0c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m-9 9h18" />,
  <path key="i" strokeLinecap="round" strokeLinejoin="round" d="M10.5 1.5H8.25A2.25 2.25 0 006 3.75v16.5a2.25 2.25 0 002.25 2.25h7.5A2.25 2.25 0 0018 20.25V3.75a2.25 2.25 0 00-2.25-2.25H13.5m-3 0V3h3V1.5m-3 0h3m-3 18.75h3" />,
];

// PRO badge flag per feature: true = PRO
const IS_PRO = [false, false, true, true, false, false];

export default function FeatureSection() {
  const { t } = useI18n();
  const items = t("features.items");

  return (
    <section id="features" className="mx-auto mt-24 max-w-6xl px-4 sm:px-6">
      <div className="mb-10 text-center">
        <span className="section-badge">{t("features.badge")}</span>
        <h2 className="mt-4 text-3xl font-black tracking-tight text-ink-950 dark:text-slate-50 sm:text-5xl">
          {t("features.heading_1")}
          <span className="brand-text">{t("features.heading_2")}</span>
        </h2>
        <p className="mx-auto mt-4 max-w-2xl text-base leading-7 text-slate-500 dark:text-slate-400">{t("features.sub")}</p>
      </div>

      <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {items.map((f, i) => {
          const isPro = IS_PRO[i];
          return (
            <div key={f.title} className={`card group relative overflow-hidden p-6 hover:-translate-y-1 hover:shadow-glow ${i === 2 ? "lg:row-span-2 lg:p-7" : ""}`}>
              <div className="pointer-events-none absolute -right-12 -top-12 h-28 w-28 rounded-full bg-neon-200/60 blur-3xl transition group-hover:bg-accent-200/60" />
              <div className="mb-4 flex items-center justify-between">
                <span className="brand-gradient relative flex h-12 w-12 items-center justify-center rounded-2xl text-white shadow-lg shadow-accent-200/40 transition group-hover:-rotate-3 group-hover:scale-105">
                  <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="1.8">
                    {ICONS[i]}
                  </svg>
                </span>
                <span
                  className={`relative rounded-full px-3 py-1 text-xs font-black ${
                    isPro
                      ? "bg-gradient-to-r from-amber-400 to-orange-500 text-white"
                      : "bg-emerald-100 text-emerald-600 dark:bg-emerald-500/20 dark:text-emerald-300"
                  }`}
                >
                  {isPro ? t("features.pro") : t("features.free")}
                </span>
              </div>
              <h3 className="relative text-xl font-black text-ink-950 dark:text-slate-100">{f.title}</h3>
              <p className="relative mt-3 text-sm leading-7 text-slate-500 dark:text-slate-400">{f.desc}</p>
              {i === 2 && (
                <div className="relative mt-6 rounded-2xl bg-slate-50 p-4 dark:bg-ink-900/50">
                  <div className="mb-3 flex items-center justify-between text-xs font-black uppercase tracking-[0.16em] text-slate-400 dark:text-slate-500">
                    <span>AI Output</span>
                    <span className="text-brand-600">Live</span>
                  </div>
                  <div className="space-y-2">
                    <span className="block h-2 rounded-full bg-brand-200" />
                    <span className="block h-2 w-4/5 rounded-full bg-neon-200" />
                    <span className="block h-2 w-2/3 rounded-full bg-accent-200" />
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
