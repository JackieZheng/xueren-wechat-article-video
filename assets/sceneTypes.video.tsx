import type {CSSProperties, ReactNode} from "react";
import {AbsoluteFill, Img, staticFile, useCurrentFrame, useVideoConfig, Video} from "remotion";
import {colors, fonts, layout} from "./theme";
import {clamp, frameFromSeconds, progress} from "./shared";

// === 数据模型 ============================================

export type Tone = "accent" | "white" | "muted";

export type RichTextPart = {
  text: string;
  tone?: Tone;
};

export type Chapter = {
  label: string;
  start: number;
};

export type Caption = {
  start: number;
  end: number;
  parts: RichTextPart[];
};

export type SfxCue = {
  id: string;
  start: number;
  duration: number;
  file: string;
  volume: number;
};

// === 基础 5 场景（与 talking-head-remotion 对齐） ===========

type CoverScene = {
  kind: "cover";
  start: number;
  eyebrow: string;
  titleLines: RichTextPart[][];
  subtitle: string;
  /** 满屏封面背景：video/image 裁切充满全屏（首帧封面用） */
  background?: {type: "video" | "image"; src: string; startFrom?: number};
};

type ListScene = {
  kind: "list";
  start: number;
  eyebrow: string;
  heading: string;
  items: Array<{
    index: string;
    label: string;
    value: string;
    tone?: Tone;
    /** 进场时刻（场景内相对秒数），来自口播说到该行内容的字幕起点 */
    appearAt?: number;
  }>;
};

type StatScene = {
  kind: "stat";
  start: number;
  eyebrow: string;
  number: string;
  unit: string;
  title: RichTextPart[];
  metrics: Array<{
    label: string;
    value: string;
    tone?: Tone;
    /** 进场时刻（场景内相对秒数），来自口播说到该指标的字幕起点 */
    appearAt?: number;
  }>;
};

type CompareScene = {
  kind: "compare";
  start: number;
  eyebrow: string;
  heading: string;
  choices: Array<{
    code: string;
    title: string;
    subtitle: string;
    tone?: Tone;
    /** 进场时刻（场景内相对秒数），来自口播说到该选项的字幕起点 */
    appearAt?: number;
  }>;
};

type OutroScene = {
  kind: "outro";
  start: number;
  eyebrow: string;
  title: string;
  subtitle: string;
};

// === 新增：article-image 场景 =============================

type ArticleImageScene = {
  kind: "article-image";
  start: number;
  eyebrow: string;
  /** 公众号原文图，相对 staticFile() 路径 */
  imageSrc: string;
  /** 图片宽/高，由 PIL 预读，用于决定 max-width 还是 max-height 优先 */
  imageAspect: number;
  /** contain=完整显示（信息图/表格默认）；cover=裁切充满画面（氛围图） */
  fit?: "contain" | "cover";
  title: RichTextPart[];
  /** 解读短句（≤ 14 字） */
  caption?: string;
  /** 图源标注，例如 "图源：公众号 / 性能对比章节" */
  source?: string;
  appearAt?: number;
  titleAppearAt?: number;
  captionAppearAt?: number;
};

// === 新增：video 场景（动态视频素材主舞台） ================

type VideoScene = {
  kind: "video";
  start: number;
  /** 本地视频素材，相对 staticFile() 路径 */
  videoSrc: string;
  eyebrow: string;
  title: RichTextPart[];
  /** 解读短句（≤ 14 字） */
  caption?: string;
  /** 素材来源标注 */
  source?: string;
  appearAt?: number;
  titleAppearAt?: number;
  captionAppearAt?: number;
};

export type ArticleScene =
  | CoverScene
  | ListScene
  | StatScene
  | CompareScene
  | OutroScene
  | ArticleImageScene
  | VideoScene;

// === Props ================================================

export type ArticleVideoProps = {
  title: string;
  fps: number;
  durationSeconds: number;
  voiceAudio?: string;
  chapters: Chapter[];
  scenes: ArticleScene[];
  captions: Caption[];
  sfxCues?: SfxCue[];
};

// === 工具函数 ============================================

const enterStyle = (
  frame: number,
  fps: number,
  delaySeconds: number,
  durationSeconds: number,
  y: number,
): CSSProperties => {
  const p = progress(frame, delaySeconds * fps, durationSeconds * fps);
  return {
    opacity: p,
    transform: `translateY(${(1 - p) * y}px)`,
  };
};

// PPT 式强调入场：从右滑入 + 缩放 + 淡入（用于 list 行 / compare 选项）
const enterPopStyle = (
  frame: number,
  fps: number,
  delaySeconds: number,
  durationSeconds: number,
  x: number,
  scaleFrom: number,
): CSSProperties => {
  const p = progress(frame, delaySeconds * fps, durationSeconds * fps);
  return {
    opacity: p,
    transform: `translateX(${(1 - p) * x}px) scale(${1 - (1 - p) * (1 - scaleFrom)})`,
    transformOrigin: "left center",
  };
};

