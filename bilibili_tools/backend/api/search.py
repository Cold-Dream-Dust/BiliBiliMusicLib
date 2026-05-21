"""
搜索 API 路由

GET  /api/search         — 搜索B站资源
GET  /api/video/{bvid}   — 获取视频详情
GET  /api/proxy/image    — 图片代理（绕过B站防盗链）
"""

from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse

from models.schemas import SearchResponse, VideoItem, VideoDetail, SortBy
from services.bilibili_service import search_bilibili, get_video_info
from core.http_client import bilibili_headers, image_proxy_client
from utils.sorting import sort_search_results

router = APIRouter()


@router.get("/search", response_model=SearchResponse)
async def search(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    page: int = Query(default=1, ge=1),
    sort_by: SortBy = Query(default=SortBy.relevance),
    order: str = Query(default="desc", pattern="^(asc|desc)$"),
):
    """
    搜索B站视频资源。

    - **q**: 搜索关键词
    - **page**: 页码（从1开始）
    - **sort_by**: relevance(综合) / views(播放量) / date(日期) / duration(时长)
    - **order**: asc 或 desc
    """
    raw = await search_bilibili(q, page)

    items = [VideoItem(**item) for item in raw.get("items", [])]

    # 排序
    sorted_items = sort_search_results(items, q, sort_by, order)

    return SearchResponse(
        items=sorted_items,
        page=page,
        total=raw.get("total", 0),
        has_more=raw.get("has_more", False),
        sort_by=sort_by.value,
    )


@router.get("/video/{bvid}", response_model=VideoDetail)
async def video_detail(bvid: str):
    """
    获取视频详细信息
    """
    info = await get_video_info(bvid)
    if not info:
        raise HTTPException(status_code=404, detail="视频未找到或API错误")
    return VideoDetail(**info)


@router.get("/proxy/image")
async def proxy_image(url: str = Query(..., description="原始图片URL")):
    """
    图片代理 — 绕过B站防盗链（Referer 限制）
    """
    async with image_proxy_client() as client:
        try:
            resp = await client.get(url, headers=bilibili_headers())
            resp.raise_for_status()
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"图片获取失败: {e}")

    content_type = resp.headers.get("content-type", "image/jpeg")
    return StreamingResponse(
        content=resp.aiter_bytes(),
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=86400"},
    )
