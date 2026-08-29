/**
 * Serve signed Android packages with installable MIME types.
 * Vite/sirv leaves Content-Type empty for .apk/.aab, which makes Vanadium
 * save a nameless blob instead of offering the GrapheneOS package installer.
 */
import { createReadStream, existsSync, statSync } from "node:fs";
import { basename, extname, join, resolve } from "node:path";

const MIME = {
  ".apk": "application/vnd.android.package-archive",
  ".aab": "application/octet-stream",
  ".txt": "text/plain; charset=utf-8",
};

function isSafeRelease(root, file) {
  const releases = resolve(root, "public", "releases");
  const resolved = resolve(file);
  return resolved === releases || resolved.startsWith(releases + "/");
}

function attach(middlewares, root) {
  middlewares.use((req, res, next) => {
    const raw = (req.url ?? "").split("?", 1)[0] ?? "";
    if (!raw.startsWith("/releases/")) {
      next();
      return;
    }
    const method = (req.method ?? "GET").toUpperCase();
    if (method !== "GET" && method !== "HEAD") {
      next();
      return;
    }
    const name = basename(raw);
    if (name.includes("..") || name.includes("/") || name.includes("\\")) {
      res.statusCode = 400;
      res.end("bad path");
      return;
    }
    const ext = extname(name).toLowerCase();
    const allowed =
      ext === ".apk" || ext === ".aab" || name === "SHA256SUMS" || name === "SHA256SUMS.txt";
    if (!allowed) {
      next();
      return;
    }
    const file = join(root, "public", "releases", name);
    if (!isSafeRelease(root, file) || !existsSync(file)) {
      next();
      return;
    }
    const st = statSync(file);
    const mime = name.startsWith("SHA256SUMS")
      ? "text/plain; charset=utf-8"
      : (MIME[ext] ?? "application/octet-stream");
    res.statusCode = 200;
    res.setHeader("Content-Type", mime);
    res.setHeader("Content-Length", String(st.size));
    res.setHeader("Cache-Control", "no-cache");
    res.setHeader("X-Content-Type-Options", "nosniff");
    res.setHeader("Accept-Ranges", "bytes");
    if (ext === ".apk" || ext === ".aab") {
      res.setHeader("Content-Disposition", `attachment; filename="${name}"`);
    }
    if (method === "HEAD") {
      res.end();
      return;
    }
    createReadStream(file).pipe(res);
  });
}

export function apkMimePlugin(root = process.cwd()) {
  return {
    name: "apk-release-mime",
    configureServer(server) {
      attach(server.middlewares, root);
    },
    configurePreviewServer(server) {
      attach(server.middlewares, root);
    },
  };
}
