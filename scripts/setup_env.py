#!/usr/bin/env python3
"""环境自检与恢复：Chrome、edge-tts、ffmpeg、依赖仓库。

沙箱每次会话重置，本脚本确保以下组件可用：
1. ~/.remotion/chrome-headless-shell/  Chrome Headless Shell（Remotion 渲染必需）
2. edge-tts                           免费中文 TTS
3. ffmpeg / ffprobe                   imageio-ffmpeg 静态版软链
4. video-skills-toolkit-main          视频模板依赖仓库（缺失时下载）
"""
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

HOME = Path.home()
REMOTION_DIR = HOME / ".remotion"
CHROME_SRC = Path("/sandbox/workspace/chrome-headless-shell/chrome-headless-shell-linux64")
CHROME_EXE = REMOTION_DIR / "chrome-headless-shell" / "chrome-headless-shell"
TOOLKIT_DIR = Path("/sandbox/workspace/video-skills-toolkit-main")
TOOLKIT_URL = "https://github.com/JackieZheng/video-skills-toolkit/archive/refs/heads/main.zip"
# 离线工具链（pip install --target 到 workspace，沙箱重置不丢，无需网络重装）
PYLIBS = Path("/sandbox/workspace/pylibs")
PYLIBS_BIN = PYLIBS / "bin"
PYLIBS_FFMPEG = PYLIBS / "imageio_ffmpeg" / "binaries" / "ffmpeg-linux-x86_64-v7.0.2"


def run(cmd, **kw):
    print(f"  $ {' '.join(cmd)}")
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def check_chrome() -> bool:
    print("[1/4] Chrome Headless Shell")
    if CHROME_EXE.exists():
        v = run([str(CHROME_EXE), "--version"])
        if v.returncode == 0:
            print(f"  ✓ {v.stdout.strip()}")
            return True
    if CHROME_SRC.exists():
        print("  → 从 workspace 备份恢复...")
        shutil.rmtree(REMOTION_DIR / "chrome-headless-shell", ignore_errors=True)
        (REMOTION_DIR / "chrome-headless-shell").mkdir(parents=True, exist_ok=True)
        for item in CHROME_SRC.iterdir():
            dst = REMOTION_DIR / "chrome-headless-shell" / item.name
            if item.is_dir():
                shutil.copytree(item, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dst)
        if CHROME_EXE.exists():
            print("  ✓ 已恢复")
            return True
    print("  ✗ Chrome 缺失且无备份，请从 remotion.media 手动下载解压到 ~/.remotion/")
    return False


def check_edge_tts() -> bool:
    print("[2/4] edge-tts")
    if shutil.which("edge-tts"):
        v = run(["edge-tts", "--version"])
        print(f"  ✓ {v.stdout.strip()}")
        return True
    # 离线优先：从 workspace/pylibs 恢复（沙箱重置后无需网络）
    if PYLIBS_BIN.exists() and (PYLIBS_BIN / "edge-tts").exists():
        # 包装脚本：设 PYTHONPATH 再 exec（console script 软链会找不到模块）
        wrapper = "#!/bin/bash\nexport PYTHONPATH=" + str(PYLIBS) + "\nexec /usr/local/bin/python3 " + str(PYLIBS_BIN / "edge-tts") + ' "$@"\n'
        with open("/usr/local/bin/edge-tts", "w") as f:
            f.write(wrapper)
        os.chmod("/usr/local/bin/edge-tts", 0o755)
        v = run(["/usr/local/bin/edge-tts", "--version"])
        print(f"  ✓ 从 workspace/pylibs 恢复 {v.stdout.strip()}")
        return True
    print("  → 网络安装 edge-tts（兜底）...")
    r = run([sys.executable, "-m", "pip", "install", "edge-tts", "-q"])
    if r.returncode == 0 and shutil.which("edge-tts"):
        print("  ✓ 已安装")
        return True
    print("  ✗ edge-tts 安装失败")
    return False


def check_ffmpeg() -> bool:
    print("[3/4] ffmpeg")
    if shutil.which("ffmpeg"):
        print("  ✓ 可用")
        return True
    # 离线优先：从 workspace/pylibs 软链静态版
    if PYLIBS_FFMPEG.exists():
        os.symlink(PYLIBS_FFMPEG, "/usr/local/bin/ffmpeg")
        print("  ✓ 从 workspace/pylibs 软链")
        return True
    print("  → 网络安装 imageio-ffmpeg（兜底）...")
    r = run([sys.executable, "-m", "pip", "install", "imageio-ffmpeg", "-q"])
    if r.returncode != 0:
        print("  ✗ imageio-ffmpeg 安装失败")
        return False
    try:
        import imageio_ffmpeg
        ff = Path(imageio_ffmpeg.get_ffmpeg_exe())
        os.symlink(ff, "/usr/local/bin/ffmpeg")
        # ffprobe 通常与 ffmpeg 同目录
        probe = ff.parent / "ffprobe"
        if probe.exists():
            os.symlink(probe, "/usr/local/bin/ffprobe")
        print("  ✓ 已软链")
        return True
    except Exception as e:
        print(f"  ✗ {e}")
        return False


def check_toolkit() -> bool:
    print("[4/4] video-skills-toolkit 依赖仓库")
    if TOOLKIT_DIR.exists() and (TOOLKIT_DIR / "skills").exists():
        print(f"  ✓ {TOOLKIT_DIR}")
        return True
    print("  → 下载依赖仓库...")
    try:
        zip_path = "/tmp/toolkit.zip"
        urllib.request.urlretrieve(TOOLKIT_URL, zip_path)
        with zipfile.ZipFile(zip_path) as z:
            z.extractall("/sandbox/workspace/")
        if TOOLKIT_DIR.exists():
            print("  ✓ 已下载")
            return True
    except Exception as e:
        print(f"  ✗ 下载失败: {e}")
    return False


def main() -> None:
    ok = all([check_chrome(), check_edge_tts(), check_ffmpeg(), check_toolkit()])
    print("\n环境自检" + ("全部通过 ✓" if ok else "存在失败项 ✗ 需修复"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
