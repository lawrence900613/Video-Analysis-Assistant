const TTL_MS = 24 * 60 * 60 * 1000;

function hashUrl(url) {
  let h = 0;
  for (let i = 0; i < url.length; i++) {
    h = (Math.imul(31, h) + url.charCodeAt(i)) | 0;
  }
  return Math.abs(h).toString(36);
}

function cacheKey(url, preferLang) {
  return `analysis:${hashUrl(url)}:${preferLang || ""}`;
}

export function loadAnalysisCache(url, preferLang) {
  try {
    const raw = localStorage.getItem(cacheKey(url, preferLang));
    if (!raw) return null;
    const entry = JSON.parse(raw);
    if (!entry?.savedAt || !entry?.result) return null;
    if (Date.now() - entry.savedAt > TTL_MS) {
      localStorage.removeItem(cacheKey(url, preferLang));
      return null;
    }
    return entry.result;
  } catch {
    return null;
  }
}

export function saveAnalysisCache(url, preferLang, result) {
  try {
    localStorage.setItem(
      cacheKey(url, preferLang),
      JSON.stringify({ savedAt: Date.now(), result }),
    );
  } catch {
    /* quota exceeded — ignore */
  }
}

export function clearAnalysisCache(url, preferLang) {
  try {
    localStorage.removeItem(cacheKey(url, preferLang));
  } catch {
    /* ignore */
  }
}
