"""
收藏夹服务 — JSON 文件持久化存储
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

_FAVORITES_FILE = Path(__file__).resolve().parent.parent / "favorites.json"
_folders: dict[str, dict] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def save():
    """持久化到 JSON 文件"""
    try:
        data = list(_folders.values())
        with open(_FAVORITES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[FavoritesService] 保存失败: {e}")


def load():
    """从 JSON 文件恢复"""
    global _folders
    if not _FAVORITES_FILE.exists():
        return
    try:
        with open(_FAVORITES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        for folder in data:
            fid = folder.get("id", "")
            if fid:
                _folders[fid] = folder
        print(f"[FavoritesService] 恢复了 {len(_folders)} 个收藏夹")
    except Exception as e:
        print(f"[FavoritesService] 加载失败: {e}")


def get_all_folders() -> list[dict]:
    """获取所有收藏夹"""
    return sorted(
        list(_folders.values()),
        key=lambda f: f.get("created_at", ""),
        reverse=True,
    )


def get_folder(folder_id: str) -> Optional[dict]:
    """获取单个收藏夹"""
    return _folders.get(folder_id)


def create_folder(name: str) -> dict:
    """创建收藏夹"""
    folder_id = uuid.uuid4().hex[:12]
    now = _now_iso()
    folder = {
        "id": folder_id,
        "name": name.strip(),
        "items": [],
        "created_at": now,
        "updated_at": now,
    }
    _folders[folder_id] = folder
    save()
    return folder


def update_folder(folder_id: str, name: str) -> Optional[dict]:
    """重命名收藏夹"""
    folder = _folders.get(folder_id)
    if not folder:
        return None
    folder["name"] = name.strip()
    folder["updated_at"] = _now_iso()
    save()
    return folder


def delete_folder(folder_id: str) -> bool:
    """删除收藏夹"""
    if folder_id not in _folders:
        return False
    del _folders[folder_id]
    save()
    return True


def add_item(folder_id: str, bvid: str, title: str, pic: str = "") -> Optional[dict]:
    """向收藏夹添加视频"""
    folder = _folders.get(folder_id)
    if not folder:
        return None

    # 检查是否已存在（按 bvid 去重）
    for item in folder["items"]:
        if item.get("bvid") == bvid:
            return folder  # 已存在，直接返回

    item = {
        "id": uuid.uuid4().hex[:12],
        "bvid": bvid,
        "title": title,
        "pic": pic,
        "added_at": _now_iso(),
    }
    folder["items"].append(item)
    folder["updated_at"] = _now_iso()
    save()
    return folder


def remove_item(folder_id: str, item_id: str) -> Optional[dict]:
    """从收藏夹移除视频"""
    folder = _folders.get(folder_id)
    if not folder:
        return None
    folder["items"] = [i for i in folder["items"] if i.get("id") != item_id]
    folder["updated_at"] = _now_iso()
    save()
    return folder


def get_folder_undownloaded_items(folder_id: str) -> list[dict]:
    """获取收藏夹中尚未下载的视频项（需要外部传入已下载的 bvid 集合来判断）"""
    folder = _folders.get(folder_id)
    if not folder:
        return []
    return folder.get("items", [])
