import { useI18n } from "../i18n.jsx";

export default function PricingSection() {
  const { t } = useI18n();
  const plans = t("pricing.plans");
  const features = t("pricing.features");

  return (
    <section id="pricing" className="mx-auto mt-24 max-w-6xl px-4 sm:px-6">
      <div className="mb-10 text-center">
        <span className="section-badge">{t("pricing.badge")}</span>
        <h2 className="mt-3 text-3xl font-extrabold text-slate-900 sm:text-4xl">
          {t("pricing.heading_1")}
          <span className="brand-text">{t("pricing.heading_2")}</span>
        </h2>
        <p className="mx-auto mt-3 max-w-xl text-slate-500">{t("pricing.sub")}</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {plans.map((plan) => (
          <div
            key={plan.name}
            className={`card relative overflow-hidden p-6 sm:p-8 ${
              plan.highlight
                ? "ring-2 ring-indigo-400 shadow-xl shadow-indigo-100"
                : "hover:shadow-lg hover:shadow-slate-100"
            }`}
          >
            {plan.highlight && (
              <span className="absolute right-4 top-4 rounded-full bg-gradient-to-r from-amber-400 to-orange-500 px-3 py-1 text-xs font-bold text-white">
                {t("pricing.popular")}
              </span>
            )}
            <h3 className="text-xl font-bold text-slate-900">{plan.name}</h3>
            <div className="mt-2 flex items-baseline gap-1">
              <span className="text-4xl font-extrabold text-slate-900">{plan.price}</span>
              {plan.period && <span className="text-sm text-slate-500">{plan.period}</span>}
            </div>
            <p className="mt-2 text-sm text-slate-500">{plan.desc}</p>

            <ul className="mt-6 space-y-3">
              {features.map((f, i) => {
                const included = plan.included[i];
                return (
                  <li key={f} className="flex items-center gap-2.5 text-sm">
                    {included ? (
                      <CheckIcon className="text-emerald-500" />
                    ) : (
                      <CrossIcon className="text-slate-300" />
                    )}
                    <span className={included ? "text-slate-700" : "text-slate-400"}>{f}</span>
                  </li>
                );
              })}
            </ul>

            <a
              href={plan.highlight ? "#home" : "#home"}
              className={`mt-8 block w-full rounded-xl py-3 text-center text-sm font-bold transition ${
                plan.highlight
                  ? "brand-gradient text-white shadow-lg shadow-indigo-200 hover:scale-[1.02]"
                  : "border-2 border-slate-200 bg-white text-slate-700 hover:border-indigo-300 hover:text-indigo-600"
              }`}
            >
              {plan.cta}
            </a>
          </div>
        ))}
      </div>

      <p className="mt-6 text-center text-xs text-slate-400">{t("pricing.note")}</p>
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
