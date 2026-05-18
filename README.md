# Python 工具集

各种实用 Python（及脚本）工具合集。

## 项目结构

```
py/
├── bilibili_downloader.py    # B站视频下载器（单脚本版，旧）
├── requirements.txt           # 旧版依赖
├── README.md                  # 说明文档
├── photo_import/              # 照片导入工具
│   └── import_z50_photos.ps1
├── bilibili_tools/            # 🆕 B站媒体搜索下载工具（前后端分离）
│   ├── backend/               # FastAPI 后端
│   └── frontend/              # Vue 3 前端
└── bilibili_downloads/        # 视频下载目录（运行后生成）
```

---

## 1. B站用户视频下载器 (`bilibili_downloader.py`)

从指定B站用户主页下载其上传的所有视频。

### 目标用户
- 用户主页: https://space.bilibili.com/1971709386/upload/video
- 用户UID: 1971709386

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

#### 直接运行
```bash
python bilibili_downloader.py
```

#### 修改目标用户
编辑 `bilibili_downloader.py` 文件中的 `TARGET_UID` 变量：

```python
TARGET_UID = "1971709386"  # 修改为目标用户的UID
```

#### 修改下载目录
编辑 `OUTPUT_DIR` 变量：

```python
OUTPUT_DIR = "./bilibili_downloads"  # 修改为你想要的目录
```

### 注意事项

1. **网络环境**: 需要能够访问B站
2. **yt-dlp**: 确保 yt-dlp 已正确安装并可在命令行中使用
3. **下载速度**: 程序会在每个视频下载后等待2秒，避免请求过快被限制
4. **存储空间**: 请确保有足够的磁盘空间存储视频

### 依赖说明

- `requests`: 用于调用B站API获取视频列表
- `yt-dlp`: 用于下载B站视频（youtube-dl的改进版）

## 常见问题

### Q: 提示"未找到yt-dlp"
A: 请运行 `pip install yt-dlp` 安装

### Q: 下载失败
A: 可能是网络问题或视频被限制，可以稍后重试

### Q: 如何只下载特定视频
A: 可以直接使用 yt-dlp 命令：
```bash
yt-dlp https://www.bilibili.com/video/BVxxxxxx
```

---

## 2. Bilibili Tools (`bilibili_tools/`) 🆕

B站媒体搜索与下载工具，前后端分离架构。

### 功能特性
- 🔍 类B站体验的搜索界面（封面卡片 + 一键下载）
- 🎵 支持视频下载 / 纯音频提取（MP3/M4A/FLAC）
- 🤖 LLM 智能识别模糊需求（如"周杰伦和茶叶有关的歌" → 自动搜索）
- 📥 三面板下载管理（等待中 / 下载中 / 已完成）
- ⚙️ 可配置并行下载数、默认格式、下载目录

### 技术栈
- **后端**: FastAPI + yt-dlp + OpenAI兼容LLM
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

# 3. 启动后端 (终端1)
cd ../backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 4. 启动前端开发服务器 (终端2)
cd ../frontend
npm run dev

# 5. 浏览器打开 http://localhost:5173
```

### 前置依赖
- **ffmpeg**: 格式转换必需。Windows 下载 ffmpeg.exe 放入 PATH，或 `winget install ffmpeg`
- **yt-dlp**: 后端依赖已包含
- **Node.js**: 前端开发需要

### 项目结构
```
bilibili_tools/
├── backend/
│   ├── main.py              # FastAPI 入口
│   ├── config.py            # 配置管理（JSON持久化）
│   ├── api/                 # 搜索/下载/LLM 路由
│   ├── services/            # B站/下载/LLM 业务逻辑
│   ├── models/schemas.py    # Pydantic 模型
│   └── utils/sorting.py     # 搜索结果加权排序算法
├── frontend/
│   └── src/
│       ├── views/           # 搜索页/下载管理/LLM助手/设置
│       ├── components/      # VideoCard/DownloadItem 等
│       ├── stores/          # Pinia 状态管理
│       └── utils/api.js     # 后端 API 封装
└── requirements.txt
```

---

## Nikon Z 50 照片导入脚本（批次传输 + 断点记录）

项目新增脚本：`import_z50_photos.ps1`

用途：
- 从“此电脑 -> Z 50”设备导入照片/短视频到本地 F 盘
- 默认采用移动模式：本地校验成功后删除相机中的源文件
- 自动分批传输（按文件数和总大小）
- 记录已导入文件与已完成批次，避免重复传输

### 运行示例

```powershell
powershell -ExecutionPolicy Bypass -File .\import_z50_photos.ps1
```

### 常用参数

```powershell
powershell -ExecutionPolicy Bypass -File .\import_z50_photos.ps1 `
	-DeviceNamePattern "Z 50" `
	-SourceSubPath "DCIM" `
	-DestinationRoot "F:\Z50_Photos_Import" `
	-MaxFilesPerBatch 120 `
	-MaxBatchBytes 2GB
```

参数说明：
- `DeviceNamePattern`: 设备名称匹配关键字
- `SourceSubPath`: 设备内来源目录（默认 `DCIM`）
- `DestinationRoot`: 本地导入目录
- `MaxFilesPerBatch`: 每批最多文件数
- `MaxBatchBytes`: 每批最大总大小（例如 `2GB`）
- `KeepSourceOnDevice`: 仅复制，不删除相机中的源文件
- `DryRun`: 仅演练，不实际复制

### 状态文件

脚本会在目标目录下自动写入状态文件：
- `.import_state_z50.json`

包含：
- `importedFiles`: 已完成的文件键值记录
- `completedBatches`: 已完成批次列表

中断后再次运行会自动跳过已完成内容并继续。
