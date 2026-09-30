#!/usr/bin/env python3
"""用 edge-tts 生成男声配音（zh-CN-YunjianNeural 云健）+ 句级字幕。

输入：work/source/script.md（每行一个短句 8-25 字）
输出：public/assets/audio/voice.mp3、work/captions/captions.word.srt（句级时间轴）
"""
import argparse
import subprocess
import sys
import shutil
from pathlib import Path

VOICE = "zh-CN-YunjianNeural"  # 云健：成熟男声（用户偏好"中年男士"）


def main() -> None:
    parser = argparse.ArgumentParser(description="edge-tts 男声配音 + 句级字幕")
    parser.add_argument("--project-dir", required=True, help="项目根目录")
    parser.add_argument("--script", default=None, help="口播稿路径（默认 work/source/script.md）")
    parser.add_argument("--voice", default=VOICE, help="音色（默认 zh-CN-YunjianNeural）")
    args = parser.parse_args()

    project = Path(args.project_dir).resolve()
    script = Path(args.script).resolve() if args.script else project / "work/source/script.md"
    if not script.exists():
        raise SystemExit(f"口播稿不存在：{script}（先写 work/source/script.md，每行一个短句）")

    audio_dir = project / "public/assets/audio"
    captions_dir = project / "work/captions"
    audio_dir.mkdir(parents=True, exist_ok=True)
    captions_dir.mkdir(parents=True, exist_ok=True)

    if not shutil.which("edge-tts"):
        raise SystemExit("edge-tts 未安装（先跑 setup_env.py）")

    print(f"[1/2] 生成配音（{args.voice}）")
    voice_out = audio_dir / "voice.mp3"
    srt_out = captions_dir / "captions.word.srt"
    r = subprocess.run(
        [
            "edge-tts", "--voice", args.voice,
            "--file", str(script),
            "--write-media", str(voice_out),
            "--write-subtitles", str(srt_out),
        ],
        capture_output=True, text=True, timeout=600,
    )
    if r.returncode != 0 or not voice_out.exists():
        print(r.stdout[-1000:])
        print(r.stderr[-1000:])
        raise SystemExit("TTS 生成失败")

    size_kb = voice_out.stat().st_size // 1024
    cues = sum(1 for line in srt_out.read_text(encoding="utf-8").splitlines()
               if line.strip().isdigit())
    print(f"  ✓ voice.mp3（{size_kb} KB）")

    # 输出时长：srt 最后一条 cue 的结束时间
    import re
    srt = srt_out.read_text(encoding="utf-8")
    times = re.findall(r"(\d+):(\d+):(\d+),(\d+) -->", srt)
    if times:
        h, m, s, ms = times[-1]
        total = int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000
        print(f"  ✓ captions.word.srt（{cues} 条短句，总时长 {total:.1f}s）")
    else:
        print(f"  ✓ captions.word.srt（{cues} 条短句）")

    print("\n下一步：按 srt 时间轴写 src/demoData.ts（scenes/captions），参考 references/scene-data-guide.md")


if __name__ == "__main__":
    main()
