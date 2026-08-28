package labs.dynogator.dslvzpdi;

import android.app.PendingIntent;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.hardware.usb.UsbConstants;
import android.hardware.usb.UsbDevice;
import android.hardware.usb.UsbDeviceConnection;
import android.hardware.usb.UsbEndpoint;
import android.hardware.usb.UsbInterface;
import android.hardware.usb.UsbManager;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Locale;

/**
 * Pure-Java USB host for HackRF One / PortaPack (Mayhem) and HamGeek AD9363.
 * PortaPack is an SPI hat — USB is still HackRF 1d50:6089.
 */
public final class UsbSdrEngine {
    static final String ACTION_USB_PERMISSION = "labs.dynogator.dslvzpdi.USB_PERMISSION";

    static final int VID_GREAT_SCOTT = 0x1d50;
    static final int PID_HACKRF = 0x6089;
    static final int PID_JAWBREAKER = 0x604b;
    static final int PID_RADIO = 0xcc15;
    static final int PID_LIBRESDR = 0x6108;
    static final int VID_ADI = 0x0456;
    static final int PID_PLUTO = 0xb673;
    static final int PID_PLUTO_OG = 0xb001;
    static final int VID_CYPRESS = 0x04b4;
    static final int PID_FX3 = 0x00f1;

    static final int VR_SET_MODE = 1;
    static final int VR_SAMPLE_RATE = 6;
    static final int VR_BB_FILTER = 7;
    static final int VR_BOARD_ID = 14;
    static final int VR_VERSION = 15;
    static final int VR_SET_FREQ = 16;
    static final int VR_AMP = 17;
    static final int VR_LNA = 19;
    static final int VR_VGA = 20;
    static final int VR_ANTENNA = 23;
    static final int MODE_OFF = 0;
    static final int MODE_RX = 1;
    static final int RT_OUT = 0x40;
    static final int RT_IN = 0xC0;

    private final Context ctx;
    private final UsbManager usb;
    private final Fft fft = new Fft();
    private final Demod demod = new Demod();
    private final AudioSink audio = new AudioSink();
    private final float[] fftDb = new float[Fft.N];
    private final float[] bins = new float[Fft.BINS];
    private final short[] pcm = new short[8192];
    private final Handler main = new Handler(Looper.getMainLooper());
    private final Object lock = new Object();

    private UsbDevice device;
    private UsbDeviceConnection conn;
    private UsbEndpoint epIn;
    private UsbInterface iface;
    private Thread rxThread;
    private volatile boolean rx;
    private volatile boolean open;
    private volatile boolean listen;
    private volatile String kind = "none";
    private volatile String version = "";
    private volatile String board = "";
    private volatile String error = "";
    private volatile long centerHz = 98_100_000L;
    private volatile int sampleRate = 2_048_000;
    private volatile int lna = 24;
    private volatile int vga = 32;
    private volatile boolean amp;
    private volatile long lastIqNs;
    private volatile long bytesIn;
    private volatile String pendingHint = "hackrf";
    private volatile boolean auto = true;
    private Socket iio;
    private BroadcastReceiver permReceiver;
    private byte leftover;
    private boolean haveLeftover;
    private int fftSkip;

    UsbSdrEngine(Context ctx) {
        this.ctx = ctx.getApplicationContext();
        this.usb = (UsbManager) ctx.getSystemService(Context.USB_SERVICE);
        for (int i = 0; i < bins.length; i++) bins[i] = -110;
        register(ctx);
        main.postDelayed(this::autoConnect, 350);
        main.postDelayed(this::watchdog, 2000);
    }

    private void register(Context activity) {
        permReceiver = new BroadcastReceiver() {
            @Override
            public void onReceive(Context c, Intent intent) {
                String a = intent.getAction();
                if (ACTION_USB_PERMISSION.equals(a)) {
                    UsbDevice d = intent.getParcelableExtra(UsbManager.EXTRA_DEVICE);
                    boolean granted = intent.getBooleanExtra(UsbManager.EXTRA_PERMISSION_GRANTED, false);
                    if (granted && d != null) {
                        error = "";
                        openUnlocked(d);
                        if (auto) setRx(true);
                    } else {
                        error = "USB permission denied";
                    }
                } else if (UsbManager.ACTION_USB_DEVICE_ATTACHED.equals(a)) {
                    UsbDevice d = intent.getParcelableExtra(UsbManager.EXTRA_DEVICE);
                    if (d != null && !"unknown".equals(classify(d))) {
                        autoConnect();
                    }
                } else if (UsbManager.ACTION_USB_DEVICE_DETACHED.equals(a)) {
                    UsbDevice d = intent.getParcelableExtra(UsbManager.EXTRA_DEVICE);
                    if (device != null && d != null && d.getDeviceId() == device.getDeviceId()) {
                        error = "OTG detached";
                        close();
                    }
                }
            }
        };
        IntentFilter f = new IntentFilter(ACTION_USB_PERMISSION);
        f.addAction(UsbManager.ACTION_USB_DEVICE_ATTACHED);
        f.addAction(UsbManager.ACTION_USB_DEVICE_DETACHED);
        if (Build.VERSION.SDK_INT >= 33) {
            activity.registerReceiver(permReceiver, f, Context.RECEIVER_NOT_EXPORTED);
        } else {
            activity.registerReceiver(permReceiver, f);
        }
    }

