---
id: xueren-wechat-article-video
name: 雪人老师·公众号文章转视频
title: 雪人老师·公众号文章转视频
description: 将微信公众号文章（mp.weixin.qq.com）制作为竖屏/横屏短视频的完整流水线：环境自检、抓取文章与原文图、下载相关视频素材、Remotion 工程搭建、短句口播稿拆解、男声 TTS 配音、字幕对齐、渲染成片与发布文案。当用户提供公众号文章链接要求\"转视频\"、\"做成视频\"、\"生成视频\"，或提到公众号文章视频化时触发。不适用于：PPT 转视频、纯图片轮播、已有视频的剪辑加工、非公众号来源的文字转视频。
description_zh: 雪人老师·公众号文章转视频
description_en: wechat-article-video
version: 1.0.0
author: 雪人
license: MIT
allowed-tools: ""
display_name: wechat-article-video
display_name_zh: 雪人老师·公众号文章转视频
trigger: ["转视频", "做成视频", "生成视频", "公众号文章视频化", "文章转视频", "公众号文章链接"]
examples: "https://mp.weixin.qq.com/s/xxxx 把这篇公众号文章转成视频。"
platforms: [ima, WorkBuddy, QClaw]
metadata:
  author: 雪人
  category: 自媒体
---

# 雪人老师·公众号文章转视频

把任意一篇公众号文章转成 Studio 风格的横屏短视频（1920×1080），带动态视频素材、男声配音、短句字幕和发布文案。

## 核心心法

视频是一条以声音为轴的时间线：**先写口播稿 → 生成配音 → 拿到句级字幕时间轴 → 用字幕驱动画面 → 渲染成片**。字幕是整条视频的唯一基准。

## 环境前提（每次会话先跑）

沙箱每次会话重置，运行前必须执行环境自检：

```bash
python3 <skill>/scripts/setup_env.py
```

脚本自动完成：恢复 Chrome（`~/.remotion/`）、安装 edge-tts、恢复 ffmpeg 软链、检查依赖仓库（`/sandbox/workspace/video-skills-toolkit-main`，缺失时自动下载）。**任何一步失败先修复再继续**——npm install 和渲染都依赖它们。

## 字体与版权（用户明确关注）

所有字体必须为免费可商用授权（SIL OFL 1.1 或同类），并记录来源：

| 用途 | 字体 | 授权 |
|---|---|---|
| 正文/标题 | Noto Sans SC（思源黑体） | SIL OFL 1.1，Google Fonts |
| 西文数字 | Space Grotesk | SIL OFL 1.1，Google Fonts |
| **字幕** | **Noto Serif CJK SC（思源宋体）** | **SIL OFL 1.1，Adobe+Google** |

**字幕用思源宋体与黑体正文区分**（用户偏好）：scaffold_project.py 自动应用 theme.video.ts（注册思源宋体）并运行 `extract_serif_font.py`——**优先本地字体**：从系统 `/usr/share/fonts/opentype/noto/NotoSerifCJK-*.ttc` 提取 SC 实例，或从 workspace 备份（`video-skills-toolkit-main/assets/fonts/`）复制，不依赖网络下载。项目 `src/theme.ts` 的 `fonts.serif` 用于字幕（sceneTypes.tsx captionStyle）。

⚠️ 不要使用未经授权的商业字体（如方正、汉仪全家桶）；确需下载新字体时优先系统已装字体或 OFL 开源字体。

## 工作流

### 1. 抓取文章与原文图

```bash
mkdir -p /tmp/rm/wx-<短标识>
cd /tmp/rm/wx-<短标识>
python3 <skill>/scripts/fetch_article.py --url "<公众号链接>" --out-dir .
```

产出：`work/source/article.md`（文章 markdown）、`public/assets/article-images/img-NN.jpg`（原文图，统一 jpg）、`work/source/images.json`（含每张图宽高比）。

