import { Panel, Pill, Row } from "@/components/panel";
import { Button } from "@/components/ui/button";
import { ISSUER, PROTOCOL, TARGET } from "@/lib/c2";
import { AAB_HREF, APK_HREF, isNativeApk } from "@/lib/native";
import { RELEASE } from "@/lib/release-meta";
import { useApp } from "@/lib/store";
import { useEffect, useState } from "react";

function fmtBytes(n: number) {
  if (!n) return "—";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(0)} KB`;
  return `${(n / (1024 * 1024)).toFixed(2)} MB`;
}

export function LinkView() {
  const mode = useApp((s) => s.mode);
  const nodeUrl = useApp((s) => s.nodeUrl);
  const c2Token = useApp((s) => s.c2Token);
  const liveOk = useApp((s) => s.liveOk);
  const liveError = useApp((s) => s.liveError);
  const operatorUnlocked = useApp((s) => s.operatorUnlocked);
  const setMode = useApp((s) => s.setMode);
  const setNodeUrl = useApp((s) => s.setNodeUrl);
  const setToken = useApp((s) => s.setToken);
  const unlockOperator = useApp((s) => s.unlockOperator);
  const setView = useApp((s) => s.setView);
  const [url, setUrl] = useState(nodeUrl);
  const [token, setTok] = useState(c2Token);
  const [pin, setPin] = useState("");
  const [pinErr, setPinErr] = useState(false);
  const native = isNativeApk();

  useEffect(() => {
    setUrl(nodeUrl);
    setTok(c2Token);
  }, [nodeUrl, c2Token]);

  return (
    <div className="flex flex-col gap-3">
      <Panel
        title="Uplink"
        action={
          <Pill tone={mode === "live" ? (liveOk ? "ok" : "warn") : mode === "standalone" ? "ok" : "default"}>
            {mode === "live" ? (liveOk ? "LIVE" : "LIVE · retry") : mode === "standalone" ? "HANDSET" : "SIMULATED"}
          </Pill>
        }
      >
        <p className="mb-3 text-sm leading-relaxed text-muted">
          This Pixel is a full SDR control stack. Handset mode runs HackRF One / PortaPack over USB-C OTG with onboard GNSS — Alpha is optional. Simulator is the Front Range offline twin. Live mode polls the Pi 5.
        </p>
        <div className="grid grid-cols-3 gap-2">
          <Button className="px-2 text-xs" variant={mode === "standalone" ? "primary" : "outline"} onClick={() => setMode("standalone")}>
            Handset
          </Button>
          <Button className="px-2 text-xs" variant={mode === "simulated" ? "primary" : "outline"} onClick={() => setMode("simulated")}>
            Simulator
          </Button>
          <Button className="px-2 text-xs" variant={mode === "live" ? "primary" : "outline"} onClick={() => setMode("live")}>
            Alpha
          </Button>
        </div>
        {liveError ? <p className="mt-2 font-mono text-xs text-danger">{liveError}</p> : null}
        <p className="mt-3 text-xs leading-relaxed text-muted">
          {native
            ? "This signed APK owns a LAN bridge. Join PiRepo, then Save and probe — HTTP to 10.42.0.1 is allowed from the handset."
            : "Hosted HTTPS cannot reach an HTTP LAN address. Sideload the Pixel APK on GrapheneOS for LIVE Alpha. Mixed-content blocks are expected from a public host."}
        </p>
        <Button className="mt-3 w-full" variant="outline" onClick={() => setView("cli")}>
          CLI · Termux / Debian aliases
        </Button>
      </Panel>

      <Panel title="Alpha endpoint">
        <label className="block">
          <span className="mb-1 block text-[0.6875rem] uppercase tracking-[0.14em] text-muted">Node URL</span>
          <input
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            className="h-11 w-full rounded-md bg-elevated px-3 font-mono text-sm text-foreground shadow-[var(--shadow-border)] outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
        </label>
        <label className="mt-3 block">
          <span className="mb-1 block text-[0.6875rem] uppercase tracking-[0.14em] text-muted">C2 bearer</span>
          <input
            type="password"
            value={token}
            onChange={(e) => setTok(e.target.value)}
            placeholder="optional"
            className="h-11 w-full rounded-md bg-elevated px-3 font-mono text-sm text-foreground shadow-[var(--shadow-border)] outline-none placeholder:text-subtle focus-visible:ring-2 focus-visible:ring-ring"
          />
        </label>
        <Button
          className="mt-3 w-full"
          onClick={() => {
            setNodeUrl(url.trim());
            setToken(token.trim());
            setMode("live");
          }}
        >
          Save and probe
        </Button>
        <div className="mt-3">
          <Row label="Protocol" value={PROTOCOL} />
          <Row label="Issuer" value={ISSUER} />
          <Row label="Target" value={TARGET} />
          <Row label="Status API" value="/api/status" />
          <Row label="SDR API" value="/api/sdr/config" />
          <Row label="Pixel C2" value=":8444 dslv-zpdi-c2/1" />
          <Row label="Telemetry" value=":8777 /telemetry" />
          <Row label="Transport" value={native ? "NativeHost · USB + LAN" : "fetch · browser CORS"} />
        </div>
      </Panel>

      <Panel title="GrapheneOS · USB OTG">
        <p className="mb-3 text-sm leading-relaxed text-muted">
          Pixel 9 Pro XL is USB-C host. No JNI — HackRF talks vendor requests. PortaPack is an SPI hat; USB is still 1d50:6089. Plug in and the radio auto-connects.
        </p>
        <ol className="list-decimal space-y-1.5 pl-5 text-xs leading-relaxed text-muted">
          <li>USB-C OTG adapter. Unlock the phone. GrapheneOS → USB controlled by this device.</li>
          <li>Plug HackRF One / PortaPack. Grant USB once. RX arms itself. RF → FM 98.1 → Listen. WFM comes out the speaker.</li>
          <li>No GPSDO? Pixel GNSS stamps captures. Pi 5 LBE-1421 stays Tier-1 when Alpha is live.</li>
          <li>HamGeek AD9363 / PlutoSDR+: firmware usb_ether=ecm (RNDIS will not enumerate IIO). Then 192.168.2.1:30431.</li>
          <li>App info → Network → Allow. Location for GNSS stamps. No extra native libraries; 16 KB pages are a non-issue.</li>
        </ol>
        <Row label="HackRF / PortaPack" value="1d50:6089" />
        <Row label="Pluto / AD9363" value="0456:b673" />
        <Row label="Default rate" value="2.048 Msps" />
        <Row label="Demod" value="WFM · NFM · AM · USB · LSB · CW" />
      </Panel>

      <section className="overflow-hidden rounded-xl bg-card shadow-[var(--shadow-border)]">
        <img
          src="/lab-banner.jpg"
          alt="DynoGator Labs circuit galleon and bootloader watch"
          className="h-40 w-full object-cover object-right sm:h-48"
        />
        <div className="p-4">
          <header className="mb-3 flex items-center justify-between gap-3">
            <h2 className="text-xs font-medium uppercase tracking-[0.16em] text-muted">Identity</h2>
            <img
              src="/lab-crest.jpg"
              alt=""
              className="size-10 rounded-md object-cover shadow-[var(--shadow-border)]"
            />
          </header>
          <Row label="Lab" value="DynoGator Labs" />
          <Row label="Stack" value={`DSLV-ZPDI Rev ${RELEASE.version}`} />
          <Row label="Role" value="Tier-2 C2 master" />
          <Row label="Handset" value="Pixel 9 Pro XL" />
          <Row label="OS" value="GrapheneOS · Termux · Debian" />
          <Row label="Mesh" value="PiRepo 10.42.0.0/24" />
          <Row label="Package" value={RELEASE.packageId} />
          <p className="mt-3 font-mono text-xs leading-relaxed text-muted">
            Lab plate · circuit galleon · bootloader watch
          </p>
        </div>
      </section>

      <Panel
        title="Restricted capabilities"
        action={<Pill tone={operatorUnlocked ? "ok" : "default"}>{operatorUnlocked ? "OPEN" : "SEALED"}</Pill>}
      >
        {operatorUnlocked ? (
          <div>
            <p className="text-sm leading-relaxed text-muted">
              MIMO TX, fox-hunt TDOA, and hop monitor are unsealed on this handset. Transmit remains RX-only in this
              build — the C2 plane will not emit RF from the Pixel.
            </p>
            <Row label="MIMO TX" value="authorized · not armed" tone="warn" />
            <Row label="Vector / TDOA" value="ready" tone="ok" />
            <Row label="Hop monitor" value="ready" tone="ok" />
          </div>
        ) : (
          <form
            className="flex gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              const ok = unlockOperator(pin);
              setPinErr(!ok);
              if (ok) setPin("");
            }}
          >
            <input
              inputMode="numeric"
              value={pin}
              onChange={(e) => setPin(e.target.value)}
              placeholder="Operator PIN"
              className="h-11 min-w-0 flex-1 rounded-md bg-elevated px-3 font-mono text-sm text-foreground shadow-[var(--shadow-border)] outline-none placeholder:text-subtle"
            />
            <Button type="submit" variant="outline">
              Unseal
            </Button>
          </form>
        )}
        {pinErr ? <p className="mt-2 text-xs text-danger">PIN rejected.</p> : null}
      </Panel>

      <Panel
        title="Install"
        action={<Pill tone={native ? "ok" : "default"}>{native ? "APK" : "PWA"}</Pill>}
      >
        {native ? (
          <div className="flex flex-col gap-2">
            <p className="text-sm leading-relaxed text-muted">
              Signed Pixel build <span className="font-mono text-foreground">{RELEASE.packageId}</span> ·{" "}
              {RELEASE.version}. USB host, HackRF demod, Pixel GNSS, HDF5 chain, and C2 listener are in-process. Grant location and USB when prompted. Alpha is optional.
            </p>
            <Row label="Build" value={`${RELEASE.version} / ${RELEASE.versionCode}`} />
            <Row label="Target" value="API 34 · min 29 · arm64 · Pixel 9 Pro XL" />
            <Row label="Cleartext" value="permitted" tone="ok" />
            <Row label="Signer" value={RELEASE.signerSha256.slice(0, 16) + "…"} />
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            <p className="text-sm leading-relaxed text-muted">
              Sideload the signed APK on GrapheneOS Pixel 9 Pro XL. That package is the usable instrument — LIVE Alpha
              over HTTP only works from it. The AAB is for Play Console upload only and will not install from Files.
            </p>
            <a
              href={APK_HREF}
              download={RELEASE.apk}
              className="inline-flex h-11 items-center justify-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground"
            >
              Download APK · GrapheneOS
            </a>
            <a
              href={AAB_HREF}
              download={RELEASE.aab}
              className="inline-flex h-11 items-center justify-center rounded-md bg-transparent px-4 text-sm font-medium text-foreground shadow-[var(--shadow-border)]"
            >
              Download AAB · Play upload
            </a>
            <div className="rounded-md bg-elevated px-3 py-2 font-mono text-[0.6875rem] leading-relaxed text-muted">
              <div>APK {fmtBytes(RELEASE.apkBytes)}</div>
              <div className="break-all">SHA256 {RELEASE.apkSha256}</div>
              <div className="mt-1">AAB {fmtBytes(RELEASE.aabBytes)}</div>
              <div className="break-all">SHA256 {RELEASE.aabSha256}</div>
            </div>
            <ol className="list-decimal space-y-1 pl-5 text-xs leading-relaxed text-muted">
              <li>Vanadium → three-dot → Downloads, or Files. Settings → Apps → Vanadium → Install unknown apps → Allow.</li>
              <li>Open {RELEASE.apk}. GrapheneOS may warn about an unknown developer — Install anyway.</li>
              <li>App info → Network → Allow (GrapheneOS INTERNET toggle). Grant Location for GPS stamps.</li>
              <li>Join PiRepo (10.42.0.0/24) only if you want Alpha. Otherwise Link → Handset. RF → FM 98.1 → Listen.</li>
            </ol>
          </div>
        )}
      </Panel>
    </div>
  );
}
