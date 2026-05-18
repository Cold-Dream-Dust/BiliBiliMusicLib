"""
排序算法 — 搜索结果加权评分 & 下载队列排序

搜索结果采用多因子加权评分模型：
  score = w1 * title_match + w2 * normalized_views + w3 * recency + w4 * duration_match

下载队列支持 FIFO + 优先级提升。
"""

from __future__ import annotations

import math
import time
from typing import Callable

from models.schemas import VideoItem, SortBy


# ── 权重配置（可调） ────────────────────────────────────

DEFAULT_WEIGHTS = {
    "title_match": 0.40,   # 标题关键词匹配度
    "views":       0.25,   # 播放量
    "recency":     0.20,   # 发布时间新鲜度
    "duration":    0.15,   # 时长匹配度
}


def _title_match_score(title: str, query: str) -> float:
    """计算标题与搜索词的匹配度 (0-1)"""
    if not query or not title:
        return 0.0
    title_lower = title.lower()
    # 分词：支持中英文混合
    keywords = query.lower().split()
    matched = sum(1 for kw in keywords if kw in title_lower)
    return matched / max(len(keywords), 1)


def _normalize_views(views: int, max_views: int) -> float:
    """播放量归一化 (对数尺度)"""
    if views <= 0 or max_views <= 0:
        return 0.0
    return math.log(views + 1) / math.log(max_views + 1)


def _recency_score(pubdate: int) -> float:
    """发布时间新鲜度 (指数衰减)，越新越高"""
    if pubdate <= 0:
        return 0.0
    now = int(time.time())
    age_seconds = max(0, now - pubdate)
    age_days = age_seconds / 86400.0
    # 半衰期 90 天
    return math.exp(-age_days / 90.0)


def _duration_match_score(duration: int, prefer_longer: bool = False) -> float:
    """时长匹配度。音频模式偏好中等长度 (60-600s)"""
    if duration <= 0:
        return 0.3  # 无时长信息给中等分
    if prefer_longer:
        # 偏好 > 60s 的内容
        return min(1.0, math.log(duration + 1) / math.log(601))
    # 默认：60-600s 之间得高分
    if 60 <= duration <= 600:
        return 1.0 - abs(duration - 300) / 300 * 0.5
    elif duration < 60:
        return max(0.2, duration / 60.0)
    else:
        return max(0.3, 600.0 / duration)


def compute_relevance_score(
    video: VideoItem,
    query: str,
    max_views: int,
    prefer_longer: bool = False,
    weights: dict | None = None,
) -> float:
    """
    计算单个视频的综合相关度评分

    Args:
        video: 视频信息
        query: 搜索关键词
        max_views: 当前结果集中最大播放量（用于归一化）
        prefer_longer: 是否偏好长内容（音频模式）
        weights: 自定义权重

    Returns:
        0-1 之间的评分
    """
    w = weights or DEFAULT_WEIGHTS
    score = (
        w["title_match"] * _title_match_score(video.title, query)
        + w["views"] * _normalize_views(video.play, max_views)
        + w["recency"] * _recency_score(video.pubdate)
        + w["duration"] * _duration_match_score(video.duration, prefer_longer)
    )
    return round(score, 4)


def sort_search_results(
    videos: list[VideoItem],
    query: str,
    sort_by: SortBy = SortBy.relevance,
    order: str = "desc",
    prefer_longer: bool = False,
) -> list[VideoItem]:
    """
    对搜索结果排序

    Args:
        videos: 原始视频列表
        query: 搜索关键词
        sort_by: 排序方式
        order: asc 或 desc
        prefer_longer: 音频模式

    Returns:
        排序后的视频列表
    """
    if not videos:
        return []

    max_views = max((v.play for v in videos), default=1)

    if sort_by == SortBy.relevance:
        # 综合评分排序
        scored = [
            (v, compute_relevance_score(v, query, max_views, prefer_longer))
            for v in videos
        ]
        scored.sort(key=lambda x: x[1], reverse=(order == "desc"))
        return [v for v, _ in scored]

    elif sort_by == SortBy.views:
        videos.sort(key=lambda v: v.play, reverse=(order == "desc"))

    elif sort_by == SortBy.date:
        videos.sort(key=lambda v: v.pubdate, reverse=(order == "desc"))

    elif sort_by == SortBy.duration:
        videos.sort(key=lambda v: v.duration, reverse=(order == "desc"))

    return videos


def sort_download_queue(
    tasks: list[dict],
    sort_key: str = "created_at",
    reverse: bool = False,
) -> list[dict]:
    """
    下载队列排序（默认 FIFO，支持优先级提升）

    Args:
        tasks: 下载任务列表，每个任务含 priority(0=普通,1=高), created_at
        sort_key: 主排序键
        reverse: 是否逆序

    Returns:
        排序后的任务列表
    """
    def sort_fn(task: dict) -> tuple:
        priority = task.get("priority", 0)
        created = task.get("created_at", "")
        # 高优先级排前面
        return (-priority, created if not reverse else "")

    return sorted(tasks, key=sort_fn)
