/**
 * Flow step for the hero progress indicator (1–4).
 * 1: URL entered · 2: parsing · 3: result shown · 4: download active/done
 */
export function computeFlowStep({ url, loading, result, downloading, downloaded }) {
  if (downloading || downloaded) return 4;
  if (result) return 3;
  if (loading) return 2;
  if (url.trim()) return 1;
  return 1;
}

/** Format bytes/sec as human-readable speed (e.g. "2.4 MB/s"). */
export function formatSpeed(bps) {
  if (bps == null || bps <= 0 || !Number.isFinite(bps)) return null;
  const mb = bps / (1024 * 1024);
  if (mb >= 0.1) return `${mb.toFixed(1)} MB/s`;
  const kb = bps / 1024;
  if (kb >= 1) return `${Math.round(kb)} KB/s`;
  return `${Math.round(bps)} B/s`;
}

/** Format ETA seconds with i18n templates. Returns null when unknown. */
export function formatEta(seconds, t) {
  if (seconds == null || seconds < 0 || !Number.isFinite(seconds)) return null;
  if (seconds < 60) {
    return t("result.progress_eta_seconds").replace("{n}", String(Math.round(seconds)));
  }
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  const time = `${m}:${String(s).padStart(2, "0")}`;
  return t("result.progress_eta_remaining").replace("{time}", time);
}
