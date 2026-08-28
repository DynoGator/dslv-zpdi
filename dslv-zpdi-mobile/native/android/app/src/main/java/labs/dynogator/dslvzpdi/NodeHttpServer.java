package labs.dynogator.dslvzpdi;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.net.ServerSocket;
import java.net.Socket;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * Pixel telemetry :8777, C2 :8444, CLI /cli/* for Termux + proot Debian + agents.
 */
public final class NodeHttpServer {
    static final int TELEMETRY_PORT = 8777;
    static final int C2_PORT = 8444;

    private final NativeHost host;
    private final ExecutorService pool = Executors.newCachedThreadPool();
    private volatile boolean running;
    private ServerSocket telSock;
    private ServerSocket c2Sock;
    private volatile String telBind = "";
    private volatile String c2Bind = "";
    private volatile String lastErr = "";

    NodeHttpServer(NativeHost host) {
        this.host = host;
    }

    void start() {
        running = true;
        pool.execute(() -> bind("telemetry", TELEMETRY_PORT, true));
        pool.execute(() -> bind("c2", C2_PORT, false));
    }

    void stop() {
        running = false;
        closeQuiet(telSock);
        closeQuiet(c2Sock);
        pool.shutdownNow();
    }

    JSONObject status() {
        JSONObject o = new JSONObject();
        try {
            o.put("telemetry", TELEMETRY_PORT);
            o.put("c2", C2_PORT);
            o.put("telemetryBind", telBind);
            o.put("c2Bind", c2Bind);
            o.put("cli", "/cli/exec");
            o.put("error", lastErr);
            o.put("running", running);
        } catch (Exception ignored) {
        }
        return o;
    }

    private void bind(String name, int port, boolean telemetry) {
        try {
            ServerSocket ss = new ServerSocket();
            ss.setReuseAddress(true);
            ss.bind(new InetSocketAddress("0.0.0.0", port));
            if (telemetry) {
                telSock = ss;
                telBind = "0.0.0.0:" + port;
            } else {
                c2Sock = ss;
                c2Bind = "0.0.0.0:" + port;
            }
            while (running) {
                Socket s = ss.accept();
                pool.execute(() -> serve(s, telemetry));
            }
        } catch (Exception e) {
            lastErr = name + " " + e.getMessage();
        }
    }

