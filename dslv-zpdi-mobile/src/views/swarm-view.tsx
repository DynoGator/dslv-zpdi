import { Panel, Pill, Row } from "@/components/panel";
import { Button } from "@/components/ui/button";
import { ISSUER, PROTOCOL, TARGET } from "@/lib/c2";
import { isNativeApk } from "@/lib/native";
import { useApp } from "@/lib/store";

export function SwarmView() {
  const tel = useApp((s) => s.tel);
  const usb = useApp((s) => s.usb);
  const pipe = useApp((s) => s.pipe);
  const applyPixelFix = useApp((s) => s.applyPixelFix);
  const applyMag = useApp((s) => s.applyMag);
  const native = isNativeApk();

  const requestFix = () => {
    if (!navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        applyPixelFix(pos.coords.latitude, pos.coords.longitude, pos.coords.accuracy, pos.coords.altitude ?? undefined);
      },
      () => {
        /* permission denied — sim continues */
      },
      { enableHighAccuracy: true, timeout: 8000 },
    );
  };

  const requestMag = async () => {
    const Mag = (
      window as unknown as {
        Magnetometer?: new (o: { frequency: number }) => {
          start: () => void;
          x: number;
          y: number;
          z: number;
          addEventListener: (e: string, fn: () => void) => void;
        };
      }
    ).Magnetometer;
    if (!Mag) return;
    try {
      const m = new Mag({ frequency: 10 });
      m.addEventListener("reading", () => applyMag(m.x, m.y, m.z));
      m.start();
    } catch {
      /* GrapheneOS may block generic sensors */
    }
  };

  const px = tel.pixel;

  return (
    <div className="flex flex-col gap-3">
      <Panel
        title="C2 MASTER · SPEC-022"
        action={<Pill tone="primary">ISSUER</Pill>}
      >
        <Row label="Protocol" value={PROTOCOL} />
        <Row label="Issuer" value={ISSUER} tone="primary" />
        <Row label="Target" value={TARGET} />
        <Row label="Listen" value=":8444 /api/v1/command" />
        <Row label="Telemetry" value=":8777 /telemetry" />
        <Row label="USB" value={usb.open ? `${usb.kind} ${usb.rx ? "RX" : "open"}` : "idle"} />
        <Row label="Ingest" value={pipe.running ? "ARMED" : "held"} tone={pipe.running ? "ok" : "default"} />
        <p className="mt-2 text-xs leading-relaxed text-muted">
          This handset issues capability envelopes and can run without Alpha. Local USB SDR executes here. Alpha timing, GPSDO, and institutional PRIMARY stay on the Pi 5 when that node is live.
        </p>
      </Panel>

      {tel.nodes.map((n) => (
        <Panel
          key={n.id}
          title={n.role}
          action={<Pill tone={n.online ? "ok" : "danger"}>{n.online ? "ONLINE" : "DOWN"}</Pill>}
        >
          <Row label="ID" value={n.id} />
          <Row label="Platform" value={n.platform} />
          <Row label="Detail" value={n.detail} />
          <Row
            label="RTT"
            value={n.latencyMs != null ? `${n.latencyMs.toFixed(0)} ms` : "—"}
            tone={n.latencyMs != null && n.latencyMs < 50 ? "ok" : "warn"}
          />
        </Panel>
      ))}

      <Panel
        title="Pixel 9 Pro XL sensors"
        action={<Pill tone={px.available || native ? "ok" : "default"}>{px.available || native ? "DEVICE" : "SIM"}</Pill>}
      >
        <Row label="|B|" value={`${px.magAbs.toFixed(2)} µT`} tone="primary" />
        <Row
          label="Bx By Bz"
          value={`${px.magUt[0].toFixed(1)}  ${px.magUt[1].toFixed(1)}  ${px.magUt[2].toFixed(1)}`}
        />
        <Row label="Heading" value={`${px.headingDeg.toFixed(1)}°`} />
        <Row
          label="Accel"
          value={`${px.accMs2[0].toFixed(2)}  ${px.accMs2[1].toFixed(2)}  ${px.accMs2[2].toFixed(2)}`}
        />
        <Row
          label="Gyro"
          value={`${px.gyroRads[0].toFixed(3)}  ${px.gyroRads[1].toFixed(3)}  ${px.gyroRads[2].toFixed(3)}`}
        />
        <Row
          label="Fix"
          value={
            px.lat != null && px.lon != null
              ? `${px.lat.toFixed(5)}, ${px.lon.toFixed(5)}`
              : "no fix"
          }
        />
        <Row label="Alt" value={px.alt != null ? `${px.alt.toFixed(0)} m` : "—"} />
        <Row label="Acc" value={px.accM != null ? `${px.accM.toFixed(1)} m` : "—"} />
        <Row label="Baro" value={px.baroHpa != null ? `${px.baroHpa.toFixed(1)} hPa` : "—"} />
        <Row label="Light" value={px.lightLux != null ? `${px.lightLux.toFixed(0)} lx` : "—"} />
        <Row label="SoC T" value={px.tempC != null ? `${px.tempC.toFixed(1)} °C` : "—"} />
        <Row label="Trust" value={px.trustScore.toFixed(2)} tone={px.trustScore >= 0.5 ? "ok" : "warn"} />
        <Row label="Frame SHA" value={px.cameraHash} />
        <Row label="Tier" value="2 · never PRIMARY" tone="warn" />
        <p className="mt-2 text-xs leading-relaxed text-muted">
          {native
            ? "SensorHub at UI rate (~16 Hz). Pixel GNSS stamps this node when the GPSDO is absent. Alpha may poll /telemetry — it is not required."
            : "On GrapheneOS, grant location. Magnetometer uses the Generic Sensor API when the OS allows it; the APK reads ICM45631 / MMC5616 / ICP20100 natively."}
        </p>
        <div className="mt-3 flex gap-2">
          <Button variant="primary" onClick={requestFix}>
            Request GPS
          </Button>
          <Button variant="outline" onClick={() => void requestMag()}>
            Mag sensor
          </Button>
        </div>
      </Panel>

      <Panel title="Radon · SPEC-015">
        <Row label="Site" value="Fremont corridor" />
        <Row label="Rn" value={`${tel.radonPci.toFixed(2)} pCi/L`} tone={tel.radonPci > 4 ? "warn" : "ok"} />
        <Row label="Route" value="SECONDARY" />
        <Row label="Session" value="staging · not PRIMARY" />
        <p className="mt-2 text-xs leading-relaxed text-muted">
          RadonEye stays quarantined on the secondary HDF5 branch until promotion gates pass. Mobile C2 can watch the
          staging endpoint; it cannot force PRIMARY.
        </p>
      </Panel>
    </div>
  );
}
