/** Preferred subtitle codes per UI locale (most specific first). */
const LOCALE_PREF_ORDER = {
  en: ["en-US", "en-GB", "en-AU", "en-CA", "en-IN", "en"],
  zh: ["zh-Hans", "zh-CN", "zh-Hant", "zh-TW", "zh-HK", "zh-SG", "zh"],
};

/**
 * Pick a default subtitle language from available tracks based on UI locale.
 * Falls back to the first available language when no locale match exists.
 */
export function pickDefaultSubtitleLang(availableLangs, uiLang = "en") {
  if (!availableLangs?.length) return "";

  const order = LOCALE_PREF_ORDER[uiLang] || LOCALE_PREF_ORDER.en;
  for (const pref of order) {
    if (availableLangs.includes(pref)) return pref;
  }

  const prefix = uiLang === "zh" ? "zh" : "en";
  const prefixMatch = availableLangs.find((code) =>
    code.toLowerCase().split("-")[0] === prefix,
  );
  if (prefixMatch) return prefixMatch;

  return availableLangs[0];
}
