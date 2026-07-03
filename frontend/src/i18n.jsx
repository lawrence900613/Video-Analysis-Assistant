import { createContext, useCallback, useContext, useEffect, useState } from "react";

export const translations = {
  zh: {
    nav: { home: "首页", platforms: "热门平台", features: "功能", history: "历史", faq: "常见问题", pro: "升级 Pro" },
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
      steps: ["粘贴链接", "解析信息", "选择格式", "开始下载"],
    },
    result: {
      no_thumb: "无封面",
      has_subtitles: "含字幕",
      select_quality: "选择清晰度 / 格式",
      quality_best: "最佳画质（自动）",
      quality_audio: "仅音频",
      quality_default: "默认画质",
      quality_hint: "高清画质会自动合成音轨，下载后即可直接播放。",
      recommend: "荐",
      download: "免费下载",
      downloading: "下载中，请稍候…",
      cancel_download: "取消下载",
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
      ffmpeg_warning: "未检测到 ffmpeg，部分高清合流格式不可用。安装 ffmpeg 后可解锁 4K 合流与 MP3 转码。",
      views: "次播放",
      subtitle_lang: "字幕语言",
      download_subs: "下载字幕",
      downloading_subs: "导出字幕中…",
      subtitle_done: "字幕已下载 (",
      subtitle_fail: "字幕下载失败：",
      progress_indeterminate: "处理中…",
      progress_downloading: "下载中…",
      progress_processing: "合成处理中…",
      progress_transferring: "保存文件中…",
      progress_starting: "准备中…",
      progress_speed: "速度",
      progress_unknown: "—",
      progress_eta_seconds: "约 {n} 秒",
      progress_eta_remaining: "剩余 {time}",
    },
    history: {
      title: "最近解析",
      clear: "清空",
      remove: "删除",
      views: "播放",
    },
    platforms: {
      badge: "热门平台",
      heading_1: "覆盖你常用的",
      heading_2: "所有平台",
      sub: "一个网站搞定所有下载需求，无需在多个工具间来回切换。",
      items: [
        { name: "YouTube", desc: "全球最大视频平台" },
        { name: "哔哩哔哩", desc: "弹幕视频社区" },
        { name: "抖音 / TikTok", desc: "短视频无水印" },
        { name: "Twitch", desc: "Twitch 直播与回放" },
        { name: "X / Twitter", desc: "推文视频下载" },
        { name: "Instagram", desc: "Reels / 帖子" },
        { name: "小红书", desc: "笔记视频" },
        { name: "1000+ 平台", desc: "yt-dlp 全面支持" },
      ],
    },
    features: {
      badge: "核心功能",
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
    pricing: {
      badge: "VIP 会员",
      heading_1: "选择适合你的",
      heading_2: "方案",
      sub: "免费版满足日常下载，Pro 解锁 AI 与高级功能。",
      popular: "最受欢迎",
      note: "支付功能即将上线 · 当前所有功能均可免费体验",
      features: ["视频解析与下载", "字幕下载 (SRT)", "AI 视频总结", "AI 字幕翻译", "4K 合流下载", "批量下载", "下载历史", "优先解析队列"],
      plans: [
        { name: "Free", price: "¥0", period: "/永久", desc: "日常下载够用", cta: "免费开始", highlight: false, included: [true, true, false, false, false, false, true, false] },
        { name: "Pro", price: "¥19", period: "/月", desc: "解锁全部 AI 与高级功能", cta: "立即升级 Pro", highlight: true, included: [true, true, true, true, true, true, true, true] },
      ],
    },
    faq: {
      badge: "常见问题",
      heading: "FAQ",
      items: [
        { q: "支持哪些平台？", a: "基于 yt-dlp，支持 YouTube、Bilibili、TikTok、Instagram 等 1000+ 视频网站，持续更新。" },
        { q: "为什么部分高清需要 ffmpeg？", a: "部分平台的高清视频和音频是分开的，需要 ffmpeg 合流。未安装时仍可下载 progressive 格式和原生音频。" },
        { q: "下载的文件保存在哪？", a: "文件通过浏览器直接下载到您的默认下载目录，服务端不永久存储。" },
        { q: "AI 功能如何开通？", a: "在 backend/.env 配置 LLM_API_KEY、LLM_BASE_URL、LLM_MODEL 即可使用 AI 总结和字幕翻译。" },
      ],
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
    nav: { home: "Home", platforms: "Platforms", features: "Features", history: "History", faq: "FAQ", pro: "Upgrade Pro" },
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
      steps: ["Paste URL", "Parse info", "Pick format", "Download"],
    },
    result: {
      no_thumb: "No cover",
      has_subtitles: "Subtitles",
      select_quality: "Select quality / format",
      quality_best: "Best quality (auto)",
      quality_audio: "Audio only",
      quality_default: "Default quality",
      quality_hint: "HD options automatically include audio — ready to play after download.",
      recommend: "Top",
      download: "Free Download",
      downloading: "Downloading, please wait…",
      cancel_download: "Cancel download",
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
      ffmpeg_warning: "ffmpeg not detected. Some HD merge formats are unavailable. Install ffmpeg for 4K merge and MP3 transcoding.",
      views: "views",
      subtitle_lang: "Subtitle language",
      download_subs: "Download Subs",
      downloading_subs: "Exporting subtitles…",
      subtitle_done: "Subtitle downloaded (",
      subtitle_fail: "Subtitle download failed: ",
      progress_indeterminate: "Processing…",
      progress_downloading: "Downloading…",
      progress_processing: "Merging…",
      progress_transferring: "Saving file…",
      progress_starting: "Starting…",
      progress_speed: "Speed",
      progress_unknown: "—",
      progress_eta_seconds: "About {n}s left",
      progress_eta_remaining: "{time} remaining",
    },
    history: {
      title: "Recent",
      clear: "Clear all",
      remove: "Remove",
      views: "views",
    },
    platforms: {
      badge: "Platforms",
      heading_1: "Covers all your ",
      heading_2: "favorite platforms",
      sub: "One site for all your download needs, no more switching between tools.",
      items: [
        { name: "YouTube", desc: "World's largest video site" },
        { name: "Bilibili", desc: "Danmaku video community" },
        { name: "Douyin / TikTok", desc: "Short videos, no watermark" },
        { name: "Twitch", desc: "Twitch streams and VODs" },
        { name: "X / Twitter", desc: "Download tweet videos" },
        { name: "Instagram", desc: "Reels / posts" },
        { name: "Xiaohongshu", desc: "Note videos" },
        { name: "1000+ sites", desc: "Full yt-dlp support" },
      ],
    },
    features: {
      badge: "Features",
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
    pricing: {
      badge: "VIP Plans",
      heading_1: "Pick the plan ",
      heading_2: "that fits you",
      sub: "Free covers daily downloads. Pro unlocks AI and advanced features.",
      popular: "Most Popular",
      note: "Payments coming soon · All features free to try for now",
      features: ["Parse & download", "Subtitle download (SRT)", "AI video summary", "AI subtitle translation", "4K merge download", "Batch download", "Download history", "Priority queue"],
      plans: [
        { name: "Free", price: "$0", period: "/forever", desc: "Great for everyday downloads", cta: "Get Started Free", highlight: false, included: [true, true, false, false, false, false, true, false] },
        { name: "Pro", price: "$9", period: "/mo", desc: "Unlock all AI and premium features", cta: "Upgrade to Pro", highlight: true, included: [true, true, true, true, true, true, true, true] },
      ],
    },
    faq: {
      badge: "FAQ",
      heading: "Frequently Asked Questions",
      items: [
        { q: "Which platforms are supported?", a: "Powered by yt-dlp — YouTube, Bilibili, TikTok, Instagram, and 1000+ video sites, continuously updated." },
        { q: "Why does some HD need ffmpeg?", a: "Some platforms split video and audio streams. ffmpeg merges them. Without it, progressive formats and native audio still work." },
        { q: "Where are files saved?", a: "Files download directly to your browser's default folder. The server does not store them permanently." },
        { q: "How to enable AI features?", a: "Set LLM_API_KEY, LLM_BASE_URL, and LLM_MODEL in backend/.env to use AI summary and subtitle translation." },
      ],
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
  const [lang, setLang] = useState(() => localStorage.getItem("lang") || "en");

  useEffect(() => {
    localStorage.setItem("lang", lang);
    document.documentElement.lang = lang === "zh" ? "zh-CN" : "en";
  }, [lang]);

  const t = useCallback(
    (path) => {
      const val = resolve(translations[lang], path);
      if (val !== undefined) return val;
      return resolve(translations.en, path) ?? path;
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
