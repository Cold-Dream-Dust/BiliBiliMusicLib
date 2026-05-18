"""
B站用户视频下载器

从指定B站用户主页下载其上传的所有视频
目标用户: https://space.bilibili.com/1971709386/upload/video
"""

import os
import json
import time
import subprocess
import requests


class BilibiliDownloader:
    """B站视频下载器类"""
    
    def __init__(self, uid: str, output_dir: str = "./downloads"):
        """
        初始化下载器
        
        Args:
            uid: B站用户UID
            output_dir: 视频保存目录
        """
        self.uid = uid
        self.output_dir = output_dir
        self.api_url = f"https://api.bilibili.com/x/space/wbi/arc/search"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": f"https://space.bilibili.com/{uid}/video"
        }
        
        # 创建输出目录
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
    
    def get_user_videos(self, page: int = 1, page_size: int = 30) -> dict:
        """
        获取用户上传的视频列表
        
        Args:
            page: 页码
            page_size: 每页数量
            
        Returns:
            包含视频信息的字典
        """
        params = {
            "mid": self.uid,
            "pn": page,
            "ps": page_size,
            "order": "pubdate",  # 按发布时间排序
            "order_avoided": "true"
        }
        
        try:
            response = requests.get(
                self.api_url, 
                headers=self.headers, 
                params=params,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"获取视频列表失败: {e}")
            return {}
    
    def get_all_video_bvids(self) -> list:
        """
        获取用户所有视频的BV号
        
        Returns:
            BV号列表
        """
        all_bvids = []
        page = 1
        
        print(f"正在获取用户 {self.uid} 的视频列表...")
        
        while True:
            data = self.get_user_videos(page=page)
            
            if data.get("code") != 0:
                print(f"API返回错误: {data.get('message', '未知错误')}")
                break
            
            vlist = data.get("data", {}).get("list", {}).get("vlist", [])
            
            if not vlist:
                break
            
            for video in vlist:
                bvid = video.get("bvid")
                title = video.get("title")
                if bvid:
                    all_bvids.append({
                        "bvid": bvid,
                        "title": title
                    })
                    print(f"  找到视频: {title} ({bvid})")
            
            # 检查是否还有更多页
            total = data.get("data", {}).get("page", {}).get("count", 0)
            if page * 30 >= total:
                break
            
            page += 1
            time.sleep(1)  # 避免请求过快
        
        print(f"\n共找到 {len(all_bvids)} 个视频")
        return all_bvids
    
    def download_video(self, bvid: str, title: str = None) -> bool:
        """
        使用yt-dlp下载单个视频
        
        Args:
            bvid: 视频BV号
            title: 视频标题（用于显示）
            
        Returns:
            是否下载成功
        """
        video_url = f"https://www.bilibili.com/video/{bvid}"
        
        # 清理文件名中的非法字符
        safe_title = title if title else bvid
        for char in ['\\', '/', ':', '*', '?', '"', '<', '>', '|']:
            safe_title = safe_title.replace(char, '_')
        
        output_template = os.path.join(self.output_dir, f"{safe_title}.%(ext)s")
        
        cmd = [
            "yt-dlp",
            "-f", "bestvideo+bestaudio/best",  # 最佳画质
            "--merge-output-format", "mp4",     # 合并为mp4
            "-o", output_template,
            "--no-playlist",
            video_url
        ]
        
        print(f"\n正在下载: {title or bvid}")
        print(f"URL: {video_url}")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✓ 下载完成: {title or bvid}")
                return True
            else:
                print(f"✗ 下载失败: {result.stderr}")
                return False
        except FileNotFoundError:
            print("错误: 未找到yt-dlp，请先安装: pip install yt-dlp")
            return False
        except Exception as e:
            print(f"下载出错: {e}")
            return False
    
    def download_all_videos(self, skip_existing: bool = True):
        """
        下载用户的所有视频
        
        Args:
            skip_existing: 是否跳过已存在的视频
        """
        videos = self.get_all_video_bvids()
        
        if not videos:
            print("未找到任何视频")
            return
        
        success_count = 0
        fail_count = 0
        skip_count = 0
        
        for i, video in enumerate(videos, 1):
            bvid = video["bvid"]
            title = video["title"]
            
            print(f"\n[{i}/{len(videos)}] 处理视频: {title}")
            
            # 检查是否已存在
            if skip_existing:
                safe_title = title
                for char in ['\\', '/', ':', '*', '?', '"', '<', '>', '|']:
                    safe_title = safe_title.replace(char, '_')
                
                # 检查是否已存在同名文件
                existing_files = [f for f in os.listdir(self.output_dir) 
                                 if f.startswith(safe_title[:50])]
                if existing_files:
                    print(f"跳过已存在的视频: {title}")
                    skip_count += 1
                    continue
            
            if self.download_video(bvid, title):
                success_count += 1
            else:
                fail_count += 1
            
            # 下载间隔，避免请求过快
            time.sleep(2)
        
        print("\n" + "=" * 50)
        print("下载完成!")
        print(f"成功: {success_count}, 失败: {fail_count}, 跳过: {skip_count}")
        print(f"视频保存在: {os.path.abspath(self.output_dir)}")


def main():
    """主函数"""
    # 目标用户UID
    TARGET_UID = "1971709386"
    
    # 下载目录
    OUTPUT_DIR = "./bilibili_downloads"
    
    print("=" * 50)
    print("B站用户视频下载器")
    print("=" * 50)
    print(f"目标用户: https://space.bilibili.com/{TARGET_UID}")
    print(f"保存目录: {os.path.abspath(OUTPUT_DIR)}")
    print("=" * 50)
    
    # 创建下载器实例
    downloader = BilibiliDownloader(uid=TARGET_UID, output_dir=OUTPUT_DIR)
    
    # 开始下载所有视频
    downloader.download_all_videos(skip_existing=True)


if __name__ == "__main__":
    main()
