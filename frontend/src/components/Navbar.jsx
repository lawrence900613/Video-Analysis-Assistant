import { useState } from "react";
import { useI18n } from "../i18n.jsx";

export default function Navbar() {
  const { t, toggle } = useI18n();
  const [menuOpen, setMenuOpen] = useState(false);

  const links = [
    { label: t("nav.home"), href: "#home" },
    { label: t("nav.platforms"), href: "#platforms" },
    { label: t("nav.features"), href: "#features" },
    { label: t("nav.faq"), href: "#faq" },
  ];

  return (
    <header className="sticky top-0 z-50 border-b border-white/70 bg-white/75 backdrop-blur-2xl">
      <nav className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
        <a href="#home" className="group flex items-center gap-2.5">
          <span className="brand-gradient flex h-10 w-10 items-center justify-center rounded-2xl text-white shadow-lg shadow-accent-200/50 transition group-hover:-rotate-3 group-hover:scale-105">
            <svg viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor">
              <path d="M8 5v14l11-7z" />
            </svg>
          </span>
          <span className="hidden leading-tight sm:block">
            <span className="block text-[11px] font-black uppercase tracking-[0.28em] text-slate-400">AI Video</span>
            <span className="text-base font-black tracking-tight text-ink-950">
              Analysis <span className="brand-text">Assistant</span>
            </span>
          </span>
        </a>

        <div className="hidden items-center gap-1 rounded-full border border-slate-200/70 bg-white/70 p-1 shadow-sm lg:flex">
          {links.map((l) => (
            <a
              key={l.href}
              href={l.href}
              className="rounded-full px-4 py-2 text-sm font-bold text-slate-600 transition hover:bg-brand-50 hover:text-brand-700"
            >
              {l.label}
            </a>
          ))}
        </div>

        <div className="flex items-center gap-2 sm:gap-3">
          <button
            onClick={toggle}
            aria-label="Switch language"
            className="flex items-center gap-1.5 rounded-full border border-slate-200/80 bg-white/80 px-3 py-2 text-sm font-bold text-slate-600 shadow-sm transition hover:border-brand-300 hover:text-brand-700"
          >
            <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="9" />
              <path strokeLinecap="round" d="M3 12h18M12 3c2.5 2.7 2.5 15.3 0 18M12 3c-2.5 2.7-2.5 15.3 0 18" />
            </svg>
            <span className="hidden sm:inline">{t("lang_switch")}</span>
          </button>
          <a
            href="#pricing"
            className="hidden premium-button rounded-full px-5 py-2.5 sm:inline-flex"
          >
            {t("nav.pro")}
          </a>
          <button
            type="button"
            onClick={() => setMenuOpen((o) => !o)}
            aria-label="Menu"
            className="rounded-xl border border-slate-200/70 bg-white/80 p-2 text-slate-600 shadow-sm transition hover:bg-brand-50 lg:hidden"
          >
            <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="2">
              {menuOpen ? (
                <path strokeLinecap="round" d="M6 18L18 6M6 6l12 12" />
              ) : (
                <path strokeLinecap="round" d="M4 6h16M4 12h16M4 18h16" />
              )}
            </svg>
          </button>
        </div>
      </nav>

      {menuOpen && (
        <div className="border-t border-slate-100 bg-white/95 px-4 py-3 shadow-xl shadow-slate-900/5 backdrop-blur-xl lg:hidden">
          {links.map((l) => (
            <a
              key={l.href}
              href={l.href}
              onClick={() => setMenuOpen(false)}
              className="block rounded-xl px-3 py-2.5 text-sm font-bold text-slate-700 hover:bg-brand-50 hover:text-brand-700"
            >
              {l.label}
            </a>
          ))}
          <a
            href="#pricing"
            onClick={() => setMenuOpen(false)}
            className="mt-2 block rounded-xl brand-gradient px-3 py-2.5 text-center text-sm font-black text-white shadow-lg shadow-accent-200/50"
          >
            {t("nav.pro")}
          </a>
        </div>
      )}
    </header>
  );
}
