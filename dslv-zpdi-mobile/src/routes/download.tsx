import { createFileRoute, Link } from "@tanstack/react-router";
import { AAB_HREF, APK_HREF } from "@/lib/native";
import { RELEASE } from "@/lib/release-meta";

export const Route = createFileRoute("/download")({
  component: DownloadPage,
  head: () => ({
    meta: [{ title: "Install DSLV-ZPDI · Pixel APK" }],
  }),
});

function fmtBytes(n: number) {
  if (!n) return "—";
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(0)} KB`;
  return `${(n / (1024 * 1024)).toFixed(2)} MB`;
}

function DownloadPage() {
  return (
    <main className="mx-auto min-h-dvh w-full max-w-lg px-4 py-8 pb-16 text-foreground">
      <p className="text-xs font-medium uppercase tracking-[0.22em] text-muted">DynoGator Labs</p>
      <h1 className="mt-2 text-2xl font-semibold tracking-tight">DSLV-ZPDI {RELEASE.version}</h1>
      <p className="mt-2 text-sm leading-relaxed text-muted">
        Signed Pixel 9 Pro XL package for GrapheneOS. Sideload the APK — independent HackRF One / PortaPack over USB-C OTG, real WFM/NFM/AM/SSB demod through the speaker, onboard GNSS, sensors, SPEC-007 HDF5, C2 master, and a Termux / proot Debian <span className="font-mono text-foreground">dslv</span> CLI for agents. Alpha is optional. The AAB is a Play Console artifact and will not install from Files.
      </p>

      <div className="mt-6 flex flex-col gap-3">
        <a
          href={APK_HREF}
          download={RELEASE.apk}
          className="inline-flex h-12 items-center justify-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground"
        >
          Download APK · {fmtBytes(RELEASE.apkBytes)}
        </a>
        <a
          href={AAB_HREF}
          download={RELEASE.aab}
          className="inline-flex h-12 items-center justify-center rounded-md bg-transparent px-4 text-sm font-medium text-foreground shadow-[var(--shadow-border)]"
        >
          Download AAB · {fmtBytes(RELEASE.aabBytes)}
        </a>
      </div>

      <dl className="mt-6 space-y-2 font-mono text-xs text-muted">
        <div className="flex justify-between gap-3">
          <dt>Package</dt>
          <dd className="text-foreground">{RELEASE.packageId}</dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt>Version</dt>
          <dd className="text-foreground">
            {RELEASE.version} / {RELEASE.versionCode}
          </dd>
        </div>
        <div>
          <dt className="text-[0.6875rem] uppercase tracking-[0.14em]">APK SHA-256</dt>
          <dd className="mt-1 break-all text-foreground">{RELEASE.apkSha256}</dd>
        </div>
        <div>
          <dt className="text-[0.6875rem] uppercase tracking-[0.14em]">Signer</dt>
          <dd className="mt-1 break-all text-foreground">{RELEASE.signerSha256}</dd>
        </div>
      </dl>

      <ol className="mt-6 list-decimal space-y-2 pl-5 text-sm leading-relaxed text-muted">
        <li>Settings → Apps → Vanadium (or Files) → Install unknown apps → Allow.</li>
        <li>Open the APK. Install anyway if GrapheneOS warns about an unknown developer.</li>
        <li>App info → Network → Allow. Grant Location when DSLV-ZPDI asks.</li>
        <li>RF → FM 98.1 → Listen. Speaker demod. Alpha is optional — Link → Handset if the Pi is dark.</li>
        <li>CLI → Bridge → Install Termux aliases (or Debian). Agents: <span className="font-mono text-foreground">dslv help</span>.</li>
      </ol>

      <Link to="/" className="mt-8 inline-block text-sm text-primary">
        Open dashboard
      </Link>
    </main>
  );
}
