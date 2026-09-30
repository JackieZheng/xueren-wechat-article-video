#!/usr/bin/env python3
"""生成视频封面：素材帧背景 + 深色渐变遮罩 + 竖屏安全区布局文字（PIL 合成）

封面竖屏安全区规范（2026-09-05 用户确认，长期有效）：
- 画布保持 1920×1080（视频原始尺寸不变，不改方形画布）
- 文字活动区收窄到中央 608×1080（1080×9/16=607.5→取 608）
- 608×1080 内再加安全边距：
  * 顶部 90px（避状态栏）
  * 底部 140px（避互动栏 + 手势条）
  * 左右各 60px
- 最终文字活动区：x=[716, 1204]（宽 488px），y=[90, 940]（高 850px）
- 字号规则：
  * 标签 34px（自适应塞进 488px，最小 22px）
  * 标题 45px 起（自适应塞进 488px，最小 30px，两行标题取较小字号统一）
  * 副标题 28px（自适应塞进 488px，最小 22px）

用法：
    python3 make_cover.py --bg <帧图> --out <输出png> \\
        --title1 "主标题1" --title2 "主标题2" [--sub 副标题] \\
        [--label 顶部标签] [--accent "R,G,B"] [--fonts 字体目录]
"""
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import numpy as np
import argparse
from pathlib import Path

# ============ 竖屏安全区常量 ============
W, H = 1920, 1080                       # 画布（视频原始尺寸）
SAFE_W = 608                            # 中央 608×1080 竖屏安全区
SAFE_X0 = (W - SAFE_W) // 2             # 656
SAFE_X1 = SAFE_X0 + SAFE_W              # 1264

PAD_LR = 60                             # 左右安全边距
PAD_TOP = 90                            # 顶部安全边距（避状态栏）
PAD_BOT = 140                           # 底部安全边距（避互动栏+手势条）

TEXT_X = SAFE_X0 + PAD_LR               # 716  文字活动区左边界
TEXT_MAX_X = SAFE_X1 - PAD_LR           # 1204 文字活动区右边界
TEXT_MAX_W = TEXT_MAX_X - TEXT_X        # 488  文字活动区宽度
TEXT_Y_TOP = PAD_TOP                    # 90   文字活动区顶
TEXT_Y_BOT = H - PAD_BOT                # 940  文字活动区底
TEXT_MAX_H = TEXT_Y_BOT - TEXT_Y_TOP    # 850  文字活动区高度

# 字号默认值
SIZE_LABEL = 34
SIZE_TITLE_START = 100                  # 标题起点，会自适应缩到塞进 488px
SIZE_TITLE_MIN = 30                     # 45px 是常规上限，起点从 100 起自动往下找
SIZE_SUB_START = 32
SIZE_LABEL_MIN = 22
SIZE_SUB_MIN = 22


def parse_accent(s):
    if not s:
        return (255, 200, 60)
    try:
        r, g, b = (int(x) for x in s.split(","))
        return (r, g, b)
    except Exception:
        return (255, 200, 60)


