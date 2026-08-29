package labs.dynogator.dslvzpdi;

import android.Manifest;
import android.annotation.SuppressLint;
import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.content.res.AssetManager;
import android.hardware.usb.UsbManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.view.View;
import android.view.WindowManager;
import android.webkit.CookieManager;
import android.webkit.GeolocationPermissions;
import android.webkit.PermissionRequest;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.net.URLDecoder;
import java.util.HashMap;
import java.util.Map;

public class MainActivity extends Activity {
    static final String APP_ORIGIN = "https://appassets.androidplatform.net";
    static final String START_URL = APP_ORIGIN + "/native.html";

    private WebView webView;
    private NativeHost nativeHost;

    @Override
    @SuppressLint("SetJavaScriptEnabled")
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        getWindow().setStatusBarColor(0xFF0A0C0F);
        getWindow().setNavigationBarColor(0xFF0A0C0F);
        if (Build.VERSION.SDK_INT >= 30) {
            getWindow().setDecorFitsSystemWindows(true);
        }

        webView = new WebView(this);
        webView.setBackgroundColor(0xFF0A0C0F);
        webView.setOverScrollMode(View.OVER_SCROLL_NEVER);

        WebSettings s = webView.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);
        s.setAllowFileAccess(true);
        s.setAllowContentAccess(true);
        s.setAllowFileAccessFromFileURLs(false);
        s.setAllowUniversalAccessFromFileURLs(false);
        s.setMediaPlaybackRequiresUserGesture(false);
        s.setLoadWithOverviewMode(true);
        s.setUseWideViewPort(true);
        s.setSupportZoom(false);
        s.setBuiltInZoomControls(false);
        s.setDisplayZoomControls(false);
        s.setCacheMode(WebSettings.LOAD_DEFAULT);
        s.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        s.setGeolocationEnabled(true);
        s.setUserAgentString(s.getUserAgentString() + " DynoGatorLabs-DSLV-ZPDI/5.8.0");
        webView.setLayerType(View.LAYER_TYPE_HARDWARE, null);
        if (Build.VERSION.SDK_INT >= 33) {
            s.setAlgorithmicDarkeningAllowed(false);
        }

        CookieManager cookies = CookieManager.getInstance();
        cookies.setAcceptCookie(true);
        cookies.setAcceptThirdPartyCookies(webView, true);

        nativeHost = new NativeHost(this);
        webView.addJavascriptInterface(nativeHost, "NativeHost");
        webView.addJavascriptInterface(nativeHost, "AlphaBridge");
        webView.setWebViewClient(new WwwClient(getAssets()));
        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onGeolocationPermissionsShowPrompt(String origin, GeolocationPermissions.Callback callback) {
                callback.invoke(origin, true, false);
            }

            @Override
            public void onPermissionRequest(PermissionRequest request) {
                request.grant(request.getResources());
            }
        });

        setContentView(webView);
        requestLocation();
        maybeOpenAttachedUsb();
        maybeExecCliIntent(getIntent());
        webView.loadUrl(START_URL);
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        maybeOpenAttachedUsb();
        maybeExecCliIntent(intent);
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (nativeHost != null) nativeHost.sdr.autoConnect();
    }

    private void maybeOpenAttachedUsb() {
        if (nativeHost == null) return;
        if (UsbManager.ACTION_USB_DEVICE_ATTACHED.equals(getIntent() != null ? getIntent().getAction() : "")) {
            nativeHost.sdr.open("hackrf");
        }
    }

    private void maybeExecCliIntent(Intent intent) {
        if (nativeHost == null || intent == null) return;
        String cmd = intent.getStringExtra("cmd");
        if (cmd == null) cmd = intent.getStringExtra("dslv");
        Uri u = intent.getData();
        if ((cmd == null || cmd.isEmpty()) && u != null && "dslv".equals(u.getScheme())) {
            cmd = u.getQueryParameter("cmd");
            if (cmd == null || cmd.isEmpty()) {
                String host = u.getHost();
                String p = u.getPath();
                cmd = (host == null ? "" : host) + (p == null ? "" : p.replace('/', ' '));
                cmd = cmd.trim();
            }
        }
        if (cmd != null && !cmd.isEmpty()) {
            try {
                nativeHost.cli.exec(cmd);
            } catch (Exception ignored) {
            }
        }
    }

    private void requestLocation() {
        if (checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{
                    Manifest.permission.ACCESS_FINE_LOCATION,
                    Manifest.permission.ACCESS_COARSE_LOCATION
            }, 41);
        }
    }

    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) {
            webView.goBack();
            return;
        }
        moveTaskToBack(true);
    }

    @Override
    protected void onDestroy() {
        if (nativeHost != null) {
            nativeHost.shutdown();
            nativeHost = null;
        }
        if (webView != null) {
            webView.loadUrl("about:blank");
            webView.destroy();
            webView = null;
        }
        super.onDestroy();
    }

    static final class WwwClient extends WebViewClient {
        private final AssetManager assets;
        private static final byte[] EMPTY = new byte[0];

        WwwClient(AssetManager assets) {
            this.assets = assets;
        }

        @Override
        public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
            Uri uri = request.getUrl();
            if (uri == null) return super.shouldInterceptRequest(view, request);
            String host = uri.getHost();
            if (host == null || !host.equals("appassets.androidplatform.net")) {
                return super.shouldInterceptRequest(view, request);
            }
            return serve(uri);
        }

        private WebResourceResponse serve(Uri uri) {
            String path = uri.getPath();
            if (path == null || path.isEmpty() || "/".equals(path)) path = "/native.html";
            try {
                path = URLDecoder.decode(path, "UTF-8");
            } catch (Exception ignored) {
            }
            if (path.contains("..")) return notFound();
            if (path.startsWith("/")) path = path.substring(1);
            String assetPath = "www/" + path;
            try {
                InputStream in = assets.open(assetPath);
                String mime = mimeOf(path);
                Map<String, String> headers = new HashMap<>();
                headers.put("Cache-Control", "no-cache");
                headers.put("Access-Control-Allow-Origin", "*");
                String encoding = (mime.startsWith("text/") || mime.contains("javascript") || mime.contains("json") || mime.contains("svg"))
                        ? "utf-8" : null;
                return new WebResourceResponse(mime, encoding, 200, "OK", headers, in);
            } catch (IOException e) {
                return notFound();
            }
        }

        private WebResourceResponse notFound() {
            Map<String, String> headers = new HashMap<>();
            headers.put("Content-Type", "text/plain");
            return new WebResourceResponse(
                    "text/plain",
                    "utf-8",
                    404,
                    "Not Found",
                    headers,
                    new ByteArrayInputStream(EMPTY));
        }

        private static String mimeOf(String path) {
            String p = path.toLowerCase();
            if (p.endsWith(".html")) return "text/html";
            if (p.endsWith(".js") || p.endsWith(".mjs")) return "text/javascript";
            if (p.endsWith(".css")) return "text/css";
            if (p.endsWith(".json") || p.endsWith(".webmanifest")) return "application/json";
            if (p.endsWith(".svg")) return "image/svg+xml";
            if (p.endsWith(".png")) return "image/png";
            if (p.endsWith(".jpg") || p.endsWith(".jpeg")) return "image/jpeg";
            if (p.endsWith(".webp")) return "image/webp";
            if (p.endsWith(".gif")) return "image/gif";
            if (p.endsWith(".woff2")) return "font/woff2";
            if (p.endsWith(".woff")) return "font/woff";
            if (p.endsWith(".ttf")) return "font/ttf";
            if (p.endsWith(".ico")) return "image/x-icon";
            if (p.endsWith(".wasm")) return "application/wasm";
            if (p.endsWith(".map")) return "application/json";
            return "application/octet-stream";
        }
    }
}
