# demoData.ts 数据结构与拆稿指南

`src/demoData.ts` 是视频的唯一真相（数据驱动，组件不写死画面）。拆稿 = 把文章内容映射到这个数据结构。

## 总结构

```ts
export const demoProject: ArticleVideoProps = {
  title: "视频标题",
  fps: 30,
  durationSeconds: 217.5,        // 必须 ≥ 最后一条字幕的 end（+0.5~1s 余量）
  voiceAudio: "assets/audio/voice.mp3",
  chapters: [{label: "开篇", start: 0}, ...],  // 顶部进度条章节
  scenes: [...],                  // 9-13 个场景，按 start 升序
  captions: [...],                // 58 条左右短句字幕（映射 srt 时间轴）
  sfxCues: [...],                 // 转场音效（可空数组）
};
```

## 场景类型

### cover（开场）
```ts
{kind: "cover", start: 0, eyebrow: "雪人说说 · 高报干货",
 titleLines: [[{text: "主标题"}], [{text: "强调词", tone: "accent"}]],
 subtitle: "副标题一句话"}
```

### list（要点清单，每屏 ≤5 行）
```ts
{kind: "list", start: 16.0, eyebrow: "小标签", heading: "大标题",
 items: [
   {index: "01", label: "短标签", value: "主要内容", tone: "accent", appearAt: 0.4},
   {index: "02", label: "短标签", value: "主要内容", appearAt: 1.0},
 ]}
```
appearAt 是场景内相对秒数，按口播说到该行的时间错开（间隔约 0.5-0.6s）。

### stat（数据大数字）
```ts
{kind: "stat", start: 88.5, eyebrow: "薪酬区间",
 number: "28", unit: "万",
 title: [{text: "解释标题"}, {text: "强调", tone: "accent"}],
 metrics: [{label: "档位", value: "数值", appearAt: 0.5}, ...]}
```

### compare（两栏对比）
```ts
{kind: "compare", start: 111.2, eyebrow: "笔面试", heading: "标题",
 choices: [
   {code: "A", title: "选项A", subtitle: "说明", tone: "accent", appearAt: 0.4},
   {code: "B", title: "选项B", subtitle: "说明", appearAt: 1.0},
 ]}
```

### article-image（原文图展示）
```ts
{kind: "article-image", start: 62.5, eyebrow: "标签",
 imageSrc: "assets/article-images/img-04.jpg", imageAspect: 1.2811,  // 值取自 images.json
 fit: "contain",   // 可选；contain=信息表格完整显示（默认），cover=氛围图裁切充满
 title: [{text: "标题"}, {text: "强调", tone: "accent"}],
 caption: "解读短句（≤14字）", source: "图源：公众号 / 章节名",
 appearAt: 0.3, titleAppearAt: 0.6, captionAppearAt: 1.0}
```
**铁律**：信息表格图（岗位表/专业表/薪酬表，含文字信息）必须 contain 完整显示，裁切会丢内容。
**信息图判定方法**（PIL 分析）：`white>0.5`（白底表格）或 `hlines>100`（大量水平线=文字行/卡片边框）→ 判定为信息图必须 contain；纯氛围图（深色、hlines≈0）才可 cover。实测误用 cover 会让图文卡片的右侧文字被裁出画面（用户投诉"文字超出画面"）。

**换行防护经验**（用户 2026-08-10/11 反馈"剩一两个字单独一行"）：
- 中文全角标点（`·`、`、`）按 **1em 宽度**计算（不是 0.5em），如"金融·经济·会计"8 字符 = 8×27px = 216px
- list 标签列 width 用 **260px**（容纳 8 个全角字符 + 余量），勿用 150/200px
- list value 列可用宽度约 **734px**（右侧 rows 区 1160px − 编号 74 − 标签 260 − 间距 92），value 字号按字符数动态缩放（valueFontFor：≤8字56px/≤11字48px/≤15字42px/更长36px）
- 标题字号按字符数动态缩放（titleFontFor：≤8字84px/≤12字72px/≤16字60px/更长52px）
- stat detail 标题 46px、stat 大数字 360/240/180px（按字符数）

### video（动态视频素材，用户偏好）
```ts
{kind: "video", start: 18.1, eyebrow: "标签",
 videoSrc: "assets/videos/rocket-45230.mp4",
 title: [{text: "主标题"}, {text: "强调", tone: "accent"}],
 caption: "短解读", source: "素材：Mixkit",
 appearAt: 0.3, titleAppearAt: 0.6, captionAppearAt: 1.0}
```
- 视频自动 **object-fit: cover 裁切充满主舞台**（用户明确要求，不留黑边）
- 素材放 `public/assets/videos/`，mixkit 720p 素材 10-20s，场景通常 8-25s 够用（Video loop）

### outro（结尾）
```ts
{kind: "outro", start: 195.9, eyebrow: "谢谢观看", title: "下期见", subtitle: "关注引导"}
```

## 拆稿规范（LLM 核心工作）

1. **scene 数**：9-13 个（3000 字文章 ≈ 12 个）
2. **版式交错**：video/list/article-image 不连续 3 个同类型（list→list→list 违规）
3. **video 场景放关键位置**：开场后主体介绍、章节过渡、总结收尾（火箭/战机/军舰等与主题匹配的素材）
4. **信息表格图**按文中实际位置插入，同一张图不重复
5. **每屏文字元素 ≤5 个**

## 字幕（captions）

直接映射 `captions.word.srt`（句级）时间轴，每条 8-25 字：

```ts
{start: 18.1, end: 23.2, parts: [{text: "核心招聘主体，一共"},
 {text: "九家", tone: "accent"}, {text: "头部央企。"}]}
```

- start/end 取 srt 的起止时间（秒）
- **accent 关键词每条最多 1 个**（蓝色强调，太多会花）
- 字幕层自动渲染 32px、最多 2 行（短句化保证），不遮挡画面

## 音效（sfxCues）

场景切换处加转场音效（assets/audio/sfx-*.mp3），音量 0.5，duration 0.5-0.8s：

```ts
{id: "s1", start: 18.0, duration: 0.8, file: "assets/audio/sfx-whoosh-fast-transition.mp3", volume: 0.5}
```

## images.json 格式（fetch_article.py 输出）

```json
[{"index": 1, "filename": "img-01.jpg", "staticFile": "assets/article-images/img-01.jpg",
  "width": 1080, "height": 720, "imageAspect": 1.5, "sourceUrl": "..."}]
```
imageAspect = width/height，article-image 场景必须与之一致。
