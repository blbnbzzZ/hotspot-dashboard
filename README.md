# 🔥 热点聚合工作台

> 多平台热点聚合、权重分析、AI 内容生成 — 自托管全栈热点监控工具

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Vue](https://img.shields.io/badge/Vue-3-green.svg)](https://vuejs.org/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

一个帮你**自动聚合 4 大主流平台热点**、**用 AI 一键生成内容**的开源桌面工具。所有数据保存在你本地，AI Key 由你自己配置。

---

## ✨ 核心功能

| 功能 | 说明 |
|---|---|
| 📡 **多平台聚合** | 微博 / 澎湃新闻 / 百度热搜 / B 站热搜，每 30 分钟自动爬取一次 |
| 🎯 **智能权重** | 综合平台覆盖、原始热度、排名位置、时间新鲜度计算权重分数 |
| 🔀 **去重聚合** | 同一热点在多平台出现时自动合并，避免重复 |
| 🤖 **AI 内容生成** | 基于热点直接生成文章、新闻、短视频脚本、社媒文案 |
| 💬 **对话历史** | 多轮对话，自动保存，每条关联热点信息和 token 消耗 |
| 📱 **手机适配** | PWA 支持，添加主屏幕像原生 App，手机局域网可访问 |
| 🎨 **亮/暗主题** | 一键切换，自动保存 |
| 🔒 **本地存储** | SQLite 数据库，不上传任何数据 |
| 🆓 **免费模板** | 无 API Key 也能生成文章（基于本地模板） |

---

## 🛠 技术栈

**后端**
- Python 3.11+ / FastAPI
- SQLAlchemy + SQLite
- APScheduler（定时爬取）
- jieba（中文分词聚合）
- httpx（异步 HTTP）
- BeautifulSoup4（HTML 解析）

**前端**
- Vue 3 + Vite
- Vue Router + Pinia
- ECharts（图表）
- vite-plugin-pwa（移动端 App 体验）

**AI 服务**
- 支持 5 家：智谱 AI / 通义千问 / DeepSeek / 豆包 / OpenAI
- 选哪个看你自己，本文档不作推荐

---

## 🚀 快速开始

### 前置要求

| 工具 | 安装 |
|---|---|
| **Python** | 从 [python.org](https://www.python.org/downloads/) 下载，安装时勾选 Add to PATH |
| **Node.js** | 从 [nodejs.org](https://nodejs.org/) 下载 18+ 版本 |

> 安装完以上两个工具后，下一步就是双击运行，不需要装 Git。

### 一键启动（Windows）

1. 下载项目到任意目录（比如 `D:\hotspot-dashboard`）
2. **双击 `run.bat`**，程序会自动：
   - 安装后端依赖（用时约 10 秒）
   - 安装前端依赖（用时约 30 秒，仅首次需要）
   - 启动后端服务（端口 8000）
   - 启动前端页面（端口 5173）
   - 自动打开浏览器

首次启动总计约 **40 秒**，后续每次只需约 **15 秒**。

### 手机访问

> 如果你有用手机打开的需求：

1. 电脑和手机连接**同一 WiFi**
2. 双击 `run.bat`，启动后窗口会显示你的局域网 IP
3. 手机浏览器打开 `http://192.168.x.x:5173`
4. **添加到主屏幕**（像原生 App 一样）：
   - **iOS Safari**：底部分享 → 添加到主屏幕
   - **Android Chrome**：菜单 → 添加到主屏幕

---

## 🔑 配置 AI（可选）

不配置也能用「🪄 免费模板生成」功能。要用 AI 智能生成：

1. 浏览器进入 http://localhost:5173
2. 点击左上角 ☰ 头像 → 「👤 我的」
3. 进入「🔑 API 设置」
4. 选一个 AI 提供商，填入你的 API Key → 保存
5. 重启后端生效

目前支持的提供商：

| 提供商 | 说明 |
|---|---|
| **智谱 AI** | 注册送 2000 万 tokens |
| **通义千问** | 阿里云，送 100 万 tokens |
| **DeepSeek** | 注册送 500 万 tokens |
| **豆包** | 字节旗下，有免费额度 |
| **OpenAI 兼容** | 支持任何 OpenAI 兼容接口（如 OneAPI） |

---

## 🎬 使用演示

### 1. 实时查看热点
打开首页，自动展示当前 4 大平台的热点综合排序。

### 2. 筛选
- 切换「🔥 所有数据源共同热点」查看跨平台热门话题
- 按分类筛选（体育 / 国际 / 财经 等）

### 3. 进入趋势详情
点任意热点 → 查看各平台具体排名 / 热度 / 原文链接。

### 4. AI 生成内容
点「基于此热点生成内容」→ 选 AI 模型 → 输入需求 → 点「🚀 发送」。

### 5. 历史对话
自动保存到「👤 我的 → 💬 对话历史」，可随时打开继续对话。

### 6. 排除批次
「⚙️ 设置 → 📋 采集历史」可手动排除某批次数据（默认引用最新 3 批）。

---

## 🛡 数据安全

- ✅ 所有数据保存在你本地 SQLite 数据库
- ✅ API Key 存在本地数据库，不上传任何服务器
- ✅ `.gitignore` 排除 `.env` 和 `*.db`，仓库零敏感信息泄露
- ✅ 开源透明，无追踪无广告

---

## ❓ 常见问题

### Q：python/node 找不到命令？
A：检查是否安装了 Python 和 Node.js，安装时记得勾选「Add to PATH」

### Q：启动后浏览器打不开？
A：手动打开 http://localhost:5173

### Q：手机上访问不了？
A：检查电脑和手机是否在同一 WiFi；Windows 防火墙可能拦截了端口

### Q：数据为空？
A：首次运行会自动爬取（约 10 秒），等待完成后刷新页面

### Q：AI 生成报错？
A：检查你的 API Key 是否有效、余额是否充足，进入「我的 → API 设置」重新配置

---

## 📦 项目结构

```
hotspot-dashboard/
├── backend/                  # FastAPI 后端
│   ├── app/
│   │   ├── crawlers/         # 4 个平台爬虫
│   │   ├── ai_service.py     # AI 服务（5 家可选）
│   │   ├── main.py           # API 入口（42 个接口）
│   │   └── ...
│   ├── requirements.txt
│   └── run.py
├── frontend/                 # Vue 3 前端
│   ├── src/views/            # 6 个页面
│   └── ...
├── launcher.py               # 一键启动器（自动装依赖）
├── run.bat                   # Windows 双击启动
└── README.md
```

---

## 📝 License

MIT License

---

**Made with ❤️ for content creators and operators**