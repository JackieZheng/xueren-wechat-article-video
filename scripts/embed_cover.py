#!/usr/bin/env python3
"""给视频嵌入首帧封面图（cover art），并导出封面/预览图。

用途：视频文件在手机相册、微信、QQ 及装了 Icaros/K-Lite 缩略图扩展的
Windows 资源管理器中显示首帧封面（默认只显示系统自动抓取的中间帧）。

用法：
    python3 embed_cover.py --video <xxx.mp4> --cover <cover.png> [--out <输出.mp4>]
    python3 embed_cover.py --video <xxx.mp4> --cover <cover.png> --cover-only

流程：
1. 封面图转 1920x1080 JPG（供上传平台）与 PNG（内嵌用）
2. ffmpeg 流复制嵌入 attached_pic 封面轨（不重编码，速度极快）
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def ensure_ffmpeg() -> str:
    ff = shutil.which("ffmpeg")
    if ff:
        return ff
    # 用 imageio-ffmpeg 静态版兜底
    import imageio_ffmpeg
    exe = imageio_ffmpeg.get_ffmpeg_exe()
    os_symlink = Path("/usr/local/bin/ffmpeg")
    if not os_symlink.exists():
        os_symlink.symlink_to(exe)
    return str(os_symlink)


def embed(video: Path, cover: Path, out: Path) -> None:
    ff = ensure_ffmpeg()
    # 封面统一转 JPG（attached_pic 用 JPEG 兼容性最好）
    jpg = out.with_suffix(".cover.jpg")
    subprocess.run(
        [ff, "-y", "-i", str(cover), "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2", "-q:v", "2", str(jpg)],
        check=True, capture_output=True,
    )
    cmd = [
        ff, "-y",
        "-i", str(video),
        "-i", str(jpg),
        "-map", "0:v:0", "-map", "0:a:0", "-map", "1",
        "-c", "copy",
        "-disposition:v:1", "attached_pic",
        "-metadata:s:v:1", "mimetype=image/jpeg",
        str(out),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-1500:])
        raise SystemExit("ffmpeg 嵌入封面失败")
    jpg.unlink(missing_ok=True)
    print(f"  ✓ 内嵌封面版：{out.name}（封面轨 attached_pic，流复制无重编码）")


def main() -> None:
    parser = argparse.ArgumentParser(description="视频嵌入首帧封面 + 导出封面图")
    parser.add_argument("--video", required=True, help="源视频 mp4")
    parser.add_argument("--cover", required=True, help="封面图（PNG/JPG）")
    parser.add_argument("--out", default=None, help="输出路径（默认 <视频名>-内嵌封面版.mp4）")
    parser.add_argument("--cover-only", action="store_true", help="只导出封面/预览图，不嵌视频")
    args = parser.parse_args()

    video = Path(args.video)
    cover = Path(args.cover)
    if not video.exists() or not cover.exists():
        raise SystemExit("视频或封面文件不存在")

    out = Path(args.out) if args.out else video.with_name(video.stem + "-内嵌封面版.mp4")

    if not args.cover_only:
        embed(video, cover, out)
    print("完成。手机相册/微信/QQ 及装了 Icaros 的 Windows 资源管理器将显示首帧封面。")


if __name__ == "__main__":
    main()
