# 雪人老师·公众号文章转视频

> 将微信公众号文章（mp.weixin.qq.com）制作为竖屏/横屏短视频的完整流水线：环境自检、抓取文章与原文图、下载相关视频素材、Remotion 工程搭建、短句口播稿拆解、男声 TTS 配音、字幕对齐、渲染成片、封面竖屏安全区布局（1920×1080 画布 + 中央 608×1080 文字活动区）与发布文案。当用户提供公众号文章链接要求"转视频"、"做成视频"、"生成视频"，或提到公众号文章视频化时触发。不适用于：PPT 转视频、纯图片轮播、已有视频的剪辑加工、非公众号来源的文字转视频。

本 skill 遵循通用 SKILL 规范（`SKILL.md` + `meta.json` + 资源目录），可装入任何支持 skill 的 AI 工具（WorkBuddy、Claude Code、Cursor 等）。

## 安装（作为 AI 工具的 skill）

1. 克隆仓库：

   ```bash
   git clone https://github.com/JackieZheng/xueren-wechat-article-video.git
   ```

2. 把目录放进你的 AI 工具 skills 目录（以 WorkBuddy 为例）：

   ```bash
   # Windows
   xcopy /E /I 雪人老师·公众号文章转视频 %USERPROFILE%\.workbuddy\skills\雪人老师·公众号文章转视频
   # macOS / Linux
   cp -r 雪人老师·公众号文章转视频 ~/.workbuddy/skills/
   ```

3. 如有依赖，进入目录安装：

   ```bash
   cd 雪人老师·公众号文章转视频 && npm install   # 或 pip install -r requirements.txt（视 skill 而定）
   ```

## 使用方式

装好后使用就是普通的对话形式——在 AI 工具里说出对应意图，它会按 `SKILL.md` 的流程引导你完成。详细流程见 `SKILL.md`。

## 项目结构

```
xueren-wechat-article-video/
assets/
references/
scripts/
.gitignore
LICENSE
SKILL.md
config.template.json
meta.json
    ArticleVideo.video.tsx
    PreloadContext.video.tsx
    background.video.tsx
    sceneTypes.video.tsx
    theme.video.ts
    delivery-guide.md
    scene-data-guide.md
    assemble_final.py
    check_media.py
    concat_cover.py
    download_videos.py
    embed_cover.py
    extract_serif_font.py
    fetch_article.py
    generate_tts.py
    generate_tts_v2.py
    make_cover.py
    retime_demoData.py
    scaffold_project.py
    setup_env.py
```

## License

[MIT](./LICENSE) © 2026 雪人

---

GitHub: https://github.com/JackieZheng/xueren-wechat-article-video