⚠️ 抓取完成后**必须验证完整性**：images.json 存在、图片数量与 article.md 中 `![]()` 数量一致（`grep -c "!\[" article.md`）。fetch 脚本偶发第 N 张图超时导致 images.json 未写出——缺图时手动 curl 补下载（带 `Referer: https://mp.weixin.qq.com/`）+ PIL 转 jpg + 重建 images.json。参考 `references/scene-data-guide.md` 的 images.json 格式。

⚠️ **ideaflow 图床不稳定**（2026-08-17 实测）：偶发缺图且 curl 补下载超时。**缺 1-2 张氛围图不阻塞主流程**——视频画面以视频素材为主，article-image 场景用已有图片即可，缺失氛围图直接跳过（不要死磕补图）。

### 2. 通读原文，提炼内容骨架

读 `work/source/article.md`，用 fetch 工具同时读原文链接确认完整结构。明确：文章核心主题、3 个以内 key points、哪些图是**信息表格**（必须完整显示）、哪些是**氛围图**（可裁切充满）。

### 3. 下载相关视频素材（必须，用户 2026-08-16 强调）

**素材必须与文章内容对得上，禁止无脑复用旧素材/套用固定模板**——同一批 factory/technology 素材反复用会让每期视频画面雷同，用户已明确投诉。

主题匹配示例（按文章实际内容选词，可组合）：
| 文章内容 | 主题词 |
|---|---|
| 计算机/编程 | `computer,coding` |
| 芯片/电子/电路 | `technology,electronics` |
| 机器人/自动化/智造 | `robot,factory` |
| 电网/电气/新能源 | `power,energy` |
| 金融/银行/投资 | `finance,stock-market,office` |
| 铁路/高铁/中车 | `railway,train` |
| 石油/油田/化工 | `oil,factory` |
| 粮油/农业/食品 | `agriculture,food,grain` |
| 通信/运营商/网络 | `communication,data` |
| 军工/航天/航空 | `rocket,space,jet` |
| 医药/教育/城市 | `medical,education,city` |

```bash
python3 <skill>/scripts/download_videos.py --topics <主题词,逗号分隔> --out-dir /tmp/rm/vids
```

脚本从 mixkit.co 提取直链并**串行下载（勿并行，易被限流）+ 自动重试**。下载后**立即 `check_media.py --dir <目录>` 校验**，通过才复制到 `public/assets/videos/` 并缓存 workspace。素材统一放 `public/assets/videos/`。

⚠️ 缓存仅用于"同主题复用"（如另一篇也是计算机主题），**跨主题复用前必须重新下载匹配素材**。

### 4. 搭建 Remotion 工程

```bash
python3 <skill>/scripts/scaffold_project.py \
  --project-dir /tmp/rm/wx-<短标识>-video \
  --title "<视频标题>" \
  --article-url "<公众号链接>" \
  --source-dir /tmp/rm/wx-<短标识>
```

脚本完成：脚手架生成 → 复制文章素材 → **应用 video 场景补丁（sceneTypes.tsx 覆盖）** → 复制视频素材 → npm install（本地磁盘 /tmp 下约 30-60 秒）。

### 5. 写短句口播稿（LLM 核心工作）

在 `work/source/script.md` 写口播稿，**每行一个短句（8-25 字）**——这是字幕 ≤2 行和"跟上口播节奏"的基础。规则：

- 按内容块组织，覆盖文章全部关键信息，口语化面向家长/学生
- 长句必须拆分：如"国家电网统考，公共行业知识占两成，八成是专业知识"拆成两句
- 数字用口语："18到28万"而非"18-28万"

**专用词汇特殊处理规则（用户规范，2026-08-09 确认）**——写口播稿时逐句检查：

