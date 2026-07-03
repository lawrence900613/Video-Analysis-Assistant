import { useI18n } from "../i18n.jsx";

const STYLES = [
  { from: "from-red-500", to: "to-rose-600", initial: "YT", tag: "hot" },
  { from: "from-sky-400", to: "to-cyan-500", initial: "B", tag: null },
  { from: "from-slate-800", to: "to-slate-900", initial: "TT", tag: null },
  { from: "from-purple-600", to: "to-violet-700", initial: "TW", tag: null },
  { from: "from-slate-700", to: "to-black", initial: "X", tag: null },
  { from: "from-fuchsia-500", to: "to-pink-600", initial: "IG", tag: null },
  { from: "from-rose-400", to: "to-red-500", initial: "XHS", tag: "new" },
  { from: "from-indigo-500", to: "to-violet-600", initial: "+", tag: null },
];

export default function PlatformGallery() {
  const { t } = useI18n();
  const items = t("platforms.items");

  return (
    <section id="platforms" className="mx-auto mt-20 max-w-6xl px-4 sm:px-6">
      <div className="mb-10 text-center">
        <span className="section-badge">{t("platforms.badge")}</span>
        <h2 className="mt-3 text-3xl font-extrabold text-slate-900 sm:text-4xl">
          {t("platforms.heading_1")}
          <span className="brand-text">{t("platforms.heading_2")}</span>
        </h2>
        <p className="mx-auto mt-3 max-w-xl text-slate-500">{t("platforms.sub")}</p>
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
        {items.map((p, i) => {
          const s = STYLES[i] || STYLES[STYLES.length - 1];
          return (
            <div
              key={p.name}
              className="card group relative cursor-default overflow-hidden p-5 hover:-translate-y-1 hover:shadow-lg hover:shadow-indigo-100"
            >
              {s.tag === "hot" && (
                <span className="absolute right-3 top-3 rounded bg-red-500 px-1.5 py-0.5 text-[10px] font-bold text-white">
                  HOT
                </span>
              )}
              {s.tag === "new" && (
                <span className="absolute right-3 top-3 rounded bg-emerald-500 px-1.5 py-0.5 text-[10px] font-bold text-white">
                  NEW
                </span>
              )}
              <div
                className={`mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br ${s.from} ${s.to} text-sm font-bold text-white shadow-md transition group-hover:scale-110`}
              >
                {s.initial}
              </div>
              <h3 className="font-bold text-slate-800">{p.name}</h3>
              <p className="mt-1 text-sm text-slate-500">{p.desc}</p>
            </div>
          );
        })}
      </div>
    </section>
  );
}
