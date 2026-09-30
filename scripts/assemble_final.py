#!/usr/bin/env python3
"""最终封装：封面 PNG → 前置静态视频 → 与主视频无转场拼接 → 内嵌封面。

前置静态段：使用封面图生成 3 秒（默认）无音频或静音 AAC 视频，分辨率和
主视频一致（1920×1080, 30fps, yuv420p）。

拼接：ffmpeg concat demuxer -c copy（要求两段视频编码参数完全一致）。
如果 copy 失败，自动降级为 concat filter 重编码。

用法：
    python3 assemble_final.py --cover cover.png --main main.mp4 --out final.mp4
        [--intro 3.0]
"""
import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def ensure_ffmpeg() -> str:
    ff = shutil.which("ffmpeg")
    if ff:
        return ff
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def ffprobe_audio_info(path: Path) -> dict:
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "a:0",
        "-show_entries", "stream=codec_name,sample_rate,channels,channel_layout",
        "-of", "default=noprint_wrappers=1", str(path),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    info = {}
    for line in r.stdout.strip().splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            info[k] = v
    return info


def make_intro(cover: Path, out: Path, duration: float, audio_info: dict) -> None:
    ff = ensure_ffmpeg()
    sample_rate = int(audio_info.get("sample_rate", "48000"))
    channels = int(audio_info.get("channels", "2"))
    # 默认 stereo 的 channel_layout
    layout = audio_info.get("channel_layout", "stereo" if channels == 2 else "mono")

    cmd = [
        ff, "-y", "-v", "error",
        "-loop", "1", "-i", str(cover),
        "-f", "lavfi", "-i", f"anullsrc=r={sample_rate}:cl={layout}",
        "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080",
        "-c:v", "libx264", "-crf", "18", "-preset", "slow",
        "-pix_fmt", "yuv420p", "-profile:v", "high", "-level:v", "4.0",
        "-r", "30",
        "-c:a", "aac", "-b:a", "128k", "-ar", str(sample_rate),
        "-shortest",
        "-t", str(duration),
        str(out),
    ]
    subprocess.run(cmd, check=True)
    print(f"  ✓ 前置静态段：{out.name}（{duration}s）")


def concat_demuxer(intro: Path, main: Path, out: Path) -> None:
    ff = ensure_ffmpeg()
    # concat demuxer 要求文件路径使用单引号包裹，Windows 路径含反斜杠需转义
    lines = [f"file '{str(p).replace(chr(92), '/')}'" for p in (intro, main)]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
        list_path = f.name
    try:
        cmd = [
            ff, "-y", "-v", "error",
            "-f", "concat", "-safe", "0", "-i", list_path,
            "-c", "copy",
            "-movflags", "+faststart",
            str(out),
        ]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(r.stderr[-1200:])
        print(f"  ✓ 拼接完成（流复制）：{out.name}")
    finally:
        Path(list_path).unlink(missing_ok=True)


def concat_filter_reencode(intro: Path, main: Path, out: Path) -> None:
    ff = ensure_ffmpeg()
    cmd = [
        ff, "-y", "-v", "error",
        "-i", str(intro), "-i", str(main),
        "-filter_complex", "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[outv][outa]",
        "-map", "[outv]", "-map", "[outa]",
        "-c:v", "libx264", "-crf", "18", "-preset", "slow",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        str(out),
    ]
    subprocess.run(cmd, check=True)
    print(f"  ✓ 拼接完成（重编码降级）：{out.name}")


def embed_cover(video: Path, cover: Path, out: Path) -> None:
    ff = ensure_ffmpeg()
    # 封面统一转 1920x1080 JPG（attached_pic 用 JPEG 兼容性最好）
    jpg = out.with_suffix(".cover.jpg")
    subprocess.run(
        [
            ff, "-y", "-v", "error", "-i", str(cover),
            "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
            "-q:v", "2", str(jpg),
        ],
        check=True,
    )
    cmd = [
        ff, "-y", "-v", "error",
        "-i", str(video),
        "-i", str(jpg),
        "-map", "0:v:0", "-map", "0:a:0", "-map", "1",
        "-c", "copy",
        "-disposition:v:1", "attached_pic",
        "-metadata:s:v:1", "mimetype=image/jpeg",
        "-movflags", "+faststart",
        str(out),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-1500:])
        raise SystemExit("ffmpeg 嵌入封面失败")
    jpg.unlink(missing_ok=True)
    print(f"  ✓ 内嵌封面版：{out.name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="封面 → 前置静态段 → 拼接主视频 → 内嵌封面")
    parser.add_argument("--cover", required=True, help="封面 PNG/JPG（1920×1080）")
    parser.add_argument("--main", required=True, help="主视频 mp4")
    parser.add_argument("--out", required=True, help="最终输出 mp4")
    parser.add_argument("--intro", type=float, default=3.0, help="前置静态段时长（秒），默认 3.0")
    args = parser.parse_args()

    cover = Path(args.cover)
    main = Path(args.main)
    if not cover.exists() or not main.exists():
        raise SystemExit("封面或主视频文件不存在")

    out = Path(args.out)
    tmp_dir = out.parent / f"_assemble_tmp_{out.stem}"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    intro = tmp_dir / "intro.mp4"
    concat = tmp_dir / "concat.mp4"

    print("步骤 1/4：生成前置静态封面视频…")
    audio_info = ffprobe_audio_info(main)
    make_intro(cover, intro, args.intro, audio_info)

    print("步骤 2/4：无转场拼接主视频…")
    try:
        concat_demuxer(intro, main, concat)
    except RuntimeError as e:
        print("流复制拼接失败，降级为重编码拼接：", e)
        concat_filter_reencode(intro, main, concat)

    print("步骤 3/4：内嵌封面…")
    embed_cover(concat, cover, out)

    print("步骤 4/4：清理临时文件…")
    shutil.rmtree(tmp_dir, ignore_errors=True)

    print(f"\n完成。最终视频：{out}")


if __name__ == "__main__":
    main()
