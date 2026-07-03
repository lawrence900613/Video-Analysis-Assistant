# 视频下载功能总结 / Video Download Feature Summary

> 本文档沉淀视频下载功能的实现细节、运行方式与排障指南。  
> 项目概览与 AI 能力请参阅 [README.md](../README.md)；需求与设计见 [01-requirements-analysis.md](./01-requirements-analysis.md)、[02-design-document.md](./02-design-document.md)。

---

## Overview / 功能概述

用户粘贴视频链接后，系统完成 **解析 URL → 选择画质/格式 → 带进度下载 → 浏览器保存文件** 的完整流程。

| 阶段 | 说明 |
| --- | --- |
| 解析 | 调用 `POST /api/parse`，返回标题、缩略图、时长、可选画质列表、字幕语言等 |
| 选质 | 前端展示分辨率选项（含「最佳画质自动合并」「仅音频 MP3」） |
| 下载 | 异步任务：`start` → 轮询 `progress` → 完成后通过 `file` 端点触发浏览器原生保存 |
| 取消 | 下载中再次点击按钮，或 `AbortController` 触发 `cancel` |

---

## Supported Platforms / 支持平台

底层依赖 [yt-dlp](https://github.com/yt-dlp/yt-dlp)，理论上支持 [1000+ 站点](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)。本次开发与验证重点如下：

| 平台 | 状态 | 备注 |
| --- | --- | --- |
| **YouTube** | ✅ | 匿名下载使用 `android_vr` + `web` 客户端，可获取完整 DASH 画质阶梯 |
| **Instagram** | ✅ | 需 **Python ≥ 3.10** + **curl_cffi**（浏览器 TLS 指纹模拟），无需 Cookie 即可匿名访问 |
| **Bilibili** | ✅ | 应用 `dm_img` 参数补丁，修复 HTTP **412** 匿名解析失败 |
| **Twitch** | UI 展示 | 平台画廊已收录；实际下载走 yt-dlp 通用提取器 |
| **TikTok / X / 小红书等** | 依赖 yt-dlp | 随 yt-dlp 版本更新，行为可能变化 |

完整站点列表：[yt-dlp supportedsites.md](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)

---

## Architecture / 架构

```
┌─────────────────┐     REST API      ┌──────────────────────────────────┐
│  React 前端      │ ◄──────────────► │  FastAPI (backend/app/main.py)   │
│  api.js 轮询进度 │                   │  ├── downloader.py  (yt-dlp 封装) │
│  ResultCard UI  │                   │  └── download_jobs.py (内存任务)  │
└─────────────────┘                   └──────────────────────────────────┘
                                              │
                                              ▼
                                    yt-dlp + curl_cffi + ffmpeg
```

### Download Job Flow / 下载任务流

1. **`POST /api/download/start`** — 创建后台线程任务，返回 `job_id`
2. **`GET /api/download/{job_id}/progress`** — 返回 `stage`、`percent`、`speed_bps`、`eta_seconds`
3. **`POST /api/download/{job_id}/cancel`** — 请求取消，清理临时目录
4. **`GET /api/download/{job_id}/file`** — 文件就绪后一次性取回；响应头含 `Content-Disposition`，响应后自动删除临时文件

> 保留同步端点 `POST /api/download`（阻塞至完成），供兼容或调试使用。

---

## Key Backend Features / 后端要点

| 模块 | 能力 |
| --- | --- |
| **URL 规范化** (`normalize_url`) | 剥离 `utm_*`、`igsh`、`fbclid` 等追踪参数，保留 YouTube `v` 等有效 query |
| **Bilibili 412 补丁** (`_patch_bilibili_dm_img`) | 在 `wbi/playurl` 请求注入 `dm_img_*` / `web_location` 占位参数，不修改 yt-dlp 源码 |
| **Windows ffmpeg 检测** (`_effective_path`) | 合并进程 PATH 与注册表 Machine/User Path，解决 WinGet 安装后子进程找不到 ffmpeg |
| **Content-Disposition** | 同时输出 ASCII `filename=` 与 UTF-8 `filename*=`，避免中文标题被存成 `.txt` |
| **异步任务** | 线程 + 内存字典；进度钩子上报速度、ETA；取消时调用 `DownloadCancelled` 并 `rmtree` 临时目录 |
| **画质选项** | 按分辨率分组；无 ffmpeg 时跳过需合并的 video-only 流；可选 MP3 后处理 |

相关文件：

- `backend/app/downloader.py` — 解析、下载、字幕
- `backend/app/download_jobs.py` — 任务生命周期
- `backend/app/main.py` — API 路由
- `backend/app/config.py` — `.env` 与 `DOWNLOAD_DIR`

---

## Key Frontend Features / 前端要点

| 能力 | 实现 |
| --- | --- |
| **真实进度条** | 轮询 progress API，展示百分比、速度、ETA、合并/传输阶段 |
| **取消下载** | 下载中再次点击 → `AbortController` + `cancel` API |
| **步骤指示器** | `computeFlowStep`：输入 URL → 解析中 → 结果展示 → 下载中/完成 |
| **缩略图修复** | `<img referrerPolicy="no-referrer">`，避免 CDN 防盗链导致空白 |
| **原生下载** | 完成后面向 `/file` 触发 `<a click>`，**不再** fetch→blob→objectURL（已修复 Chrome/Edge 遗留 `{uuid}.tmp`） |
| **历史记录** | `localStorage` 保存解析/下载历史（`HistoryPanel`） |
| **平台画廊** | YouTube、Bilibili、TikTok、Twitch、X、Instagram、小红书等展示 |

相关文件：

- `frontend/src/api.js` — `downloadVideo`、`cancelDownload`
- `frontend/src/components/ResultCard.jsx` — 下载 UI 与进度
- `frontend/src/utils/progress.js` — 步骤与格式化
- `frontend/src/utils/history.js` — 本地历史

---

## Environment Setup / 环境配置

### Python 虚拟环境

推荐使用 **Python 3.12** 虚拟环境（Instagram 匿名提取依赖较新版本运行时）：

```powershell
cd backend
py -3.12 -m venv .venv312
.\.venv312\Scripts\Activate.ps1
pip install -r requirements.txt
```

> ⚠️ 勿使用旧版 **Python 3.9** venv：Instagram 的 curl_cffi  impersonation 无法正常工作。

### 核心依赖 (`backend/requirements.txt`)

| 包 | 用途 |
| --- | --- |
| `yt-dlp>=2026.6.9` | 下载核心；含重构后的 Instagram 提取器 |
| `curl_cffi>=0.7` | Instagram 匿名访问所需的浏览器 TLS 指纹 |
| `fastapi` / `uvicorn` | HTTP 服务 |

### ffmpeg

高清合并（video+audio）与 MP3 转码需要 ffmpeg：

```powershell
winget install Gyan.FFmpeg
```

安装后重启终端；后端 `/api/health` 的 `ffmpeg: true` 表示检测成功。

### 可选：Cookie 配置

在 `backend/.env` 中设置（参见 `.env.example`）：

```env
YTDLP_COOKIES=cookies.txt
# 或
YTDLP_COOKIES_FROM_BROWSER=edge
```

用于私有视频、年龄限制、403 等场景。

---

## How to Run / 运行方式

### 后端

```powershell
cd backend
.\.venv312\Scripts\Activate.ps1
copy .env.example .env   # 首次；AI 功能需填写 LLM_API_KEY
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 前端（开发）

```powershell
cd frontend
npm install
npm run dev
```

Vite 开发服务器默认代理 `/api` 到 `http://127.0.0.1:8000`。

### 生产一体部署

```powershell
cd frontend && npm run build
cd ..\backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

若存在 `frontend/dist`，FastAPI 会自动托管静态资源。

### 单元测试

```powershell
cd backend
pip install -r requirements-dev.txt
pytest -q
```

---

## API Quick Reference / 接口速查

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/health` | 健康检查（ffmpeg、LLM 就绪状态） |
| POST | `/api/parse` | 解析视频元数据 |
| POST | `/api/download/start` | 启动异步下载 |
| GET | `/api/download/{id}/progress` | 查询进度 |
| POST | `/api/download/{id}/cancel` | 取消任务 |
| GET | `/api/download/{id}/file` | 下载文件（一次性） |

---

## Known Limitations / 已知限制

1. **私有 / 年龄限制内容** — 需配置 Cookie 或浏览器 Cookie 导入，无法保证所有站点匿名可用。
2. **内存任务存储** — 任务状态保存在进程内存，**重启服务后 job_id 失效**；不适合多实例水平扩展。
3. **并发限制** — 无全局队列；大量并发下载会占用磁盘与带宽，建议单机适度使用。
4. **平台策略变化** — yt-dlp 需定期 `pip install -U yt-dlp`；Bilibili / Instagram 等可能再次调整反爬策略。
5. **无 ffmpeg 降级** — 仍可下载 progressive 单文件流，但无法合并最高画质或转 MP3。

---

## Troubleshooting / 排障

| 现象 | 可能原因 | 处理 |
| --- | --- | --- |
| Instagram 返回空响应 / 解析失败 | 使用了 Python 3.9 venv 或未装 curl_cffi | 切换到 `.venv312`（3.12），`pip install curl_cffi` |
| Bilibili HTTP 412 | 缺少 dm_img 风控参数 | 确认 `downloader.py` 中 `_patch_bilibili_dm_img()` 已执行（模块 import 时自动调用） |
| `/api/health` 显示 `ffmpeg: false` | PATH 未包含 WinGet 安装路径 | `winget install Gyan.FFmpeg`，重启终端；Windows 下后端已尝试读注册表 Path |
| 端口 8000 被占用 | 旧 uvicorn 进程未退出 | `netstat -ano \| findstr :8000` 后结束进程，或修改 `.env` 中 `PORT` |
| 缩略图不显示 |  referrer 策略拦截 | 前端已设 `referrerPolicy="no-referrer"`；若仍失败多为 CDN 临时问题 |
| 下载文件名变成 `.txt` | Content-Disposition 编码问题 | 已修复：后端同时发送 `filename*` UTF-8 编码 |
| Downloads 文件夹出现 `{uuid}.tmp` | blob 下载过早 revoke objectURL | **已修复**：改用语义化 `/file` 原生下载 |
| YouTube 403 / 格式不可用 | 平台策略或需登录 | 升级 yt-dlp；必要时配置 Cookie |
| 下载取消后仍占磁盘 | 取消清理失败 | 检查 `backend/downloads/`；任务取消会 `rmtree` job 目录 |

---

## File Layout / 相关文件索引

```
backend/
├── app/
│   ├── downloader.py      # yt-dlp 封装、Bilibili 补丁、ffmpeg 检测
│   ├── download_jobs.py   # 异步任务与取消
│   └── main.py            # REST 路由
├── tests/
│   ├── test_downloader.py
│   └── test_download_jobs.py
├── requirements.txt
└── .env.example

frontend/src/
├── api.js                 # downloadVideo 流程
├── components/
│   ├── ResultCard.jsx     # 进度条、取消、缩略图
│   └── HistoryPanel.jsx
└── utils/
    ├── progress.js
    └── history.js
```

---

*文档版本：与 `feat: complete video download…` 提交同步。*
