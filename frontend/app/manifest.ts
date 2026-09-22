import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "狗头军师 · Goutoujunshi",
    short_name: "狗头军师",
    description: "本地、隐私优先的私人关系分析助手",
    start_url: "/",
    display: "standalone",
    background_color: "#f7f4ed",
    theme_color: "#2c302c",
    orientation: "portrait-primary",
    icons: [
      { src: "/icon-192.png", sizes: "192x192", type: "image/png" },
      { src: "/icon-512.png", sizes: "512x512", type: "image/png" },
      { src: "/icon-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}

