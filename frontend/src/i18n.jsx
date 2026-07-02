import { createContext, useCallback, useContext, useEffect, useState } from "react";

export const translations = {
  zh: {
    nav: { home: "首页", platforms: "热门平台", features: "功能", faq: "常见问题", pro: "升级 Pro" },
    hero: {
      badge: "支持 1000+ 平台 · 高清无水印 · 手机可用",
      title_pre: "随时随地，",
      title_highlight: "一键下载",
      title_post: "任意视频",
      sub_1: "粘贴链接即可极速下载。告别平台限制，支持批量清晰度选择、",
      sub_ai: "AI 视频总结",
      sub_2: "与",
      sub_translate: "字幕翻译",
      sub_3: "。",
      placeholder: "粘贴视频链接，例如 https://www.youtube.com/watch?v=...",
      parse: "立即解析",
      parsing: "解析中",
      empty_url: "请输入视频链接",
    },
    result: {
      no_thumb: "无封面",
      has_subtitles: "含字幕",
      select_quality: "选择清晰度 / 格式",
      quality_best: "最佳画质（自动）",
      quality_audio: "仅音频",
      quality_merge: "(合流)",
      quality_default: "默认画质",
      recommend: "荐",
      download: "免费下载",
      downloading: "下载中，请稍候…",
      ai_summary: "AI 总结",
      summarizing: "总结中…",
      translate: "字幕翻译",
      translating: "翻译中…",
      llm_hint: "提示：AI 总结 / 字幕翻译需在后端 .env 配置大模型 API Key",
      summary_title: "AI 视频总结",
      sub_lang: "字幕语言：",
      auto: "（自动）",
      translate_done: "翻译完成，字幕已开始下载 (subtitle.srt)",
      translate_fail: "翻译失败：",
    },
    platforms: {
      heading_1: "覆盖你常用的",
      heading_2: "所有平台",
      sub: "一个网站搞定所有下载需求，无需在多个工具间来回切换。",
      items: [
        { name: "YouTube", desc: "全球最大视频平台" },
        { name: "哔哩哔哩", desc: "弹幕视频社区" },
        { name: "抖音 / TikTok", desc: "短视频无水印" },
        { name: "Threads", desc: "Threads 帖子视频" },
        { name: "X / Twitter", desc: "推文视频下载" },
        { name: "Instagram", desc: "Reels / 帖子" },
        { name: "小红书", desc: "笔记视频" },
        { name: "1000+ 平台", desc: "yt-dlp 全面支持" },
      ],
    },
    features: {
      heading_1: "不止下载，更是",
      heading_2: "效率神器",
      sub: "把下载、理解、翻译一次搞定，让你的视频生产力翻倍。",
      free: "免费",
      pro: "PRO",
      items: [
        { title: "极速下载", desc: "服务端直连解析，多线程加速，告别漫长等待。" },
        { title: "高清无水印", desc: "支持最高 4K 画质，自动合流音视频，纯净无水印。" },
        { title: "AI 视频总结", desc: "一键提炼视频要点与大纲，几秒看懂一小时长视频。" },
        { title: "字幕翻译", desc: "自动提取字幕并翻译成中文，导出标准 SRT 文件。" },
        { title: "全平台通用", desc: "基于 yt-dlp，支持 1000+ 视频网站，持续更新。" },
        { title: "手机可用", desc: "响应式设计，手机、平板、电脑随时随地下载。" },
      ],
    },
    cta: {
      title: "升级 Pro，解锁全部生产力",
      sub: "AI 视频总结、字幕翻译、批量下载、4K 无损画质…… 让每一次下载都物超所值。",
      button: "立即免费试用",
      note: "无需注册 · 打开即用",
    },
    footer: {
      brand_desc: "随时随地，一键下载任意平台视频。基于开源 yt-dlp 打造。",
      col_faq: "常见问题",
      faq_items: ["支持哪些平台？", "为什么部分高清需要 ffmpeg？", "下载的文件保存在哪？", "AI 功能如何开通？"],
      col_features: "功能",
      feature_items: ["视频下载", "AI 总结", "字幕翻译", "批量下载 (即将上线)"],
      col_about: "关于",
      about_items: ["使用条款", "隐私政策", "版权声明", "联系我们"],
      legal: "请遵守各平台版权规定，仅将下载内容用于个人学习。本项目仅供技术学习交流。",
      copyright: "Video Analysis Assistant · Powered by yt-dlp + FastAPI + React",
    },
    lang_switch: "EN",
  },

  en: {
    nav: { home: "Home", platforms: "Platforms", features: "Features", faq: "FAQ", pro: "Upgrade Pro" },
    hero: {
      badge: "1000+ platforms · HD, watermark-free · Works on mobile",
      title_pre: "Download ",
      title_highlight: "any video",
      title_post: ", anytime & anywhere",
      sub_1: "Just paste a link to download instantly. No platform limits, choose any quality, plus ",
      sub_ai: "AI video summary",
      sub_2: " and ",
      sub_translate: "subtitle translation",
      sub_3: ".",
      placeholder: "Paste a video link, e.g. https://www.youtube.com/watch?v=...",
      parse: "Parse Now",
      parsing: "Parsing",
      empty_url: "Please enter a video link",
    },
    result: {
      no_thumb: "No cover",
      has_subtitles: "Subtitles",
      select_quality: "Select quality / format",
      quality_best: "Best quality (auto)",
      quality_audio: "Audio only",
      quality_merge: "(merge)",
      quality_default: "Default quality",
      recommend: "Top",
      download: "Free Download",
      downloading: "Downloading, please wait…",
      ai_summary: "AI Summary",
      summarizing: "Summarizing…",
      translate: "Translate Subtitles",
      translating: "Translating…",
      llm_hint: "Tip: AI summary / translation requires an LLM API key in backend .env",
      summary_title: "AI Video Summary",
      sub_lang: "Subtitle language: ",
      auto: " (auto)",
      translate_done: "Done! Subtitle download started (subtitle.srt)",
      translate_fail: "Translation failed: ",
    },
    platforms: {
      heading_1: "Covers all your ",
      heading_2: "favorite platforms",
      sub: "One site for all your download needs, no more switching between tools.",
      items: [
        { name: "YouTube", desc: "World's largest video site" },
        { name: "Bilibili", desc: "Danmaku video community" },
        { name: "Douyin / TikTok", desc: "Short videos, no watermark" },
        { name: "Threads", desc: "Threads post videos" },
        { name: "X / Twitter", desc: "Download tweet videos" },
        { name: "Instagram", desc: "Reels / posts" },
        { name: "Xiaohongshu", desc: "Note videos" },
        { name: "1000+ sites", desc: "Full yt-dlp support" },
      ],
    },
    features: {
      heading_1: "More than downloads, a ",
      heading_2: "productivity booster",
      sub: "Download, understand and translate in one place, doubling your video productivity.",
      free: "Free",
      pro: "PRO",
      items: [
        { title: "Blazing Fast", desc: "Server-side parsing with multi-thread acceleration. No more waiting." },
        { title: "HD, No Watermark", desc: "Up to 4K quality, auto audio/video merge, clean and watermark-free." },
        { title: "AI Video Summary", desc: "Extract key points and outline in one click. Grasp a long video in seconds." },
        { title: "Subtitle Translation", desc: "Auto-extract and translate subtitles, export standard SRT files." },
        { title: "All Platforms", desc: "Powered by yt-dlp, supports 1000+ video sites, continuously updated." },
        { title: "Mobile Friendly", desc: "Responsive design. Download on phone, tablet or desktop, anywhere." },
      ],
    },
    cta: {
      title: "Upgrade to Pro, unlock full productivity",
      sub: "AI summary, subtitle translation, batch download, lossless 4K… make every download worth it.",
      button: "Start Free Now",
      note: "No sign-up · Ready to use",
    },
    footer: {
      brand_desc: "Download any video from any platform, anytime. Built on open-source yt-dlp.",
      col_faq: "FAQ",
      faq_items: ["Which platforms are supported?", "Why does some HD need ffmpeg?", "Where are files saved?", "How to enable AI features?"],
      col_features: "Features",
      feature_items: ["Video Download", "AI Summary", "Subtitle Translation", "Batch Download (soon)"],
      col_about: "About",
      about_items: ["Terms of Use", "Privacy Policy", "Copyright", "Contact Us"],
      legal: "Please respect each platform's copyright rules and use downloads for personal learning only. This project is for technical study only.",
      copyright: "Video Analysis Assistant · Powered by yt-dlp + FastAPI + React",
    },
    lang_switch: "中文",
  },
};

const LangContext = createContext(null);

function resolve(obj, path) {
  return path.split(".").reduce((acc, key) => (acc == null ? undefined : acc[key]), obj);
}

export function LanguageProvider({ children }) {
  const [lang, setLang] = useState(() => localStorage.getItem("lang") || "zh");

  useEffect(() => {
    localStorage.setItem("lang", lang);
    document.documentElement.lang = lang === "zh" ? "zh-CN" : "en";
  }, [lang]);

  const t = useCallback(
    (path) => {
      const val = resolve(translations[lang], path);
      if (val !== undefined) return val;
      return resolve(translations.zh, path) ?? path;
    },
    [lang]
  );

  const toggle = useCallback(() => setLang((l) => (l === "zh" ? "en" : "zh")), []);

  return <LangContext.Provider value={{ lang, setLang, toggle, t }}>{children}</LangContext.Provider>;
}

export function useI18n() {
  const ctx = useContext(LangContext);
  if (!ctx) throw new Error("useI18n must be used within LanguageProvider");
  return ctx;
}
