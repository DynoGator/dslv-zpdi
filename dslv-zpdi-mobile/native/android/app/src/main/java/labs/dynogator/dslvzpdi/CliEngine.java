package labs.dynogator.dslvzpdi;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;
import java.util.Locale;

/** Shared argv → NativeHost dispatch. HTTP / JS / ContentProvider all land here. */
final class CliEngine {
    private final NativeHost host;
    private final File scriptDir;

    CliEngine(NativeHost host) {
        this.host = host;
        this.scriptDir = new File(host.activity.getFilesDir(), "scripts");
        if (!scriptDir.exists()) scriptDir.mkdirs();
        seedScripts();
    }

    JSONObject exec(String line) {
        return exec(line, true);
    }

    JSONObject exec(String line, boolean pretty) {
        List<String> raw = tokenize(line == null ? "" : line.trim());
        boolean jsonFlag = false;
        List<String> argv = new ArrayList<>();
        for (String a : raw) {
            if ("--json".equals(a) || "-j".equals(a)) jsonFlag = true;
            else argv.add(a);
        }
        if (argv.size() > 0 && "dslv".equalsIgnoreCase(argv.get(0))) argv.remove(0);
        if (argv.isEmpty()) argv.add("help");
        JSONObject out = dispatch(argv);
        try {
            if (!out.has("ok")) out.put("ok", true);
            if (!out.has("text")) out.put("text", out.optString("result", out.toString()));
            if (jsonFlag) pretty = false;
            out.put("argv", new JSONArray(argv));
        } catch (Exception ignored) {
        }
        return out;
    }

    private JSONObject dispatch(List<String> a) {
        if (a.isEmpty()) a.add("help");
        String c0 = a.get(0).toLowerCase(Locale.US);
        String mapped = aliasOf(c0);
        if (mapped != null) {
            List<String> next = new ArrayList<>(tokenize(mapped));
            if (a.size() > 1) next.addAll(a.subList(1, a.size()));
            return dispatch(next);
        }
        if (c0.startsWith("!") && c0.length() > 1) {
            String cmd = c0.substring(1);
            if (a.size() > 1) cmd = cmd + " " + join(a, 1);
            return host.termux.run(cmd.trim(), true);
        }
        try {
            switch (c0) {
                case "help":
                case "-h":
                case "--help":
                    return text(true, HELP);
                case "version":
                    return obj(true, "DSLV-ZPDI " + NativeHost.VERSION, new JSONObject()
                            .put("version", NativeHost.VERSION)
                            .put("node", "pixel-9-pro-xl"));
                case "doctor":
                    return doctor();
                case "status":
                    return wrap(host.nodeStatus());
                case "sensors":
                    return wrap(host.sensors());
                case "tools":
                    return tools();
                case "commands":
                    return catalog();
                case "listen":
                    return listen(a.size() > 1 ? a.get(1) : "on");
                case "mute":
                    return listen("off");
                case "preset":
                    return preset(a.size() > 1 ? a.get(1) : "");
                case "capture":
                    return capture(a.size() > 1 ? join(a, 1) : "cli");
                case "sdr":
                    return sdr(a.subList(1, a.size()));
                case "pipeline":
                    return pipeline(a.size() > 1 ? a.get(1) : "stats");
                case "c2":
                    return c2(a);
                case "script":
                    return script(a.subList(1, a.size()));
                case "termux":
                    return termux(a.subList(1, a.size()));
                case "sh":
                case "!":
                    return host.termux.run(join(a, 1), true);
                default:
                    return err("unknown command: " + c0 + "  (dslv help)");
            }
        } catch (Exception e) {
            return err(e.getMessage());
        }
    }

