"""
收藏夹 API 路由

GET    /api/favorites/folders                    — 获取所有收藏夹
POST   /api/favorites/folders                    — 创建收藏夹
PUT    /api/favorites/folders/{folder_id}        — 重命名收藏夹
DELETE /api/favorites/folders/{folder_id}        — 删除收藏夹
POST   /api/favorites/folders/{folder_id}/items  — 添加视频到收藏夹
DELETE /api/favorites/folders/{folder_id}/items/{item_id} — 移除视频
POST   /api/favorites/folders/{folder_id}/download-all    — 下载全部未下载视频
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks

from models.schemas import (
    FavoriteFolderCreate,
    FavoriteFolderUpdate,
    FavoriteItemAdd,
)
from services import favorites_service as fs
from services import download_service as ds
from services.bilibili_service import get_video_info

router = APIRouter()


# ── 收藏夹 CRUD ──────────────────────────────────────

@router.get("/favorites/folders")
async def list_folders():
    """获取所有收藏夹"""
    return {"folders": fs.get_all_folders()}


@router.post("/favorites/folders")
async def create_folder(body: FavoriteFolderCreate):
    """创建收藏夹"""
    folder = fs.create_folder(body.name)
    return {"folder": folder}


@router.put("/favorites/folders/{folder_id}")
async def rename_folder(folder_id: str, body: FavoriteFolderUpdate):
    """重命名收藏夹"""
    folder = fs.update_folder(folder_id, body.name)
    if not folder:
        raise HTTPException(status_code=404, detail="收藏夹不存在")
    return {"folder": folder}


@router.delete("/favorites/folders/{folder_id}")
async def delete_folder(folder_id: str):
    """删除收藏夹"""
    if not fs.delete_folder(folder_id):
        raise HTTPException(status_code=404, detail="收藏夹不存在")
    return {"status": "deleted"}


# ── 收藏项管理 ───────────────────────────────────────

@router.post("/favorites/folders/{folder_id}/items")
async def add_item(folder_id: str, body: FavoriteItemAdd):
    """向收藏夹添加视频"""
    folder = fs.add_item(folder_id, body.bvid, body.title, body.pic)
    if not folder:
        raise HTTPException(status_code=404, detail="收藏夹不存在")
    return {"status": "added", "folder": folder}


@router.delete("/favorites/folders/{folder_id}/items/{item_id}")
async def remove_item(folder_id: str, item_id: str):
    """从收藏夹移除视频"""
    folder = fs.remove_item(folder_id, item_id)
    if not folder:
        raise HTTPException(status_code=404, detail="收藏夹不存在")
    return {"status": "removed", "folder": folder}


# ── 批量下载 ─────────────────────────────────────────

@router.post("/favorites/folders/{folder_id}/download-all")
async def download_all(folder_id: str):
    """
    下载收藏夹中尚未下载的所有视频。
    通过检查下载任务队列中的已完成任务来判断是否已下载。
    """
    folder = fs.get_folder(folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="收藏夹不存在")

    items = folder.get("items", [])
    if not items:
        raise HTTPException(status_code=400, detail="收藏夹为空")

    # 获取已完成的下载和正在进行的下载
    all_tasks = ds.get_all_tasks()
    downloaded_or_active = set()
    for t in all_tasks:
        if t.get("status") in ("done", "active", "pending"):
            downloaded_or_active.add(t.get("bvid", ""))

    submitted = 0
    skipped = 0
    errors = []

    for item in items:
        bvid = item.get("bvid", "")
        if bvid in downloaded_or_active:
            skipped += 1
            continue
        try:
            await ds.submit_download(bvid=bvid)
            downloaded_or_active.add(bvid)
            submitted += 1
        except Exception as e:
            errors.append({"bvid": bvid, "error": str(e)})

    return {
        "status": "done",
        "submitted": submitted,
        "skipped": skipped,
        "errors": errors,
        "total": len(items),
    }