    void autoConnect() {
        if (open) {
            if (!rx && auto) setRx(true);
            return;
        }
        UsbDevice match = find(pendingHint);
        if (match == null) match = find("hackrf");
        if (match == null) return;
        open(pendingHint == null || pendingHint.isEmpty() ? "hackrf" : pendingHint);
    }

    private void watchdog() {
        if (auto && !open && (error == null || !error.contains("denied"))) autoConnect();
        main.postDelayed(this::watchdog, 2500);
    }

    void shutdown(Context activity) {
        auto = false;
        setListen(false);
        close();
        try {
            if (permReceiver != null) activity.unregisterReceiver(permReceiver);
        } catch (Exception ignored) {
        }
    }

    JSONArray scan() {
        JSONArray arr = new JSONArray();
        if (usb == null) return arr;
        HashMap<String, UsbDevice> list = usb.getDeviceList();
        for (UsbDevice d : list.values()) {
            JSONObject o = new JSONObject();
            try {
                o.put("deviceId", d.getDeviceId());
                o.put("vid", String.format(Locale.US, "%04x", d.getVendorId()));
                o.put("pid", String.format(Locale.US, "%04x", d.getProductId()));
                o.put("kind", classify(d));
                o.put("name", safeName(d));
                o.put("hasPermission", usb.hasPermission(d));
                arr.put(o);
            } catch (Exception ignored) {
            }
        }
        return arr;
    }

    String open(String hint) {
        pendingHint = hint == null || hint.isEmpty() ? "hackrf" : hint;
        UsbDevice match = find(pendingHint);
        if (match == null) {
            error = "No USB SDR. Plug HackRF One / PortaPack via USB-C OTG.";
            return fail(error);
        }
        if (!usb.hasPermission(match)) {
            Intent i = new Intent(ACTION_USB_PERMISSION);
            i.setPackage(ctx.getPackageName());
            int flags = PendingIntent.FLAG_MUTABLE;
            PendingIntent pi = PendingIntent.getBroadcast(ctx, 0, i, flags);
            usb.requestPermission(match, pi);
            return okPending("USB permission requested");
        }
        return openUnlocked(match);
    }

    private UsbDevice find(String hint) {
        if (usb == null) return null;
        String h = hint == null ? "" : hint.toLowerCase(Locale.US);
        UsbDevice any = null;
        UsbDevice hack = null;
        for (UsbDevice d : usb.getDeviceList().values()) {
            String k = classify(d);
            if ("unknown".equals(k)) continue;
            any = d;
            if ("hackrf".equals(k)) hack = d;
            if ((h.contains("hack") || h.contains("porta")) && "hackrf".equals(k)) return d;
            if ((h.contains("pluto") || h.contains("ad936") || h.contains("libre"))
                    && ("pluto".equals(k) || "libresdr".equals(k))) return d;
        }
        if (h.contains("hack") || h.isEmpty()) return hack != null ? hack : any;
        return any;
    }

    private String openUnlocked(UsbDevice d) {
        closeKeepAudio();
        String k = classify(d);
        device = d;
        kind = k;
        if ("hackrf".equals(k)) {
            String r = openHackrf(d);
            if (open && auto) setRx(true);
            return r;
        }
        return openPluto(d);
    }