| 类型 | 处理方式 | 示例 |
|---|---|---|
| 数字代号（985/211/C9） | **画面文字写数字，配音读逐字**；**211 特指院校层级读"二幺幺"（er yao yao）** | demoData/captions 写"985""211"；script.md（配音）写"九八五""二幺幺" |
| 专有名词（技术标准等） | 保留原文数字+字母 | 5G/4G/3G 写"5G"，**不写"五G"** |
| 多音字院校缩写 | 写全称规避误读 | "重邮"→"重庆邮电"（重读 chóng 不读 zhòng） |
| 多音字注意语境 | 金融语境"行"读 háng | "六大行"→配音写"六大银行"（háng）；"总行/分行"保留（常见词 TTS 读 háng） |
| 多音字注意语境 | 公务员考试"行测"读 xíng cè | 配音写"行政能力测验"确保读音（画面字幕仍显示"行测"） |
| 长并列名词 | 加顿号强制断句 | "北邮、南邮、重庆邮电、西邮""各位同学、家长朋友们" |
| 生僻/易错读音词 | 用全称或常见表述 | 不确定时优先全称，不赌 TTS 多音字 |

⚠️ 读音细节：**211 = "二幺幺"**（èr yāo yāo，编号中"1"读"幺"），不是"二一一"；**985 = "九八五"**。

核心原则：**不赌 TTS 的断词和多音字判断**——有风险就写全称/加标点，确保读音和断句 100% 正确。

### 6. 生成男声配音与句级字幕

```bash
cd /tmp/rm/wx-<短标识>-video
python3 <skill>/scripts/generate_tts_v2.py --project-dir .
```

用 edge-tts `zh-CN-YunjianNeural`（云健，中年男声）**逐句生成** → 实测每句 wav 时长 → 裁剪句首尾静音 → 句间 0.3s 静音拼接 → `public/assets/audio/voice.mp3` + `work/captions/captions.word.srt`（时间轴 = 实测时长累加，与实际音频严格对齐）。

⚠️ **不要用 edge-tts 的 `--write-subtitles`**（generate_tts.py 旧版）：其 srt 时间戳是模型预测值，长文本累积漂移（实测 18s 处已漂移 3.2s），导致字幕/画面滞后于声音。v2 脚本生成后可用 `ffmpeg silencedetect` 抽查：srt 边界与静音段偏差应 <0.1s。

⚠️ **TTS 网络超时自动重试**（2026-08-17 实测 edge-tts 间歇性超时，120s/句）：脚本已支持断点续传（跳过已生成的 mp3），超时后直接重跑即可续传。自动重试循环：
```bash
cd /tmp/rm/wx-<短标识>-video
for i in $(seq 1 8); do
  python3 <skill>/scripts/generate_tts_v2.py --project-dir . 2>&1 | tail -1
  [ -f public/assets/audio/voice.mp3 ] && echo "✅ 配音完成" && break
  sleep 3
done
```
配音完成后**立即把 voice.mp3 + captions.word.srt 持久化到 workspace**（`projects/<标识>/audio/` + `captions/`），/tmp 被清后无需重跑 TTS。

### 7. 拆稿写 demoData.ts（LLM 核心工作）

按 `references/scene-data-guide.md` 的完整数据结构，将文章拆成 9-13 个场景写入 `src/demoData.ts`：

- 场景类型：cover / list / stat / compare / article-image / **video** / outro
- **video 场景**：动态素材封面式展示，object-fit: cover 裁切充满（用户明确偏好），配标题+短 caption
- **article-image 场景**：信息表格图用 contain 完整显示（不裁切，会丢文字）；氛围图可设 `fit: "cover"`
- **字幕**：直接映射 srt 的 58 条左右短句时间轴，关键词蓝色 `tone: "accent"` 强调（每条最多 1 个关键词）
- 版式交错：video/list/article-image 不要连续 3 个同类型
- 每屏文字元素 ≤5 个

### 8. 验证与渲染

```bash
cd /tmp/rm/wx-<短标识>-video
npx tsc --noEmit                 # 类型检查
python3 <skill>/scripts/check_media.py .   # 渲染前素材校验（ffmpeg 全量解码，拦截损坏素材）
npx remotion still src/index.ts ArticleVideo renders/check.png --frame=<帧> --scale=0.3   # 抽帧审核
npm run render                   # 正式 1080p 渲染（6000+ 帧约 15-20 分钟，后台运行+轮询）
```

审核要点：video 场景是否充满画面、表格图是否完整、字幕 ≤2 行且不遮挡画面、无文字溢出。

