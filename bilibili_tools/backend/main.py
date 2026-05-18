"""
Bilibili Tools — FastAPI 应用入口

启动方式:
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# ── 创建应用 ──────────────────────────────────────────
app = FastAPI(
    title="Bilibili Tools",
    description="B站媒体搜索与下载工具",
    version="0.1.0",
)

# ── CORS 配置（允许前端开发服务器跨域）─────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发阶段全放行，生产应限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 注册路由 ──────────────────────────────────────────
from api.search import router as search_router
from api.download import router as download_router
from api.llm import router as llm_router

app.include_router(search_router, prefix="/api")
app.include_router(download_router, prefix="/api")
app.include_router(llm_router, prefix="/api")


# ── 健康检查 ──────────────────────────────────────────
@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}


@app.get("/api/config")
async def get_config():
    """获取当前配置（隐藏敏感字段）"""
    from config import settings
    return {
        "download_type": settings.download_type,
        "audio_format": settings.audio_format,
        "video_format": settings.video_format,
        "max_concurrent_downloads": settings.max_concurrent_downloads,
        "download_dir": settings.download_dir,
        "bili_sessdata": "***" if settings.bili_sessdata else "",
        "bili_jct": "***" if settings.bili_jct else "",
        "bili_dedeuserid": settings.bili_dedeuserid,
        "browser_cookies_available": settings.browser_cookies_available,
        "llm_base_url": settings.llm_base_url,
        "llm_model": settings.llm_model,
        "llm_configured": bool(settings.llm_api_key),
    }


@app.put("/api/config")
async def update_config(payload: dict):
    """更新配置并持久化"""
    from config import settings

    updatable = [
        "download_type", "audio_format", "video_format",
        "max_concurrent_downloads", "download_dir",
        "bili_sessdata", "bili_jct", "bili_dedeuserid",
        "llm_base_url", "llm_api_key", "llm_model",
    ]
    for key in updatable:
        if key in payload and payload[key] is not None:
            setattr(settings, key, payload[key])

    settings.save()

    # 更新下载并发信号量
    from services.download_service import _update_semaphore
    _update_semaphore()

    return {"status": "saved"}


# ── 生产模式: 挂载前端静态文件 ──────────────────────────
frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
