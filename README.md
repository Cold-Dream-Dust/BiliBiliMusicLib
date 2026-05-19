# BiliBiliMusicLib

B站媒体搜索与下载工具集，支持视频/音频下载、在线搜索、LLM 智能辅助。

## 项目结构

```
├── bilibili_downloader.py    # 命令行版：按 UID 批量下载用户视频
├── requirements.txt          # 命令行版依赖
├── bilibili_tools/           # Web 版：前后端分离的完整工具
│   ├── backend/              # FastAPI 后端
│   └── frontend/             # Vue 3 前端
```

---

## 1. 命令行版 (`bilibili_downloader.py`)

从指定 B站用户主页批量下载其所有上传视频。

### 功能特性
- 自动获取用户所有上传的视频列表
- 使用 yt-dlp 下载视频（最佳画质）
- 支持断点续传，跳过已下载的视频
- 自动合并视频和音频为 MP4 格式

### 安装依赖

```bash
pip install -r requirements.txt
```

或者单独安装：

```bash
pip install requests yt-dlp
```

### 使用方法

1. 编辑 `bilibili_downloader.py`，修改 `TARGET_UID` 为目标用户 UID：

```python
TARGET_UID = "1971709386"  # 替换为目标 UID
```

2. 运行：

```bash
python bilibili_downloader.py
```

### 配置项

| 变量 | 说明 | 默认值 |
|------|------|--------|
| TARGET_UID | B站用户 UID | — |
| OUTPUT_DIR | 下载保存目录 | ./downloads |

### 注意事项

- 需要能正常访问 B站
- 每个视频下载后等待 2 秒，避免请求过快被限
- 请确保有足够磁盘空间

---

## 2. Web 版 (`bilibili_tools/`) 🆕

前后端分离的 B站媒体搜索下载工具，提供可视化界面。

### 功能特性
- 🔍 类 B站体验的搜索界面（封面卡片 + 一键下载）
- 🎵 支持视频下载 / 纯音频提取（MP3/M4A/FLAC）
- 🤖 LLM 智能识别模糊需求（如"周杰伦和茶叶有关的歌" → 自动搜索）
- 📥 三面板下载管理（等待中 / 下载中 / 已完成）
- ⚙️ 可配置并行下载数、默认格式、下载目录

### 技术栈
- **后端**: FastAPI + yt-dlp + OpenAI 兼容 LLM
- **前端**: Vue 3 + Vite + Pinia
- **转码**: 需系统安装 ffmpeg

### 快速启动

```bash
# 1. 安装后端依赖
cd bilibili_tools/backend
pip install -r requirements.txt

# 2. 安装前端依赖
cd ../frontend
npm install

# 3. 配置（复制模板并填入你的信息）
cp config.example.json config.json

# 4. 启动后端（终端1）
cd ../backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 5. 启动前端（终端2）
cd ../frontend
npm run dev

# 6. 浏览器打开 http://localhost:5173
```

### 前置依赖
- **ffmpeg**: 格式转换必需。`winget install ffmpeg` 或从 [ffmpeg.org](https://ffmpeg.org) 下载
- **Python 3.9+**
- **Node.js 18+**

### 配置说明

复制 `config.example.json` 为 `config.json` 并填入：

| 字段 | 说明 |
|------|------|
| bili_sessdata | B站 Cookie SESSDATA（可选，用于高清下载） |
| bili_jct | B站 Cookie bili_jct |
| llm_api_key | LLM API Key（可选，用于智能搜索） |
| download_dir | 下载保存目录 |

### 项目结构
```
bilibili_tools/
├── backend/
│   ├── main.py              # FastAPI 入口
│   ├── config.py            # 配置管理（JSON 持久化）
│   ├── config.example.json  # 配置模板
│   ├── api/                 # 搜索/下载/LLM 路由
│   ├── services/            # B站/下载/LLM 业务逻辑
│   ├── models/schemas.py    # Pydantic 模型
│   └── utils/sorting.py     # 搜索结果加权排序算法
└── frontend/
    └── src/
        ├── views/           # 搜索页/下载管理/LLM助手/设置
        ├── components/      # VideoCard/DownloadItem 等
        ├── stores/          # Pinia 状态管理
        └── utils/api.js     # 后端 API 封装
```

## 常见问题

### Q: 提示"未找到 yt-dlp"
A: 运行 `pip install yt-dlp` 安装

### Q: 下载失败
A: 可能是网络问题或视频被限制，可稍后重试；部分高清格式需要提供 B站 Cookie

### Q: 如何只下载单个视频
A: 可直接使用 yt-dlp 命令：
```bash
yt-dlp https://www.bilibili.com/video/BVxxxxxx
```