**渲染参数（已固化到 remotion.config.ts 模板 + package.json，自动生效）**：
- `Config.setConcurrency(os.cpus().length)`：并发吃满全部核心（沙箱 4 核，提速 ~30%）
- `Config.setDelayRenderTimeoutInMilliseconds(600000)`：视频素材加载超时 10 分钟（**180s 会在 4 核并发解码慢时误杀**，实测渲染 85% 处因 delayRender timeout 失败）
- `render` script 带 `--crf=20`：编码提速 ~20%，画质无感差异（原 18）

**渲染启动必须确认**（nohup 后台命令偶发未真正执行，不确认会白等）：
```bash
nohup npm run render > render.log 2>&1 &
sleep 15 && head -3 render.log && pgrep -f "[r]emotion" | wc -l   # 必须看到命令回显 + 进程数 >0
```

**渲染失败排错速查表**（先看 render.log 错误类型再动手）：
| 报错特征 | 根因 | 处理 |
|---|---|---|
| `PIPELINE_ERROR_DECODE: video decode error` | 视频素材文件损坏（下载不完整） | 换素材或重新下载，替换前先 `ffmpeg -v error -i <f> -f null -` 验证 |
| `A delayRender() ... was called but not cleared after <ms>ms` | 素材在 Remotion 浏览器中加载失败 | **看报错里的素材路径**：① 若多个素材都超时→放宽 timeout；② **若特定单个素材超时（其他正常）→ ffmpeg 校验通过≠浏览器可解码（实测 business-47005 案例），直接换素材重渲染** |
| `Version mismatch`（remotion 版本不一致） | `npm install` 变更了依赖版本 | 忽略（非致命），渲染照常 |
| `RangeError: Maximum call stack` | React 渲染栈溢出 | 通常是场景数据结构问题，检查 demoData.ts |

### 9. 封面图与内嵌封面版（用户确认规范）

最终方案：**先生成正片（无封面场景）→ PIL 合成封面图 → 生成 2s 静态封面段 → 封面段在前合并**（彻底避免画面重叠和首帧网格问题）。

```bash
# 1) 从原始素材视频抽一帧做封面背景（选主题贴切的画面，如工厂/校园/城市夜景）
# ⚠️ 必须从 public/assets/videos/*.mp4（原始素材）截取，严禁从 renders/demo.mp4 或 final.mp4 截取
#    渲染视频含有字幕、进度条等画面元素，截取做封面会导致这些元素出现在封面上
ffmpeg -y -ss 5 -i public/assets/videos/factory-14051.mp4 -frames:v 1 -update 1 renders/cov-factory.png

# 2) PIL 合成封面（深色渐变遮罩 + 白字大标题 + 金色强调副题）
python3 <skill>/scripts/make_cover.py --bg renders/cov-factory.png --out renders/cover.png \
  --title1 "主标题" --title2 "强调副题" --sub "一句话副标题"

# 3) 封面段合并 + 内嵌封面
python3 <skill>/scripts/concat_cover.py --project-dir . --cover renders/cover.png --demo renders/demo.mp4
python3 <skill>/scripts/embed_cover.py --video renders/final.mp4 --cover renders/cover.png
```

**🔴 封面帧来源铁律（2026-08-23 确认）**：封面背景帧**必须**从 `public/assets/videos/*.mp4`（原始素材视频）中截取，**严禁**从 `renders/demo.mp4` 或 `renders/final.mp4`（渲染后的成片）中截取。渲染视频中含有字幕、进度条等画面元素，截取做封面背景会导致这些元素直接出现在封面上。正确做法：选一段主题贴切的素材视频（如工厂/校园/实验室等），用 `ffmpeg -ss <秒> -i <素材mp4> -frames:v 1` 截取干净画面帧作为封面背景。也可用文章原图（如城市主题用原文的城市夜景图）做封面背景——分辨率不足时 make_cover.py 的模糊遮罩可掩盖画质损失（2026-08-25 实测 911×519 原图放大可用）。

