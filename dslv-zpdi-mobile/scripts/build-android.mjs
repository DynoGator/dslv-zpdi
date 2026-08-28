#!/usr/bin/env node
/**
 * Build the Pixel WebView SPA into assets, then assemble a signed APK + AAB.
 */
import { spawnSync } from "node:child_process";
import { copyFileSync, mkdirSync, writeFileSync, statSync } from "node:fs";
import { createHash } from "node:crypto";
import { readFileSync, existsSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const env = {
  ...process.env,
  JAVA_HOME: process.env.JAVA_HOME || "/usr/lib/jvm/java-17-openjdk-amd64",
  ANDROID_HOME: "/opt/android-sdk",
  ANDROID_SDK_ROOT: "/opt/android-sdk",
  GRADLE_USER_HOME: resolve(root, ".gradle"),
  PATH: `${resolve(root, "node_modules/.bin")}:/opt/gradle/gradle-8.7/bin:/opt/android-sdk/platform-tools:${process.env.PATH}`,
};

function run(cmd, args, extra = {}) {
  console.log(`$ ${cmd} ${args.join(" ")}`);
  const r = spawnSync(cmd, args, {
    cwd: root,
    env,
    stdio: "inherit",
    ...extra,
  });
  if (r.status !== 0) {
    process.exit(r.status ?? 1);
  }
}

function sha256(file) {
  const buf = readFileSync(file);
  return createHash("sha256").update(buf).digest("hex");
}

const gradleSrc = readFileSync(resolve(root, "native/android/app/build.gradle"), "utf8");
const versionName = gradleSrc.match(/versionName "([^"]+)"/)?.[1] ?? "0.0.0";
const versionCode = Number(gradleSrc.match(/versionCode (\d+)/)?.[1] ?? "0");

run("node", ["scripts/with-app-env.mjs", "vite", "build", "-c", "vite.native.config.ts"]);

const gradle = "/opt/gradle/gradle-8.7/bin/gradle";
run(gradle, ["-p", "native/android", "assembleRelease", "bundleRelease", "--stacktrace"]);

const apkSrc = resolve(root, "native/android/app/build/outputs/apk/release/app-release.apk");
const aabSrc = resolve(root, "native/android/app/build/outputs/bundle/release/app-release.aab");
if (!existsSync(apkSrc)) {
  console.error("missing release APK", apkSrc);
  process.exit(1);
}
if (!existsSync(aabSrc)) {
  console.error("missing release AAB", aabSrc);
  process.exit(1);
}

const apkName = `DynoGatorLabs-DSLV-ZPDI-${versionName}.apk`;
const aabName = `DynoGatorLabs-DSLV-ZPDI-${versionName}.aab`;
const dests = [resolve(root, "artifacts/android"), resolve(root, "public/releases")];
for (const d of dests) mkdirSync(d, { recursive: true });
for (const d of dests) {
  copyFileSync(apkSrc, resolve(d, apkName));
  copyFileSync(aabSrc, resolve(d, aabName));
  copyFileSync(apkSrc, resolve(d, "DSLV-ZPDI.apk"));
  copyFileSync(aabSrc, resolve(d, "DSLV-ZPDI.aab"));
}

const apkHash = sha256(apkSrc);
const aabHash = sha256(aabSrc);
const apkBytes = statSync(apkSrc).size;
const aabBytes = statSync(aabSrc).size;
const sums =
  `${apkHash}  ${apkName}\n` +
  `${aabHash}  ${aabName}\n` +
  `${apkHash}  DSLV-ZPDI.apk\n` +
  `${aabHash}  DSLV-ZPDI.aab\n`;
for (const d of dests) writeFileSync(resolve(d, "SHA256SUMS"), sums);

const signerSha = "6779d030844096386e02dff6480b836903716fbb3658164515a56831b52f7f6b";
const meta = `export const RELEASE = {
  version: ${JSON.stringify(versionName)},
  versionCode: ${versionCode},
  packageId: "labs.dynogator.dslvzpdi",
  apk: ${JSON.stringify(apkName)},
  aab: ${JSON.stringify(aabName)},
  apkAlias: "DSLV-ZPDI.apk",
  aabAlias: "DSLV-ZPDI.aab",
  apkSha256: ${JSON.stringify(apkHash)},
  aabSha256: ${JSON.stringify(aabHash)},
  apkBytes: ${apkBytes},
  aabBytes: ${aabBytes},
  signerSha256: ${JSON.stringify(signerSha)},
  signerDn: "CN=DynoGator Labs, OU=DSLV-ZPDI, O=Resonant Genesis LLC, L=Penrose, ST=Colorado, C=US",
} as const;

export type ReleaseMeta = typeof RELEASE;
`;
writeFileSync(resolve(root, "src/lib/release-meta.ts"), meta);

console.log(sums);
console.log("android artifacts ready");
