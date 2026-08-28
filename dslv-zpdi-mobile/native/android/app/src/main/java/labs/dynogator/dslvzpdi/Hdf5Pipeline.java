package labs.dynogator.dslvzpdi;

import android.content.Context;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.File;
import java.io.FileOutputStream;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Locale;
import java.util.TimeZone;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;

/**
 * SPEC-007 Pixel writer. hardware_tier=2, clock_source=internal.
 * USB RF is SECONDARY_QUARANTINED. Sensor archive is LOCAL PRIMARY, never
 * institutional Tier-1. HMAC key lives in filesDir/hmac.key (SecureRandom).
 */
public final class Hdf5Pipeline {
    static final String FILE_VERSION = "3.3";
    static final String GENESIS =
            "89129408c9090ce97207b3f27690f0628fee4c53d3d603799ebb3dd3d4fc0108";
    static final String SOURCE = "pixel-9-pro-xl";
    static final int MAX_EVENTS = 256;

    private final File primaryDir;
    private final File secondaryDir;
    private final File hmacFile;
    private final byte[] hmacKey;
    private final Object lock = new Object();
    private final List<JSONObject> events = new ArrayList<>();

    private volatile boolean running;
    private volatile int primaryWritten;
    private volatile int secondaryWritten;
    private volatile int integrityFailed;
    private volatile String chainHead = GENESIS;
    private volatile String lastFile = "";
    private volatile String lastSha256 = "";
    private volatile String lastHmac = "";
    private Thread pump;
    private SensorHub sensors;
    private UsbSdrEngine sdr;

    Hdf5Pipeline(Context ctx) {
        File root = new File(ctx.getFilesDir(), "output");
        primaryDir = new File(root, "primary");
        secondaryDir = new File(root, "secondary");
        primaryDir.mkdirs();
        secondaryDir.mkdirs();
        hmacFile = new File(ctx.getFilesDir(), "hmac.key");
        hmacKey = loadOrCreateKey(hmacFile);
    }

    void attach(SensorHub sensors, UsbSdrEngine sdr) {
        this.sensors = sensors;
        this.sdr = sdr;
    }

    String start() {
        synchronized (lock) {
            running = true;
            if (pump == null || !pump.isAlive()) {
                pump = new Thread(this::loop, "hdf5-pump");
                pump.start();
            }
            return stats().putSilent("message", "started").toString();
        }
    }

    String stop() {
        running = false;
        return stats().putSilent("message", "stopped").toString();
    }

    String seal() {
        synchronized (lock) {
            flushLocked(true);
            return stats().putSilent("message", "sealed").toString();
        }
    }

    String rotate() {
        synchronized (lock) {
            flushLocked(true);
            events.clear();
            return stats().putSilent("message", "rotated").toString();
        }
    }

    String ingest(JSONObject payload) {
        synchronized (lock) {
            return ingestLocked(payload);
        }
    }

    private void loop() {
        while (running) {
            try {
                JSONObject p = buildLive();
                synchronized (lock) {
                    ingestLocked(p);
                    if (events.size() >= MAX_EVENTS) flushLocked(true);
                }
                Thread.sleep(500);
            } catch (InterruptedException e) {
                return;
            } catch (Exception ignored) {
            }
        }
    }

    private JSONObject buildLive() {
        JSONObject p = new JSONObject();
        try {
            JSONObject sns = sensors != null ? sensors.snapshot() : new JSONObject();
            float[] spec = sdr != null ? sdr.copyBins() : new float[192];
            boolean rf = sdr != null && sdr.isRx();
            p.put("timestamp_utc", System.currentTimeMillis() / 1000.0);
            p.put("node_id", SOURCE);
            p.put("hardware_tier", 2);
            p.put("clock_source", "internal");
            p.put("modality", rf ? "rf_iq" : "magnetometer");
            p.put("sensors", sns);
            JSONArray bins = new JSONArray();
            for (float v : spec) bins.put(Math.round(v * 100.0) / 100.0);
            p.put("spectrum", bins);
            p.put("sdr_kind", sdr == null ? "none" : sdr.kind());
            p.put("rf_live", rf);
        } catch (Exception ignored) {
        }
        return p;
    }