⚠️ **mp4 concat demuxer 直接 -c copy 会损坏 duration 元数据**：两段 timebase 不一致（封面 15360 vs Remotion 90k）时 moov duration 被错误计算（实测 4:18 内容写成 25:14），播放器按错误时基播放 → "时长不对 + 音画不同步"。concat_cover.py 用 filter_complex 重编码统一时基（crf18 veryfast，约 5 分钟）。另注意 ffmpeg 7.0.2 静态版在此环境读取 mpegts 输入会静默失败（ts 中转方案不可用），concat demuxer 对文件内相对路径解析也不可靠（必须绝对路径）。

**交付前必须验证**（缺一不可）：
- `ffmpeg -i final.mp4` 的 Duration ≈ 正片 + 2s（不允许出现分钟级偏差）
- 首帧像素 = 封面（PIL diff < 5）
- 音频尾部语音与 srt 最后一条对齐（silencedetect 偏差 <0.1s）

- **Windows 资源管理器默认取视频中间帧做缩略图**（无法指定帧）；内嵌封面（attached_pic 轨）让手机相册、微信、QQ、装了 Icaros/K-Lite 缩略图扩展的 Windows 显示首帧封面
- 交付物：视频 mp4（仅推荐版-内嵌封面版）+ 封面 PNG + 宣发文案

### 10. 交付

- 成品复制到 workspace 根目录（`/sandbox/workspace/<主题>-雪人说说-v<n>.mp4` + `<主题>-封面-v<n>.png`），provide_file 给下载链接（仅交付推荐版-内嵌封面版 + 封面 PNG + 宣发文案，不交付普通版/预览图）
- 源文件备份到 `/sandbox/workspace/video-skills-toolkit-main/projects/<标识>/`（沙箱重置后凭此恢复）：script.md、demoData.ts、images.json、captions.word.srt、voice.mp3、gen_demodata.py（成品 final-v<n>.mp4 也备份一份，供沙箱重置后快速恢复）
- **发布文案**：按 `references/delivery-guide.md` 规范输出（约 300 字 + 标题 ≤20 字 + 末尾话题标签），存 `projects/<标识>/<主题>-宣发文案-v<n>.md`

## 注意事项

- **🔴 新任务先清理旧数据（用户 2026-08-24 明确要求，保障磁盘空间）**：接到新任务第一步先执行清理 SOP——① /tmp 下旧工程、渲染缓存直接删（`rm -rf /tmp/rm/* /tmp/remotion-webpack-bundle-* /tmp/remotion-v4.0.484-assets* /tmp/react-motion-render*`）；② workspace 根目录只保留最近 1-2 篇已交付的三件套（视频/封面），更早的旧交付视频与封面删除（宣发文案 .md 体积小全部保留）；③ `video-skills-toolkit-main/demo-output/` 历史交付汇总可整体删除；④ `projects/<标识>/` 只保留恢复源文件（script.md/demoData.ts/audio/captions/images.json/gen_demodata.py），成品 final-v*.mp4 删除（如根目录已保留交付副本）；⑤ `assets/videos/` 素材缓存只保留最近 1-2 篇的目录，散落素材与更早项目目录删除（素材可随时重新下载）。清理前先列文件清单核对，确认不误删用户上传原文件与最近交付物。
- **一切重文件操作（npm install、bundle、render）必须在 /tmp 下**——`/sandbox/workspace` 是 virtiofs，海量小文件操作会卡死（npm install 要 31 分钟 vs 本地 31 秒）
- 渲染前确认 `remotion.config.ts` 存在且 `setBrowserExecutable` 指向 `/root/.remotion/chrome-headless-shell/chrome-headless-shell`
- mixkit 素材下载**禁止并行 curl**（会整批失败），串行 + 失败重试
- 长渲染用 `nohup npm run render > render.log 2>&1 &` 后台跑，轮询 `tail -3 render.log`，**启动 15s 后必须确认日志与进程**
- 清理 Chrome 残留进程用 `pgrep -f "[c]hrome-headless-shell" | xargs -r kill -9`（pkill 会误杀自身 shell）