    private String openHackrf(UsbDevice d) {
        try {
            conn = usb.openDevice(d);
            if (conn == null) return fail("openDevice returned null");
            iface = d.getInterface(0);
            if (!conn.claimInterface(iface, true)) return fail("claimInterface failed");
            epIn = findBulkIn(iface);
            if (epIn == null) return fail("no bulk IN endpoint");
            byte[] ver = new byte[255];
            int n = conn.controlTransfer(RT_IN, VR_VERSION, 0, 0, ver, ver.length, 500);
            if (n > 0) version = new String(ver, 0, n, StandardCharsets.UTF_8).trim();
            byte[] bid = new byte[1];
            if (conn.controlTransfer(RT_IN, VR_BOARD_ID, 0, 0, bid, 1, 500) == 1) {
                int id = bid[0] & 0xff;
                board = id == 2 ? "HackRF One" : id == 1 ? "Jawbreaker" : "board-" + id;
            }
            String name = safeName(d);
            if (name.toLowerCase(Locale.US).contains("porta")) {
                board = "PortaPack · " + board;
            }
            applyHackrfConfig();
            open = true;
            error = "";
            haveLeftover = false;
            demod.reset();
            return statusJson(true, "HackRF ready " + version);
        } catch (Exception e) {
            return fail("HackRF: " + e.getMessage());
        }
    }

    private String openPluto(UsbDevice d) {
        open = true;
        version = safeName(d);
        board = String.format(Locale.US, "%04x:%04x", d.getVendorId(), d.getProductId());
        String iioErr = connectIio();
        if (iioErr != null) {
            error = "USB " + board + " seen. " + iioErr;
            return statusJson(true, error);
        }
        error = "";
        applyIioConfig();
        return statusJson(true, "Pluto IIO " + version);
    }

    private String connectIio() {
        String[] hosts = {"192.168.2.1", "192.168.3.1", "192.168.1.10"};
        Exception last = null;
        for (String host : hosts) {
            Socket s = new Socket();
            try {
                s.connect(new InetSocketAddress(host, 30431), 800);
                s.setSoTimeout(1500);
                InputStream in = s.getInputStream();
                byte[] buf = new byte[128];
                int n = in.read(buf);
                if (n > 0) {
                    version = new String(buf, 0, n, StandardCharsets.UTF_8).trim();
                }
                iio = s;
                return null;
            } catch (Exception e) {
                last = e;
                try {
                    s.close();
                } catch (Exception ignored) {
                }
            }
        }
        return "IIO TCP 192.168.2.1:30431 unreachable — set usb_ether=ecm ("
                + (last == null ? "timeout" : last.getClass().getSimpleName())
                + ")";
    }

    private void applyHackrfConfig() {
        if (conn == null) return;
        byte[] freq = new byte[8];
        ByteBuffer.wrap(freq).order(ByteOrder.LITTLE_ENDIAN)
                .putInt((int) (centerHz / 1_000_000L))
                .putInt((int) (centerHz % 1_000_000L));
        conn.controlTransfer(RT_OUT, VR_SET_FREQ, 0, 0, freq, 8, 500);
        byte[] sr = new byte[8];
        ByteBuffer.wrap(sr).order(ByteOrder.LITTLE_ENDIAN).putInt(sampleRate).putInt(1);
        conn.controlTransfer(RT_OUT, VR_SAMPLE_RATE, 0, 0, sr, 8, 500);
        int bw = basebandBw(sampleRate);
        conn.controlTransfer(RT_OUT, VR_BB_FILTER, bw & 0xffff, (bw >> 16) & 0xffff, null, 0, 500);
        byte[] one = new byte[1];
        conn.controlTransfer(RT_IN, VR_LNA, 0, lna, one, 1, 500);
        conn.controlTransfer(RT_IN, VR_VGA, 0, vga, one, 1, 500);
        amp = lna >= 32;
        conn.controlTransfer(RT_OUT, VR_AMP, amp ? 1 : 0, 0, null, 0, 500);
        conn.controlTransfer(RT_OUT, VR_ANTENNA, 1, 0, null, 0, 400);
        demod.setSampleRate(sampleRate);
        demod.reset();
    }

    private static int basebandBw(int sr) {
        int[] legal = {
                1_750_000, 2_500_000, 3_500_000, 5_000_000, 5_500_000, 6_000_000, 7_000_000,
                8_000_000, 9_000_000, 10_000_000, 12_000_000, 14_000_000, 15_000_000, 20_000_000,
                24_000_000, 28_000_000
        };
        int want = Math.max(1_750_000, sr);
        int best = legal[0];
        for (int v : legal) {
            if (v >= want) return v;
            best = v;
        }
        return best;
    }

    private void applyIioConfig() {
        if (iio == null) return;
        try {
            iioWrite("ad9361-phy", "out_altvoltage0_RX_LO_frequency", Long.toString(centerHz));
            iioWrite("ad9361-phy", "in_voltage_sampling_frequency", Integer.toString(Math.min(sampleRate, 20_000_000)));
            iioWrite("ad9361-phy", "in_voltage0_gain_control_mode", "manual");
            iioWrite("ad9361-phy", "in_voltage0_hardwaregain", Integer.toString(lna));
        } catch (Exception e) {
            error = "IIO config: " + e.getMessage();
        }
    }