    private String ingestLocked(JSONObject payload) {
        try {
            byte[] raw = payload.toString().getBytes(StandardCharsets.UTF_8);
            String blake = Blake2b.hex256(raw);
            payload.put("payload_checksum", blake);
            payload.put("payload_checksum_alg", "blake2b-256");
            boolean rf = payload.optBoolean("rf_live", false)
                    || "rf_iq".equals(payload.optString("modality"));
            if (rf) {
                appendJsonl(new File(secondaryDir, "quarantine.jsonl"), payload, blake, "SECONDARY_QUARANTINED");
                secondaryWritten++;
            } else {
                events.add(payload);
                primaryWritten++;
            }
            String prev = chainHead;
            String meta = payload.optString("timestamp_utc") + "|" + events.size();
            MessageDigest sha = MessageDigest.getInstance("SHA-256");
            sha.update(prev.getBytes(StandardCharsets.UTF_8));
            sha.update(blake.getBytes(StandardCharsets.UTF_8));
            sha.update(meta.getBytes(StandardCharsets.UTF_8));
            chainHead = Blake2b.hex(sha.digest());
            payload.put("previous_event_chain_sha256", prev);
            payload.put("event_chain_sha256", chainHead);
            if (!rf) {
                appendJsonl(new File(primaryDir, "events.jsonl"), payload, blake, "LOCAL_PRIMARY");
            }
            if (events.size() >= MAX_EVENTS) flushLocked(false);
            return stats().putSilent("event_chain_sha256", chainHead).toString();
        } catch (Exception e) {
            integrityFailed++;
            return "{\"ok\":false,\"error\":" + AlphaBridge.quote(e.getMessage()) + "}";
        }
    }

    private void flushLocked(boolean force) {
        if (events.isEmpty() && !force) return;
        if (events.isEmpty()) return;
        try {
            String stamp = stamp();
            String name = "dslv_zpdi_" + stamp + ".h5";
            File partial = new File(primaryDir, name + ".partial");
            File dest = new File(primaryDir, name);
            byte[] h5 = Hdf5Lite.build(events, chainHead);
            try (FileOutputStream fos = new FileOutputStream(partial)) {
                fos.write(h5);
                fos.getFD().sync();
            }
            String fileSha = sha256Hex(h5);
            File shaFile = new File(primaryDir, name + ".sha256");
            writeText(shaFile, fileSha + "  " + name + "\n");
            if (!partial.renameTo(dest)) {
                throw new IllegalStateException("atomic rename failed");
            }
            lastFile = dest.getAbsolutePath();
            lastSha256 = fileSha;
            JSONObject att = new JSONObject();
            att.put("system", "DSLV-ZPDI");
            att.put("file_version", FILE_VERSION);
            att.put("source_node", SOURCE);
            att.put("hardware_tier", 2);
            att.put("clock_source", "internal");
            att.put("event_count", events.size());
            att.put("final_event_chain_sha256", chainHead);
            att.put("file_sha256", fileSha);
            att.put("not_institutional", true);
            att.put("filename", name);
            String attJson = att.toString();
            lastHmac = hmacHex(attJson.getBytes(StandardCharsets.UTF_8));
            att.put("hmac_sha256", lastHmac);
            writeText(new File(primaryDir, name.replace(".h5", ".status.json")), att.toString());
            events.clear();
        } catch (Exception e) {
            integrityFailed++;
        }
    }