### 素材校验铁律（2026-08-16 教训，两次渲染失败的根因）

1. **下载后立即校验再入库 + 立即缓存**：`python3 <skill>/scripts/check_media.py --dir <目录>`，通过后**马上复制到 `assets/videos/<标识>/` 缓存**（/tmp 随时可能被清，实测 2026-08-17 下载好的素材因未及时缓存而丢失）。mixkit 下载偶发文件不完整（NAL 错误），坏文件会被后续所有项目复用（实测 railway-27768 损坏 → 渲染 6777/10704 帧才报 `PIPELINE_ERROR_DECODE`，白白浪费 15 分钟）
2. **渲染前全量校验**：`python3 <skill>/scripts/check_media.py .`（校验 public/assets/videos/）
3. **损坏素材处理**：用同主题完好素材替换（如 railway-27768→railway-25132），替换后修改 demoData.ts 的 videoSrc
4. **ffmpeg 校验通过 ≠ Remotion 可解码**（2026-08-17 实测 business-47005）：ffmpeg 解码正常但渲染时 `<Video>` 组件加载超时。渲染报 `delayRender timeout` 且报错指向**单个特定素材**时，直接换素材重渲染（不必纠结根因）
5. **同一素材之前用过成功 ≠ 这次一定成功**（2026-08-25 实测 office-45923）：office-45923 在 wx-gh 项目渲染成功，wx-cs 项目复用时渲染卡在 frame 2179 报 `delayRender timeout`。缓存复用的素材也可能在特定渲染批次/浏览器实例下解码失败——遇 `delayRender timeout` 指向单个素材时，直接换用未使用的同主题素材（如 finance-46979）重渲染，**不要在同一素材上重试**（重试大概率再次失败）

### 沙箱 /tmp 重置恢复流程（2026-08-16 实测，一天内被清 3-4 次）

`/tmp` 生命周期不可控（可能每 30-60 分钟被清），**所有中间产物必须立即持久化到 workspace**：

| 产物 | 持久化位置 | 恢复方式 |
|---|---|---|
| 文章（article.md/images.json/图） | `projects/<标识>/source/` + `public/` | 直接复制回 /tmp 工程 |
| 口播稿 script.md | `projects/<标识>/script.md` | 复制到工程 work/source/ |
| 配音 voice.mp3 + 字幕 srt | `projects/<标识>/audio/` + `captions/` | 复制到工程（**不用重跑 TTS**） |
| 组装脚本 gen/assemble_demodata.py | `projects/<标识>/` | 直接运行 |
| 视频素材 | `assets/videos/<标识>/` | 复制到工程 public/assets/videos/ |

重建流程：setup_env → 恢复文章目录 → scaffold → 复制素材/脚本/配音 → gen_captions + assemble → tsc → check_media → 渲染。**全程约 5 分钟**（跳过抓文章与 TTS，这两步最耗时）。

### 流程时间预估（供排期参考）

| 环节 | 时间 |
|---|---|
| 环境自检 + 抓文章 + 下载素材 | 5-10 分钟 |
| 工程搭建 + npm install | 2 分钟 |
| 写口播稿 + 配音（123 句约 6 分钟） | 10 分钟 |
| 组装 demoData + tsc + 抽帧审核 | 5 分钟 |
| 正式渲染 1080p（10000 帧） | 15-20 分钟 |
| 封面 + 合并 + 内嵌 + 验证 | 5 分钟 |
| **合计** | **约 45-60 分钟/篇** |

### 常见问题与解决方案（2026-08-23 更新）

#### 1. 章节导航（TopBar chapters）

- **现象**：视频顶部显示章节标签导航条（如"开篇|行政编制|事业编制|..."），当前章节高亮，未来章节灰色
- **原因**：`demoData.ts` 中 `chapters` 字段被 TopBar 组件渲染为顶部导航
- **去掉方法**：从 `demoData.ts` 删除 `"chapters": [...]` 字段即可（TopBar 已修改为 `chapters` 为空或未定义时返回 null）
- **批量处理**：`python3 -c "import re; c=open('demoData.ts','r',encoding='utf-8').read(); c=re.sub(r',\\s*\"chapters\":\\s*\\[[^\\]]*\\]','',c); open('demoData.ts','w',encoding='utf-8').write(c)"`

