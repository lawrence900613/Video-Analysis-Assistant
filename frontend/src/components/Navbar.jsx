import { useI18n } from "../i18n.jsx";

export default function Navbar() {
  const { t, toggle } = useI18n();

  const links = [
    { label: t("nav.home"), href: "#home" },
    { label: t("nav.platforms"), href: "#platforms" },
    { label: t("nav.features"), href: "#features" },
    { label: t("nav.faq"), href: "#faq" },
  ];

  return (
    <header className="sticky top-0 z-50 border-b border-slate-100 bg-white/80 backdrop-blur-lg">
      <nav className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
        <a href="#home" className="flex items-center gap-2">
          <span className="brand-gradient flex h-9 w-9 items-center justify-center rounded-xl text-white shadow-md shadow-indigo-200">
            <svg viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor">
              <path d="M8 5v14l11-7z" />
            </svg>
          </span>
          <span className="hidden text-base font-extrabold tracking-tight sm:inline">
            Video <span className="brand-text">Analysis</span> Assistant
          </span>
        </a>

        <div className="hidden items-center gap-8 md:flex">
          {links.map((l) => (
            <a
              key={l.href}
              href={l.href}
              className="text-sm font-medium text-slate-600 transition hover:text-indigo-600"
            >
              {l.label}
            </a>
          ))}
        </div>

        <div className="flex items-center gap-2 sm:gap-3">
          <button
            onClick={toggle}
            aria-label="切换语言 / Switch language"
            className="flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-600 transition hover:border-indigo-300 hover:text-indigo-600"
          >
            <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="9" />
              <path strokeLinecap="round" d="M3 12h18M12 3c2.5 2.7 2.5 15.3 0 18M12 3c-2.5 2.7-2.5 15.3 0 18" />
            </svg>
            {t("lang_switch")}
          </button>
          <a
            href="#pricing"
            className="brand-gradient rounded-full px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-indigo-200 transition hover:scale-105 hover:shadow-indigo-300 sm:px-5"
          >
            {t("nav.pro")}
          </a>
        </div>
      </nav>
    </header>
  );
}