def fit_font(temp_draw, load_font, text, weight, start_size, min_size, max_w):
    """自适应字号：从 start_size 递减，直到宽度 <= max_w 或触底"""
    size = start_size
    font = load_font(weight, size)
    w = temp_draw.textlength(text, font=font)
    while size > min_size and w > max_w:
        size -= 1
        font = load_font(weight, size)
        w = temp_draw.textlength(text, font=font)
    return font, size, w


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bg", required=True, help="背景帧图路径")
    ap.add_argument("--out", required=True, help="输出 png 路径")
    ap.add_argument("--title1", required=True, help="主标题第一行")
    ap.add_argument("--title2", required=True, help="主标题第二行")
    ap.add_argument("--sub", default="", help="副标题（一句话）")
    ap.add_argument("--label", default="雪人说说 · 高报干货", help="顶部标签")
    ap.add_argument("--accent", default="255,200,60", help="强调色 R,G,B")
    ap.add_argument("--fonts", default=None, help="字体目录，默认 ./public/assets/fonts")
    ap.add_argument("--line-spacing", type=float, default=1.8, help="标题两行之间的行距倍数（默认 1.8）")
    ap.add_argument("--no-verify", action="store_true", help="跳过像素扫描验证")
    args = ap.parse_args()

    F = args.fonts or str(Path.cwd() / "public/assets/fonts")
    if not Path(F).exists():
        raise SystemExit(f"字体目录不存在：{F}（可用 --fonts 指定）")

    def load_font(weight, size):
        return ImageFont.truetype(f"{F}/NotoSansSC-{weight}.ttf", size)

    ACCENT = parse_accent(args.accent)

    print("=" * 60)
    print("🎨 生成封面（1920×1080 画布 + 中央 608×1080 竖屏安全区）")
    print("=" * 60)
    print(f"   中央安全区: x=[{SAFE_X0}, {SAFE_X1}] (宽 {SAFE_W}px)")
    print(f"   文字活动区: x=[{TEXT_X}, {TEXT_MAX_X}] (宽 {TEXT_MAX_W}px)")
    print(f"   文字活动区: y=[{TEXT_Y_TOP}, {TEXT_Y_BOT}] (高 {TEXT_MAX_H}px)")

    # 1. 加载背景帧，居中裁切 1920×1080
    bg = Image.open(args.bg).convert("RGB")
    scale = max(W / bg.width, H / bg.height)
    bg = bg.resize((int(bg.width * scale) + 1, int(bg.height * scale) + 1), Image.LANCZOS)
    x = (bg.width - W) // 2
    y = (bg.height - H) // 2
    bg = bg.crop((x, y, x + W, y + H))

    # 2. 深色渐变遮罩（顶强压 0.82、中 1.0、底再收 0.35）
    arr = np.array(bg).astype(float)
    mask = np.zeros((H, W, 1), dtype=float)
    for i in range(H):
        t = i / H
        top = 0.82 if t < 0.25 else 1.0
        bot = 1.0 - 0.65 * max(0.0, (t - 0.45) / 0.55)
        mask[i, :, 0] = min(top, bot)
    arr = arr * mask
    img = Image.fromarray(arr.astype(np.uint8)).convert("RGB").filter(ImageFilter.GaussianBlur(1.2))

    # 3. 标题区压暗带（y 250-950 覆盖文字活动区，增强任意背景下标题对比；顶部 250 以下柔和起始）
    band = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(band)
    for i in range(H):
        if 250 <= i <= 950:
            a = int(200 * ((i - 250) / 700) ** 1.6)
            bd.line([(0, i), (W, i)], fill=(0, 0, 0, a))
    img = Image.alpha_composite(img.convert("RGBA"), band).convert("RGB")
    img_base = img.copy()  # 无文字背景基准（差分法验证用）
    d = ImageDraw.Draw(img)

    temp_draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))

    # 4. 顶部标签（34px 自适应）
    f_label = load_font(500, SIZE_LABEL)
    w_label = temp_draw.textlength(args.label, font=f_label)
    if w_label > TEXT_MAX_W:
        f_label, _, w_label = fit_font(temp_draw, load_font, args.label, 500, SIZE_LABEL, SIZE_LABEL_MIN, TEXT_MAX_W)
    print(f"  标签: 字号 {f_label.size}px, 宽度 {w_label:.0f}px")

    # 5. 主标题（自适应到 488px 内，两行统一取较小字号）
    _, size1, _ = fit_font(temp_draw, load_font, args.title1, 900, SIZE_TITLE_START, SIZE_TITLE_MIN, TEXT_MAX_W)
    _, size2, _ = fit_font(temp_draw, load_font, args.title2, 900, SIZE_TITLE_START, SIZE_TITLE_MIN, TEXT_MAX_W)
    title_size = min(size1, size2)
    font_title = load_font(900, title_size)
    w1 = temp_draw.textlength(args.title1, font=font_title)
    w2 = temp_draw.textlength(args.title2, font=font_title)
    print(f"  标题1 '{args.title1}': 字号 {title_size}px, 宽度 {w1:.0f}px")
    print(f"  标题2 '{args.title2}': 字号 {title_size}px, 宽度 {w2:.0f}px")

    # 6. 副标题（28px 起，自适应）
    f_sub = load_font(500, SIZE_SUB_START)
    w3 = 0.0
    if args.sub:
        w3 = temp_draw.textlength(args.sub, font=f_sub)
        if w3 > TEXT_MAX_W:
            f_sub, _, w3 = fit_font(temp_draw, load_font, args.sub, 500, SIZE_SUB_START, SIZE_SUB_MIN, TEXT_MAX_W)
        print(f"  副标题: 字号 {f_sub.size}px, 宽度 {w3:.0f}px")

    # 7. 整体垂直布局（居中于画面垂直中线 y=540 附近，但整体落在文字活动区内）
    label_cx = title_cx = (TEXT_X + TEXT_MAX_X) / 2
    line_h = int(title_size * args.line_spacing)
    gap_label_title = 60
    gap_title_sub = 50
    block_h = f_label.size + gap_label_title + line_h * 2
    if args.sub:
        block_h += gap_title_sub + f_sub.size
    block_top = 540 - block_h // 2
    # 安全区边界保护：整体不超出文字活动区 y=[90, 940]
    if block_top < TEXT_Y_TOP:
        block_top = TEXT_Y_TOP
    if block_top + block_h > TEXT_Y_BOT:
        block_top = TEXT_Y_BOT - block_h

    label_y = block_top
    y1 = label_y + f_label.size + gap_label_title
    y2 = y1 + line_h
    sub_y = y2 + line_h + gap_title_sub

    d.text((label_cx - w_label / 2, label_y), args.label, font=f_label, fill=(255, 255, 255, 220))
    d.text((title_cx - w1 / 2, y1), args.title1, font=font_title, fill=(255, 255, 255))
    d.text((title_cx - w2 / 2, y2), args.title2, font=font_title, fill=ACCENT)
    if args.sub:
        d.text((title_cx - w3 / 2, sub_y), args.sub, font=f_sub, fill=(235, 235, 235, 230))
    print(f"  布局: 标签 y={label_y}, 标题1 y={y1}, 标题2 y={y2}, 副标题 y={sub_y if args.sub else 'N/A'}")
    print(f"  块范围 y=[{block_top}, {block_top + block_h}]（高 {block_h}px）")

    # 8. 保存
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    img.save(args.out, quality=95)
    print(f"\n✅ 封面已保存: {args.out}")
    print(f"   画布尺寸: {img.size[0]}×{img.size[1]}")

    # 9. 像素扫描验证
    if not args.no_verify:
        print("\n" + "=" * 60)
        print("📊 像素扫描验证")
        print("=" * 60)
        arr_out = np.array(img).astype(int)
        arr_base = np.array(img_base).astype(int)
        # 差分法：文字合成前后的像素差 = 纯文字像素（排除背景亮灯/光斑干扰）
        diff = np.abs(arr_out - arr_base).max(axis=2)
        text_mask = diff > 30
        ys, xs = np.where(text_mask)
        if len(xs) > 0:
            print(f"   文字像素范围: x=[{xs.min()}, {xs.max()}], y=[{ys.min()}, {ys.max()}]")
            in_safe = (xs.min() >= SAFE_X0) and (xs.max() <= SAFE_X1)
            print(f"   中央 608×1080 安全区 x=[{SAFE_X0}, {SAFE_X1}]: {'✅ 完全在内' if in_safe else '❌ 越界'}")
            in_pad = (xs.min() >= TEXT_X) and (xs.max() <= TEXT_MAX_X) and (ys.min() >= TEXT_Y_TOP) and (ys.max() <= TEXT_Y_BOT)
            print(f"   内边距安全区 x=[{TEXT_X}, {TEXT_MAX_X}], y=[{TEXT_Y_TOP}, {TEXT_Y_BOT}]: {'✅ 完全在内' if in_pad else '❌ 越界'}")
        else:
            print("   ⚠️ 未检测到文字像素")


if __name__ == "__main__":
    main()
