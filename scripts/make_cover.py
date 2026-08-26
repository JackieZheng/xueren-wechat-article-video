#!/usr/bin/env python3
"""生成视频封面：素材帧背景 + 深色渐变遮罩 + 大标题（PIL 合成，1920x1080）。
用法：python3 make_cover.py --bg <帧图> --out <输出png> --title1 <主标题1> --title2 <主标题2> [--sub 副标题] [--label 顶部标签]
"""
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import numpy as np
import argparse
from pathlib import Path

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bg", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--title1", required=True)
    ap.add_argument("--title2", required=True)
    ap.add_argument("--sub", default="")
    ap.add_argument("--label", default="雪人说说 · 高报干货")
    ap.add_argument("--accent", default=(255, 200, 60), type=tuple)
    ap.add_argument("--fonts", default=None)
    args = ap.parse_args()
    F = args.fonts or str(Path.cwd() / "public/assets/fonts")
    if not Path(F).exists():
        raise SystemExit(f"字体目录不存在：{F}（可用 --fonts 指定）")
    W, H = 1920, 1080

    bg = Image.open(args.bg).convert("RGB")
    scale = max(W / bg.width, H / bg.height)
    bg = bg.resize((int(bg.width * scale) + 1, int(bg.height * scale) + 1), Image.LANCZOS)
    x = (bg.width - W) // 2; y = (bg.height - H) // 2
    bg = bg.crop((x, y, x + W, y + H))
    arr = np.array(bg).astype(float)
    mask = np.zeros((H, W, 1), dtype=float)
    for i in range(H):
        t = i / H
        top = 0.82 if t < 0.25 else 1.0
        bot = 1.0 - 0.65 * max(0.0, (t - 0.45) / 0.55)
        mask[i, :, 0] = min(top, bot)
    arr = arr * mask
    img = Image.fromarray(arr.astype(np.uint8)).convert("RGB").filter(ImageFilter.GaussianBlur(1.2))

    d = ImageDraw.Draw(img)
    f_label = ImageFont.truetype(f"{F}/NotoSansSC-500.ttf", 40)
    f_title = ImageFont.truetype(f"{F}/NotoSansSC-900.ttf", 118)
    f_sub = ImageFont.truetype(f"{F}/NotoSansSC-500.ttf", 44)

    w = d.textlength(args.label, font=f_label)
    d.text(((W - w) / 2, 96), args.label, font=f_label, fill=(255, 255, 255, 220))

    # 标题区压暗带
    band = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(band)
    for i in range(H):
        if 600 <= i <= 1000:
            a = int(160 * ((i - 600) / 400) ** 1.6)
            bd.line([(0, i), (W, i)], fill=(0, 0, 0, a))
    img = Image.alpha_composite(img.convert("RGBA"), band).convert("RGB")
    d = ImageDraw.Draw(img)

    w1 = d.textlength(args.title1, font=f_title)
    w2 = d.textlength(args.title2, font=f_title)
    y1, y2 = 620, 770
    d.text(((W - w1) / 2, y1), args.title1, font=f_title, fill=(255, 255, 255))
    d.text(((W - w2) / 2, y2), args.title2, font=f_title, fill=args.accent)
    if args.sub:
        w3 = d.textlength(args.sub, font=f_sub)
        d.text(((W - w3) / 2, y2 + 170), args.sub, font=f_sub, fill=(235, 235, 235, 230))
    img.save(args.out, quality=95)
    print("saved", args.out)

if __name__ == "__main__":
    main()