// 数字弹出：缩放 + 淡入（用于 stat 大数字）
const enterPopCenterStyle = (
  frame: number,
  fps: number,
  delaySeconds: number,
  durationSeconds: number,
  scaleFrom: number,
): CSSProperties => {
  const p = progress(frame, delaySeconds * fps, durationSeconds * fps);
  return {
    opacity: p,
    transform: `scale(${1 - (1 - p) * (1 - scaleFrom)})`,
    transformOrigin: "center center",
  };
};

const toneColor = (tone?: Tone) => {
  if (tone === "accent") return colors.accent;
  if (tone === "white") return colors.ink;
  if (tone === "muted") return colors.muted;
  return colors.ink;
};

const RichText = ({
  parts,
  strong = false,
  preserveLineBreaks = false,
  defaultColor = colors.ink,
}: {
  parts: RichTextPart[];
  strong?: boolean;
  preserveLineBreaks?: boolean;
  defaultColor?: string;
}) => (
  <>
    {parts.map((part, index) => (
      <span
        key={`${part.text}-${index}`}
        style={{
          color: part.tone ? toneColor(part.tone) : defaultColor,
          fontWeight: part.tone || strong ? 700 : undefined,
          whiteSpace: preserveLineBreaks ? "pre-line" : undefined,
        }}
      >
        {part.text}
      </span>
    ))}
  </>
);

const Eyebrow = ({children, style}: {children: ReactNode; style?: CSSProperties}) => (
  <div style={{...eyebrowStyle, ...style}}>
    <span style={eyebrowRuleStyle} />
    <span>{children}</span>
  </div>
);

const scaleXStyle = (
  frame: number,
  fps: number,
  delaySeconds: number,
  durationSeconds: number,
): CSSProperties => ({
  transform: `scaleX(${progress(frame, delaySeconds * fps, durationSeconds * fps)})`,
  transformOrigin: "left center",
});

const scaleYStyle = (
  frame: number,
  fps: number,
  delaySeconds: number,
  durationSeconds: number,
): CSSProperties => ({
  transform: `scaleY(${progress(frame, delaySeconds * fps, durationSeconds * fps)})`,
  transformOrigin: "center center",
});

// === Cover 场景 =========================================

const CoverSceneView = ({scene}: {scene: CoverScene}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const hasBg = !!scene.background;
  // 有满屏背景时标题不做进场动画：第 0 帧即完整封面（用户要求"首帧=封面"）
  return (
    <AbsoluteFill>
      {hasBg ? (
        <>
          <div style={coverBackgroundStyle}>
            {scene.background!.type === "video" ? (
              <Video
                src={staticFile(scene.background!.src)}
                loop
                muted
                startFrom={scene.background!.startFrom ?? 0}
                style={coverMediaStyle}
              />
            ) : (
              <Img src={staticFile(scene.background!.src)} style={coverMediaStyle} />
            )}
          </div>
          {/* 暗色渐变遮罩：保证深/浅背景下标题都可读 */}
          <div style={coverOverlayStyle} />
        </>
      ) : null}
      <div
        style={{
          ...sceneContentStyle,
          justifyContent: "center",
          alignItems: "center",
          textAlign: "center",
          position: "relative",
          zIndex: 1,
        }}
      >
        <Eyebrow
          style={
            hasBg
              ? {color: "rgba(255,255,255,0.92)"}
              : enterStyle(frame, fps, 0.14, 0.42, 18)
          }
        >
          {scene.eyebrow}
        </Eyebrow>
        <h1
          style={
            hasBg
              ? {
                  ...coverTitleStyle,
                  color: "#ffffff",
                  textShadow: "0 4px 30px rgba(0,0,0,0.45)",
                }
              : {...coverTitleStyle, ...enterStyle(frame, fps, 0.25, 0.56, 42)}
          }
        >
          {scene.titleLines.map((line, index) => (
            <span key={index} style={{display: "block"}}>
              <RichText parts={line} strong defaultColor={hasBg ? "#ffffff" : undefined} />
            </span>
          ))}
        </h1>
        <div
          style={
            hasBg
              ? {...subtitleStyle, color: "rgba(255,255,255,0.88)"}
              : {...subtitleStyle, ...enterStyle(frame, fps, 0.52, 0.44, 24)}
          }
        >
          {scene.subtitle}
        </div>
      </div>
    </AbsoluteFill>
  );
};

// === List 场景 ==========================================

