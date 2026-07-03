/**
 * Best-effort parse of in-progress streamed Markdown into VideoSummary fields.
 * Mirrors backend ai.parse_markdown_to_summary for incremental UI rendering.
 */
export function parsePartialSummary(md) {
  const text = (md || "").trim();
  if (!text) {
    return { tldr: "", key_points: [], chapters: [] };
  }

  let tldr = "";
  const keyPoints = [];
  const chapters = [];

  const tldrMatch = text.match(
    /(?:^|\n)#+\s*(?:TL;DR|tl;dr|一句话总结|总结)\s*\n+([\s\S]*?)(?=\n#|\n##|$)/i,
  );
  if (tldrMatch) {
    tldr = tldrMatch[1].trim().split("\n")[0].trim();
  } else {
    for (const line of text.split("\n")) {
      const stripped = line.trim();
      if (stripped && !stripped.startsWith("#") && !stripped.startsWith("-") && !stripped.startsWith("*")) {
        tldr = stripped;
        break;
      }
    }
  }

  let inKeyPoints = false;
  for (const line of text.split("\n")) {
    const stripped = line.trim();
    if (/^#+\s*(?:key points|核心要点|要点)/i.test(stripped)) {
      inKeyPoints = true;
      continue;
    }
    if (stripped.startsWith("##") && !/\[[\d:]+\]/.test(stripped)) {
      inKeyPoints = false;
    }
    if (inKeyPoints) {
      const m = stripped.match(/^[-*]\s+(.+)$/);
      if (m) keyPoints.push(m[1].trim());
    }
  }

  if (!keyPoints.length) {
    for (const m of text.matchAll(/^[-*]\s+(.+)$/gm)) {
      const pt = m[1].trim();
      if (pt && !/^\[[\d:]+\]/.test(pt)) keyPoints.push(pt);
    }
  }

  const chapterRe = /^##+\s*(?:\[([^\]]+)\]\s*)?(.+?)\s*$/gm;
  const matches = [...text.matchAll(chapterRe)];
  for (let i = 0; i < matches.length; i++) {
    const m = matches[i];
    const startLabel = (m[1] || "").trim();
    const titleText = m[2].trim();
    if (/^(?:key points|tldr|核心要点|要点|一句话总结|总结)$/i.test(titleText)) continue;

    const startPos = m.index + m[0].length;
    const endPos = i + 1 < matches.length ? matches[i + 1].index : text.length;
    const body = text.slice(startPos, endPos).trim();
    const bodyLines = body
      .split("\n")
      .map((ln) => ln.trim())
      .filter((ln) => ln && !ln.startsWith("#"));
    chapters.push({
      title: titleText,
      summary: bodyLines.slice(0, 3).join(" ").trim(),
      start_label: startLabel,
    });
  }

  return {
    tldr,
    key_points: keyPoints.slice(0, 6),
    chapters,
  };
}
