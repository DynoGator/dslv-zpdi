package labs.dynogator.dslvzpdi;

import android.app.Activity;
import android.os.Build;
import android.webkit.JavascriptInterface;

import org.json.JSONObject;

/**
 * WebView bridge: USB SDR, Pixel sensors, SPEC-007 HDF5, C2 master, Alpha LAN, CLI.
 * Registered as both NativeHost and AlphaBridge.
 */
public final class NativeHost {
    static final String VERSION = "5.8.0";
    static volatile NativeHost INSTANCE;

    final Activity activity;
    private final AlphaBridge http = new AlphaBridge();
    final UsbSdrEngine sdr;
    final SensorHub sensors;
    final Hdf5Pipeline pipeline;
    final NodeHttpServer httpd;
    final TermuxBridge termux;
    final CliEngine cli;

    NativeHost(Activity activity) {
        this.activity = activity;
        this.sdr = new UsbSdrEngine(activity);
        this.sensors = new SensorHub(activity);
        this.pipeline = new Hdf5Pipeline(activity);
        this.pipeline.attach(sensors, sdr);
        this.sensors.start();
        this.termux = new TermuxBridge(activity);
        this.cli = new CliEngine(this);
        this.httpd = new NodeHttpServer(this);
        this.httpd.start();
        this.sdr.autoConnect();
        INSTANCE = this;
    }

    void shutdown() {
        INSTANCE = null;
        try {
            pipeline.stop();
            pipeline.seal();
        } catch (Exception ignored) {
        }
        sensors.stop();
        sdr.shutdown(activity);
        termux.shutdown();
        httpd.stop();
    }

    @JavascriptInterface
    public boolean isNative() {
        return true;
    }

    @JavascriptInterface
    public String request(String method, String url, String body, String bearer) {
        return http.request(method, url, body, bearer);
    }

    @JavascriptInterface
    public String usbScan() {
        try {
            JSONObject o = new JSONObject();
            o.put("ok", true);
            o.put("devices", sdr.scan());
            o.put("status", sdr.status());
            return o.toString();
        } catch (Exception e) {
            return err(e);
        }
    }

    @JavascriptInterface
    public String usbOpen(String hint) {
        return sdr.open(hint);
    }

    @JavascriptInterface
    public String usbClose() {
        sdr.close();
        return sdr.status().toString();
    }

    @JavascriptInterface
    public String usbConfig(String json) {
        try {
            return sdr.config(new JSONObject(json == null || json.isEmpty() ? "{}" : json));
        } catch (Exception e) {
            return err(e);
        }
    }

    @JavascriptInterface
    public String usbRx(String onOff) {
        boolean on = "1".equals(onOff) || "true".equalsIgnoreCase(onOff) || "on".equalsIgnoreCase(onOff);
        return sdr.setRx(on);
    }

    @JavascriptInterface
    public String listen(String json) {
        try {
            JSONObject o = new JSONObject(json == null || json.isEmpty() ? "{}" : json);
            if (o.has("demod") || o.has("volume") || o.has("squelch") || o.has("centerHz")) {
                sdr.config(o);
            }
            boolean on = o.optBoolean("on", true);
            if (o.has("listen")) on = o.optBoolean("listen");
            return sdr.setListen(on);
        } catch (Exception e) {
            return err(e);
        }
    }

    @JavascriptInterface
    public String usbAuto() {
        sdr.autoConnect();
        return sdr.status().toString();
    }

    @JavascriptInterface
    public String usbSpectrum() {
        return sdr.spectrumJson().toString();
    }

    @JavascriptInterface
    public String sensors() {
        return sensors.snapshot().toString();
    }

    @JavascriptInterface
    public String pipeline(String action) {
        if (action == null) action = "stats";
        switch (action) {
            case "start":
                return pipeline.start();
            case "stop":
                return pipeline.stop();
            case "seal":
                return pipeline.seal();
            case "rotate":
                return pipeline.rotate();
            default:
                return pipeline.stats().toString();
        }
    }

    @JavascriptInterface
    public String ingest(String json) {
        try {
            JSONObject p = new JSONObject(json == null || json.isEmpty() ? "{}" : json);
            return pipeline.ingest(p);
        } catch (Exception e) {
            return err(e);
        }
    }

    @JavascriptInterface
    public String cli(String cmd) {
        try {
            return this.cli.exec(cmd == null ? "help" : cmd).toString();
        } catch (Exception e) {
            return err(e);
        }
    }

    @JavascriptInterface
    public String termux(String action) {
        try {
            if (action == null || action.isEmpty() || "status".equals(action)) return termux.status().toString();
            if ("install".equals(action) || "aliases".equals(action)) return termux.installAliases().toString();
            if ("debian".equals(action)) return termux.installDebian().toString();
            if (action.startsWith("run:")) return termux.run(action.substring(4), true).toString();
            return termux.run(action, true).toString();
        } catch (Exception e) {
            return err(e);
        }
    }