    private JSONObject sdr(List<String> a) throws Exception {
        if (a.isEmpty()) return wrap(host.sdr.status().toString());
        String op = a.get(0).toLowerCase(Locale.US);
        switch (op) {
            case "scan":
                return wrap(host.usbScan());
            case "open":
                return wrap(host.usbOpen(a.size() > 1 ? a.get(1) : "hackrf"));
            case "close":
                return wrap(host.usbClose());
            case "auto":
                return wrap(host.usbAuto());
            case "rx":
                return wrap(host.usbRx(a.size() > 1 ? a.get(1) : "on"));
            case "tune":
            case "freq":
            case "center": {
                if (a.size() < 2) return err("usage: dslv sdr tune <mhz>");
                long hz = parseHz(a.get(1));
                JSONObject cfg = new JSONObject().put("centerHz", hz);
                host.sdr.config(cfg);
                return obj(true, String.format(Locale.US, "tuned %.4f MHz", hz / 1e6), cfg);
            }
            case "demod": {
                if (a.size() < 2) return err("usage: dslv sdr demod WFM|NFM|AM|USB|LSB|CW|RAW");
                String d = a.get(1).toUpperCase(Locale.US);
                host.sdr.config(new JSONObject().put("demod", d));
                return obj(true, "demod " + d, null);
            }
            case "gain": {
                if (a.size() < 3) return err("usage: dslv sdr gain lna|vga <db>");
                String stage = a.get(1).toLowerCase(Locale.US);
                int db = Integer.parseInt(a.get(2));
                JSONObject g = new JSONObject();
                if ("lna".equals(stage)) g.put("lnaGain", db);
                else g.put("vgaGain", db);
                host.sdr.config(g);
                return obj(true, stage + " " + db + " dB", g);
            }
            case "volume": {
                if (a.size() < 2) return err("usage: dslv sdr volume 0-1");
                host.sdr.config(new JSONObject().put("volume", Double.parseDouble(a.get(1))));
                return obj(true, "volume " + a.get(1), null);
            }
            case "squelch": {
                if (a.size() < 2) return err("usage: dslv sdr squelch 0-1");
                host.sdr.config(new JSONObject().put("squelch", Double.parseDouble(a.get(1))));
                return obj(true, "squelch " + a.get(1), null);
            }
            case "listen":
                return listen(a.size() > 1 ? a.get(1) : "on");
            case "preset":
                return preset(a.size() > 1 ? a.get(1) : "");
            case "spectrum":
                return wrap(host.usbSpectrum());
            case "status":
                return wrap(host.sdr.status().toString());
            default:
                return err("sdr ops: scan open close auto rx tune demod gain volume squelch listen preset spectrum");
        }
    }

    private JSONObject listen(String onOff) throws Exception {
        boolean on = !"off".equalsIgnoreCase(onOff) && !"0".equals(onOff) && !"mute".equalsIgnoreCase(onOff);
        JSONObject o = new JSONObject().put("on", on);
        String r = host.listen(o.toString());
        return obj(true, on ? "LISTEN" : "muted", new JSONObject(r));
    }

    private JSONObject preset(String id) throws Exception {
        long[] p = presetOf(id);
        if (p == null) return err("unknown preset. " + PRESET_HELP);
        JSONObject cfg = new JSONObject().put("centerHz", p[0]).put("demod", demodName((int) p[1]));
        host.sdr.config(cfg);
        host.sdr.setRx(true);
        return obj(true, "preset " + id + " " + (p[0] / 1e6) + " MHz " + demodName((int) p[1]), cfg);
    }

    private JSONObject pipeline(String op) {
        return wrap(host.pipeline(op));
    }

    private JSONObject capture(String note) throws Exception {
        JSONObject p = new JSONObject()
                .put("note", note)
                .put("hardware_tier", 2)
                .put("modality", "cli")
                .put("ts", System.currentTimeMillis());
        String r = host.ingest(p.toString());
        host.pipeline("seal");
        return obj(true, "capture sealed · " + note, new JSONObject(r));
    }

    private JSONObject c2(List<String> a) throws Exception {
        if (a.size() < 2) return err("usage: dslv c2 <capability> [json]");
        JSONObject env = new JSONObject();
        env.put("protocol", "dslv-zpdi-c2/1");
        env.put("capability", a.get(1));
        env.put("issuer_node_id", "pixel-9-pro-xl");
        env.put("target_node_id", "pixel-9-pro-xl");
        env.put("parameters", a.size() > 2 ? new JSONObject(join(a, 2)) : new JSONObject());
        return wrap(host.c2(env.toString()));
    }

    private JSONObject termux(List<String> a) {
        if (a.isEmpty() || "status".equals(a.get(0))) return host.termux.status();
        String op = a.get(0).toLowerCase(Locale.US);
        if ("install".equals(op) || "aliases".equals(op)) return host.termux.installAliases();
        if ("debian".equals(op)) return host.termux.installDebian();
        if ("run".equals(op)) return host.termux.run(join(a, 1), true);
        return err("termux ops: status install debian run <cmd>");
    }

