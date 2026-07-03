const BASE = "/api";

/** POST /api/mindmap — LLM-generated mind map JSON + markdown. */
export async function fetchMindmap(
  url,
  { summary, transcript, preferLang, outputLang, signal } = {},
) {
  const body = { url, output_lang: outputLang || "English" };
  if (preferLang) body.prefer_lang = preferLang;
  if (summary) body.summary = summary;
  if (transcript) body.transcript = transcript;

  const res = await fetch(`${BASE}/mindmap`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });

  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const data = await res.json();
      if (data.detail) detail = data.detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }

  return res.json();
}
