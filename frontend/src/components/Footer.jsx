import { useI18n } from "../i18n.jsx";

export default function Footer() {
  const { t } = useI18n();

  return (
    <footer id="faq" className="mt-24 border-t border-slate-100 bg-white/60">
      <div className="mx-auto max-w-6xl px-4 py-12 sm:px-6">
        <div className="grid gap-10 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="brand-gradient flex h-8 w-8 items-center justify-center rounded-lg text-white">
                <svg viewBox="0 0 24 24" className="h-4 w-4" fill="currentColor"><path d="M8 5v14l11-7z" /></svg>
              </span>
              <span className="text-base font-extrabold">Video <span className="brand-text">Analysis</span> Assistant</span>
            </div>
            <p className="mt-3 max-w-xs text-sm text-slate-500">{t("footer.brand_desc")}</p>
          </div>

          <FooterCol title={t("footer.col_faq")} items={t("footer.faq_items")} />
          <FooterCol title={t("footer.col_features")} items={t("footer.feature_items")} />
          <FooterCol title={t("footer.col_about")} items={t("footer.about_items")} />
        </div>

        <div className="mt-10 border-t border-slate-100 pt-6 text-center text-xs text-slate-400">
          <p>{t("footer.legal")}</p>
          <p className="mt-2">© {new Date().getFullYear()} {t("footer.copyright")}</p>
        </div>
      </div>
    </footer>
  );
}

function FooterCol({ title, items }) {
  return (
    <div>
      <h4 className="text-sm font-bold text-slate-700">{title}</h4>
      <ul className="mt-3 space-y-2">
        {items.map((it) => (
          <li key={it}>
            <a href="#" className="text-sm text-slate-500 transition hover:text-indigo-600">{it}</a>
          </li>
        ))}
      </ul>
    </div>
  );
}
