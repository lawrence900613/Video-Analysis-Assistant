const BASE = "/api";

async function postJSON(path, body) {
  const res = await fetch(BASE + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
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
  return res;
}

function triggerBrowserDownload(url) {
  const a = document.createElement("a");
  a.href = url;
  a.style.display = "none";
  document.body.appendChild(a);
  a.click();
  a.remove();
}

function triggerDownload(blob, filename) {
  const objectUrl = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = objectUrl;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  // Chrome/Edge write blob downloads as {uuid}.tmp; revoking too early orphans them.
  window.setTimeout(() => window.URL.revokeObjectURL(objectUrl), 60_000);
}

function sleep(ms, signal) {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(new DOMException("Aborted", "AbortError"));
      return;
    }
    const timer = window.setTimeout(resolve, ms);
    signal?.addEventListener(
      "abort",
      () => {
        window.clearTimeout(timer);
        reject(new DOMException("Aborted", "AbortError"));
      },
      { once: true },
    );
  });
}

export class DownloadCancelledError extends Error {
  constructor(message = "Download cancelled") {
    super(message);
    this.name = "DownloadCancelledError";
  }
}

export async function parseVideo(url) {
  const res = await postJSON("/parse", { url });
  return res.json();
}

export async function summarizeVideo(url, outputLang = "English") {
  const res = await postJSON("/summary", { url, output_lang: outputLang });
  return res.json();
}

export function downloadUrl() {
  return BASE + "/download";
}

export async function cancelDownload(jobId) {
  const res = await fetch(`${BASE}/download/${jobId}/cancel`, { method: "POST" });
  if (!res.ok) {
    let detail = `Cancel failed (${res.status})`;
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

/** Download video with optional progress callback. Supports cancellation via signal. */
export async function downloadVideo(url, formatId, { onProgress, onFilename, signal } = {}) {
  const startRes = await postJSON("/download/start", { url, format_id: formatId });
  const { job_id: jobId } = await startRes.json();

  if (signal?.aborted) {
    await cancelDownload(jobId).catch(() => {});
    throw new DownloadCancelledError();
  }

  let filename = "video.mp4";
  try {
    while (true) {
      if (signal?.aborted) {
        await cancelDownload(jobId).catch(() => {});
        throw new DownloadCancelledError();
      }

      const progRes = await fetch(`${BASE}/download/${jobId}/progress`, { signal });
      if (!progRes.ok) {
        let detail = `Progress check failed (${progRes.status})`;
        try {
          const data = await progRes.json();
          if (data.detail) detail = data.detail;
        } catch {
          /* ignore */
        }
        throw new Error(detail);
      }

      const prog = await progRes.json();
      if (prog.cancelled || prog.stage === "cancelled") {
        throw new DownloadCancelledError();
      }
      if (onProgress) {
        onProgress({
          stage: prog.stage,
          percent: prog.percent,
          speed_bps: prog.speed_bps ?? null,
          eta_seconds: prog.eta_seconds ?? null,
        });
      }
      if (prog.error) throw new Error(prog.error);
      if (prog.ready) {
        filename = prog.filename || filename;
        break;
      }
      await sleep(400, signal);
    }
  } catch (e) {
    if (e instanceof DownloadCancelledError) throw e;
    if (e?.name === "AbortError" || signal?.aborted) {
      await cancelDownload(jobId).catch(() => {});
      throw new DownloadCancelledError();
    }
    throw e;
  }

  if (signal?.aborted) {
    await cancelDownload(jobId).catch(() => {});
    throw new DownloadCancelledError();
  }

  if (onFilename) onFilename(filename);
  if (onProgress) {
    onProgress({
      stage: "transferring",
      percent: null,
      speed_bps: null,
      eta_seconds: null,
    });
  }

  // Let the browser save via Content-Disposition instead of fetch→blob→objectURL,
  // which leaves orphaned {uuid}.tmp files in Downloads on Chrome/Edge (Windows).
  triggerBrowserDownload(`${BASE}/download/${jobId}/file`);
  return filename;
}

/** Download original subtitles as SRT. */
export async function downloadSubtitles(url, preferLang) {
  const body = { url };
  if (preferLang) body.prefer_lang = preferLang;
  const res = await postJSON("/subtitles", body);
  const text = await res.text();
  const lang = res.headers.get("X-Subtitle-Lang") || preferLang || "sub";
  triggerDownload(new Blob([text], { type: "application/x-subrip" }), `subtitle_${lang}.srt`);
  return { lang, isAuto: res.headers.get("X-Subtitle-Auto") === "1" };
}

/** Translate subtitles: return SRT text and trigger download. */
export async function translateSubtitle(url, targetLang, preferLang) {
  const body = { url, target_lang: targetLang };
  if (preferLang) body.prefer_lang = preferLang;
  const res = await postJSON("/translate", body);
  const text = await res.text();
  triggerDownload(new Blob([text], { type: "application/x-subrip" }), "subtitle.srt");
  return text;
}

export async function health() {
  const res = await fetch(BASE + "/health");
  if (!res.ok) {
    throw new Error(`Health check failed (${res.status})`);
  }
  return res.json();
}

/** Parse SSE stream from POST /api/summarize; yields { event, data }. */
export async function* streamSummarize(url, { preferLang, outputLang, forceRefresh, signal } = {}) {
  const body = { url, output_lang: outputLang || "English" };
  if (preferLang) body.prefer_lang = preferLang;
  if (forceRefresh) body.force_refresh = true;

  const res = await fetch(BASE + "/summarize", {
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

    const parts = buffer.split("\n\n");
    buffer = parts.pop() || "";

    for (const part of parts) {
      if (!part.trim()) continue;
      let event = "message";
      let dataStr = "";
      for (const line of part.split("\n")) {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        else if (line.startsWith("data:")) dataStr += line.slice(5).trim();
      }
      if (!dataStr) continue;
      let data;
      try {
        data = JSON.parse(dataStr);
      } catch {
        data = { raw: dataStr };
      }
      yield { event, data };
    }
  }
}

export async function fetchTranscript(url, preferLang) {
  const body = { url };
  if (preferLang) body.prefer_lang = preferLang;
  const res = await postJSON("/transcript", body);
  return res.json();
}