    private void iioWrite(String dev, String attr, String value) throws Exception {
        byte[] payload = value.getBytes(StandardCharsets.UTF_8);
        String cmd = "WRITE " + dev + " " + attr + " " + payload.length + "\n";
        OutputStream os = iio.getOutputStream();
        os.write(cmd.getBytes(StandardCharsets.UTF_8));
        os.write(payload);
        os.flush();
        InputStream in = iio.getInputStream();
        byte[] buf = new byte[64];
        in.read(buf);
    }

    String config(JSONObject cfg) {
        synchronized (lock) {
            if (cfg.has("centerHz")) centerHz = cfg.optLong("centerHz", centerHz);
            if (cfg.has("sampleRateHz")) sampleRate = cfg.optInt("sampleRateHz", sampleRate);
            if (cfg.has("lnaGain")) lna = cfg.optInt("lnaGain", lna);
            if (cfg.has("vgaGain")) vga = cfg.optInt("vgaGain", vga);
            if (cfg.has("amp")) amp = cfg.optBoolean("amp", amp);
            if (cfg.has("demod")) demod.setMode(cfg.optString("demod"));
            if (cfg.has("volume")) demod.setVolume((float) cfg.optDouble("volume", 0.7));
            if (cfg.has("squelch")) demod.setSquelch((float) cfg.optDouble("squelch", 0.08));
            if ("hackrf".equals(kind) && conn != null) applyHackrfConfig();
            if (("pluto".equals(kind) || "libresdr".equals(kind)) && iio != null) applyIioConfig();
            return statusJson(open, "configured");
        }
    }

    String setRx(boolean on) {
        if (on && !open) {
            String r = open(pendingHint);
            if (!open) return r;
        }
        if (!open) return fail("no SDR open");
        if (on) startRx();
        else {
            if (listen) setListen(false);
            stopRx();
        }
        return statusJson(true, on ? "RX" : "idle");
    }

    String setListen(boolean on) {
        listen = on;
        if (on) {
            if (!open) open("hackrf");
            if (open && !rx) startRx();
            demod.reset();
            audio.start();
        } else {
            audio.stop();
        }
        return statusJson(true, on ? "LISTEN" : "mute");
    }

    private void startRx() {
        stopRx();
        if ("hackrf".equals(kind) && conn != null) {
            applyHackrfConfig();
            conn.controlTransfer(RT_OUT, VR_SET_MODE, MODE_RX, 0, null, 0, 500);
            rx = true;
            haveLeftover = false;
            rxThread = new Thread(this::rxLoop, "hackrf-rx");
            rxThread.setPriority(Thread.MAX_PRIORITY);
            rxThread.start();
        } else if (iio != null) {
            rx = true;
            rxThread = new Thread(this::iioRxLoop, "pluto-rx");
            rxThread.start();
        } else {
            error = "RX armed but no sample path";
        }
    }

    private void stopRx() {
        rx = false;
        Thread t = rxThread;
        rxThread = null;
        if (t != null) {
            try {
                t.join(400);
            } catch (InterruptedException ignored) {
            }
        }
        if ("hackrf".equals(kind) && conn != null) {
            try {
                conn.controlTransfer(RT_OUT, VR_SET_MODE, MODE_OFF, 0, null, 0, 400);
            } catch (Exception ignored) {
            }
        }
    }

    private void rxLoop() {
        byte[] buf = new byte[32768];
        byte[] work = new byte[32770];
        fftSkip = 0;
        while (rx && conn != null && epIn != null) {
            int n = conn.bulkTransfer(epIn, buf, buf.length, 800);
            if (n <= 0) continue;
            bytesIn += n;
            lastIqNs = System.nanoTime();

            int woff = 0;
            if (haveLeftover) {
                work[0] = leftover;
                woff = 1;
            }
            System.arraycopy(buf, 0, work, woff, n);
            int total = n + woff;
            if ((total & 1) == 1) {
                leftover = work[total - 1];
                haveLeftover = true;
                total--;
            } else {
                haveLeftover = false;
            }

            if (listen) {
                int produced = demod.process(work, 0, total, pcm);
                if (produced > 0) audio.write(pcm, produced);
            }

            fftSkip++;
            if (fftSkip % 12 != 0) continue;
            int use = Math.min(total, Fft.N * 2);
            int off = total - use;
            if (off < 0) off = 0;
            fft.powerDbm(work, off, use, fftDb);
            synchronized (lock) {
                Fft.collapse(fftDb, bins);
            }
        }
    }

