package labs.dynogator.dslvzpdi;

import android.app.PendingIntent;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;

import org.json.JSONObject;

import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;

/**
 * Termux RUN_COMMAND + package detect. GrapheneOS: queries manifest + RUN_COMMAND permission.
 * Operator must enable Termux → Settings → Allow external apps.
 */
final class TermuxBridge {
    static final String TERMUX = "com.termux";
    static final String RUN_SERVICE = "com.termux.app.RunCommandService";
    static final String ACTION_RUN = "com.termux.RUN_COMMAND";
    static final String ACTION_RESULT = "labs.dynogator.dslvzpdi.TERMUX_RESULT";
    static final String EXTRA_PATH = "com.termux.RUN_COMMAND_PATH";
    static final String EXTRA_ARGS = "com.termux.RUN_COMMAND_ARGUMENTS";
    static final String EXTRA_CWD = "com.termux.RUN_COMMAND_WORKDIR";
    static final String EXTRA_BG = "com.termux.RUN_COMMAND_BACKGROUND";
    static final String EXTRA_LABEL = "com.termux.RUN_COMMAND_COMMAND_LABEL";
    static final String EXTRA_SESSION = "com.termux.RUN_COMMAND_SESSION_ACTION";
    static final String EXTRA_PENDING = "com.termux.RUN_COMMAND_PENDING_INTENT";
    static final String BASH = "/data/data/com.termux/files/usr/bin/bash";
    static final String HOME = "/data/data/com.termux/files/home";

    private final Context ctx;
    private final AtomicReference<CountDownLatch> latch = new AtomicReference<>();
    private final AtomicReference<JSONObject> last = new AtomicReference<>();

    private final BroadcastReceiver resultRx = new BroadcastReceiver() {
        @Override
        public void onReceive(Context context, Intent intent) {
            JSONObject o = new JSONObject();
            try {
                Bundle b = intent.getExtras();
                o.put("ok", true);
                if (b != null) {
                    for (String k : b.keySet()) {
                        Object v = b.get(k);
                        o.put(k, v == null ? JSONObject.NULL : String.valueOf(v));
                    }
                    String stdout = b.getString("stdout", b.getString("com.termux.RUN_COMMAND_RESULT_STDOUT", ""));
                    String stderr = b.getString("stderr", b.getString("com.termux.RUN_COMMAND_RESULT_STDERR", ""));
                    o.put("stdout", stdout == null ? "" : stdout);
                    o.put("stderr", stderr == null ? "" : stderr);
                    o.put("text", ((stdout == null ? "" : stdout) + (stderr == null || stderr.isEmpty() ? "" : "\n" + stderr)).trim());
                }
            } catch (Exception ignored) {
            }
            last.set(o);
            CountDownLatch l = latch.get();
            if (l != null) l.countDown();
        }
    };

    TermuxBridge(Context ctx) {
        this.ctx = ctx.getApplicationContext();
        IntentFilter f = new IntentFilter(ACTION_RESULT);
        if (Build.VERSION.SDK_INT >= 33) {
            this.ctx.registerReceiver(resultRx, f, Context.RECEIVER_NOT_EXPORTED);
        } else {
            this.ctx.registerReceiver(resultRx, f);
        }
    }

    void shutdown() {
        try {
            ctx.unregisterReceiver(resultRx);
        } catch (Exception ignored) {
        }
    }

    boolean installed() {
        try {
            ctx.getPackageManager().getPackageInfo(TERMUX, 0);
            return true;
        } catch (PackageManager.NameNotFoundException e) {
            return false;
        }
    }

    JSONObject status() {
        JSONObject o = new JSONObject();
        try {
            boolean have = installed();
            o.put("ok", true);
            o.put("termux", have);
            o.put("debian", have);
            o.put("runCommand", have);
            o.put("hint", have
                    ? "Termux → Settings → Allow external apps, then CLI → Install aliases."
                    : "Install Termux (F-Droid / GitHub). GrapheneOS will prompt on first RUN_COMMAND.");
            o.put("install", "curl -fsS http://127.0.0.1:8444/cli/install.sh | sh");
            o.put("debianInstall", "curl -fsS http://127.0.0.1:8444/cli/install.sh | DEST=/usr/local/bin sh");
        } catch (Exception ignored) {
        }
        return o;
    }

