import {createContext, useContext} from "react";

/**
 * 资源预加载映射：原始相对路径 -> prefetch 返回的 URL（通常是 base64）。
 * 用于在渲染前把静态图片资源全部预加载到内存，避免 concurrency>1 时
 * 多个浏览器标签同时请求本地文件服务器造成的偶发空白帧。
 */
export const PreloadContext = createContext<Record<string, string>>({});

export const usePreloadedSrc = (src: string) => {
  const map = useContext(PreloadContext);
  return map[src] ?? src;
};