    private void iioRxLoop() {
        while (rx) {
            try {
                Thread.sleep(80);
            } catch (InterruptedException e) {
                return;
            }
            lastIqNs = System.nanoTime();
        }
    }

    void close() {
        setListen(false);
        closeKeepAudio();
    }

    private void closeKeepAudio() {
        stopRx();
        open = false;
        try {
            if (conn != null && iface != null) conn.releaseInterface(iface);
        } catch (Exception ignored) {
        }
        try {
            if (conn != null) conn.close();
        } catch (Exception ignored) {
        }
        conn = null;
        iface = null;
        epIn = null;
        device = null;
        try {
            if (iio != null) iio.close();
        } catch (Exception ignored) {
        }
        iio = null;
        kind = "none";
    }

    JSONObject spectrumJson() {
        JSONObject o = new JSONObject();
        try {
            o.put("ok", true);
            o.put("rx", rx);
            o.put("open", open);
            o.put("listen", listen);
            o.put("kind", kind);
            o.put("centerHz", centerHz);
            o.put("sampleRateHz", sampleRate);
            o.put("rssi", Math.round(demod.rssi() * 1e6) / 1e6);
            o.put("muted", demod.muted());
            JSONArray a = new JSONArray();
            synchronized (lock) {
                for (float b : bins) a.put(Math.round(b * 100.0) / 100.0);
            }
            o.put("bins", a);
            o.put("source", rx && open ? "usb" : "none");
            o.put("bytesIn", bytesIn);
            o.put("ageMs", lastIqNs == 0 ? -1 : (System.nanoTime() - lastIqNs) / 1_000_000L);
        } catch (Exception ignored) {
        }
        return o;
    }

    JSONObject status() {
        JSONObject o = new JSONObject();
        try {
            o.put("ok", error.isEmpty());
            o.put("open", open);
            o.put("rx", rx);
            o.put("listen", listen);
            o.put("kind", kind);
            o.put("version", version);
            o.put("board", board);
            o.put("error", error);
            o.put("centerHz", centerHz);
            o.put("sampleRateHz", sampleRate);
            o.put("lnaGain", lna);
            o.put("vgaGain", vga);
            o.put("amp", amp);
            o.put("devices", scan());
            o.put("iio", iio != null);
            o.put("auto", auto);
        } catch (Exception ignored) {
        }
        return o;
    }

    float[] copyBins() {
        float[] out = new float[bins.length];
        synchronized (lock) {
            System.arraycopy(bins, 0, out, 0, bins.length);
        }
        return out;
    }

    boolean isRx() {
        return rx;
    }

    boolean isOpen() {
        return open;
    }

    boolean isListen() {
        return listen;
    }

    String kind() {
        return kind;
    }

    private static UsbEndpoint findBulkIn(UsbInterface iface) {
        for (int i = 0; i < iface.getEndpointCount(); i++) {
            UsbEndpoint e = iface.getEndpoint(i);
            if (e.getType() == UsbConstants.USB_ENDPOINT_XFER_BULK
                    && e.getDirection() == UsbConstants.USB_DIR_IN) {
                return e;
            }
        }
        return null;
    }

    static String classify(UsbDevice d) {
        int v = d.getVendorId();
        int p = d.getProductId();
        if (v == VID_GREAT_SCOTT && (p == PID_HACKRF || p == PID_JAWBREAKER || p == PID_RADIO)) {
            return "hackrf";
        }
        if (v == VID_GREAT_SCOTT && p == PID_LIBRESDR) return "libresdr";
        if (v == VID_ADI && (p == PID_PLUTO || p == PID_PLUTO_OG)) return "pluto";
        if (v == VID_CYPRESS && p == PID_FX3) return "pluto";
        return "unknown";
    }

    private static String safeName(UsbDevice d) {
        try {
            String n = d.getProductName();
            if (n != null && !n.isEmpty()) return n;
        } catch (Exception ignored) {
        }
        return classify(d);
    }

    private String fail(String msg) {
        error = msg;
        return statusJson(false, msg);
    }

    private String okPending(String msg) {
        try {
            JSONObject o = status();
            o.put("ok", true);
            o.put("pending", true);
            o.put("message", msg);
            return o.toString();
        } catch (Exception e) {
            return "{\"ok\":true,\"pending\":true}";
        }
    }

    private String statusJson(boolean ok, String msg) {
        try {
            JSONObject o = status();
            o.put("ok", ok);
            o.put("message", msg);
            return o.toString();
        } catch (Exception e) {
            return "{\"ok\":" + ok + "}";
        }
    }
}
