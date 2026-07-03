import { useState } from "react";
import { useI18n } from "../i18n.jsx";

export default function FaqSection() {
  const { t } = useI18n();
  const items = t("faq.items");
  const [open, setOpen] = useState(0);

  return (
    <section id="faq" className="mx-auto mt-16 max-w-3xl px-4 sm:px-6">
      <div className="mb-8 text-center">
        <span className="section-badge">{t("faq.badge")}</span>
        <h2 className="mt-3 text-2xl font-extrabold text-slate-900 sm:text-3xl">{t("faq.heading")}</h2>
      </div>

      <div className="space-y-3">
        {items.map((item, i) => {
          const isOpen = open === i;
          return (
            <div key={item.q} className="card overflow-hidden">
              <button
                type="button"
                onClick={() => setOpen(isOpen ? -1 : i)}
                className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left"
              >
                <span className="text-sm font-semibold text-slate-800 sm:text-base">{item.q}</span>
                <svg
                  viewBox="0 0 24 24"
                  className={`h-5 w-5 shrink-0 text-slate-400 transition ${isOpen ? "rotate-180" : ""}`}
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <path strokeLinecap="round" d="M6 9l6 6 6-6" />
                </svg>
              </button>
              {isOpen && (
                <div className="border-t border-slate-100 px-5 py-4 text-sm leading-relaxed text-slate-600">
                  {item.a}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