    private void appendJsonl(File f, JSONObject payload, String blake, String stream) {
        try {
            JSONObject row = new JSONObject();
            row.put("timestamp_utc", payload.opt("timestamp_utc"));
            row.put("stream", stream);
            row.put("hardware_tier", 2);
            row.put("payload_uuid", blake.substring(0, Math.min(16, blake.length())));
            row.put("payload_checksum", blake);
            row.put("event_chain_sha256", chainHead);
            row.put("payload", payload);
            try (FileOutputStream fos = new FileOutputStream(f, true)) {
                fos.write((row.toString() + "\n").getBytes(StandardCharsets.UTF_8));
            }
        } catch (Exception ignored) {
        }
    }

    Jstats stats() {
        Jstats o = new Jstats();
        o.putSilent("ok", true);
        o.putSilent("running", running);
        o.putSilent("hardwareTier", 2);
        o.putSilent("clockSource", "internal");
        o.putSilent("route", "LOCAL_PRIMARY");
        o.putSilent("primaryWritten", primaryWritten);
        o.putSilent("secondaryWritten", secondaryWritten);
        o.putSilent("integrityFailed", integrityFailed);
        o.putSilent("lastFile", lastFile);
        o.putSilent("chainHead", chainHead);
        o.putSilent("genesis", GENESIS);
        o.putSilent("hmacReady", hmacKey.length == 32);
        o.putSilent("lastSha256", lastSha256);
        o.putSilent("lastHmac", lastHmac);
        o.putSilent("fileVersion", FILE_VERSION);
        o.putSilent("buffered", events.size());
        o.putSilent("primaryDir", primaryDir.getAbsolutePath());
        return o;
    }

    private static byte[] loadOrCreateKey(File f) {
        try {
            if (f.exists() && f.length() == 32) {
                byte[] k = new byte[32];
                try (java.io.FileInputStream in = new java.io.FileInputStream(f)) {
                    if (in.read(k) == 32) return k;
                }
            }
            byte[] k = new byte[32];
            new SecureRandom().nextBytes(k);
            try (FileOutputStream out = new FileOutputStream(f)) {
                out.write(k);
            }
            return k;
        } catch (Exception e) {
            byte[] k = new byte[32];
            new SecureRandom().nextBytes(k);
            return k;
        }
    }

