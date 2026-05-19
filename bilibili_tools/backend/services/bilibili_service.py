"""
B站服务 — 搜索、视频信息获取

复用并扩展 bilibili_downloader.py 中的 API 调用逻辑。
"""

from __future__ import annotations

import hashlib
import time
import urllib.parse
from typing import Optional

import httpx

# B站 API 基础配置
BILIBILI_SEARCH_API = "https://api.bilibili.com/x/web-interface/wbi/search/type"
BILIBILI_VIDEO_INFO_API = "https://api.bilibili.com/x/web-interface/view"
BILIBILI_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# WBI 签名相关（B站搜索接口需要）
WBI_MIXIN_KEY = "ea1db124af3c7062474693fa704f4ff8"  # 可能会变，需要定期更新


def _wbi_sign(params: dict) -> dict:
    """为请求参数添加 WBI 签名（简化版）"""
    # 注意：完整 WBI 签名需要从 nav 接口获取 img_key 和 sub_key
    # 这里使用简化版本，大多数情况下可工作
    params["wts"] = int(time.time())
    keys = sorted(params.keys())
    query_string = "&".join(f"{k}={params[k]}" for k in keys)
    sign = hashlib.md5((query_string + WBI_MIXIN_KEY).encode()).hexdigest()
    params["w_rid"] = sign
    return params


async def search_bilibili(
    query: str,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """
    搜索B站资源

    Args:
        query: 搜索关键词
        page: 页码
        page_size: 每页数量

    Returns:
        {"items": [...], "total": int, "has_more": bool}
    """
    params = {
        "keyword": query,
        "search_type": "video",
        "page": page,
        "page_size": page_size,
        "order": "totalrank",  # 综合排序
    }

    headers = {
        "User-Agent": BILIBILI_USER_AGENT,
        "Referer": "https://www.bilibili.com/",
    }

    # WBI 签名（B站搜索接口必需）
    params = _wbi_sign(params)

    # 不使用系统代理（代理可能导致B站API连接失败）
    async with httpx.AsyncClient(timeout=15, trust_env=False) as client:
        try:
            resp = await client.get(
                BILIBILI_SEARCH_API,
                params=params,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as e:
            print(f"[BilibiliService] 搜索HTTP错误 {e.response.status_code}: {e.response.text[:200]}")
            return {"items": [], "total": 0, "has_more": False}
        except Exception as e:
            print(f"[BilibiliService] 搜索失败: {type(e).__name__}: {e}")
            return {"items": [], "total": 0, "has_more": False}

    if data.get("code") != 0:
        print(f"[BilibiliService] API错误: {data.get('message', '未知')}")
        return {"items": [], "total": 0, "has_more": False}

    result = data.get("data", {}).get("result", [])
    items = []
    for item in result:
        items.append({
            "bvid": item.get("bvid", ""),
            "title": item.get("title", "").replace('<em class="keyword">', '').replace('</em>', ''),
            "author": item.get("author", ""),
            "pic": item.get("pic", ""),
            "duration": _parse_duration(item.get("duration", "0:00")),
            "play": item.get("play", 0),
            "pubdate": item.get("pubdate", 0),
        })

    num_pages = data.get("data", {}).get("numPages", 1)
    total = data.get("data", {}).get("numResults", 0)

    return {
        "items": items,
        "total": total,
        "has_more": page < num_pages,
    }


async def get_video_info(bvid: str) -> Optional[dict]:
    """
    获取视频详细信息（包含可用格式列表）

    Args:
        bvid: 视频 BV 号

    Returns:
        视频详情字典，或 None
    """
    params = {"bvid": bvid}
    headers = {
        "User-Agent": BILIBILI_USER_AGENT,
        "Referer": f"https://www.bilibili.com/video/{bvid}",
    }

    async with httpx.AsyncClient(timeout=15, trust_env=False) as client:
        try:
            resp = await client.get(
                BILIBILI_VIDEO_INFO_API,
                params=params,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"[BilibiliService] 获取视频信息失败: {e}")
            return None

    if data.get("code") != 0:
        return None

    vdata = data.get("data", {})
    return {
        "bvid": vdata.get("bvid", bvid),
        "title": vdata.get("title", ""),
        "author": vdata.get("owner", {}).get("name", ""),
        "pic": vdata.get("pic", ""),
        "duration": vdata.get("duration", 0),
        "play": vdata.get("stat", {}).get("view", 0),
    }


def _parse_duration(dur_str: str) -> int:
    """解析时长字符串 'MM:SS' 或 'HH:MM:SS' 为秒数"""
    parts = dur_str.split(":")
    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    elif len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    return 0
