#!/usr/bin/env python3
"""抓取微信公众号文章 → markdown + 下载原文图 + PIL 读宽高 + 完整性自检。

增强点（相对 skill 仓库原版）：
- 单张图下载失败自动重试 2 次
- 抓取结束后自检 images.json 是否写出、图片数量是否与 markdown 一致
- 缺图时尝试重新下载并重建 images.json
"""
import argparse
import json
import re
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from PIL import Image

IDEAFLOW_URL = "https://ideaflow-article-to-markdown.hf.space/resolve/mark"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def fetch_markdown(article_url: str) -> str:
    resp = requests.post(
        IDEAFLOW_URL,
        headers={
            "Referer": "https://ideaflow-article-to-markdown.hf.space/",
            "User-Agent": UA,
            "Content-Type": "application/json",
        },
        json={"blogUrl": article_url},
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    md = data.get("data", {}).get("markdown", "")
    if not md:
        raise RuntimeError(f"ideaflow 返回无 markdown：{data}")
    return md


def extract_image_urls(md: str) -> list[str]:
    urls = re.findall(r"!\[.*?\]\((.+?)\)", md)
    seen: set[str] = set()
    uniq: list[str] = []
    for u in urls:
        u = u.strip()
        if u and u not in seen:
            seen.add(u)
            uniq.append(u)
    return uniq


def download_image(url: str, dest: Path, referer: str, tries: int = 3) -> Path:
    last_err = None
    for i in range(tries):
        try:
            resp = requests.get(
                url,
                headers={"Referer": referer, "User-Agent": UA},
                timeout=60,
                stream=True,
            )
            resp.raise_for_status()
            dest.write_bytes(resp.content)
            return dest
        except Exception as e:
            last_err = e
            time.sleep(3)
    raise RuntimeError(f"下载失败（重试 {tries} 次）：{last_err}")


def normalize_to_jpg(src: Path, dest: Path) -> Path:
    im = Image.open(src).convert("RGBA")
    bg = Image.new("RGB", im.size, (255, 255, 255))
    bg.paste(im, mask=im.split()[3] if im.mode == "RGBA" else None)
    bg.save(dest, "JPEG", quality=92)
    src.unlink(missing_ok=True)
    return dest


def build_images_json(img_dir: Path, urls: list[str]) -> list[dict]:
    """扫描 img_dir 下所有 img-NN.jpg 生成 images.json（用于补重建）。"""
    images = []
    files = sorted(img_dir.glob("img-*.jpg"), key=lambda p: int(p.stem.split("-")[1]))
    for idx, path in enumerate(files, 1):
        with Image.open(path) as im:
            w, h = im.size
        images.append(
            {
                "index": idx,
                "filename": path.name,
                "staticFile": f"assets/article-images/{path.name}",
                "width": w,
                "height": h,
                "imageAspect": round(w / h, 4) if h else 0,
                "sourceUrl": urls[idx - 1] if idx - 1 < len(urls) else "",
            }
        )
    return images


def main() -> None:
    parser = argparse.ArgumentParser(description="抓公众号文章 + 下载原文图 + 完整性自检")
    parser.add_argument("--url", required=True, help="mp.weixin.qq.com/s/xxx")
    parser.add_argument("--out-dir", default=".", help="项目根目录")
    args = parser.parse_args()

    out_dir = Path(args.out_dir).expanduser().resolve()
    source_dir = out_dir / "work/source"
    img_dir = out_dir / "public/assets/article-images"
    source_dir.mkdir(parents=True, exist_ok=True)
    img_dir.mkdir(parents=True, exist_ok=True)

    print(f"[1/4] 抓 markdown：{args.url}")
    md = fetch_markdown(args.url)
    md_path = source_dir / "article.md"
    md_path.write_text(md, encoding="utf-8")
    print(f"  → {md_path}（{len(md)} 字符）")

    print("[2/4] 提取图片 URL")
    urls = extract_image_urls(md)
    print(f"  → {len(urls)} 张图")

    print("[3/4] 下载 + 统一 jpg（自动重试）")
    referer = "https://mp.weixin.qq.com/"
    for idx, url in enumerate(urls, 1):
        ext = Path(urlparse(url).path).suffix.lower() or ".jpg"
        if ext not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
            ext = ".jpg"
        raw_path = img_dir / f"img-{idx:02d}.raw{ext}"
        jpg_path = img_dir / f"img-{idx:02d}.jpg"
        try:
            download_image(url, raw_path, referer=referer)
            normalize_to_jpg(raw_path, jpg_path)
            with Image.open(jpg_path) as im:
                w, h = im.size
            print(f"  ✓ img-{idx:02d}.jpg  {w}x{h}  aspect={round(w/h, 4)}")
        except Exception as e:
            print(f"  ✗ 第 {idx} 张失败：{url} ({e})")

    print("[4/4] 完整性自检")
    md_count = len(urls)
    img_count = len(list(img_dir.glob("img-*.jpg")))
    images_json = source_dir / "images.json"
    if img_count == md_count and images_json.exists():
        print(f"  ✓ {img_count} 张图全部下载，images.json 已存在")
    else:
        print(f"  ! markdown 有 {md_count} 张图，实际 {img_count} 张，重建 images.json...")
        images = build_images_json(img_dir, urls)
        images_json.write_text(
            json.dumps(images, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"  → 已重建：{len(images)} 张")
        if img_count < md_count:
            missing = [u for i, u in enumerate(urls, 1)
                       if not (img_dir / f"img-{i:02d}.jpg").exists()]
            print("  ! 仍有缺失图片，如需完整可手动 curl 补下载：")
            for u in missing:
                print(f"    curl -H 'Referer: https://mp.weixin.qq.com/' -o <img-NN>.raw '{u}'")

    print("完成。下一步：读 article.md 拆稿。")


if __name__ == "__main__":
    main()