    private String hmacHex(byte[] data) {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(hmacKey, "HmacSHA256"));
            return Blake2b.hex(mac.doFinal(data));
        } catch (Exception e) {
            return "";
        }
    }

    private static String sha256Hex(byte[] data) throws Exception {
        return Blake2b.hex(MessageDigest.getInstance("SHA-256").digest(data));
    }

    private static void writeText(File f, String s) throws Exception {
        try (FileOutputStream fos = new FileOutputStream(f)) {
            fos.write(s.getBytes(StandardCharsets.UTF_8));
        }
    }

    private static String stamp() {
        SimpleDateFormat fmt = new SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US);
        fmt.setTimeZone(TimeZone.getTimeZone("UTC"));
        return fmt.format(new Date());
    }

    /** Tiny JSONObject with fluent put that swallows. */
    static final class Jstats extends JSONObject {
        Jstats putSilent(String k, Object v) {
            try {
                put(k, v);
            } catch (Exception ignored) {
            }
            return this;
        }
    }

    /**
     * Minimal HDF5 superblock-0 container: root group + uint8 dataset "payload"
     * holding the JSONL of events, plus a DSLV trailer for forensic recovery.
     */
    static final class Hdf5Lite {
        static byte[] build(List<JSONObject> events, String chainHead) throws Exception {
            StringBuilder sb = new StringBuilder();
            for (JSONObject e : events) sb.append(e.toString()).append('\n');
            byte[] payload = sb.toString().getBytes(StandardCharsets.UTF_8);
            byte[] jsonAttr = ("{\"system\":\"DSLV-ZPDI\",\"file_version\":\"" + FILE_VERSION
                    + "\",\"hardware_tier\":2,\"source_node\":\"" + SOURCE
                    + "\",\"chain\":\"" + chainHead + "\",\"n\":" + events.size() + "}")
                    .getBytes(StandardCharsets.UTF_8);

            // Superblock 0 (8-byte addrs) + pad to 96, then OHDR v1 dataset at 96.
            int ohdr = 96;
            int dataAddr = 512;
            int dataEnd = dataAddr + payload.length;
            int trailer = (dataEnd + 7) & ~7;
            int total = trailer + 8 + 4 + jsonAttr.length + payload.length;

            ByteBuffer b = ByteBuffer.allocate(Math.max(total + 64, 1024));
            b.order(ByteOrder.LITTLE_ENDIAN);
            // signature
            b.put(new byte[]{(byte) 0x89, 'H', 'D', 'F', '\r', '\n', 0x1a, '\n'});
            b.put((byte) 0); // superblock v0
            b.put((byte) 0);
            b.put((byte) 0);
            b.put((byte) 0);
            b.put((byte) 0);
            b.put((byte) 8); // sizeof addr
            b.put((byte) 8); // sizeof len
            b.put((byte) 0);
            b.putShort((short) 4);
            b.putShort((short) 16);
            b.putInt(0);
            b.putLong(0); // base
            b.putLong(-1L); // free
            b.putLong(total); // eof (patched later)
            b.putLong(-1L); // driver
            // root symbol table entry (36 bytes) — root IS the dataset
            b.putLong(0); // name offset
            b.putLong(ohdr);
            b.put((byte) 0); // cache type none
            b.put((byte) 0);
            b.putShort((short) 0);
            byte[] scratch = new byte[16];
            b.put(scratch);
            while (b.position() < ohdr) b.put((byte) 0);

            // Object header v1: dataspace, datatype uint8, layout contiguous, attr
            int msgStart = ohdr + 16;
            ByteBuffer msgs = ByteBuffer.allocate(256);
            msgs.order(ByteOrder.LITTLE_ENDIAN);
            // dataspace (type 1) simple 1D
            putMsg(msgs, 1, dsSimple1d(payload.length));
            // datatype (type 3) uint8
            putMsg(msgs, 3, new byte[]{0x00, 0x00, 0x00, 0x00, 1, 0, 0, 0});
            // layout (type 8) v3 contiguous
            ByteBuffer lay = ByteBuffer.allocate(18).order(ByteOrder.LITTLE_ENDIAN);
            lay.put((byte) 3);
            lay.put((byte) 1);
            lay.putLong(dataAddr);
            lay.putLong(payload.length);
            putMsg(msgs, 8, java.util.Arrays.copyOf(lay.array(), 18));
            int msgBytes = msgs.position();

            b.position(ohdr);
            b.put((byte) 1); // version
            b.put((byte) 0);
            b.putShort((short) 3);
            b.putInt(1); // ref count
            b.putInt(msgBytes);
            b.put(msgs.array(), 0, msgBytes);
            while (b.position() < dataAddr) b.put((byte) 0);
            b.put(payload);
            while (b.position() < trailer) b.put((byte) 0);
            b.put("DSLVJSON".getBytes(StandardCharsets.US_ASCII));
            b.putInt(jsonAttr.length);
            b.put(jsonAttr);
            int eof = b.position();
            b.position(40);
            b.putLong(eof);
            b.position(eof);
            byte[] out = new byte[eof];
            b.position(0);
            b.get(out);
            return out;
        }

        private static byte[] dsSimple1d(int n) {
            ByteBuffer d = ByteBuffer.allocate(24).order(ByteOrder.LITTLE_ENDIAN);
            d.put((byte) 1); // version
            d.put((byte) 1); // ndims
            d.put((byte) 0);
            d.put(new byte[5]);
            d.putLong(n);
            return d.array();
        }

        private static void putMsg(ByteBuffer msgs, int type, byte[] data) {
            int pad = (8 - ((data.length) % 8)) % 8;
            msgs.putShort((short) type);
            msgs.putShort((short) data.length);
            msgs.put((byte) 0);
            msgs.put(new byte[3]);
            msgs.put(data);
            for (int i = 0; i < pad; i++) msgs.put((byte) 0);
        }
    }
}
