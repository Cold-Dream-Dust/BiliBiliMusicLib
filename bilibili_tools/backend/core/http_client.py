"""
共享 HTTP 客户端 — 项目中所有外部 HTTP 请求的唯一出口

集中管理:
- User-Agent / Referer 等公共请求头
- 超时策略（搜索/下载/图片代理分别设定）
- 代理绕过 (trust_env=False)
- Cookie 注入

使用方式:
    from core.http_client import http

    async with http.search_client() as client:
        resp = await client.get("https://api.bilibili.com/...")
"""

from __future__ import annotations

from typing import Optional

import httpx

# ── 公共常量 ──────────────────────────────────────────
BILIBILI_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
BILIBILI_REFERER = "https://www.bilibili.com/"

# ── 公共请求头 ────────────────────────────────────────
def bilibili_headers(extra: Optional[dict] = None) -> dict:
    """返回带标准 UA+Referer 的请求头"""
    h = {
        "User-Agent": BILIBILI_UA,
        "Referer": BILIBILI_REFERER,
    }
    if extra:
        h.update(extra)
    return h


# ── 客户端工厂 ────────────────────────────────────────
# 所有客户端统一参数:
#   trust_env=False — 不走系统代理（避免国内环境代理干扰B站直连）
#   http2=False     — 禁用HTTP/2（兼容性问题）


def search_client(timeout: float = 15) -> httpx.AsyncClient:
    """搜索 API 客户端（短超时）"""
    return httpx.AsyncClient(
        timeout=timeout,
        trust_env=False,
        http2=False,
    )


def download_page_client(timeout: float = 20) -> httpx.AsyncClient:
    """下载页面请求客户端（中等超时）"""
    return httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=True,
        trust_env=False,
        http2=False,
    )


def download_stream_client(timeout: float = 300) -> httpx.AsyncClient:
    """流式下载客户端（长超时，用于大文件）"""
    return httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=True,
        trust_env=False,
        http2=False,
    )


def image_proxy_client(timeout: float = 15) -> httpx.AsyncClient:
    """图片代理客户端"""
    return httpx.AsyncClient(
        timeout=timeout,
        trust_env=False,
        http2=False,
    )