    private JSONObject script(List<String> a) throws Exception {
        if (a.isEmpty() || "list".equals(a.get(0))) return scriptList();
        String op = a.get(0).toLowerCase(Locale.US);
        if ("show".equals(op) && a.size() > 1) return scriptShow(a.get(1));
        if ("run".equals(op) && a.size() > 1) return scriptRun(a.get(1));
        if ("delete".equals(op) && a.size() > 1) return scriptDelete(a.get(1));
        if (("put".equals(op) || "save".equals(op)) && a.size() > 2) {
            String name = a.get(1);
            String json = join(a, 2);
            writeScript(name, json);
            return obj(true, "saved " + name, null);
        }
        return err("script ops: list show <name> run <name> save <name> <json> delete <name>");
    }

    private JSONObject scriptList() throws Exception {
        JSONArray names = new JSONArray();
        File[] files = scriptDir.listFiles();
        if (files != null) {
            for (File f : files) {
                if (f.getName().endsWith(".json")) names.put(f.getName().replace(".json", ""));
            }
        }
        JSONObject o = obj(true, names.length() + " scripts", null);
        o.put("scripts", names);
        o.put("text", names.length() == 0 ? "no scripts" : names.toString());
        return o;
    }

    private JSONObject scriptShow(String name) throws Exception {
        File f = scriptFile(name);
        if (!f.isFile()) return err("no script " + name);
        String raw = readFile(f);
        JSONObject o = obj(true, raw, new JSONObject(raw));
        o.put("text", raw);
        return o;
    }

    private JSONObject scriptRun(String name) throws Exception {
        File f = scriptFile(name);
        if (!f.isFile()) return err("no script " + name);
        JSONObject doc = new JSONObject(readFile(f));
        JSONArray steps = doc.optJSONArray("steps");
        if (steps == null) return err("script has no steps");
        StringBuilder log = new StringBuilder();
        JSONArray results = new JSONArray();
        for (int i = 0; i < steps.length(); i++) {
            JSONObject step = steps.getJSONObject(i);
            String op = step.optString("op");
            if ("wait".equals(op)) {
                int ms = Math.min(60_000, Math.max(0, step.optInt("ms", 1000)));
                try {
                    Thread.sleep(ms);
                } catch (InterruptedException ie) {
                    Thread.currentThread().interrupt();
                }
                log.append("wait ").append(ms).append("ms\n");
                continue;
            }
            String cmd = step.optString("cmd", opToCmd(step));
            JSONObject r = exec(cmd, true);
            results.put(r);
            log.append("$ ").append(cmd).append("\n").append(r.optString("text")).append("\n");
            if (!r.optBoolean("ok", true)) {
                JSONObject out = err("script aborted at step " + i);
                out.put("log", log.toString());
                out.put("results", results);
                return out;
            }
        }
        JSONObject out = obj(true, log.toString().trim(), null);
        out.put("results", results);
        return out;
    }

    private JSONObject scriptDelete(String name) throws Exception {
        File f = scriptFile(name);
        boolean gone = !f.exists() || f.delete();
        return gone ? obj(true, "deleted " + name, null) : err("could not delete " + name);
    }

    void writeScript(String name, String json) throws Exception {
        String safe = name.replaceAll("[^a-zA-Z0-9._-]", "_");
        if (!json.trim().startsWith("{")) {
            JSONObject doc = new JSONObject();
            doc.put("name", safe);
            JSONArray steps = new JSONArray();
            for (String line : json.split("\\n")) {
                String t = line.trim();
                if (t.isEmpty() || t.startsWith("#")) continue;
                steps.put(new JSONObject().put("cmd", t.startsWith("dslv ") ? t.substring(5) : t));
            }
            json = doc.put("steps", steps).toString();
        }
        File f = scriptFile(safe);
        try (FileOutputStream os = new FileOutputStream(f)) {
            os.write(json.getBytes(StandardCharsets.UTF_8));
        }
    }

    private File scriptFile(String name) {
        return new File(scriptDir, name.replaceAll("[^a-zA-Z0-9._-]", "_") + ".json");
    }

