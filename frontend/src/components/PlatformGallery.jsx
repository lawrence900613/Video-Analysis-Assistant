import { useI18n } from "../i18n.jsx";

const STYLES = [
  { from: "from-red-500", to: "to-rose-600", initial: "YT", tag: "hot", href: "https://www.youtube.com/" },
  { from: "from-sky-400", to: "to-cyan-500", initial: "B", tag: null, href: "https://www.bilibili.com/" },
  {
    from: "from-slate-800",
    to: "to-slate-900",
    initial: "TT",
    tag: null,
    hrefByLang: {
      zh: "https://www.douyin.com/",
      en: "https://www.tiktok.com/",
    },
  },
  { from: "from-purple-600", to: "to-violet-700", initial: "TW", tag: null, href: "https://www.twitch.tv/" },
  { from: "from-slate-700", to: "to-black", initial: "X", tag: null, href: "https://x.com/" },
  { from: "from-fuchsia-500", to: "to-pink-600", initial: "IG", tag: null, href: "https://www.instagram.com/" },
  { from: "from-rose-400", to: "to-red-500", initial: "XHS", tag: "new", href: "https://www.xiaohongshu.com/" },
  {
    from: "from-indigo-500",
    to: "to-violet-600",
    initial: "+",
    tag: null,
    href: "https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md",
  },
];

function resolveHref(style, lang) {
  if (style.hrefByLang) {
    return style.hrefByLang[lang] || style.hrefByLang.en;
  }
  return style.href;
}

export default function PlatformGallery() {
  const { t, lang } = useI18n();
  const items = t("platforms.items");

  return (
    <section id="platforms" className="mx-auto mt-20 max-w-6xl px-4 sm:px-6">
      <div className="mb-10 text-center">
        <span className="section-badge">{t("platforms.badge")}</span>
        <h2 className="mt-4 text-3xl font-black tracking-tight text-ink-950 dark:text-slate-50 sm:text-5xl">
          {t("platforms.heading_1")}
          <span className="brand-text">{t("platforms.heading_2")}</span>
        </h2>
        <p className="mx-auto mt-4 max-w-2xl text-base leading-7 text-slate-500 dark:text-slate-400">{t("platforms.sub")}</p>
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
        {items.map((p, i) => {
          const s = STYLES[i] || STYLES[STYLES.length - 1];
          return (
            <a
              key={p.name}
              href={resolveHref(s, lang)}
              target="_blank"
              rel="noopener noreferrer"
              className="card group relative block min-h-40 overflow-hidden p-5 transition hover:-translate-y-1 hover:shadow-glow"
            >
              <div className="pointer-events-none absolute -right-10 -top-10 h-24 w-24 rounded-full bg-brand-100 opacity-0 blur-2xl transition group-hover:opacity-100" />
              {s.tag === "hot" && (
                <span className="absolute right-3 top-3 rounded-full bg-accent-500 px-2 py-1 text-[10px] font-black text-white">
                  HOT
                </span>
              )}
              {s.tag === "new" && (
                <span className="absolute right-3 top-3 rounded-full bg-emerald-500 px-2 py-1 text-[10px] font-black text-white">
                  NEW
                </span>
              )}
              <div
                className={`relative mb-5 flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br ${s.from} ${s.to} text-sm font-black text-white shadow-lg transition group-hover:scale-110 group-hover:-rotate-3`}
              >
                {s.initial}
              </div>
              <h3 className="relative font-black text-ink-950 dark:text-slate-100">{p.name}</h3>
              <p className="relative mt-2 text-sm leading-6 text-slate-500 dark:text-slate-400">{p.desc}</p>
            </a>
          );
        })}
      </div>
    </section>
  );
}