    @JavascriptInterface
    public String c2(String envelopeJson) {
        try {
            JSONObject env = new JSONObject(envelopeJson == null || envelopeJson.isEmpty() ? "{}" : envelopeJson);
            String proto = env.optString("protocol");
            if (!proto.isEmpty() && !"dslv-zpdi-c2/1".equals(proto)) {
                return "{\"ok\":false,\"state\":\"FAILED\",\"error\":\"bad protocol\"}";
            }
            String cap = env.optString("capability");
            String target = env.optString("target_node_id", "pixel-9-pro-xl");
            JSONObject p = env.optJSONObject("parameters");
            if (p == null) p = new JSONObject();
            boolean local = target.isEmpty()
                    || "pixel-9-pro-xl".equals(target)
                    || "*".equals(target)
                    || "tier2-c2-master".equals(target);
            JSONObject out = new JSONObject();
            out.put("ok", true);
            out.put("command_id", env.optString("command_id"));
            out.put("capability", cap);
            if (!local && target.contains("alpha")) {
                out.put("state", "ACCEPTED");
                out.put("forward", true);
                out.put("result", "forward to Tier-1 — Pixel cannot override timing authority");
                return out.toString();
            }
            String result = dispatch(cap, p);
            out.put("state", "COMPLETED");
            out.put("result", result);
            out.put("issuer_node_id", "pixel-9-pro-xl");
            return out.toString();
        } catch (Exception e) {
            return err(e);
        }
    }

    private String dispatch(String cap, JSONObject p) {
        try {
            switch (cap) {
                case "sdr.center_frequency.set":
                    sdr.config(new JSONObject().put("centerHz", p.optLong("hz")));
                    return "local USB " + p.optLong("hz") + " Hz";
                case "sdr.gain.set":
                    JSONObject g = new JSONObject();
                    if ("lna".equals(p.optString("stage"))) g.put("lnaGain", p.optInt("gain_db"));
                    else g.put("vgaGain", p.optInt("gain_db"));
                    sdr.config(g);
                    return "local gain";
                case "sdr.sample_rate.set":
                    sdr.config(new JSONObject().put("sampleRateHz", p.optInt("sample_rate_hz")));
                    return "local rate";
                case "sdr.mode.set":
                    String mode = p.optString("mode");
                    if ("real".equals(mode) || "hardware".equals(mode)) {
                        sdr.open(p.optString("device", "hackrf"));
                        sdr.setRx(true);
                    } else if ("offline".equals(mode)) {
                        sdr.setRx(false);
                    }
                    return "local mode " + mode;
                case "sdr.demod.set":
                    sdr.config(new JSONObject().put("demod", p.optString("demod")));
                    return "demod " + p.optString("demod");
                case "sdr.listen":
                    sdr.setListen(p.optBoolean("on", true));
                    return p.optBoolean("on", true) ? "LISTEN" : "mute";
                case "pipeline.start":
                    return pipeline.start();
                case "pipeline.stop":
                    return pipeline.stop();
                case "pipeline.rotate_output":
                    return pipeline.rotate();
                case "hdf5.summary.read":
                    return pipeline.stats().toString();
                case "node.status.read":
                    return nodeStatus();
                case "cli.exec":
                    return cli.exec(p.optString("cmd")).toString();
                case "baseline.reset":
                    return "REJECTED: Pixel C2 cannot override Tier-1 baseline/timing authority";
                default:
                    return "unknown capability";
            }
        } catch (Exception e) {
            return e.getMessage();
        }
    }

    @JavascriptInterface
    public String nodeStatus() {
        try {
            JSONObject o = new JSONObject();
            o.put("ok", true);
            o.put("version", VERSION);
            o.put("node_id", "pixel-9-pro-xl");
            o.put("role", "tier2-c2-master");
            o.put("hardware_tier", 2);
            o.put("sdk", Build.VERSION.SDK_INT);
            o.put("model", Build.MODEL);
            o.put("sdr", sdr.status());
            o.put("sensors", sensors.snapshot());
            o.put("pipeline", pipeline.stats());
            o.put("http", httpd.status());
            o.put("termux", termux.status());
            o.put("cli", "/cli/exec");
            o.put("clock_source", "internal");
            o.put("timing_authority", "alpha-pi-tier1");
            return o.toString();
        } catch (Exception e) {
            return err(e);
        }
    }

    String telemetryPayload() {
        try {
            JSONObject sns = sensors.snapshot();
            JSONObject o = new JSONObject();
            o.put("node_id", "pixel-9-pro-xl");
            o.put("hardware_tier", 2);
            o.put("timestamp_utc", System.currentTimeMillis() / 1000.0);
            o.put("gps", new JSONObject()
                    .put("lat", sns.opt("lat"))
                    .put("lon", sns.opt("lon"))
                    .put("alt", sns.opt("alt"))
                    .put("acc_m", sns.opt("accM")));
            o.put("magnetometer", new JSONObject()
                    .put("x", sns.optJSONArray("magUt") != null ? sns.getJSONArray("magUt").opt(0) : 0)
                    .put("y", sns.optJSONArray("magUt") != null ? sns.getJSONArray("magUt").opt(1) : 0)
                    .put("z", sns.optJSONArray("magUt") != null ? sns.getJSONArray("magUt").opt(2) : 0)
                    .put("abs", sns.opt("magAbs")));
            o.put("baro_hpa", sns.opt("baroHpa"));
            o.put("heading_deg", sns.opt("headingDeg"));
            o.put("camera_hash", sns.opt("cameraHash"));
            o.put("trust_score", sns.opt("trustScore"));
            o.put("sdr", sdr.status());
            o.put("pipeline", pipeline.stats());
            o.put("accelerometer", sns.opt("accMs2"));
            o.put("gyro", sns.opt("gyroRads"));
            o.put("light_lux", sns.opt("lightLux"));
            return o.toString();
        } catch (Exception e) {
            return err(e);
        }
    }

    private static String err(Exception e) {
        String m = e.getMessage();
        if (m == null) m = e.getClass().getSimpleName();
        return "{\"ok\":false,\"error\":" + AlphaBridge.quote(m) + "}";
    }
}