#### 2. 并行渲染崩溃（Chrome Page crashed）

- **现象**：多个分段同时渲染时，Chrome headless-shell 崩溃报 "Page crashed"
- **根因**：每个渲染进程启动独立 Chrome 实例，6 个并行 = 6 个 Chrome 争抢 4 核 CPU + 内存
- **解决**：**最多同时渲染 2 个分段**，`--concurrency=2`，一个完成后再启下一个
- **清理残留**：`pgrep -f "[c]hrome-headless-shell" | xargs -r kill -9`

#### 3. /tmp 磁盘空间不足（ENOSPC）

- **现象**：渲染报 "ENOSPC: no space left on device"
- **根因**：Remotion 在 /tmp 生成大量 webpack bundle 和资产缓存（每个渲染 ~20-30MB）
- **预防**：渲染前清理 `rm -rf /tmp/remotion-webpack-bundle-* /tmp/remotion-v4.0.484-assets* /tmp/react-motion-render*`
- **监控**：`df -h /tmp` 确认可用空间 > 500MB

#### 4. npm install 缺包（@remotion/layout-utils）

- **现象**：渲染报 "Can't resolve '@remotion/layout-utils'"
- **原因**：sceneTypes.video.tsx 使用 `measureText`，依赖该包但 scaffold 未自动安装
- **解决**：scaffold 后执行 `npm install @remotion/layout-utils`

#### 5. 后台渲染启动确认

- **正确模式**：`nohup npx remotion render ... > render.log 2>&1 & echo "PID=$!"`
- **确认运行**：`sleep 15 && tail -3 render.log && pgrep -f "[r]emotion" | wc -l`
- **常见失败**：命令返回 exit_code=-1 但实际未启动，重试一次即可

#### 6. 🔴 渲染期间严禁清理 Remotion webpack 缓存（2026-08-24 wx-zsb 事故）

- **现象**：渲染到 80% 报 `Error while downloading .../public/assets/audio/voice.mp3: 404`，渲染中断需重头再来
- **根因**：渲染中执行了 `rm -rf /tmp/remotion-webpack-bundle-*`——该 bundle 目录含渲染器正在用的 **public 静态资源副本**（voice.mp3 被复制到 bundle 里），删除后渲染器找不到素材直接 404
- **铁律**：**渲染进行中绝对禁止清理 /tmp/remotion-* 缓存**，只能清理其他无关文件（如旧的 tts_tmp、voice.wav 中间产物）；渲染前清理、渲染后清理都安全
- **渲染中磁盘告急时的可删项**：`public/assets/audio/voice.wav`（30M，TTS 中间产物）、`work/tts_tmp/`（逐句 mp3）、旧的 /tmp/rm 工程（已交付的）

#### 7. edge-tts 间歇性超时（2026-08-24 wx-zsb 实测）

- **现象**：`subprocess.TimeoutExpired`（45s）或 `ConnectionTimeoutError to host wss://speech.platform.bing.com`，大量句子连续失败
- **根因**：edge-tts 走微软 WSS 服务，网络波动时连接超时；沙箱对微软服务不稳定
- **解决**：① 脚本超时已从 45s 提高到 **120s**（`generate_tts_v2.py` 的 `def run(cmd, timeout=120)`）；② 脚本支持断点续传（跳过已生成的 mp3），失败后直接重跑即可续传；③ 用重试循环后台跑：`nohup bash -c 'for i in $(seq 1 20); do python3 generate_tts_v2.py --project-dir .; [ -f public/assets/audio/voice.mp3 ] && break; sleep 5; done' > /dev/null 2>&1 &`
- **耗时参考**：134 句网络正常约 3 分钟，网络波动时可能 30-60 分钟（分多轮续跑完成）
