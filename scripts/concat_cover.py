#!/usr/bin/env python3
"""封面段 + 正片合并（TS 中转，修复 concat -c copy 的 duration 元数据损坏）。

背景：mp4 concat demuxer 直接 -c copy 时，若两段 timebase 不一致（封面段 15360 vs
Remotion 90k），moov 的 duration 会被错误计算（实测 4:18 内容写成 25:14），
播放器按错误时基播放导致"时长不对+音画不同步"。TS 中转统一时基后彻底修复。

用法：
  python3 concat_cover.py --project-dir <路径> --cover <封面png> --demo <正片mp4>
输出：<project>/renders/final.mp4（封面 2s + 正片，时长正确）
"""
import argparse
import subprocess
from pathlib import Path

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-1000:]); print(r.stderr[-1000:])
        raise SystemExit(f"失败: {' '.join(cmd[:5])}...")
    return r

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-dir", required=True)
    ap.add_argument("--cover", required=True, help="封面 PNG")
    ap.add_argument("--demo", required=True, help="正片 mp4")
    args = ap.parse_args()
    proj = Path(args.project_dir)
    renders = proj / "renders"
    renders.mkdir(exist_ok=True)

    cover_seg = renders / "cover_seg.mp4"
    # 封面 2s 静态段（含静音轨，与正片音频参数一致：48kHz stereo aac）
    run(["ffmpeg", "-y", "-loop", "1", "-i", args.cover,
         "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
         "-t", "2", "-r", "30",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-profile:v", "high",
         "-c:a", "aac", "-b:a", "128k", "-shortest", str(cover_seg)])

    # TS 中转：统一时基，避免 concat 流复制损坏 duration
    seg1 = renders / "seg1.ts"; seg2 = renders / "seg2.ts"
    run(["ffmpeg", "-y", "-i", str(cover_seg), "-c", "copy",
         "-bsf:v", "h264_mp4toannexb", "-f", "mpegts", str(seg1)])
    run(["ffmpeg", "-y", "-i", args.demo, "-c", "copy",
         "-bsf:v", "h264_mp4toannexb", "-f", "mpegts", str(seg2)])
    final = renders / "final.mp4"
    # filter_complex concat 重编码统一时基（crf18 veryfast 约 5 分钟）。
    # 注意：concat demuxer 直接 -c copy 会损坏 duration（时基不一致），
    # 且本环境 concat demuxer/mpegts 读取均不可靠（ffmpeg 7.0.2 静态版静默失败）。
    run(["ffmpeg", "-y", "-i", str(cover_seg), "-i", args.demo,
         "-filter_complex",
         "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[v][a]",
         "-map", "[v]", "-map", "[a]",
         "-c:v", "libx264", "-crf", "18", "-preset", "veryfast",
         "-c:a", "aac", "-b:a", "192k",
         "-movflags", "+faststart", str(final)])

    # 验证：Duration 应为 正片时长 + 2s，帧率 30
    r = run(["ffmpeg", "-i", str(final), "-f", "null", "-"])
    for line in r.stderr.splitlines():
        if "Duration" in line or "fps" in line:
            print(" ", line.strip())
    print(f"✓ final.mp4：{final.stat().st_size/1024/1024:.1f} MB")

if __name__ == "__main__":
    main()
