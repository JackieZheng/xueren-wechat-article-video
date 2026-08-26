# 雪人老师·公众号文章转视频

> 将微信公众号文章自动转为竖屏/横屏短视频的完整技能流水线

## 简介

本技能实现了从微信公众号文章到短视频的端到端自动化流程，适用于「雪人说说」等自媒体账号的内容二次分发。

**输入**：公众号文章链接（mp.weixin.qq.com）
**输出**：竖屏/横屏短视频 + 封面图 + 宣发文案

## 流水线步骤

| 步骤 | 说明 | 核心脚本 |
|------|------|----------|
| 1. 环境自检 | 检查 ffmpeg、Remotion、edge-tts 等依赖 | `scripts/setup_env.py` |
| 2. 抓取文章 | 解析公众号全文、提取正文与配图 | `scripts/fetch_article.py` |
| 3. 下载素材 | 根据文章内容匹配免费视频素材（Mixkit） | `scripts/download_videos.py` |
| 4. 搭建工程 | 生成 Remotion 项目脚手架 | `scripts/scaffold_project.py` |
| 5. 口播稿 | AI 生成短句口播稿（每句8-25字） | — |
| 6. TTS配音 | edge-tts 男声配音 + 句级字幕 | `scripts/generate_tts_v2.py` |
| 7. 场景数据 | 生成 demoData.ts 场景配置 | `scripts/retime_demoData.py` |
| 8. 渲染正片 | Remotion 分段渲染（每段3000帧，CRF=20） | — |
| 9. 封面合成 | 从素材抽帧 + 标题排版 | `scripts/make_cover.py` |
| 10. 合并交付 | 封面+正片 concat，混入配音 | `scripts/concat_cover.py` |

## 技术栈

- **前端渲染**：Remotion 4.x（TypeScript + React）
- **配音**：edge-tts（edge-tts 7.2.8，中年男声 zh-CN-YunjianNeural）
- **字体**：Noto Sans SC 黑体（正文）、Space Grotesk（西文）、Noto Serif CJK SC 思源宋体（字幕）
- **视频处理**：ffmpeg 7.0.2（johnvansickle 静态版）
- **浏览器**：Chrome Headless Shell

## 使用方式

1. 确保已安装依赖：`python scripts/setup_env.py`
2. 在 IMA 平台搜索并安装本技能「雪人老师·公众号文章转视频」
3. 向助手发送公众号文章链接 + 「转视频」指令
4. 等待完成后获取三件套：视频 MP4 + 封面 PNG + 宣发文案 MD

## 项目结构

```
雪人老师·公众号文章转视频/
├── SKILL.md                  # 技能说明文档
├── skill.json                # 技能元数据
├── assets/
│   ├── sceneTypes.video.tsx  # 场景类型定义与组件
│   ├── background.video.tsx  # 背景组件
│   └── theme.video.ts        # 主题配置
├── references/
│   ├── scene-data-guide.md   # 场景数据指南
│   └── delivery-guide.md     # 交付指南
└── scripts/
    ├── setup_env.py          # 环境初始化
    ├── fetch_article.py      # 文章抓取
    ├── download_videos.py    # 素材下载
    ├── scaffold_project.py   # 项目脚手架
    ├── generate_tts_v2.py    # TTS 配音 + 字幕
    ├── generate_tts.py       # TTS（旧版）
    ├── make_cover.py         # 封面生成
    ├── concat_cover.py       # 封面+正片合并
    ├── embed_cover.py        # 封面嵌入
    ├── retime_demoData.py    # 场景数据调整
    ├── check_media.py        # 素材校验
    ├── extract_serif_font.py # 字体提取
```

## 常见问题

- **沙箱网络限制**：github.com:443 在沙箱环境可能超时，建议本地开发
- **素材下载**：Mixkit 素材需逐个串行下载并校验字节大小
- **字体**：思源宋体从系统 `/usr/share/fonts/opentype/noto/` 提取，已备份至 `assets/fonts/`
- **渲染**：Remotion bundling 需在本地磁盘（/tmp）执行，virtiofs 上会卡死

## **查看效果演示**
- https://mp.weixin.qq.com/s/WQhmg27Z5YLHcIZ52fm5LQ?scene=1&click_id=979349242

## License

MIT License © 雪人