    private void seedScripts() {
        try {
            if (scriptFile("fm-watch").exists()) return;
            writeScript("fm-watch", "{\"name\":\"fm-watch\",\"steps\":["
                    + "{\"cmd\":\"sdr preset fm_broadcast\"},"
                    + "{\"cmd\":\"listen on\"},"
                    + "{\"op\":\"wait\",\"ms\":8000},"
                    + "{\"cmd\":\"capture fm-watch\"},"
                    + "{\"cmd\":\"listen off\"}]}");
            writeScript("wx-net", "{\"name\":\"wx-net\",\"steps\":["
                    + "{\"cmd\":\"sdr preset nws\"},"
                    + "{\"cmd\":\"listen on\"}]}");
            writeScript("otg-arm", "{\"name\":\"otg-arm\",\"steps\":["
                    + "{\"cmd\":\"sdr scan\"},"
                    + "{\"cmd\":\"sdr open hackrf\"},"
                    + "{\"cmd\":\"sdr rx on\"}]}");
        } catch (Exception ignored) {
        }
    }

    private JSONObject doctor() throws Exception {
        JSONObject t = host.termux.status();
        JSONObject http = host.httpd.status();
        JSONObject s = new JSONObject(host.nodeStatus());
        StringBuilder b = new StringBuilder();
        b.append("version ").append(NativeHost.VERSION).append('\n');
        b.append("http c2 ").append(http.optString("c2Bind")).append('\n');
        b.append("termux ").append(t.optBoolean("termux") ? "yes" : "no").append('\n');
        b.append("sdr ").append(s.optJSONObject("sdr") != null && s.getJSONObject("sdr").optBoolean("open") ? "open" : "idle").append('\n');
        b.append("install ").append(t.optString("install"));
        JSONObject o = obj(true, b.toString(), s);
        o.put("termux", t);
        o.put("http", http);
        return o;
    }

    JSONObject catalog() throws Exception {
        JSONArray cmds = new JSONArray();
        String[] rows = {
                "help|Show command list",
                "status|Node, SDR, pipeline JSON",
                "sensors|Pixel mag/GNSS/IMU/baro",
                "sdr scan|Enumerate USB OTG",
                "sdr open|Open HackRF / PortaPack",
                "sdr tune|Set center MHz",
                "sdr demod|WFM NFM AM USB LSB CW RAW",
                "sdr listen|Speaker demod on/off",
                "sdr preset|Named band presets",
                "sdr spectrum|192-bin dBm",
                "listen|Alias of sdr listen",
                "capture|Seal HDF5 capture",
                "pipeline|start stop seal rotate stats",
                "script|list show run save delete",
                "termux|status install debian run",
                "tools|JSON function defs for agents",
                "doctor|Bridge self-test",
        };
        for (String r : rows) {
            String[] p = r.split("\\|", 2);
            cmds.put(new JSONObject().put("cmd", p[0]).put("summary", p[1]));
        }
        JSONObject o = obj(true, cmds.length() + " commands", null);
        o.put("commands", cmds);
        o.put("text", HELP);
        return o;
    }

    JSONObject tools() throws Exception {
        JSONArray tools = new JSONArray();
        tools.put(tool("dslv_status", "Node / SDR / pipeline snapshot", "{}"));
        tools.put(tool("dslv_sensors", "Pixel GNSS magnetometer IMU baro", "{}"));
        tools.put(tool("dslv_sdr_tune", "Tune HackRF center frequency",
                "{\"type\":\"object\",\"properties\":{\"mhz\":{\"type\":\"number\"}},\"required\":[\"mhz\"]}"));
        tools.put(tool("dslv_sdr_listen", "Start or stop speaker demod",
                "{\"type\":\"object\",\"properties\":{\"on\":{\"type\":\"boolean\"}},\"required\":[\"on\"]}"));
        tools.put(tool("dslv_sdr_preset", "Apply a named RF preset",
                "{\"type\":\"object\",\"properties\":{\"id\":{\"type\":\"string\"}},\"required\":[\"id\"]}"));
        tools.put(tool("dslv_sdr_demod", "Set demodulator",
                "{\"type\":\"object\",\"properties\":{\"demod\":{\"type\":\"string\",\"enum\":[\"WFM\",\"NFM\",\"AM\",\"USB\",\"LSB\",\"CW\",\"RAW\"]}},\"required\":[\"demod\"]}"));
        tools.put(tool("dslv_capture", "Seal a capture into the HDF5 chain",
                "{\"type\":\"object\",\"properties\":{\"note\":{\"type\":\"string\"}}}"));
        tools.put(tool("dslv_pipeline", "HDF5 pipeline control",
                "{\"type\":\"object\",\"properties\":{\"op\":{\"type\":\"string\",\"enum\":[\"start\",\"stop\",\"seal\",\"rotate\",\"stats\"]}},\"required\":[\"op\"]}"));
        tools.put(tool("dslv_script_run", "Run a saved visual/CLI script",
                "{\"type\":\"object\",\"properties\":{\"name\":{\"type\":\"string\"}},\"required\":[\"name\"]}"));
        JSONObject o = obj(true, tools.length() + " tools", null);
        o.put("tools", tools);
        o.put("text", tools.toString(2));
        return o;
    }

