const BASE = "/api";

async function postJSON(path, body) {
  const res = await fetch(BASE + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    let detail = `请求失败 (${res.status})`;
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

export async function parseVideo(url) {
  const res = await postJSON("/parse", { url });
  return res.json();
}

export async function summarizeVideo(url) {
  const res = await postJSON("/summary", { url });
  return res.json();
}

export function downloadUrl() {
  return BASE + "/download";
}

/** 下载视频：通过 fetch 拿到 blob 再触发浏览器保存，便于展示进度/错误。 */
export async function downloadVideo(url, formatId, onFilename) {
  const res = await postJSON("/download", { url, format_id: formatId });
  const disposition = res.headers.get("Content-Disposition") || "";
  let filename = "video";
  const match = disposition.match(/filename="?([^"]+)"?/);
  if (match) filename = decodeURIComponent(match[1]);
  if (onFilename) onFilename(filename);
  const blob = await res.blob();
  const objectUrl = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = objectUrl;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(objectUrl);
}

/** 翻译字幕：返回 SRT 文本并触发下载。 */
export async function translateSubtitle(url, targetLang) {
  const res = await postJSON("/translate", { url, target_lang: targetLang });
  const text = await res.text();
  const blob = new Blob([text], { type: "application/x-subrip" });
  const objectUrl = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = objectUrl;
  a.download = "subtitle.srt";
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(objectUrl);
  return text;
}

export async function health() {
  const res = await fetch(BASE + "/health");
  return res.json();
}
