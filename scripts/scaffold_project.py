#!/usr/bin/env python3
"""搭建 Remotion 视频工程：脚手架 → 素材复制 → video 场景补丁 → npm install。

依赖 video-skills-toolkit-main（setup_env.py 会确保其存在）和 fetch_article.py 的输出。
"""
import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

TOOLKIT_DIR = Path("/sandbox/workspace/video-skills-toolkit-main")
SCAFFOLD = TOOLKIT_DIR / "skills/wechat-article-remotion/scripts/scaffold_wechat_article_project.py"
PATCH_SCENE_TYPES = Path(__file__).resolve().parent.parent / "assets/sceneTypes.video.tsx"
PATCH_THEME = Path(__file__).resolve().parent.parent / "assets/theme.video.ts"
PATCH_BACKGROUND = Path(__file__).resolve().parent.parent / "assets/background.video.tsx"
EXTRACT_FONT = Path(__file__).resolve().parent / "extract_serif_font.py"
REMOTION_CONFIG = Path("/sandbox/workspace/demo-talking-head/remotion.config.ts")


def run(cmd, timeout=600, check=False):
    print(f"  $ {' '.join(cmd)}")
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0 and check:
        print(r.stdout[-2000:])
        print(r.stderr[-2000:])
        raise SystemExit(f"命令失败: {' '.join(cmd)}")
    return r


def main() -> None:
    parser = argparse.ArgumentParser(description="搭建 Remotion 视频工程")
    parser.add_argument("--project-dir", required=True, help="目标项目目录")
    parser.add_argument("--title", required=True, help="视频标题")
    parser.add_argument("--article-url", required=True, help="公众号文章链接")
    parser.add_argument("--source-dir", default=None, help="fetch_article 输出目录（含 work/source 和图片）")
    parser.add_argument("--videos-dir", default=None, help="视频素材目录（可选，复制到 public/assets/videos/）")
    parser.add_argument("--skip-install", action="store_true", help="跳过 npm install")
    args = parser.parse_args()

    project = Path(args.project_dir).resolve()
    print("[1/4] 脚手架生成")
    if not SCAFFOLD.exists():
        raise SystemExit(f"脚手架脚本不存在：{SCAFFOLD}（先跑 setup_env.py）")
    run(["python3", str(SCAFFOLD), "--project-dir", str(project),
         "--title", args.title, "--article-url", args.article_url], check=True)

    print("[2/4] 复制文章素材")
    if args.source_dir:
        src = Path(args.source_dir).resolve()
        if (src / "work/source").exists():
            shutil.copytree(src / "work/source", project / "work/source", dirs_exist_ok=True)
        if (src / "public/assets/article-images").exists():
            shutil.copytree(
                src / "public/assets/article-images",
                project / "public/assets/article-images",
                dirs_exist_ok=True,
            )
        print(f"  ✓ 从 {src} 复制 article.md / images.json / 原文图")

    print("[3/4] video 场景补丁 + 字体 + 配置")
    if PATCH_SCENE_TYPES.exists():
        shutil.copy2(PATCH_SCENE_TYPES, project / "src/sceneTypes.tsx")
        print("  ✓ sceneTypes.tsx 已应用 video 场景补丁（cover 视频 + fit 字段 + 32px 宋体字幕）")
    if PATCH_THEME.exists():
        shutil.copy2(PATCH_THEME, project / "src/theme.ts")
        print("  ✓ theme.ts 已应用（含思源宋体 + 彩色背景光晕主题色）")
    if PATCH_BACKGROUND.exists():
        shutil.copy2(PATCH_BACKGROUND, project / "src/background.tsx")
        print("  ✓ background.tsx 已应用（彩色光晕背景，非纯白）")
    # 本地思源宋体：系统 ttc 提取或 workspace 备份
    fonts_dir = project / "public/assets/fonts"
    fonts_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, str(EXTRACT_FONT), str(fonts_dir)], check=False)
    if args.videos_dir:
        vids = Path(args.videos_dir).resolve()
        if vids.exists():
            dest = project / "public/assets/videos"
            dest.mkdir(parents=True, exist_ok=True)
            for f in sorted(vids.glob("*.mp4")):
                shutil.copy2(f, dest / f.name)
            print(f"  ✓ 复制 {len(list(dest.glob('*.mp4')))} 个视频素材")
    if REMOTION_CONFIG.exists():
        shutil.copy2(REMOTION_CONFIG, project / "remotion.config.ts")
        print("  ✓ remotion.config.ts")

    if args.skip_install:
        return

    print("[4/4] npm install（本地磁盘，约 30-60 秒）")
    r = subprocess.run(
        ["bash", "-c", f"ulimit -n 65535 && cd {project} && npm install --no-audit --no-fund"],
        capture_output=True, text=True, timeout=600,
    )
    if r.returncode != 0:
        print(r.stdout[-1500:])
        print(r.stderr[-1500:])
        raise SystemExit("npm install 失败")
    node_modules = project / "node_modules"
    print(f"  ✓ npm install 完成（{sum(1 for _ in node_modules.iterdir()) if node_modules.exists() else 0} 顶层包）")

    print("\n完成。下一步：写口播稿 script.md → generate_tts.py → 拆稿 demoData.ts → 渲染")


if __name__ == "__main__":
    main()
