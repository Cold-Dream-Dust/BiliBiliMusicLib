"""
应用配置管理

配置优先级: 环境变量 > config.json > 默认值
运行时修改通过 API 写入 config.json
"""

import json
import tempfile
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings

CONFIG_FILE = Path(__file__).resolve().parent / "config.json"


def _load_json_config() -> dict:
    """从 JSON 文件加载持久化配置"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def save_json_config(data: dict) -> None:
    """保存配置到 JSON 文件"""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


class Settings(BaseSettings):
    """应用设置，支持环境变量覆盖"""

    # --- 下载设置 ---
    download_type: str = "audio"  # "video" | "audio"
    audio_format: str = "mp3"     # mp3 | m4a | flac
    video_format: str = "mp4"     # mp4 | webm | mkv
    max_concurrent_downloads: int = 3  # 1-10
    download_dir: str = str(Path.home() / "Downloads")
    # 缓存/临时目录 — 不对用户暴露
    temp_dir: str = tempfile.gettempdir()

    # --- B站设置 ---
    bili_sessdata: str = ""     # SESSDATA
    bili_jct: str = ""          # bili_jct
    bili_dedeuserid: str = ""   # DedeUserID
    # 是否已从浏览器自动读取到可用cookie
    browser_cookies_available: bool = False

    # --- LLM 设置 ---
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"

    class Config:
        env_prefix = "BLTOOLS_"
        # 允许通过环境变量覆盖，例如 BLTOOLS_DOWNLOAD_DIR=D:\media

    @classmethod
    def load(cls) -> "Settings":
        """加载配置: JSON 文件 + 环境变量"""
        json_config = _load_json_config()
        # 环境变量优先于 JSON
        return cls(**json_config)

    def save(self) -> None:
        """持久化当前配置到 JSON"""
        data = {
            "download_type": self.download_type,
            "audio_format": self.audio_format,
            "video_format": self.video_format,
            "max_concurrent_downloads": self.max_concurrent_downloads,
            "download_dir": self.download_dir,
            "bili_sessdata": self.bili_sessdata,
            "bili_jct": self.bili_jct,
            "bili_dedeuserid": self.bili_dedeuserid,
            "llm_base_url": self.llm_base_url,
            "llm_api_key": self.llm_api_key,
            "llm_model": self.llm_model,
        }
        save_json_config(data)


# 全局单例
settings = Settings.load()