    private static JSONObject tool(String name, String desc, String schema) throws Exception {
        return new JSONObject()
                .put("type", "function")
                .put("function", new JSONObject()
                        .put("name", name)
                        .put("description", desc)
                        .put("parameters", new JSONObject(schema)));
    }

    static List<String> tokenize(String line) {
        List<String> out = new ArrayList<>();
        StringBuilder cur = new StringBuilder();
        boolean quote = false;
        for (int i = 0; i < line.length(); i++) {
            char c = line.charAt(i);
            if (c == '"') {
                quote = !quote;
                continue;
            }
            if (!quote && Character.isWhitespace(c)) {
                if (cur.length() > 0) {
                    out.add(cur.toString());
                    cur.setLength(0);
                }
                continue;
            }
            cur.append(c);
        }
        if (cur.length() > 0) out.add(cur.toString());
        return out;
    }

    static long parseHz(String s) {
        String t = s.trim().toLowerCase(Locale.US).replace("_", "");
        double mul = 1;
        if (t.endsWith("ghz")) {
            mul = 1e9;
            t = t.substring(0, t.length() - 3);
        } else if (t.endsWith("mhz") || t.endsWith("m")) {
            mul = 1e6;
            t = t.endsWith("mhz") ? t.substring(0, t.length() - 3) : t.substring(0, t.length() - 1);
        } else if (t.endsWith("khz") || t.endsWith("k")) {
            mul = 1e3;
            t = t.endsWith("khz") ? t.substring(0, t.length() - 3) : t.substring(0, t.length() - 1);
        } else if (t.endsWith("hz")) {
            t = t.substring(0, t.length() - 2);
        }
        double v = Double.parseDouble(t.trim());
        if (mul == 1 && v < 10_000) mul = 1e6;
        return Math.round(v * mul);
    }

    private static String join(List<String> a, int from) {
        StringBuilder b = new StringBuilder();
        for (int i = from; i < a.size(); i++) {
            if (b.length() > 0) b.append(' ');
            b.append(a.get(i));
        }
        return b.toString();
    }

    private static String opToCmd(JSONObject step) {
        String op = step.optString("op");
        switch (op) {
            case "preset":
                return "sdr preset " + step.optString("arg");
            case "tune":
                return "sdr tune " + step.optString("mhz", step.optString("arg"));
            case "demod":
                return "sdr demod " + step.optString("arg");
            case "listen":
                return "listen " + step.optString("arg", "on");
            case "mute":
                return "listen off";
            case "rx":
                return "sdr rx " + step.optString("arg", "on");
            case "gain":
                return "sdr gain " + step.optString("stage", "lna") + " " + step.optInt("db");
            case "capture":
                return "capture " + step.optString("arg", "script");
            case "pipeline":
                return "pipeline " + step.optString("arg", "stats");
            case "scan":
                return "sdr scan";
            default:
                return step.optString("cmd", op);
        }
    }

    private static String demodName(int i) {
        String[] d = {"WFM", "NFM", "AM", "USB", "LSB", "CW", "RAW"};
        return i >= 0 && i < d.length ? d[i] : "WFM";
    }

