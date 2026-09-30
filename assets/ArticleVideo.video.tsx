import {useEffect, useState, type CSSProperties} from "react";
import {
  AbsoluteFill,
  Audio,
  Sequence,
  prefetch,
  staticFile,
  useCurrentFrame,
  useDelayRender,
  useVideoConfig,
} from "remotion";
import {colors, fonts} from "./theme";
import {frameFromSeconds, progress} from "./shared";
import {PremiumGridBackground} from "./background";
import {PreloadContext} from "./PreloadContext";
import {
  type ArticleScene,
  type ArticleVideoProps,
  CaptionLayer,
  SceneRenderer,
  TopBar,
} from "./sceneTypes";

// 转发导出，外部 import 仍走 "./ArticleVideo"
export type {ArticleScene, ArticleVideoProps};

const collectImageAssets = (scenes: ArticleScene[]) => {
  const set = new Set<string>();
  scenes.forEach((scene) => {
    if (
      (scene.kind === "cover" ||
        scene.kind === "list" ||
        scene.kind === "outro") &&
      scene.background?.src
    ) {
      set.add(scene.background.src);
    }
    if (scene.kind === "article-image") {
      set.add(scene.imageSrc);
    }
    if (scene.kind === "video") {
      set.add(scene.videoSrc);
    }
  });
  return Array.from(set);
};

const ImagePreloader: React.FC<{assets: string[]; children: React.ReactNode}> = ({
  assets,
  children,
}) => {
  const [map, setMap] = useState<Record<string, string> | null>(null);
  const {delayRender, continueRender} = useDelayRender();

  useEffect(() => {
    const handle = delayRender("Preloading static images");
    Promise.all(
      assets.map(async (src) => {
        const p = prefetch(src, {method: "base64"});
        const url = await p.waitUntilDone();
        return {src, url};
      }),
    )
      .then((results) => {
        const next: Record<string, string> = {};
        results.forEach((r) => {
          next[r.src] = r.url;
        });
        setMap(next);
        continueRender(handle);
      })
      .catch((err) => {
        console.error("Failed to preload images:", err);
        // 即使失败也放行，让子组件回退到原始 staticFile 路径
        setMap({});
        continueRender(handle);
      });
  }, [assets, delayRender, continueRender]);

  if (!map) {
    return null;
  }

  return <PreloadContext.Provider value={map}>{children}</PreloadContext.Provider>;
};

export const ArticleVideo = ({
  durationSeconds,
  voiceAudio,
  chapters,
  scenes,
  captions,
  sfxCues = [],
}: ArticleVideoProps) => {
  const {fps} = useVideoConfig();
  const transitionFrames = Math.round(0.42 * fps);
  const totalFrames = frameFromSeconds(durationSeconds, fps);

  return (
    <ImagePreloader assets={collectImageAssets(scenes)}>
      <AbsoluteFill style={stageStyle}>
        <PremiumGridBackground />
        {voiceAudio ? <Audio src={staticFile(voiceAudio)} volume={1} /> : null}
        {sfxCues.map((cue) => (
          <Sequence
            key={cue.id}
            from={frameFromSeconds(cue.start, fps)}
            durationInFrames={Math.max(1, frameFromSeconds(cue.duration, fps))}
            premountFor={fps}
          >
            <Audio src={staticFile(cue.file)} volume={cue.volume} />
          </Sequence>
        ))}
        {scenes.map((scene, index) => {
          const nextStart = scenes[index + 1]?.start ?? durationSeconds;
          const sceneStart = frameFromSeconds(scene.start, fps);
          const baseDuration = frameFromSeconds(nextStart - scene.start, fps);
          const isLast = index === scenes.length - 1;
          const durationInFrames = Math.max(1, baseDuration + (isLast ? 0 : transitionFrames));
          return (
            <Sequence
              key={`${scene.kind}-${scene.start}`}
              from={sceneStart}
              durationInFrames={durationInFrames}
              premountFor={fps}
            >
              <SceneRenderer
                scene={scene}
                durationInFrames={durationInFrames}
                isLast={isLast}
              />
            </Sequence>
          );
        })}
        <TopBar chapters={chapters} durationSeconds={durationSeconds} />
        <CaptionLayer captions={captions} />
        <BrandMark totalFrames={totalFrames} fps={fps} />
      </AbsoluteFill>
    </ImagePreloader>
  );
};

// === 底部右下角品牌小标（轻量、不抢戏） ==================

const BrandMark = ({totalFrames, fps}: {totalFrames: number; fps: number}) => {
  const frame = useCurrentFrame();
  const enter = progress(frame, totalFrames * 0.7, 0.5 * fps);
  if (enter <= 0) {
    return null;
  }
  return (
    <div style={{...brandMarkStyle, opacity: enter}}>
      <span style={brandRuleStyle} />
      <span>公众号文章视频</span>
    </div>
  );
};

const stageStyle: CSSProperties = {
  backgroundColor: colors.canvas,
  color: colors.ink,
  fontFamily: fonts.sans,
  overflow: "hidden",
};

const brandMarkStyle: CSSProperties = {
  position: "absolute",
  right: 36,
  top: 100,
  zIndex: 80,
  display: "flex",
  alignItems: "center",
  gap: 12,
  color: colors.muted,
  fontFamily: fonts.mono,
  fontSize: 14,
  fontWeight: 500,
  letterSpacing: 1.2,
  textTransform: "uppercase",
};

const brandRuleStyle: CSSProperties = {
  width: 28,
  height: 1,
  backgroundColor: colors.lineStrong,
};
