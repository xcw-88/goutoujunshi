import { spawnSync } from "node:child_process";
import { resolve } from "node:path";

const nextCli = resolve(process.cwd(), "node_modules", "next", "dist", "bin", "next");
const result = spawnSync(process.execPath, [nextCli, "build"], {
  cwd: process.cwd(),
  env: {
    ...process.env,
    CLOUDFLARE_BUILD: "1",
    NEXT_PUBLIC_API_BASE: "",
  },
  stdio: "inherit",
});

process.exit(result.status ?? 1);
