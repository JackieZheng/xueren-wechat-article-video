#!/usr/bin/env python3
"""TTS v2：逐句生成配音 + 实测时长拼接，彻底消除 edge-tts word-boundary 时间轴漂移。

背景：edge-tts --write-subtitles 的 srt 时间戳是模型预测值，长文本累积误差
导致字幕/画面滞后于实际语音（实测 18s 处漂移 3.2s）。本脚本改为：
  1. 对 script.md 每行单独调用 edge-tts 生成单句 mp3
  2. ffmpeg 转 wav，用 wave 模块实测每句音频时长（100% 真实）
  3. 句间加固定 0.3s 静音，numpy 拼接 → voice.mp3
  4. srt 时间轴 = 逐句实测时长累加，与实际音频严格对齐

用法：
  python3 generate_tts_v2.py --project-dir <路径> [--gap 0.3] [--voice zh-CN-YunjianNeural]
"""
import argparse
import subprocess
import sys
import wave
import re
from pathlib import Path

import numpy as np

VOICE = "zh-CN-YunjianNeural"
GAP = 0.3  # 句间静音秒数
SR = 24000  # edge-tts 输出 24kHz

def run(cmd, timeout=120):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        print(r.stdout[-800:]); print(r.stderr[-800:])
        raise SystemExit(f"命令失败: {' '.join(cmd[:4])}...")
    return r

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-dir", required=True)
    parser.add_argument("--gap", type=float, default=GAP)
    parser.add_argument("--voice", default=VOICE)
    args = parser.parse_args()

    project = Path(args.project_dir).resolve()
    script = project / "work/source/script.md"
    if not script.exists():
        raise SystemExit(f"口播稿不存在：{script}")

    lines = [l.strip() for l in script.read_text(encoding="utf-8").splitlines() if l.strip()]
    print(f"[1/3] 口播稿 {len(lines)} 句，逐句生成（{args.voice}）...")

    tmp = project / "work/tts_tmp"
    tmp.mkdir(parents=True, exist_ok=True)

    segs = []      # numpy 音频数组
    cues = []      # (text, start, end)
    cursor = 0.0
    silent = np.zeros(int(SR * args.gap), dtype=np.float32)

    for i, line in enumerate(lines, 1):
        mp3 = tmp / f"s{i:03d}.mp3"
        wav = tmp / f"s{i:03d}.wav"
        # 逐句生成（--text 单句，避免 --file 整篇的边界预测）
        # 断点续传：mp3 已存在且非空则跳过 TTS（网络超时重跑时保留已生成句）
        if mp3.exists() and mp3.stat().st_size > 1000:
            print(f"  {i} 已生成，跳过")
        else:
            run(["edge-tts", "--voice", args.voice, "--text", line,
                 "--write-media", str(mp3)])
        run(["ffmpeg", "-y", "-i", str(mp3), "-ar", str(SR), "-ac", "1",
             "-f", "wav", str(wav)])
        with wave.open(str(wav), "rb") as w:
            n = w.getnframes()
            data = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768.0
        # 裁剪句首尾静音（edge-tts 单句输出自带前后静音，74 句累加虚增时长）
        th = 0.008  # ~-42dB
        nz = np.where(np.abs(data) > th)[0]
        if len(nz) > 0:
            a = max(0, nz[0] - int(SR * 0.05))     # 保留 50ms 余量
            b = min(len(data), nz[-1] + int(SR * 0.08))
            data = data[a:b]
        dur = len(data) / SR
        start = cursor
        end = cursor + dur
        cues.append((line, start, end))
        segs.append(data)
        if i < len(lines):
            segs.append(silent)
            cursor = end + args.gap
        else:
            cursor = end
        if i % 10 == 0 or i == len(lines):
            print(f"  {i}/{len(lines)}（累计 {cursor:.1f}s）")

    # 拼接 → voice.mp3
    audio = np.concatenate(segs)
    audio_i16 = (np.clip(audio, -1, 1) * 32767).astype(np.int16)
    out_wav = project / "public/assets/audio/voice.wav"
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out_wav), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(audio_i16.tobytes())
    run(["ffmpeg", "-y", "-i", str(out_wav), "-b:a", "192k",
         str(project / "public/assets/audio/voice.mp3")])

    # 精确 srt
    srt_path = project / "work/captions/captions.word.srt"
    srt_path.parent.mkdir(parents=True, exist_ok=True)
    def ts(t):
        h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
        return f"{h:02d}:{m:02d}:{int(s):02d},{int((s - int(s)) * 1000):03d}"
    with srt_path.open("w", encoding="utf-8") as f:
        for i, (text, start, end) in enumerate(cues, 1):
            f.write(f"{i}\n{ts(start)} --> {ts(end)}\n{text}\n\n")

    total = cursor
    print(f"[2/3] 拼接完成：{len(audio)/SR:.1f}s 音频，{len(cues)} 条字幕")
    print(f"[3/3] ✓ voice.mp3 + captions.word.srt（总时长 {total:.2f}s，句间静音 {args.gap}s）")
    print(f"      最后一句：{ts(cues[-1][1])} --> {ts(cues[-1][2])}")

if __name__ == "__main__":
    main()
