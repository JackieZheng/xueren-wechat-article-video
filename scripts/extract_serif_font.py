#!/usr/bin/env python3
"""从系统字体中提取思源宋体（Noto Serif CJK SC）到项目 public/assets/fonts/。

优先本地字体（用户偏好）：沙箱 /usr/share/fonts/opentype/noto/ 自带
NotoSerifCJK-Regular.ttc / NotoSerifCJK-Bold.ttc（思源宋体 Noto 版，
SIL OFL 1.1 免费可商用）。从 ttc 集合中提取简体中文（SC）实例为独立 otf。
"""
import shutil
import sys
from pathlib import Path

TTC_DIR = Path("/usr/share/fonts/opentype/noto")
BACKUP_DIR = Path("/sandbox/workspace/video-skills-toolkit-main/assets/fonts")


def extract_sc_from_ttc(ttc: Path, weight: str) -> Path:
    from fontTools.ttLib import TTCollection

    tc = TTCollection(str(ttc))
    for font in tc.fonts:
        if "SC" in font["name"].getDebugName(1):
            out = BACKUP_DIR / f"NotoSerifCJKsc-{weight}.otf"
            font.save(str(out))
            return out
    raise RuntimeError(f"{ttc} 中未找到 SC 实例")


def ensure_serif_fonts(project_fonts_dir: Path) -> None:
    project_fonts_dir.mkdir(parents=True, exist_ok=True)
    for weight, ttc_name in [("Regular", "NotoSerifCJK-Regular.ttc"),
                             ("Bold", "NotoSerifCJK-Bold.ttc")]:
        ttc = TTC_DIR / ttc_name
        dest = project_fonts_dir / f"NotoSerifCJKsc-{weight}.otf"
        if dest.exists() and dest.stat().st_size > 10_000_000:
            print(f"  ✓ {dest.name} 已存在")
            continue
        # 优先 workspace 备份（沙箱重置后系统字体也可能丢失）
        backup = BACKUP_DIR / f"NotoSerifCJKsc-{weight}.otf"
        if backup.exists() and backup.stat().st_size > 10_000_000:
            shutil.copy2(backup, dest)
            print(f"  ✓ {dest.name} ← workspace 备份")
            continue
        if ttc.exists():
            try:
                extract_sc_from_ttc(ttc, weight)
                shutil.copy2(BACKUP_DIR / f"NotoSerifCJKsc-{weight}.otf", dest)
                print(f"  ✓ {dest.name} ← 系统 ttc 提取")
            except Exception as e:
                print(f"  ✗ {weight} 提取失败: {e}")
        else:
            print(f"  ✗ 系统无 {ttc_name}，且 workspace 无备份（可手动放置 NotoSerifCJKsc-{weight}.otf）")


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("用法: extract_serif_font.py <项目 public/assets/fonts 目录>")
    ensure_serif_fonts(Path(sys.argv[1]))
    print("完成。字幕字体 = Noto Serif CJK SC（思源宋体，OFL 免费可商用），与黑体正文区分。")


if __name__ == "__main__":
    main()
