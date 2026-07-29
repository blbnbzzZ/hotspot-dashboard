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
- 推荐**智谱 AI**：注册送 2000 万 tokens 永久免费

---

## 🚀 快速开始

### 前置要求

| 工具 | 版本 | 安装 |
|---|---|---|
| **Python** | 3.11+ | [官网下载](https://www.python.org/downloads/) |
| **Node.js** | 18+ | [官网下载](https://nodejs.org/) |
| **Git** | 任意 | [官网下载](https://git-scm.com/) |

> Windows 用户直接装好 Python 和 Node 后往下走。

### 一键启动（推荐）

**Windows 用户**：双击项目根目录的 `run.bat`

```bash
# 或命令行运行
run.bat
```

启动后会打开 3 个窗口：
- Launcher（启动器）
- Backend-8000（FastAPI 后端）
- Frontend-5173（Vue 前端）

等待 ~20 秒，浏览器自动打开 http://localhost:5173

### 手动启动

如果 `run.bat` 启动失败，可手动启动：

```bash
# 1. 克隆仓库
git clone https://github.com/blbnbzzZ/hotspot-dashboard.git
cd hotspot-dashboard

# 2. 安装后端依赖
cd backend
pip install -r requirements.txt
python run.py &
cd ..

# 3. 安装前端依赖
cd frontend
npm install
npm run dev
```

---

## 🔑 配置 AI（可选）

不配置也能用「🪄 免费模板生成」功能。要用 AI 智能生成：

1. 浏览器进入 http://localhost:5173
2. 点击左上角 ☰ 头像 → 「👤 我的」
3. 进入「🔑 API 设置」
4. 选一个 AI 提供商（推荐智谱 AI）
5. 填入 API Key → 点击「保存」

### 推荐：智谱 AI（免费额度最多）

1. 打开 [open.bigmodel.cn](https://open.bigmodel.cn/)
2. 注册并登录（手机号即可）
3. 进入「API Keys」→ 创建 Key
4. 复制 Key 填入本工具
5. 重启后端生效

---

## 📱 手机访问

工作台支持局域网访问 + 添加到桌面：

1. **确保手机和电脑在同一 WiFi**
2. 重启 `run.bat`，启动窗口会显示局域网 IP，类似：
   ```
   📱 手机浏览器打开: http://192.168.x.x:5173
   ```
3. 手机浏览器输入该地址
4. **添加到主屏幕**（像 App 一样）：
   - **iOS Safari**: 分享按钮 → 添加到主屏幕
   - **Android Chrome**: 菜单 → 添加到主屏幕 / 安装应用

---

## 🎬 使用演示

### 1. 实时查看热点
打开首页，自动展示当前 4 大平台的热点综合排序。

### 2. 排序与筛选
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

## ⚙️ 核心架构

```
┌─────────────────────────────────────────────┐
│  Frontend (Vue 3 + Vite, 端口 5173)         │
│  - Dashboard / Detail / ContentGen         │
│  - History / MyPage / Settings             │
│  - PWA（手机适配）                          │
└──────────────┬──────────────────────────────┘
               │ /api/* 代理
┌──────────────▼──────────────────────────────┐
│  Backend (FastAPI, 端口 8000)              │
│  - /api/hotspots (聚合去重)                │
│  - /api/conversations (对话历史)           │
│  - /api/ai/* (AI 调用)                     │
│  - APScheduler (每 30 分钟爬取)            │
└──────────────┬──────────────────────────────┘
               │
   ┌───────────┼───────────┬──────────┐
   ▼           ▼           ▼          ▼
┌──────┐  ┌──────┐  ┌─────────┐  ┌──────┐
│微博  │  │澎湃  │  │百度热搜 │  │B站   │
└──────┘  └──────┘  └─────────┘  └──────┘
   + jieba 分词聚合（jaccard 相似度）
   + SQLite 持久化（hotspots.db）
```

---

## 🛡 数据安全

- ✅ 所有数据保存在你本地 `backend/data/hotspots.db`
- ✅ API Key 存在本地数据库，不上传任何服务器
- ✅ `.gitignore` 排除 `.env` 和 `*.db`，**仓库零敏感信息泄露**
- ✅ 开源透明，无追踪无广告

---

## ❓ 常见问题

### Q：后端启动报错 `ModuleNotFoundError`
A：进入 `backend` 目录运行 `pip install -r requirements.txt`

### Q：前端启动报错 `Cannot find module`
A：进入 `frontend` 目录运行 `npm install`

### Q：手机访问显示「拒绝连接」
A：检查电脑和手机是否在同一 WiFi；Windows 防火墙可能拦截了 5173 / 8000 端口

### Q：爬取数据为空
A：可能平台有反爬，等待几分钟后重试；或者浏览器访问微博/百度确认你的网络通畅

### Q：AI 生成报错「Invalid API Key」
A：进入「👤 我的 → 🔑 API 设置」检查 Key 是否填对，重启后端

---

## 📦 项目结构

```
hotspot-dashboard/
├── backend/                  # FastAPI 后端
│   ├── app/
│   │   ├── crawlers/         # 4 个平台爬虫
│   │   ├── ai_service.py     # AI 服务（5 家）
│   │   ├── aggregator.py     # jieba 聚合去重
│   │   ├── main.py           # API 入口
│   │   ├── models.py         # 数据库模型
│   │   └── database.py       # SQLite 配置
│   ├── data/                 # SQLite 数据库（gitignore）
│   ├── requirements.txt
│   └── run.py
├── frontend/                 # Vue 3 前端
│   ├── src/
│   │   ├── views/            # 6 个页面
│   │   ├── components/       # 侧边栏 / 进度条
│   │   ├── stores/           # Pinia 状态管理
│   │   ├── styles/           # 全局样式
│   │   └── router/
│   ├── package.json
│   └── vite.config.js
├── launcher.py               # 一键启动器
├── run.bat                   # Windows 一键启动
├── promo_script.md           # 视频宣传脚本
└── README.md                 # 你正在看的
```

---

## 🤝 二次开发

欢迎 PR！建议方向：

- 🔌 添加新数据源（抖音/知乎/今日头条等）
- 🌍 添加海外数据源（HackerNews 已实现）
- 🤖 接入更多 AI（Claude / Gemini）
- 📊 数据可视化增强（趋势预测 / 关联分析）
- 🌐 多语言界面

---

## 📝 License

MIT License — 自由使用、修改、商用

---

## 🌟 Star History

如果这个项目对你有帮助，欢迎给个 ⭐️ Star 支持！

---

## 🙋 联系 / 反馈

遇到问题？在 GitHub Issues 留言。

---

**Made with ❤️ for content creators and operators**