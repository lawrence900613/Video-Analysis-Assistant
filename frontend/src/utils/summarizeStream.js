const BASE = "/api";

/**
 * Parse SSE stream from fetch ReadableStream.
 * Yields { event, data } objects.
 */
export async function* streamSummarize(
  url,
  { preferLang, outputLang, forceRefresh, signal } = {},
) {
  const body = { url, output_lang: outputLang || "English" };
  if (preferLang) body.prefer_lang = preferLang;
  if (forceRefresh) body.force_refresh = true;

  const res = await fetch(`${BASE}/summarize`, {
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

  const reader = res.body?.getReader();
  if (!reader) throw new Error("Streaming not supported");

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const blocks = buffer.split("\n\n");
    buffer = blocks.pop() || "";

    for (const block of blocks) {
      const parsed = parseSseBlock(block);
      if (parsed) yield parsed;
    }
  }

  if (buffer.trim()) {
    const parsed = parseSseBlock(buffer);
    if (parsed) yield parsed;
  }
}

function parseSseBlock(block) {
  let event = "message";
  const dataLines = [];

  for (const line of block.split("\n")) {
    if (line.startsWith("event:")) {
      event = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trim());
    }
  }

  if (!dataLines.length) return null;

  const raw = dataLines.join("\n");
  try {
    return { event, data: JSON.parse(raw) };
  } catch {
    return { event, data: raw };
  }
}
