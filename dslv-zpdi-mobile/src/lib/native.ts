import { RELEASE } from "./release-meta";

export type NativeBridgeResult = {
  ok: boolean;
  status: number;
  data: unknown;
  error?: string | null;
};

export interface NativeHostApi {
  request: (method: string, url: string, body: string, bearer: string) => string;
  isNative: () => boolean;
  usbScan?: () => string;
  usbOpen?: (hint: string) => string;
  usbClose?: () => string;
  usbConfig?: (json: string) => string;
  usbRx?: (onOff: string) => string;
  usbSpectrum?: () => string;
  listen?: (json: string) => string;
  usbAuto?: () => string;
  sensors?: () => string;
  pipeline?: (action: string) => string;
  ingest?: (json: string) => string;
  c2?: (envelopeJson: string) => string;
  nodeStatus?: () => string;
  cli?: (cmd: string) => string;
  termux?: (action: string) => string;
}

export type AlphaBridgeApi = NativeHostApi;

declare global {
  interface Window {
    AlphaBridge?: NativeHostApi;
    NativeHost?: NativeHostApi;
  }
}

export function nativeHost(): NativeHostApi | undefined {
  try {
    if (typeof window === "undefined") return undefined;
    return window.NativeHost ?? window.AlphaBridge;
  } catch {
    return undefined;
  }
}

export function isNativeApk(): boolean {
  try {
    return Boolean(nativeHost()?.isNative?.());
  } catch {
    return false;
  }
}

export function nativeRequest(
  method: string,
  url: string,
  body = "",
  bearer = "",
): NativeBridgeResult {
  try {
    const raw = nativeHost()!.request(method, url, body, bearer);
    const parsed = JSON.parse(raw) as NativeBridgeResult;
    return parsed;
  } catch (err) {
    return {
      ok: false,
      status: 0,
      data: null,
      error: err instanceof Error ? err.message : "native bridge failed",
    };
  }
}

export function nativeJson<T = Record<string, unknown>>(fn: () => string | undefined): T | null {
  try {
    const raw = fn();
    if (!raw) return null;
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

export const APK_HREF = `/releases/${RELEASE.apk}`;
export const AAB_HREF = `/releases/${RELEASE.aab}`;
export const APK_ALIAS_HREF = `/releases/${RELEASE.apkAlias}`;
export const AAB_ALIAS_HREF = `/releases/${RELEASE.aabAlias}`;
export const SUMS_HREF = "/releases/SHA256SUMS";
