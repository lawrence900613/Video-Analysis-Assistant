import { useI18n } from "../i18n.jsx";

export default function PricingSection() {
  const { t } = useI18n();
  const plans = t("pricing.plans");
  const features = t("pricing.features");

  return (
    <section id="pricing" className="mx-auto mt-24 max-w-6xl px-4 sm:px-6">
      <div className="mb-10 text-center">
        <span className="section-badge">{t("pricing.badge")}</span>
        <h2 className="mt-4 text-3xl font-black tracking-tight text-ink-950 dark:text-slate-50 sm:text-5xl">
          {t("pricing.heading_1")}
          <span className="brand-text">{t("pricing.heading_2")}</span>
        </h2>
        <p className="mx-auto mt-4 max-w-2xl text-base leading-7 text-slate-500 dark:text-slate-400">{t("pricing.sub")}</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {plans.map((plan) => (
          <div
            key={plan.name}
            className={`relative overflow-hidden rounded-[2rem] p-6 transition duration-300 sm:p-8 ${
              plan.highlight
                ? "dark-panel hover:-translate-y-1"
                : "card hover:-translate-y-1 hover:shadow-glow"
            }`}
          >
            <div className="pointer-events-none absolute -right-10 -top-10 h-32 w-32 rounded-full bg-neon-300/20 blur-3xl" />
            {plan.highlight && (
              <span className="absolute right-4 top-4 rounded-full bg-gradient-to-r from-amber-400 to-orange-500 px-3 py-1 text-xs font-black text-white">
                {t("pricing.popular")}
              </span>
            )}
            <h3 className={`relative text-xl font-black ${plan.highlight ? "text-white" : "text-ink-950 dark:text-slate-100"}`}>{plan.name}</h3>
            <div className="mt-2 flex items-baseline gap-1">
              <span className={`relative text-5xl font-black tracking-tight ${plan.highlight ? "text-white" : "text-ink-950 dark:text-slate-100"}`}>{plan.price}</span>
              {plan.period && <span className={`relative text-sm font-bold ${plan.highlight ? "text-white/55" : "text-slate-500 dark:text-slate-400"}`}>{plan.period}</span>}
            </div>
            <p className={`relative mt-3 text-sm leading-6 ${plan.highlight ? "text-white/65" : "text-slate-500 dark:text-slate-400"}`}>{plan.desc}</p>

            <ul className="relative mt-6 space-y-3">
              {features.map((f, i) => {
                const included = plan.included[i];
                return (
                  <li key={f} className="flex items-center gap-2.5 text-sm">
                    {included ? (
                      <CheckIcon className={plan.highlight ? "text-neon-300" : "text-emerald-500"} />
                    ) : (
                      <CrossIcon className="text-slate-300" />
                    )}
                    <span className={included ? (plan.highlight ? "font-semibold text-white/85" : "font-semibold text-slate-700 dark:text-slate-200") : "text-slate-400 dark:text-slate-500"}>{f}</span>
                  </li>
                );
              })}
            </ul>

            <a
              href={plan.highlight ? "#home" : "#home"}
              className={`relative mt-8 block w-full rounded-2xl py-3 text-center text-sm font-black transition ${
                plan.highlight
                  ? "bg-white text-ink-950 shadow-xl shadow-white/10 hover:-translate-y-0.5"
                  : "border-2 border-slate-200 bg-white text-slate-700 hover:border-brand-300 hover:text-brand-700 dark:border-white/10 dark:bg-ink-900/80 dark:text-slate-200 dark:hover:border-brand-400/40 dark:hover:text-brand-300"
              }`}
            >
              {plan.cta}
            </a>
          </div>
        ))}
      </div>

      <p className="mt-6 text-center text-xs font-bold uppercase tracking-[0.14em] text-slate-400 dark:text-slate-500">{t("pricing.note")}</p>
    </section>
  );
}

function CheckIcon({ className }) {
  return (
    <svg viewBox="0 0 24 24" className={`h-5 w-5 shrink-0 ${className}`} fill="none" stroke="currentColor" strokeWidth="2.5">
      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
    </svg>
  );
}

function CrossIcon({ className }) {
  return (
    <svg viewBox="0 0 24 24" className={`h-5 w-5 shrink-0 ${className}`} fill="none" stroke="currentColor" strokeWidth="2">
      <path strokeLinecap="round" d="M6 18L18 6M6 6l12 12" />
    </svg>
  );
}
