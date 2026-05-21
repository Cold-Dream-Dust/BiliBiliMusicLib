"""
Pydantic 数据模型 — API 请求/响应结构
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ── 枚举 ──────────────────────────────────────────────

class DownloadType(str, Enum):
    video = "video"
    audio = "audio"


class DownloadStatus(str, Enum):
    pending = "pending"
    active = "active"
    done = "done"
    failed = "failed"


class SortBy(str, Enum):
    relevance = "relevance"  # 综合排序（加权评分）
    views = "views"          # 播放量
    date = "date"            # 发布时间
    duration = "duration"    # 时长


# ── 搜索 ──────────────────────────────────────────────

class SearchRequest(BaseModel):
    q: str = Field(..., min_length=1, description="搜索关键词")
    page: int = Field(default=1, ge=1)
    sort_by: SortBy = Field(default=SortBy.relevance)
    order: str = Field(default="desc", pattern="^(asc|desc)$")


class VideoItem(BaseModel):
    bvid: str
    title: str
    author: str = ""
    pic: str = ""          # 封面图 URL
    duration: int = 0      # 秒
    play: int = 0          # 播放量
    pubdate: int = 0       # Unix 时间戳


class SearchResponse(BaseModel):
    items: list[VideoItem]
    page: int
    total: int = 0
    has_more: bool = False
    sort_by: str = "relevance"


# ── 视频详情 ───────────────────────────────────────────

class FormatInfo(BaseModel):
    format_id: str
    ext: str               # 文件扩展名
    resolution: str = ""   # 分辨率（视频）
    filesize: int = 0      # 字节
    note: str = ""         # 格式说明


class VideoDetail(BaseModel):
    bvid: str
    title: str
    author: str = ""
    pic: str = ""
    duration: int = 0
    play: int = 0
    formats: list[FormatInfo] = []


# ── 下载 ──────────────────────────────────────────────

class DownloadRequest(BaseModel):
    bvid: str
    title: str = ""                      # 视频标题，用于生成文件名
    type: Optional[DownloadType] = None  # None 时使用 settings 默认值
    format: Optional[str] = None         # 不传则用设置中的默认格式
    force: bool = False                  # 为 True 时强制重新下载并覆盖本地文件


class DownloadTask(BaseModel):
    id: str
    bvid: str
    title: str = ""
    thumbnail: str = ""
    status: DownloadStatus = DownloadStatus.pending
    progress: int = 0       # 0-100
    speed: str = ""         # "2.3MB/s"
    file_path: str = ""     # 完成后的文件路径
    error: str = ""
    queue_position: int = 0
    created_at: str = ""


# ── LLM ──────────────────────────────────────────────

class LlmIdentifyRequest(BaseModel):
    query: str = Field(..., min_length=1, description="用户模糊描述")
    model: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None


class LlmIdentifyResponse(BaseModel):
    keywords: str = ""           # 推荐搜索关键词
    confidence: float = 0.0      # 0-1
    explanation: str = ""        # AI 解释
    suggestions: list[str] = []  # 备选搜索词


# ── 配置 ──────────────────────────────────────────────

class ConfigResponse(BaseModel):
    download_type: str
    audio_format: str
    video_format: str
    max_concurrent_downloads: int
    download_dir: str
    llm_base_url: str
    llm_model: str
    llm_configured: bool = False


class ConfigUpdateRequest(BaseModel):
    download_type: Optional[str] = None
    audio_format: Optional[str] = None
    video_format: Optional[str] = None
    max_concurrent_downloads: Optional[int] = None
    download_dir: Optional[str] = None
    llm_base_url: Optional[str] = None
    llm_api_key: Optional[str] = None
    llm_model: Optional[str] = None


# ── 收藏夹 ────────────────────────────────────────────

class FavoriteItem(BaseModel):
    """收藏夹中的单个视频"""
    id: str                    # 唯一 ID
    bvid: str
    title: str
    pic: str = ""              # 封面图 URL
    added_at: str = ""         # ISO 时间戳


class FavoriteFolder(BaseModel):
    """收藏夹"""
    id: str
    name: str
    items: list[FavoriteItem] = []
    created_at: str = ""
    updated_at: str = ""


class FavoriteFolderCreate(BaseModel):
    """创建收藏夹请求"""
    name: str = Field(..., min_length=1, max_length=50)


class FavoriteFolderUpdate(BaseModel):
    """更新收藏夹请求"""
    name: str = Field(..., min_length=1, max_length=50)


class FavoriteItemAdd(BaseModel):
    """添加收藏项请求"""
    bvid: str
    title: str
    pic: str = ""
