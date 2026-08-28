package labs.dynogator.dslvzpdi;

import android.webkit.JavascriptInterface;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URI;
import java.net.URL;
import java.nio.charset.StandardCharsets;

/**
 * Synchronous LAN HTTP from the WebView. Hosted HTTPS pages cannot fetch
 * http://10.42.0.1:8080 (mixed content + CORS). The Pixel APK owns cleartext
 * and returns JSON so JS never issues a cross-origin fetch.
 */
public class AlphaBridge {
    private static final int TIMEOUT_MS = 2500;
    private static final int MAX_BODY = 900_000;

    @JavascriptInterface
    public boolean isNative() {
        return true;
    }

    @JavascriptInterface
    public String request(String method, String url, String body, String bearer) {
        HttpURLConnection conn = null;
        try {
            if (method == null || method.isEmpty()) method = "GET";
            method = method.toUpperCase();
            if (url == null || url.isEmpty()) {
                return err(0, "missing url");
            }
            URI uri = URI.create(url);
            String scheme = uri.getScheme();
            if (!"http".equalsIgnoreCase(scheme) && !"https".equalsIgnoreCase(scheme)) {
                return err(0, "only http/https allowed");
            }
            URL u = uri.toURL();
            conn = (HttpURLConnection) u.openConnection();
            conn.setConnectTimeout(TIMEOUT_MS);
            conn.setReadTimeout(TIMEOUT_MS);
            conn.setInstanceFollowRedirects(true);
            conn.setUseCaches(false);
            conn.setRequestMethod(method);
            conn.setRequestProperty("Accept", "application/json, text/plain, */*");
            conn.setRequestProperty("User-Agent", "DynoGatorLabs-DSLV-ZPDI/5.7.0 (Pixel; NativeHost)");
            if (bearer != null && !bearer.isEmpty()) {
                conn.setRequestProperty("Authorization", "Bearer " + bearer);
            }
            if ("POST".equals(method) || "PUT".equals(method) || "PATCH".equals(method)) {
                byte[] bytes = (body == null ? "" : body).getBytes(StandardCharsets.UTF_8);
                conn.setDoOutput(true);
                conn.setRequestProperty("Content-Type", "application/json; charset=utf-8");
                conn.setRequestProperty("Content-Length", Integer.toString(bytes.length));
                try (OutputStream os = conn.getOutputStream()) {
                    os.write(bytes);
                }
            }
            int status = conn.getResponseCode();
            InputStream stream = status >= 400 ? conn.getErrorStream() : conn.getInputStream();
            String payload = readLimited(stream);
            boolean ok = status >= 200 && status < 300;
            return envelope(ok, status, payload, ok ? null : ("HTTP " + status));
        } catch (Exception e) {
            String msg = e.getMessage();
            if (msg == null || msg.isEmpty()) msg = e.getClass().getSimpleName();
            return err(0, msg);
        } finally {
            if (conn != null) conn.disconnect();
        }
    }

    private static String readLimited(InputStream stream) throws Exception {
        if (stream == null) return "";
        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        byte[] buf = new byte[4096];
        int n;
        int total = 0;
        while ((n = stream.read(buf)) != -1) {
            total += n;
            if (total > MAX_BODY) break;
            bos.write(buf, 0, n);
        }
        stream.close();
        return bos.toString("UTF-8");
    }

    private static String err(int status, String message) {
        return envelope(false, status, null, message);
    }

    private static String envelope(boolean ok, int status, String payload, String error) {
        String dataField = "null";
        if (payload != null && !payload.isEmpty()) {
            String trimmed = payload.trim();
            if (trimmed.startsWith("{") || trimmed.startsWith("[")) {
                dataField = trimmed;
            } else {
                dataField = quote(payload);
            }
        }
        String errField = error == null ? "null" : quote(error);
        return "{\"ok\":" + ok + ",\"status\":" + status + ",\"data\":" + dataField + ",\"error\":" + errField + "}";
    }

    static String quote(String s) {
        if (s == null) return "null";
        StringBuilder sb = new StringBuilder(s.length() + 8);
        sb.append('"');
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            switch (c) {
                case '"':
                    sb.append("\\\"");
                    break;
                case '\\':
                    sb.append("\\\\");
                    break;
                case '\n':
                    sb.append("\\n");
                    break;
                case '\r':
                    sb.append("\\r");
                    break;
                case '\t':
                    sb.append("\\t");
                    break;
                default:
                    if (c < 0x20) sb.append(String.format("\\u%04x", (int) c));
                    else sb.append(c);
            }
        }
        sb.append('"');
        return sb.toString();
    }
}
