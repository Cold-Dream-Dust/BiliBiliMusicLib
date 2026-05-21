"""
下载服务 — HTTP 直抓 B站 playinfo + 流式下载
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import time
import uuid
from pathlib import Path
from typing import Optional

import httpx

from config import settings
from core.http_client import (
    BILIBILI_UA,
    bilibili_headers,
    download_page_client,
    download_stream_client,
)


# ── 任务存储 ──────────────────────────────────────────
_tasks: dict[str, dict] = {}
_semaphore: Optional[asyncio.Semaphore] = None
_TASKS_FILE = Path(__file__).resolve().parent.parent / "tasks.json"


def save_tasks():
    """持久化任务到 JSON 文件"""
    try:
        data = list(_tasks.values())
        with open(_TASKS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[DownloadService] 保存任务失败: {e}")


def load_tasks():
    """从 JSON 文件恢复任务"""
    global _tasks
    if not _TASKS_FILE.exists():
        return
    try:
        with open(_TASKS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        for t in data:
            tid = t.get("id", "")
            if tid and tid not in _tasks:
                t["progress"] = 0
                t["speed"] = ""
                if t.get("status") in ("active", "pending"):
                    t["status"] = "failed"
                    t["error"] = "上次会话中断"
                _tasks[tid] = t
        print(f"[DownloadService] 恢复了 {len(_tasks)} 个历史任务")
    except Exception as e:
        print(f"[DownloadService] 加载任务失败: {e}")

def _get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(settings.max_concurrent_downloads)
    return _semaphore


def _update_semaphore() -> None:
    global _semaphore
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return
    _semaphore = asyncio.Semaphore(settings.max_concurrent_downloads)


def _build_cookie_header() -> str:
    """用设置中的三个字段构建 Cookie 请求头"""
    parts = []
    for key, val in [
        ("SESSDATA", settings.bili_sessdata),
        ("bili_jct", settings.bili_jct),
        ("DedeUserID", settings.bili_dedeuserid),
    ]:
        v = (val or "").strip()
        if v:
            parts.append(f"{key}={v}")
    return "; ".join(parts)


async def _fetch_playinfo(bvid: str) -> Optional[dict]:
    """请求B站视频页，提取 __playinfo__ JSON"""
    url = f"https://www.bilibili.com/video/{bvid}"
    headers = bilibili_headers()
    cookie = _build_cookie_header()
    if cookie:
        headers["Cookie"] = cookie

    async with download_page_client() as client:
        try:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            html = resp.text
        except Exception as e:
            print(f"[DownloadService] 请求视频页失败: {e}")
            return None

    # 提取 window.__playinfo__
    m = re.search(r"window\.__playinfo__\s*=\s*(\{.+?\})\s*</script>", html, re.DOTALL)
    if not m:
        # 尝试非贪婪
        m = re.search(r"window\.__playinfo__\s*=\s*(.+?)</script>", html, re.DOTALL)
    if not m:
        print("[DownloadService] 未找到 __playinfo__（可能需要登录）")
        return None

    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError as e:
        print(f"[DownloadService] __playinfo__ 解析失败: {e}")
        return None


def _pick_best_audio(playinfo: dict) -> Optional[str]:
    """从 playinfo 中选最高音质音频 URL"""
    dash = playinfo.get("data", {}).get("dash", {})
    audios = dash.get("audio", [])
    if not audios:
        return None
    # 按 bitrate 降序选最高音质
    best = max(audios, key=lambda a: a.get("bandwidth", 0))
    return best.get("baseUrl") or best.get("base_url") or best.get("backupUrl") or best.get("backup_url")


def _pick_best_video(playinfo: dict) -> Optional[str]:
    """从 playinfo 中选最高画质视频 URL"""
    dash = playinfo.get("data", {}).get("dash", {})
    videos = dash.get("video", [])
    if not videos:
        return None
    best = max(videos, key=lambda v: v.get("bandwidth", 0))
    return best.get("baseUrl") or best.get("base_url") or best.get("backupUrl") or best.get("backup_url")


async def _download_stream(url: str, output_path: str, task: dict) -> bool:
    """流式下载单个文件，实时更新进度"""
    headers = bilibili_headers()
    async with download_stream_client() as client:
        try:
            async with client.stream("GET", url, headers=headers) as resp:
                resp.raise_for_status()
                total = int(resp.headers.get("content-length", 0))
                downloaded = 0
                start_time = time.time()
                with open(output_path, "wb") as f:
                    async for chunk in resp.aiter_bytes(chunk_size=65536):
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total > 0:
                            task["progress"] = min(99, int(downloaded / total * 100))
                            elapsed = time.time() - start_time
                            if elapsed > 0:
                                speed_bytes = downloaded / elapsed
                                if speed_bytes > 1_000_000:
                                    task["speed"] = f"{speed_bytes/1_000_000:.1f}MB/s"
                                elif speed_bytes > 1_000:
                                    task["speed"] = f"{speed_bytes/1_000:.0f}KB/s"
                return True
        except Exception as e:
            print(f"[DownloadService] 下载流失败: {e}")
            task["error"] = str(e)[:300]
            return False


def _find_output_file(output_path: str, ext: str) -> Optional[str]:
    """查找实际输出文件（yt-dlp 可能修改扩展名）"""
    directory = os.path.dirname(output_path)
    base = os.path.basename(output_path)
    if os.path.exists(output_path + f".{ext}"):
        return output_path + f".{ext}"
    # 搜索匹配文件
    if os.path.exists(directory):
        for f in os.listdir(directory):
            if f.startswith(base) and f.endswith(f".{ext}"):
                return os.path.join(directory, f)
    return None


async def submit_download(
    bvid: str,
    title: str = "",
    thumbnail: str = "",
    download_type: Optional[str] = None,
    fmt: Optional[str] = None,
    force: bool = False,  # 为 True 时忽略本地文件检测，强制下载
) -> str:
    task_id = str(uuid.uuid4())[:8]
    dl_type = download_type or settings.download_type
    out_fmt = fmt or (settings.audio_format if dl_type == "audio" else settings.video_format)

    # 用标题做文件名：优先提取《》内文本，否则用原标题
    raw_title = extract_music_title(title or bvid)
    safe_title = _sanitize_filename(raw_title)

    # 检测本地文件是否已存在
    output_dir = Path(settings.download_dir)
    expected_file = str(output_dir / f"{safe_title}.{out_fmt}")
    file_exists = os.path.exists(expected_file)

    task = {
        "id": task_id,
        "bvid": bvid,
        "title": title or bvid,
        "raw_title": raw_title,
        "safe_title": safe_title,
        "thumbnail": thumbnail,
        "status": "pending",
        "progress": 0,
        "speed": "",
        "file_path": expected_file if file_exists else "",
        "error": "",
        "queue_position": 0,
        "created_at": str(time.time()),
        "priority": 0,
        "download_type": dl_type,
        "format": out_fmt,
        "paused": False,
        "file_exists": file_exists,
        "force": force,
    }
    _tasks[task_id] = task
    save_tasks()

    if file_exists and not force:
        # 文件已存在 — 直接标记为失败，前端可点击"仍要下载"
        task["status"] = "failed"
        task["error"] = f"本地文件已存在: {safe_title}.{out_fmt}"
        task["progress"] = 0
        save_tasks()
        print(f"[DownloadService] 文件已存在，跳过: {safe_title}.{out_fmt}")
        return task_id

    asyncio.create_task(_run_download(task_id))
    return task_id


async def _run_download(task_id: str) -> None:
    task = _tasks.get(task_id)
    if not task:
        return

    sem = _get_semaphore()
    async with sem:
        task["status"] = "active"
        task["progress"] = 0
        task["speed"] = ""
        task["error"] = ""
        task["paused"] = False

        safe_title = task.get("safe_title") or _sanitize_filename(task["title"])
        output_dir = Path(settings.download_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_base = str(output_dir / safe_title)
        task["_output_dir"] = str(output_dir)

        print(f"[DownloadService] 开始下载: {task['title']} (BV={task['bvid']}) → {task['format']}")

        try:
            # 1. 获取 playinfo
            playinfo = await _fetch_playinfo(task["bvid"])
            if not playinfo:
                task["error"] = "无法获取视频信息（可能需要登录B站，请在设置中填写 SESSDATA / bili_jct）"
                settings.browser_cookies_available = False
                task["status"] = "failed"
                return

            # 2. 选流
            if task["download_type"] == "audio":
                stream_url = _pick_best_audio(playinfo)
                if not stream_url:
                    task["error"] = "未找到音频流（可能为付费/限制内容）"
                    task["status"] = "failed"
                    return
                output_file = output_base + "." + task["format"]

                # 下载音频
                ok = await _download_stream(stream_url, output_file, task)
                if ok:
                    task["status"] = "done"
                    task["progress"] = 100
                    task["file_path"] = output_file
                    settings.browser_cookies_available = True
                    save_tasks()
                    print(f"[DownloadService] ✓ 完成: {task['title']}")
                else:
                    task["status"] = "failed"
            else:
                # 视频: 分别下载视频流 + 音频流，用 ffmpeg 合并
                video_url = _pick_best_video(playinfo)
                audio_url = _pick_best_audio(playinfo)
                if not video_url:
                    task["error"] = "未找到视频流"
                    task["status"] = "failed"
                    return

                video_tmp = output_base + ".video.tmp"
                audio_tmp = output_base + ".audio.tmp"
                output_file = output_base + "." + task["format"]

                ok_v = await _download_stream(video_url, video_tmp, task)
                if audio_url:
                    ok_a = await _download_stream(audio_url, audio_tmp, task)
                else:
                    ok_a = True  # 无独立音轨也能接受

                if ok_v:
                    # ffmpeg 合并
                    if ok_a and os.path.exists(audio_tmp):
                        loop = asyncio.get_running_loop()
                        result = await loop.run_in_executor(
                            None,
                            lambda: _merge_with_ffmpeg(video_tmp, audio_tmp, output_file),
                        )
                        if result:
                            task["status"] = "done"
                            task["progress"] = 100
                            task["file_path"] = output_file
                            settings.browser_cookies_available = True
                            print(f"[DownloadService] ✓ 完成: {task['title']}")
                        else:
                            task["error"] = "ffmpeg 合并失败，请检查 ffmpeg 是否安装"
                            task["status"] = "failed"
                    else:
                        # 无音轨，直接重命名视频
                        os.replace(video_tmp, output_file)
                        task["status"] = "done"
                        task["progress"] = 100
                        task["file_path"] = output_file
                        settings.browser_cookies_available = True
                        print(f"[DownloadService] ✓ 完成: {task['title']}")
                else:
                    task["status"] = "failed"

                # 清理临时文件
                for tmp in [video_tmp, audio_tmp]:
                    if os.path.exists(tmp):
                        os.remove(tmp)

        except Exception as e:
            task["status"] = "failed"
            task["error"] = str(e) if str(e) else "下载异常"
            settings.browser_cookies_available = False
            save_tasks()
            print(f"[DownloadService] ✗ 异常: {task['title']}: {e}")


def _merge_with_ffmpeg(video_path: str, audio_path: str, output_path: str) -> bool:
    """用 ffmpeg 合并视频和音频"""
    import subprocess
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", audio_path,
        "-c:v", "copy",
        "-c:a", "aac",
        "-shortest",
        output_path,
    ]
    try:
        subprocess.run(cmd, capture_output=True, check=True, timeout=120)
        return True
    except Exception as e:
        print(f"[DownloadService] ffmpeg 错误: {e}")
        return False


def get_all_tasks() -> list[dict]:
    return list(_tasks.values())


def get_task(task_id: str) -> Optional[dict]:
    return _tasks.get(task_id)


def cancel_task(task_id: str) -> bool:
    task = _tasks.get(task_id)
    if task and task["status"] in ("pending", "active"):
        task["status"] = "failed"
        task["error"] = "用户取消"
        save_tasks()
        return True
    return False


def remove_task(task_id: str) -> bool:
    task = _tasks.get(task_id)
    if task and task["status"] in ("done", "failed"):
        del _tasks[task_id]
        save_tasks()
        return True
    return False


def prioritize_task(task_id: str) -> bool:
    task = _tasks.get(task_id)
    if task and task["status"] == "pending":
        task["priority"] = 1
        return True
    return False


def _sanitize_filename(name: str) -> str:
    for ch in ['\\', '/', ':', '*', '?', '"', '<', '>', '|']:
        name = name.replace(ch, '_')
    if len(name) > 80:
        name = name[:77] + "..."
    return name


def extract_music_title(title: str) -> str:
    """
    从标题中提取《》内的文本作为文件名。
    只取第一个匹配，没有则返回原标题。
    例: 「【AI翻唱】周杰伦《晴天》完整版」 → 「晴天」
    """
    import re
    m = re.search(r'《([^》]+)》', title)
    if m:
        content = m.group(1).strip()
        if content:
            return content
    return title