const ListSceneView = ({scene}: {scene: ListScene}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  return (
    <div style={{...sceneContentStyle, ...splitLayoutStyle}}>
      <div style={sectionTitleRailStyle}>
        <span style={{...smallRuleStyle, ...scaleXStyle(frame, fps, 0.1, 0.28)}} />
        <div style={{...sectionLabelStyle, ...enterStyle(frame, fps, 0.16, 0.34, 16)}}>
          {scene.eyebrow}
        </div>
        <div style={{...sectionHeadingStyle, fontSize: fitFontSize(scene.heading, 400, 100, 28, 96), ...enterStyle(frame, fps, 0.24, 0.44, 28)}}>
          {scene.heading}
        </div>
      </div>
      <div style={rowsStyle}>
        {scene.items.map((item, index) => (
          <div
            key={item.index}
            style={{
              ...rowStyle,
              ...enterPopStyle(frame, fps, item.appearAt ?? 0.28 + index * 0.1, 0.4, 36, 0.96),
            }}
          >
            <span style={rowIndexStyle}>{item.index}</span>
            <span style={{...rowLabelStyle, fontSize: fitFontSize(item.label, 250, 100, 18, 27)}}>{item.label}</span>
            <span style={{...rowValueStyle, fontSize: fitFontSize(item.value, 734, 100, 24, 56), color: toneColor(item.tone)}}>{item.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

// === Stat 场景 ==========================================

const StatSceneView = ({scene}: {scene: StatScene}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  // 大数字与单位整体按空间实测：数字 maxWidth 预留单位空间，unit 防拆行
  const unitFont = fitFontSize(scene.unit, 200, 100, 18, 56);
  const numFont = fitFontSize(scene.number, 660, 100, 100, 360);
  const detailTitleFont = fitFontSize(scene.title.map((p) => p.text).join(""), 600, 100, 24, 46);
  return (
    <div style={{...sceneContentStyle, ...statLayoutStyle}}>
      <div style={{...bigStatStyle, maxWidth: "62%"}}>
        <div style={{...sectionLabelStyle, ...enterStyle(frame, fps, 0.08, 0.34, 0)}}>
          {scene.eyebrow}
        </div>
        <div style={{...statNumberWrapStyle, ...enterPopCenterStyle(frame, fps, 0.16, 0.55, 0.5)}}>
          <span style={{...statNumberStyle, fontSize: numFont}}>{scene.number}</span>
          <span style={{...statUnitStyle, fontSize: unitFont}}>{scene.unit}</span>
        </div>
        <span style={{...statRuleStyle, ...scaleXStyle(frame, fps, 0.48, 0.32)}} />
      </div>
      <div style={{...statDetailStyle, minWidth: 0, ...enterStyle(frame, fps, 0.28, 0.48, 0)}}>
        <div style={{...detailTitleStyle, fontSize: detailTitleFont}}>
          <RichText parts={scene.title} strong preserveLineBreaks />
        </div>
        <div style={miniStatsStyle}>
          {scene.metrics.map((metric, index) => (
            <div
              key={metric.label}
              style={{
                ...miniRowStyle,
                ...enterStyle(
                  frame,
                  fps,
                  metric.appearAt ?? 0.52 + index * 0.08,
                  0.28,
                  18,
                ),
              }}
            >
              <span>{metric.label}</span>
              <span style={{color: toneColor(metric.tone), fontFamily: fonts.mono}}>
                {metric.value}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// === Compare 场景 =======================================

const CompareSceneView = ({scene}: {scene: CompareScene}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  return (
    <div style={{...sceneContentStyle, justifyContent: "flex-start"}}>
      <span style={{...smallRuleStyle, ...scaleXStyle(frame, fps, 0.1, 0.28)}} />
      <div style={{...sectionLabelStyle, ...enterStyle(frame, fps, 0.16, 0.34, 16)}}>
        {scene.eyebrow}
      </div>
      <div
        style={{
          ...sectionHeadingStyle,
          fontSize: 88,
          ...enterStyle(frame, fps, 0.24, 0.44, 28),
        }}
      >
        {scene.heading}
      </div>
      <div style={compareGridStyle}>
        {scene.choices.map((choice, index) => (
          <div
            key={choice.code}
            style={{
              ...choiceStyle(index),
              ...enterPopStyle(
                frame,
                fps,
                choice.appearAt ?? 0.38 + index * 0.12,
                0.46,
                40,
                0.94,
              ),
            }}
          >
            <span style={{...choiceCodeStyle, color: toneColor(choice.tone)}}>
              {choice.code}
            </span>
            <div style={choiceTitleStyle}>{choice.title}</div>
            <div style={choiceSubtitleStyle}>{choice.subtitle}</div>
          </div>
        ))}
        <div style={{...dividerStyle, ...scaleYStyle(frame, fps, 0.34, 0.36)}} />
      </div>
    </div>
  );
};

// === Outro 场景 =========================================

const OutroSceneView = ({scene}: {scene: OutroScene}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  return (
    <div
      style={{
        ...sceneContentStyle,
        alignItems: "center",
        justifyContent: "center",
        textAlign: "center",
      }}
    >
      <span style={{...outroRuleStyle, ...scaleXStyle(frame, fps, 0.08, 0.3)}} />
      <div style={{...sectionLabelStyle, ...enterStyle(frame, fps, 0.16, 0.34, 16)}}>
        {scene.eyebrow}
      </div>
      <div style={{...outroTitleStyle, ...enterStyle(frame, fps, 0.24, 0.5, 34)}}>
        {scene.title}
      </div>
      <div style={{...outroSubtitleStyle, ...enterStyle(frame, fps, 0.48, 0.4, 22)}}>
        {scene.subtitle}
      </div>
    </div>
  );
};

// === article-image 场景（核心新增） ======================

const ArticleImageSceneView = ({scene}: {scene: ArticleImageScene}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  // 铁律：object-fit: contain，永不 cover（信息图/表格）
  // cover 模式（氛围图）则裁切充满画面
  // 宽高比决定 max-width 还是 max-height 优先
  // 注意：maxHeight 用 calc(100% - X) 而不是 78vh，避免在紧凑布局里溢出 frame
  // 标题(~80) + caption(~50) + eyebrow(~50) + 间距(36) ≈ 216，需要从高度里让出
  const isWideImage = scene.imageAspect >= 1.78;
  const isCover = scene.fit === "cover";
  const imageSizeStyle: CSSProperties = isCover
    ? {width: "100%", height: "100%", objectFit: "cover"}
    : isWideImage
      ? {maxWidth: "88%", maxHeight: "calc(100% - 16px)", width: "auto", height: "auto"}
      : {maxHeight: "calc(100% - 16px)", maxWidth: "88%", width: "auto", height: "auto"};

  // 持续动效：图源标签 6s 呼吸一次
  const sourceGlow = 0.6 + Math.sin((frame / fps) * (Math.PI / 3)) * 0.4;

  // 氛围图 cover：全屏铺满 + 文字反白叠加（可读性保障）
  if (isCover) {
    return (
      <AbsoluteFill>
        <Img src={staticFile(scene.imageSrc)} style={fullScreenMediaStyle} />
        <div style={fullScreenOverlayStyle} />
        <AbsoluteFill style={{zIndex: 1}}>
          <div style={fullScreenTextLayoutStyle}>
            <Eyebrow style={fullScreenEyebrowStyle}>{scene.eyebrow}</Eyebrow>
            <h2 style={{...fullScreenTitleStyle, fontSize: fitFontSize(scene.title.map((p) => p.text).join(""), 1500, 100, 36, 84)}}>
              <RichText parts={scene.title} strong defaultColor="#ffffff" />
            </h2>
            {scene.caption ? (
              <div style={fullScreenCaptionStyle}>{scene.caption}</div>
            ) : null}
          </div>
        </AbsoluteFill>
        {scene.source ? (
          <div style={{...fullScreenSourceBadgeStyle, opacity: sourceGlow}}>
            {scene.source}
          </div>
        ) : null}
      </AbsoluteFill>
    );
  }

  return (
    <div style={{...sceneContentStyle, ...articleImageLayoutStyle}}>
      <div style={articleImageHeaderStyle}>
        <Eyebrow style={enterStyle(frame, fps, scene.appearAt ?? 0.08, 0.34, 12)}>
          {scene.eyebrow}
        </Eyebrow>
        <h2
          style={{
            ...articleImageTitleStyle,
            ...enterStyle(frame, fps, scene.titleAppearAt ?? 0.24, 0.5, 24),
          }}
        >
          <RichText parts={scene.title} strong />
        </h2>
      </div>

      <div
        style={{
          ...articleImageFrameStyle,
          ...enterStyle(frame, fps, scene.appearAt ?? 0.16, 0.6, 16),
        }}
      >
        <Img
          src={staticFile(scene.imageSrc)}
          style={{...articleImageImgStyle, ...imageSizeStyle, objectFit: isCover ? "cover" : "contain"}}
        />
        {scene.source ? (
          <div style={{...imageSourceBadgeStyle, opacity: sourceGlow}}>
            {scene.source}
          </div>
        ) : null}
      </div>

      {scene.caption ? (
        <div
          style={{
            ...articleImageCaptionStyle,
            ...enterStyle(frame, fps, scene.captionAppearAt ?? 0.5, 0.4, 14),
          }}
        >
          {scene.caption}
        </div>
      ) : null}
    </div>
  );
};

// === 新增：video 场景视图（素材全屏 cover 铺满 + 文字可读叠加） =============

const VideoSceneView = ({scene}: {scene: VideoScene}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  // 持续动效：来源标签 6s 呼吸一次
  const sourceGlow = 0.6 + Math.sin((frame / fps) * (Math.PI / 3)) * 0.4;

  return (
    <AbsoluteFill>
      {/* 素材全屏 cover 铺满（无留白） */}
      <Video
        src={staticFile(scene.videoSrc)}
        loop
        muted
        style={fullScreenMediaStyle}
      />
      {/* 上下渐变遮罩：保证叠加文字可读 */}
      <div style={fullScreenOverlayStyle} />
      {/* 文字层 */}
      <AbsoluteFill style={{zIndex: 1}}>
        <div style={fullScreenTextLayoutStyle}>
          <Eyebrow style={fullScreenEyebrowStyle}>{scene.eyebrow}</Eyebrow>
          <h2 style={{...fullScreenTitleStyle, fontSize: fitFontSize(scene.title.map((p) => p.text).join(""), 1500, 100, 36, 84)}}>
            <RichText parts={scene.title} strong defaultColor="#ffffff" />
          </h2>
          {scene.caption ? (
            <div style={fullScreenCaptionStyle}>{scene.caption}</div>
          ) : null}
        </div>
      </AbsoluteFill>
      {scene.source ? (
        <div style={{...fullScreenSourceBadgeStyle, opacity: sourceGlow}}>
          {scene.source}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

// === SceneRouter ========================================

export const SceneRenderer = ({
  scene,
  durationInFrames,
  isLast,
}: {
  scene: ArticleScene;
  durationInFrames: number;
  isLast: boolean;
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  // 首帧场景（start=0）跳过淡入动画：保证视频第 0 帧就是完整封面画面（否则 opacity=0 露出网格背景）
  const enter = scene.start === 0 ? 1 : progress(frame, 0, 0.42 * fps);
  const exit = isLast ? 0 : progress(frame, durationInFrames - 0.42 * fps, 0.42 * fps);
  const opacity = clamp(enter - exit, 0, 1);

  return (
    <AbsoluteFill style={{...sceneShellStyle, opacity}}>
      {scene.kind === "cover" ? <CoverSceneView scene={scene} /> : null}
      {scene.kind === "list" ? <ListSceneView scene={scene} /> : null}
      {scene.kind === "stat" ? <StatSceneView scene={scene} /> : null}
      {scene.kind === "compare" ? <CompareSceneView scene={scene} /> : null}
      {scene.kind === "outro" ? <OutroSceneView scene={scene} /> : null}
      {scene.kind === "article-image" ? <ArticleImageSceneView scene={scene} /> : null}
      {scene.kind === "video" ? <VideoSceneView scene={scene} /> : null}
    </AbsoluteFill>
  );
};

// === Caption / TopBar（暴露给 ArticleVideo 使用） =======

export const CaptionPill = ({caption}: {caption: Caption}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const start = frameFromSeconds(caption.start, fps);
  const end = frameFromSeconds(caption.end, fps);

  if (frame < start - 1 || frame > end) {
    return null;
  }

  const enter = progress(frame, start, 0.16 * fps);
  const exit = progress(frame, Math.max(start, end - 0.12 * fps), 0.12 * fps);
  const visible = clamp(enter - exit, 0, 1);

  return (
    <div
      style={{
        ...captionStyle,
        opacity: visible,
        transform: `translate(-50%, ${(1 - visible) * 18}px) scale(${0.98 + visible * 0.02})`,
      }}
    >
      <RichText parts={caption.parts} defaultColor={colors.ink} />
    </div>
  );
};

export const CaptionLayer = ({captions}: {captions: Caption[]}) => {
  return (
    <AbsoluteFill style={captionLayerStyle}>
      {captions.map((caption, index) => (
        <CaptionPill key={`${caption.start}-${index}`} caption={caption} />
      ))}
    </AbsoluteFill>
  );
};

export const TopBar = ({
  chapters,
  durationSeconds,
}: {
  chapters?: Chapter[];
  durationSeconds: number;
}) => {
  if (!chapters || chapters.length === 0) return null;
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const time = frame / fps;
  const progressWidth = 16 + progress(frame, 0, durationSeconds * fps) * 84;

  return (
    <div style={topbarStyle}>
      <div style={{...navFillStyle, width: `${progressWidth}%`}} />
      <div style={chapterRowStyle}>
        {chapters.map((chapter, index) => {
          const reached = time >= chapter.start;
          return (
            <span key={chapter.label} style={chapterGroupStyle}>
              <span
                style={{
                  ...chapterLabelStyle,
                  color: reached ? colors.ink : colors.topbarMuted,
                  fontWeight: reached ? 600 : 500,
                }}
              >
                {chapter.label}
              </span>
              {index < chapters.length - 1 ? <span style={chapterSepStyle}>|</span> : null}
            </span>
          );
        })}
      </div>
    </div>
  );
};

// 字号按空间实测自适应（用户 2026-08-11 要求"根据空间大小确定字号"）：
// 用 measureText 精确测量文本宽度，反推能放入指定空间的最大字号，杜绝拆行。
// 实测 Noto Sans SC 全角字符（含 · 等标点）实际宽度 ≈ 1.22em，估算不可靠。
import {measureText} from "@remotion/layout-utils";

const FONT_SANS = '"Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif';

const fitFontSize = (
  text: string,
  maxWidth: number,
  baseSize = 100,
  min = 20,
  max = 200,
): number => {
  const m = measureText({text, fontFamily: FONT_SANS, fontSize: baseSize, fontWeight: 700});
  const fs = Math.floor((baseSize * maxWidth) / m.width);
  return Math.max(min, Math.min(max, fs));
};

// === 样式 ================================================

const sceneShellStyle: CSSProperties = {
  padding: `${layout.safeTop}px ${layout.safeX}px ${layout.safeBottom}px`,
};

const sceneContentStyle: CSSProperties = {
  width: "100%",
  height: "100%",
  display: "flex",
  flexDirection: "column",
};

const eyebrowStyle: CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 20,
  marginBottom: 24,
  color: colors.accent,
  fontFamily: fonts.mono,
  fontSize: 22,
  fontWeight: 600,
  letterSpacing: 0,
  textTransform: "uppercase",
};

const eyebrowRuleStyle: CSSProperties = {
  width: 52,
  height: 2,
  backgroundColor: colors.accent,
  flex: "none",
};

// Cover
const coverTitleStyle: CSSProperties = {
  maxWidth: 1400,
  margin: 0,
  color: colors.ink,
  fontSize: 112,
  fontWeight: 800,
  lineHeight: 1.14,
  letterSpacing: 0,
};
const subtitleStyle: CSSProperties = {
  marginTop: 46,
  color: colors.muted,
  fontSize: 38,
  fontWeight: 300,
  letterSpacing: 0,
};

// 满屏封面背景
const coverBackgroundStyle: CSSProperties = {
  position: "absolute",
  top: 0,
  left: 0,
  right: 0,
  bottom: 0,
  overflow: "hidden",
  backgroundColor: "#0d0d12",
};
const coverMediaStyle: CSSProperties = {
  width: "100%",
  height: "100%",
  objectFit: "cover",
};
const coverOverlayStyle: CSSProperties = {
  position: "absolute",
  top: 0,
  left: 0,
  right: 0,
  bottom: 0,
  background:
    "linear-gradient(180deg, rgba(0,0,0,0.32) 0%, rgba(0,0,0,0.10) 45%, rgba(0,0,0,0.60) 100%)",
};

// 素材全屏 cover（video/氛围图满屏铺满，无留白）
const fullScreenMediaStyle: CSSProperties = {
  position: "absolute",
  top: 0,
  left: 0,
  right: 0,
  bottom: 0,
  width: "100%",
  height: "100%",
  objectFit: "cover",
  backgroundColor: "#0d0d12",
};
// 上下渐变遮罩：保证叠加文字在任何画面亮度下可读
const fullScreenOverlayStyle: CSSProperties = {
  position: "absolute",
  top: 0,
  left: 0,
  right: 0,
  bottom: 0,
  background:
    "linear-gradient(180deg, rgba(0,0,0,0.42) 0%, rgba(0,0,0,0.06) 38%, rgba(0,0,0,0.06) 62%, rgba(0,0,0,0.52) 100%)",
};
// 文字布局：顶部 eyebrow + 中部标题 + 底部 caption
const fullScreenTextLayoutStyle: CSSProperties = {
  position: "absolute",
  top: 0,
  left: 0,
  right: 0,
  bottom: 0,
  display: "flex",
  flexDirection: "column",
  alignItems: "center",
  justifyContent: "center",
  textAlign: "center",
  padding: "60px 120px",
};
const fullScreenEyebrowStyle: CSSProperties = {
  marginBottom: 26,
  color: "rgba(255,255,255,0.92)",
  fontFamily: fonts.mono,
  fontSize: 24,
  fontWeight: 600,
  letterSpacing: 2,
  textTransform: "uppercase",
  textShadow: "0 2px 16px rgba(0,0,0,0.6)",
};
const fullScreenTitleStyle: CSSProperties = {
  maxWidth: 1500,
  margin: 0,
  color: "#ffffff",
  fontSize: 84,
  fontWeight: 900,
  lineHeight: 1.2,
  letterSpacing: 0,
  textShadow: "0 4px 28px rgba(0,0,0,0.55)",
};
const fullScreenCaptionStyle: CSSProperties = {
  position: "absolute",
  bottom: 120,
  color: "rgba(255,255,255,0.95)",
  fontSize: 34,
  fontWeight: 500,
  letterSpacing: 0,
  textShadow: "0 3px 18px rgba(0,0,0,0.6)",
};
const fullScreenSourceBadgeStyle: CSSProperties = {
  position: "absolute",
  right: 28,
  bottom: 96,
  zIndex: 2,
  padding: "5px 12px",
  borderRadius: 100,
  backgroundColor: "rgba(0,0,0,0.45)",
  color: "rgba(255,255,255,0.85)",
  fontFamily: fonts.mono,
  fontSize: 13,
  letterSpacing: 0.4,
};

// List
const splitLayoutStyle: CSSProperties = {flexDirection: "row", alignItems: "center", gap: 100};
const sectionTitleRailStyle: CSSProperties = {width: 420, flex: "none"};
const smallRuleStyle: CSSProperties = {
  width: 48,
  height: 2,
  backgroundColor: colors.accent,
  display: "block",
  marginBottom: 30,
};
const sectionLabelStyle: CSSProperties = {
  color: colors.accent,
  fontFamily: fonts.mono,
  fontSize: 22,
  fontWeight: 600,
  letterSpacing: 0,
  textTransform: "uppercase",
  marginBottom: 20,
};
const sectionHeadingStyle: CSSProperties = {
  color: colors.ink,
  fontSize: 96,
  fontWeight: 800,
  lineHeight: 1.08,
  letterSpacing: 0,
};
const rowsStyle: CSSProperties = {flex: 1, display: "flex", flexDirection: "column"};
const rowStyle: CSSProperties = {
  display: "flex",
  alignItems: "baseline",
  gap: 46,
  padding: "42px 0",
  borderTop: `1px solid ${colors.line}`,
};
const rowIndexStyle: CSSProperties = {
  width: 74,
  flex: "none",
  color: colors.weak,
  fontFamily: fonts.mono,
  fontSize: 40,
  fontWeight: 500,
};
const rowLabelStyle: CSSProperties = {
  width: 260,
  flex: "none",
  color: colors.muted,
  fontSize: 27,
  fontWeight: 400,
  letterSpacing: 0,
};
const rowValueStyle: CSSProperties = {
  color: colors.ink,
  fontSize: 56,
  fontWeight: 600,
  lineHeight: 1.2,
};

// Stat
const statLayoutStyle: CSSProperties = {flexDirection: "row", alignItems: "center", gap: 110};
const bigStatStyle: CSSProperties = {flex: "none"};
const statNumberWrapStyle: CSSProperties = {display: "flex", alignItems: "flex-start", whiteSpace: "nowrap"};
const statNumberStyle: CSSProperties = {
  color: colors.ink,
  fontFamily: fonts.mono,
  fontSize: 420,
  fontWeight: 700,
  lineHeight: 0.82,
  letterSpacing: 0,
};
const statUnitStyle: CSSProperties = {
  marginTop: 40,
  color: colors.muted,
  fontFamily: fonts.mono,
  fontSize: 56,
  fontWeight: 500,
};
const statRuleStyle: CSSProperties = {
  display: "block",
  width: 380,
  height: 3,
  marginTop: 6,
  backgroundColor: colors.accent,
};
const statDetailStyle: CSSProperties = {
  flex: 1,
  borderLeft: `1px solid ${colors.line}`,
  padding: "18px 0 18px 88px",
};
const detailTitleStyle: CSSProperties = {
  color: colors.ink,
  fontSize: 46,
  fontWeight: 700,
  lineHeight: 1.28,
};
const miniStatsStyle: CSSProperties = {maxWidth: 540, marginTop: 48};
const miniRowStyle: CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "baseline",
  padding: "24px 0",
  borderTop: `1px solid ${colors.line}`,
  color: colors.muted,
  fontSize: 32,
};

// Compare
const compareGridStyle: CSSProperties = {
  flex: 1,
  display: "grid",
  gridTemplateColumns: "1fr 1px 1fr",
  alignItems: "stretch",
  marginTop: 60,
};
const choiceStyle = (index: number): CSSProperties => ({
  gridColumn: index === 0 ? 1 : 3,
  display: "flex",
  flexDirection: "column",
  justifyContent: "center",
  padding: index === 0 ? "12px 90px 12px 0" : "12px 0 12px 90px",
});
const choiceCodeStyle: CSSProperties = {
  color: colors.weak,
  fontFamily: fonts.mono,
  fontSize: 40,
  fontWeight: 600,
};
const choiceTitleStyle: CSSProperties = {
  margin: "16px 0 30px",
  color: colors.ink,
  fontSize: 84,
  fontWeight: 800,
  letterSpacing: 0,
};
const choiceSubtitleStyle: CSSProperties = {
  color: colors.muted,
  fontSize: 40,
  fontWeight: 300,
  letterSpacing: 0,
};
const dividerStyle: CSSProperties = {
  gridColumn: 2,
  width: 1,
  backgroundColor: colors.lineStrong,
};

// Outro
const outroRuleStyle: CSSProperties = {
  width: 70,
  height: 2,
  backgroundColor: colors.accent,
  marginBottom: 38,
};
const outroTitleStyle: CSSProperties = {
  color: colors.ink,
  fontSize: 172,
  fontWeight: 800,
  lineHeight: 1,
  letterSpacing: 0,
};
const outroSubtitleStyle: CSSProperties = {
  marginTop: 42,
  color: colors.muted,
  fontSize: 40,
  fontWeight: 300,
  letterSpacing: 0,
};

// Article-image（核心新增）
const articleImageLayoutStyle: CSSProperties = {
  alignItems: "center",
  justifyContent: "flex-start",
  textAlign: "center",
};
const articleImageHeaderStyle: CSSProperties = {
  width: "100%",
  display: "flex",
  flexDirection: "column",
  alignItems: "center",
  marginBottom: 18,
};
const articleImageTitleStyle: CSSProperties = {
  width: "100%",
  maxWidth: 1500,
  margin: 0,
  color: colors.ink,
  fontSize: 64,
  fontWeight: 800,
  lineHeight: 1.2,
  letterSpacing: 0,
};
const articleImageFrameStyle: CSSProperties = {
  position: "relative",
  flex: 1,
  width: "100%",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  minHeight: 0,
  overflow: "hidden",
};
const articleImageImgStyle: CSSProperties = {
  objectFit: "contain",
  borderRadius: 12,
  boxShadow:
    "0 30px 90px rgba(28,38,54,0.18), 0 4px 16px rgba(28,38,54,0.08)",
  backgroundColor: colors.white,
  display: "block",
};
const imageSourceBadgeStyle: CSSProperties = {
  position: "absolute",
  right: 12,
  bottom: 12,
  padding: "6px 14px",
  borderRadius: 100,
  backgroundColor: "rgba(28,38,54,0.78)",
  color: colors.white,
  fontFamily: fonts.mono,
  fontSize: 14,
  fontWeight: 500,
  letterSpacing: 0.4,
};
const articleImageCaptionStyle: CSSProperties = {
  marginTop: 20,
  color: colors.muted,
  fontSize: 26,
  fontWeight: 400,
  letterSpacing: 0,
  maxWidth: 1200,
};

// Caption
const captionLayerStyle: CSSProperties = {zIndex: 100, pointerEvents: "none"};
const captionStyle: CSSProperties = {
  position: "absolute",
  left: "50%",
  bottom: layout.captionBottom,
  maxWidth: 1300,
  color: colors.ink,
  fontFamily: fonts.serif,
  fontSize: 32,
  fontWeight: 500,
  lineHeight: 1.3,
  textAlign: "center",
  letterSpacing: 0,
  // 半透明背景：保证任何画面颜色下字幕都可读（白色半透明 + 圆角 + 内边距）
  backgroundColor: "rgba(255,255,255,0.82)",
  borderRadius: 10,
  padding: "8px 18px",
  boxShadow: "0 2px 12px rgba(28,38,54,0.10)",
};

// TopBar
const topbarStyle: CSSProperties = {
  position: "absolute",
  top: 0,
  left: 0,
  right: 0,
  height: layout.topbarHeight,
  zIndex: 120,
  backgroundColor: colors.topbar,
  overflow: "hidden",
};
const navFillStyle: CSSProperties = {
  position: "absolute",
  top: 7,
  bottom: 7,
  left: 0,
  backgroundColor: colors.white,
  borderRadius: "0 14px 14px 0",
};
const chapterRowStyle: CSSProperties = {
  position: "absolute",
  inset: 0,
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  padding: "0 34px",
  fontSize: 22,
  lineHeight: 1,
  whiteSpace: "nowrap",
  zIndex: 1,
};
const chapterGroupStyle: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  gap: 28,
};
const chapterLabelStyle: CSSProperties = {
  fontWeight: 500,
  letterSpacing: 0,
};
const chapterSepStyle: CSSProperties = {
  color: colors.topbarSeparator,
};
