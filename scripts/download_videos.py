#!/usr/bin/env python3
"""从 mixkit.co 下载免费可商用视频素材（按主题）。

用法：
    python3 download_videos.py --topics rocket,space,jet --out-dir /tmp/rm/vids

内置主题 → mixkit 主题页映射。脚本抓取主题页 HTML 提取视频直链，
串行下载（并行会被限流整批失败）+ 失败自动重试。
"""
import argparse
import re
import subprocess
import time
from pathlib import Path

TOPIC_PAGES = {
    "rocket": ["rocket-launch"],
    "space": ["space-station"],
    "jet": ["fighter-jet"],
    "ship": ["ship"],
    "factory": ["factory", "industrial-factory"],
    "technology": ["technology"],
    "city": ["city"],
    "nature": ["nature"],
    "education": ["education", "students-classroom"],
    "energy": ["wind-turbine", "solar-energy"],
    # 细分主题（2026-08-16 扩充，保证素材与内容匹配，避免多期复用同一批素材）
    "computer": ["computer", "coding"],
    "robot": ["robot", "robotics"],
    "power": ["electricity", "power-lines"],
    "finance": ["finance", "stock-market", "trading"],
    "office": ["office", "business-meeting"],
    "data": ["data", "big-data"],
    "agriculture": ["agriculture", "farm"],
    "food": ["food", "grain", "wheat"],
    "construction": ["construction"],
    "medical": ["medical", "hospital"],
    "car": ["car", "automobile"],
    "railway": ["railway", "train"],
    "oil": ["oil", "petroleum"],
    "communication": ["network", "internet"],
}

MIXKIT_BASE = "https://mixkit.co/free-stock-video/{}"
ASSET_RE = re.compile(r"https://assets\.mixkit\.co/videos/(\d+)/(\d+)-720\.mp4")


def find_assets(topic_page: str) -> list[str]:
    url = MIXKIT_BASE.format(topic_page)
    try:
        r = subprocess.run(
            ["curl", "-sL", "--max-time", "30", "-o", "/tmp/mixkit-page.html", url],
            capture_output=True,
        )
        if r.returncode != 0:
            return []
        html = Path("/tmp/mixkit-page.html").read_text(errors="ignore")
        matches = re.findall(r"https://assets\.mixkit\.co/videos/(\d+)/(\d+)-720\.mp4", html)
        return sorted({f"https://assets.mixkit.co/videos/{a}/{b}-720.mp4" for a, b in matches})[:5]
    except Exception:
        return []


def download(url: str, dest: Path, tries: int = 4) -> bool:
    for i in range(tries):
        r = subprocess.run(
            ["curl", "-sL", "--max-time", "100", "-o", str(dest), url,
             "-w", "%{http_code} %{size_download}"],
            capture_output=True,
            text=True,
        )
        out = r.stdout.strip()
        if r.returncode == 0 and dest.exists() and dest.stat().st_size > 100000:
            print(f"  ✓ {dest.name} ({dest.stat().st_size // 1024} KB)")
            return True
        print(f"  ! {dest.name} 第{i+1}次失败（{out}），重试...")
        time.sleep(4)
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="下载 mixkit 免费视频素材")
    parser.add_argument("--topics", required=True, help="逗号分隔主题，如 rocket,space")
    parser.add_argument("--out-dir", default="/tmp/rm/vids", help="输出目录")
    parser.add_argument("--max-per-topic", type=int, default=3, help="每主题最多下载数")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    topics = [t.strip() for t in args.topics.split(",") if t.strip()]
    for topic in topics:
        pages = TOPIC_PAGES.get(topic, [topic])
        print(f"[{topic}] 搜索主题页：{', '.join(pages)}")
        assets: list[str] = []
        for page in pages:
            assets.extend(find_assets(page))
        # 去重保序
        seen: set[str] = set()
        uniq = [a for a in assets if not (a in seen or seen.add(a))]
        if not uniq:
            print(f"  ✗ 未找到素材（主题页可能不存在，可改 --topics 用其他主题）")
            continue
        for url in uniq[: args.max_per_topic]:
            vid_id = url.split("/")[-2]
            dest = out_dir / f"{topic}-{vid_id}.mp4"
            if dest.exists() and dest.stat().st_size > 100000:
                print(f"  = 已存在，跳过 {dest.name}")
                continue
            download(url, dest)
        print(f"  → 完成，共下载 {len(list(out_dir.glob(f'{topic}-*.mp4')))} 个")

    print(f"\n全部完成。素材目录：{out_dir}")
    print("提示：下载后抽帧确认内容（ffmpeg -ss 2 -i <f> -frames:v 1 out.jpg），再复制到项目 public/assets/videos/")


if __name__ == "__main__":
    main()
