#!/usr/bin/env python3
"""渲染前素材校验：ffmpeg 全量解码测试 public/assets/videos/*.mp4。

背景（2026-08-16 教训）：railway-27768.mp4 下载时已损坏（Invalid NAL unit size），
渲染到 6777 帧才 PIPELINE_ERROR_DECODE 失败，浪费 ~15 分钟；且损坏文件被缓存，
后续项目复用时再次触发。此脚本在渲染前一次性拦截。

用法：
    python3 check_media.py [project-dir]   # 校验项目 public/assets/videos/
    python3 check_media.py --dir <视频目录>  # 校验任意目录（下载后即校验，防止损坏入库）
"""
import argparse
import subprocess
import sys
from pathlib import Path


def check_file(path: Path) -> tuple[bool, str]:
    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-f", "null", "-"],
        capture_output=True, text=True, timeout=120,
    )
    err = r.stderr.strip()
    if err:
        return False, err.splitlines()[0][:120]
    return True, ""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", default=None, help="项目目录（校验其 public/assets/videos/）")
    ap.add_argument("--dir", default=None, help="直接指定视频目录")
    args = ap.parse_args()

    if args.dir:
        vids_dir = Path(args.dir)
    elif args.path:
        vids_dir = Path(args.path) / "public/assets/videos"
    else:
        vids_dir = Path("public/assets/videos")
    if not vids_dir.exists():
        print(f"✗ 目录不存在：{vids_dir}")
        sys.exit(1)

    mp4s = sorted(vids_dir.glob("*.mp4"))
    if not mp4s:
        print(f"✗ 无 mp4 素材：{vids_dir}")
        sys.exit(1)

    bad = []
    for f in mp4s:
        ok, err = check_file(f)
        if ok:
            print(f"  ✓ {f.name}")
        else:
            print(f"  ⚠️ {f.name}: {err}")
            bad.append(f)

    if bad:
        print(f"\n✗ {len(bad)} 个素材损坏，渲染前必须替换/重新下载：{[b.name for b in bad]}")
        sys.exit(1)
    print(f"\n✓ 全部 {len(mp4s)} 个素材解码通过，可安全渲染")


if __name__ == "__main__":
    main()
