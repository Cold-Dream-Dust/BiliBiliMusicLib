"""
下载 API 路由

POST   /api/download              — 提交下载任务
GET    /api/downloads             — 获取所有任务
GET    /api/downloads/poll        — 轮询进度更新
DELETE /api/downloads/{task_id}   — 取消下载
POST   /api/downloads/{task_id}/prioritize — 优先下载
DELETE /api/downloads/{task_id}/remove     — 删除任务
GET    /api/downloads/{task_id}/open-folder — 打开文件夹
"""

import os
import subprocess
import platform
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from models.schemas import DownloadRequest
from services import download_service as ds
from config import settings

router = APIRouter()


@router.post("/download")
async def submit_download(req: DownloadRequest):
    """
    提交下载任务。使用默认设置时 type 和 format 可留空。
    """
    task_id = await ds.submit_download(
        bvid=req.bvid,
        download_type=req.type.value if req.type else None,
        fmt=req.format,
    )
    task = ds.get_task(task_id)
    if not task:
        raise HTTPException(status_code=500, detail="创建任务失败")
    return {
        "task_id": task_id,
        "status": task["status"],
    }


@router.get("/downloads")
async def list_downloads():
    """
    获取所有下载任务及其状态
    """
    tasks = ds.get_all_tasks()
    return {"tasks": tasks}


@router.delete("/downloads/{task_id}")
async def cancel_download(task_id: str):
    """
    取消下载（仅 pending/active 状态）
    """
    if not ds.cancel_task(task_id):
        raise HTTPException(status_code=404, detail="任务不存在或无法取消")
    return {"status": "cancelled"}


@router.delete("/downloads/{task_id}/remove")
async def remove_download(task_id: str):
    """
    删除已完成/失败的任务
    """
    if not ds.remove_task(task_id):
        raise HTTPException(status_code=404, detail="任务不存在或无法删除")
    return {"status": "removed"}


@router.post("/downloads/{task_id}/prioritize")
async def prioritize_download(task_id: str):
    """
    提升等待中任务的优先级
    """
    if not ds.prioritize_task(task_id):
        raise HTTPException(status_code=404, detail="任务不存在或无法优先")
    return {"status": "prioritized"}


@router.get("/downloads/poll")
async def poll_progress():
    """
    前端轮询 — 返回所有任务的最新状态
    """
    tasks = ds.get_all_tasks()
    return {
        "tasks": [
            {
                "id": t["id"],
                "status": t["status"],
                "progress": t.get("progress", 0),
                "speed": t.get("speed", ""),
                "error": t.get("error", ""),
                "file_path": t.get("file_path", ""),
                "paused": t.get("paused", False),
            }
            for t in tasks
        ]
    }


@router.get("/downloads/{task_id}/open-folder")
async def open_folder(task_id: str):
    """
    打开下载任务所在文件夹
    """
    task = ds.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    folder = None
    fp = task.get("file_path", "")
    if fp and os.path.exists(fp):
        folder = os.path.dirname(fp)
    else:
        folder = task.get("_output_dir", settings.download_dir)

    if not folder or not os.path.exists(folder):
        raise HTTPException(status_code=404, detail="文件夹不存在")

    try:
        system = platform.system()
        if system == "Windows":
            os.startfile(folder)
        elif system == "Darwin":
            subprocess.run(["open", folder])
        else:
            subprocess.run(["xdg-open", folder])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"无法打开文件夹: {e}")

    return {"status": "opened", "folder": folder}