    private void serve(Socket s, boolean telemetry) {
        try {
            s.setSoTimeout(4000);
            BufferedReader br = new BufferedReader(new InputStreamReader(s.getInputStream(), StandardCharsets.UTF_8));
            String line = br.readLine();
            if (line == null) return;
            String[] parts = line.split(" ");
            String method = parts.length > 0 ? parts[0] : "GET";
            String rawPath = parts.length > 1 ? parts[1] : "/";
            String query = "";
            String path = rawPath;
            int qi = rawPath.indexOf('?');
            if (qi >= 0) {
                query = rawPath.substring(qi + 1);
                path = rawPath.substring(0, qi);
            }
            int contentLen = 0;
            String header;
            while ((header = br.readLine()) != null && !header.isEmpty()) {
                if (header.toLowerCase().startsWith("content-length:")) {
                    try {
                        contentLen = Integer.parseInt(header.substring(15).trim());
                    } catch (Exception ignored) {
                    }
                }
            }
            char[] bodyBuf = new char[Math.max(0, Math.min(contentLen, 200_000))];
            int got = 0;
            while (got < bodyBuf.length) {
                int n = br.read(bodyBuf, got, bodyBuf.length - got);
                if (n < 0) break;
                got += n;
            }
            String body = new String(bodyBuf, 0, got);
            if ("OPTIONS".equals(method)) {
                write(s, 204, "text/plain", "");
                return;
            }
            String mime = "application/json";
            String resp;
            int code = 200;
            if (path.startsWith("/health")) {
                resp = "{\"ok\":true,\"node\":\"pixel-9-pro-xl\",\"tier\":2,\"cli\":true}";
            } else if (telemetry && (path.startsWith("/telemetry") || path.startsWith("/mobile_node_tier2") || path.equals("/"))) {
                resp = host.telemetryPayload();
            } else if (!telemetry && path.startsWith("/api/v1/status")) {
                resp = host.nodeStatus();
            } else if (!telemetry && path.startsWith("/api/v1/command") && "POST".equals(method)) {
                resp = host.c2(body);
                code = 202;
            } else if (path.startsWith("/api/status")) {
                resp = host.nodeStatus();
            } else if (path.equals("/cli/dslv") || path.equals("/cli/dslv.sh")) {
                mime = "text/x-shellscript";
                resp = CliAssets.DSLV_SH;
            } else if (path.equals("/cli/install.sh") || path.equals("/cli/install-debian.sh")) {
                mime = "text/x-shellscript";
                resp = CliAssets.INSTALL_SH;
            } else if (path.equals("/cli/AGENTS.md") || path.equals("/cli/README.md")) {
                mime = "text/markdown";
                resp = CliAssets.AGENTS_MD;
            } else if (path.startsWith("/cli/tools")) {
                resp = host.cli.tools().toString();
            } else if (path.startsWith("/cli/commands")) {
                resp = host.cli.catalog().toString();
            } else if (path.startsWith("/cli/help") || path.equals("/cli") || path.equals("/cli/")) {
                resp = host.cli.exec("help").toString();
            } else if (path.startsWith("/cli/exec") || path.startsWith("/cli/run")) {
                String cmd = queryParam(query, "cmd");
                if (cmd.isEmpty() && "POST".equals(method) && !body.isEmpty()) {
                    try {
                        JSONObject o = new JSONObject(body);
                        cmd = o.optString("cmd");
                        if (cmd.isEmpty() && o.has("argv")) {
                            StringBuilder b = new StringBuilder();
                            for (int i = 0; i < o.getJSONArray("argv").length(); i++) {
                                if (b.length() > 0) b.append(' ');
                                b.append(o.getJSONArray("argv").optString(i));
                            }
                            cmd = b.toString();
                        }
                    } catch (Exception e) {
                        cmd = body.trim();
                    }
                }
                if (cmd.isEmpty()) cmd = "help";
                if ("1".equals(queryParam(query, "json")) || "true".equals(queryParam(query, "json"))) {
                    if (!cmd.contains("--json")) cmd = cmd + " --json";
                }
                resp = host.cli.exec(cmd).toString();
            } else {
                code = 404;
                resp = "{\"ok\":false,\"error\":\"not found\"}";
            }
            write(s, code, mime, resp);
        } catch (Exception ignored) {
        } finally {
            try {
                s.close();
            } catch (Exception ignored) {
            }
        }
    }

    private static String queryParam(String query, String key) {
        if (query == null || query.isEmpty()) return "";
        for (String p : query.split("&")) {
            int eq = p.indexOf('=');
            String k = eq < 0 ? p : p.substring(0, eq);
            String v = eq < 0 ? "" : p.substring(eq + 1);
            try {
                k = URLDecoder.decode(k, "UTF-8");
                v = URLDecoder.decode(v, "UTF-8");
            } catch (Exception ignored) {
            }
            if (key.equals(k)) return v;
        }
        return "";
    }

    private static void write(Socket s, int code, String mime, String resp) throws Exception {
        byte[] bytes = resp.getBytes(StandardCharsets.UTF_8);
        String reason = code == 202 ? "Accepted" : code == 204 ? "No Content" : code == 404 ? "Not Found" : "OK";
        String hdr = "HTTP/1.1 " + code + " " + reason
                + "\r\nContent-Type: " + mime + "; charset=utf-8"
                + "\r\nAccess-Control-Allow-Origin: *"
                + "\r\nAccess-Control-Allow-Methods: GET, POST, OPTIONS"
                + "\r\nAccess-Control-Allow-Headers: Content-Type, Authorization"
                + "\r\nContent-Length: " + bytes.length
                + "\r\nConnection: close\r\n\r\n";
        OutputStream os = s.getOutputStream();
        os.write(hdr.getBytes(StandardCharsets.UTF_8));
        if (code != 204) os.write(bytes);
        os.flush();
    }

    private static void closeQuiet(ServerSocket ss) {
        try {
            if (ss != null) ss.close();
        } catch (Exception ignored) {
        }
    }
}