    JSONObject run(String cmd, boolean wait) {
        JSONObject fail = new JSONObject();
        try {
            if (!installed()) {
                fail.put("ok", false);
                fail.put("error", "Termux not installed");
                fail.put("text", "Termux not installed. Sideload Termux, then retry.");
                return fail;
            }
            Intent i = new Intent();
            i.setClassName(TERMUX, RUN_SERVICE);
            i.setAction(ACTION_RUN);
            i.putExtra(EXTRA_PATH, BASH);
            i.putExtra("com.termux.RUN_COMMAND_SERVICE.EXTRA_COMMAND_PATH", BASH);
            i.putExtra(EXTRA_ARGS, new String[]{"-lc", cmd});
            i.putExtra("com.termux.RUN_COMMAND_SERVICE.EXTRA_ARGUMENTS", new String[]{"-lc", cmd});
            i.putExtra(EXTRA_CWD, HOME);
            i.putExtra("com.termux.RUN_COMMAND_SERVICE.EXTRA_WORKDIR", HOME);
            i.putExtra(EXTRA_BG, true);
            i.putExtra("com.termux.RUN_COMMAND_SERVICE.EXTRA_BACKGROUND", true);
            i.putExtra(EXTRA_LABEL, "dslv");
            i.putExtra("com.termux.RUN_COMMAND_SERVICE.EXTRA_COMMAND_LABEL", "dslv");
            i.putExtra(EXTRA_SESSION, "0");
            i.putExtra("com.termux.RUN_COMMAND_SERVICE.EXTRA_SESSION_ACTION", "0");
            Intent bounce = new Intent(ACTION_RESULT);
            bounce.setPackage(ctx.getPackageName());
            int flags = PendingIntent.FLAG_UPDATE_CURRENT;
            if (Build.VERSION.SDK_INT >= 31) flags |= PendingIntent.FLAG_MUTABLE;
            PendingIntent pi = PendingIntent.getBroadcast(ctx, (int) (System.currentTimeMillis() & 0xffff), bounce, flags);
            i.putExtra(EXTRA_PENDING, pi);
            i.putExtra("com.termux.RUN_COMMAND_SERVICE.EXTRA_PENDING_INTENT", pi);
            CountDownLatch l = new CountDownLatch(1);
            latch.set(l);
            last.set(null);
            ctx.startService(i);
            if (!wait) {
                JSONObject o = new JSONObject();
                o.put("ok", true);
                o.put("text", "Termux accepted: " + cmd);
                o.put("pending", true);
                return o;
            }
            boolean ok = l.await(20, TimeUnit.SECONDS);
            JSONObject got = last.get();
            if (got != null) return got;
            JSONObject o = new JSONObject();
            o.put("ok", ok);
            o.put("text", ok
                    ? "Termux ran with no captured stdout. Enable Allow external apps."
                    : "Termux did not return in 20s. Enable Allow external apps, keep Termux awake.");
            return o;
        } catch (SecurityException se) {
            try {
                fail.put("ok", false);
                fail.put("error", "RUN_COMMAND blocked");
                fail.put("text", "Grant com.termux.permission.RUN_COMMAND and Termux → Allow external apps.\n"
                        + "Manual: curl -fsS http://127.0.0.1:8444/cli/install.sh | sh");
            } catch (Exception ignored) {
            }
            return fail;
        } catch (Exception e) {
            try {
                fail.put("ok", false);
                fail.put("error", e.getMessage());
                fail.put("text", String.valueOf(e.getMessage()));
            } catch (Exception ignored) {
            }
            return fail;
        }
    }

    JSONObject installAliases() {
        String cmd = "curl -fsS http://127.0.0.1:8444/cli/install.sh | sh";
        JSONObject r = run(cmd, true);
        try {
            r.put("cmd", cmd);
        } catch (Exception ignored) {
        }
        return r;
    }

    JSONObject installDebian() {
        String cmd = "if command -v proot-distro >/dev/null; then "
                + "proot-distro login debian --shared-tmp -- bash -c "
                + "'curl -fsS http://127.0.0.1:8444/cli/install.sh | DEST=/usr/local/bin sh'; "
                + "else echo 'proot-distro not found. pkg install proot-distro && proot-distro install debian'; fi";
        return run(cmd, true);
    }
}