    /** hz, demodIndex */
    private static long[] presetOf(String id) {
        String k = id.toLowerCase(Locale.US).replace("-", "_");
        switch (k) {
            case "fm_broadcast":
            case "fm":
            case "fm981":
                return new long[]{98_100_000L, 0};
            case "fm_887":
                return new long[]{88_700_000L, 0};
            case "fm_1073":
                return new long[]{107_300_000L, 0};
            case "nws":
            case "noaa":
                return new long[]{162_400_000L, 1};
            case "airband":
            case "air":
                return new long[]{124_000_000L, 2};
            case "marine":
                return new long[]{156_800_000L, 1};
            case "2m_call":
            case "2m":
                return new long[]{146_520_000L, 1};
            case "70cm":
                return new long[]{446_000_000L, 1};
            case "gmrs":
                return new long[]{462_675_000L, 1};
            case "am_broadcast":
            case "am":
                return new long[]{1_000_000L, 2};
            case "cb":
                return new long[]{27_185_000L, 2};
            case "20m_usb":
            case "20m":
                return new long[]{14_200_000L, 3};
            case "40m_lsb":
            case "40m":
                return new long[]{7_200_000L, 4};
            case "40m_cw":
                return new long[]{7_030_000L, 5};
            case "adsb":
                return new long[]{1_090_000_000L, 6};
            default:
                return null;
        }
    }

    private static String readFile(File f) throws Exception {
        try (FileInputStream in = new FileInputStream(f)) {
            byte[] b = new byte[(int) f.length()];
            int n = in.read(b);
            return new String(b, 0, Math.max(0, n), StandardCharsets.UTF_8);
        }
    }

    private static JSONObject wrap(String raw) {
        try {
            JSONObject o = new JSONObject(raw);
            if (!o.has("ok")) o.put("ok", true);
            if (!o.has("text")) o.put("text", o.toString(2));
            return o;
        } catch (Exception e) {
            return text(true, raw);
        }
    }

    private static JSONObject obj(boolean ok, String text, JSONObject data) throws Exception {
        JSONObject o = new JSONObject();
        o.put("ok", ok);
        o.put("text", text);
        if (data != null) {
            Iterator<String> it = data.keys();
            while (it.hasNext()) {
                String k = it.next();
                if (!o.has(k)) o.put(k, data.get(k));
            }
        }
        return o;
    }

    private static JSONObject text(boolean ok, String t) {
        try {
            return obj(ok, t, null);
        } catch (Exception e) {
            return new JSONObject();
        }
    }

    private static JSONObject err(String m) {
        try {
            JSONObject o = obj(false, m, null);
            o.put("error", m);
            return o;
        } catch (Exception e) {
            return new JSONObject();
        }
    }

    private static String aliasOf(String c0) {
        switch (c0) {
            case "dslv-status":
                return "status";
            case "dslv-listen":
                return "listen";
            case "dslv-mute":
                return "mute";
            case "dslv-tune":
                return "sdr tune";
            case "dslv-capture":
                return "capture";
            case "dslv-sensors":
                return "sensors";
            case "dslv-spectrum":
                return "sdr spectrum";
            case "dslv-help":
                return "help";
            default:
                return null;
        }
    }

    static final String PRESET_HELP = "fm_broadcast nws airband marine 2m_call 70cm gmrs am_broadcast cb 20m_usb 40m_lsb 40m_cw adsb";

    static final String HELP = ""
            + "dslv — DSLV-ZPDI CLI  " + NativeHost.VERSION + "\n"
            + "status                 node / sdr / pipeline\n"
            + "sensors                Pixel GNSS mag IMU baro\n"
            + "sdr scan|open|close|auto|rx on|off\n"
            + "sdr tune <mhz>         e.g. 98.1  146.52  7.2\n"
            + "sdr demod WFM|NFM|AM|USB|LSB|CW|RAW\n"
            + "sdr gain lna|vga <db>\n"
            + "sdr listen on|off      speaker demod\n"
            + "sdr preset <id>        " + PRESET_HELP + "\n"
            + "sdr spectrum           192-bin dBm\n"
            + "listen on|off          alias\n"
            + "capture [note]\n"
            + "pipeline start|stop|seal|rotate|stats\n"
            + "script list|show|run|save|delete\n"
            + "termux status|install|debian|run <cmd>\n"
            + "tools                  JSON function defs for agents\n"
            + "doctor                 bridge self-test\n"
            + "\nAliases: dslv-status dslv-listen dslv-mute dslv-tune dslv-capture dslv-sensors dslv-spectrum\n"
            + "Add --json for machine output. USB IQ is SECONDARY.\n";
}
