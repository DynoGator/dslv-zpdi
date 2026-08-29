package labs.dynogator.dslvzpdi;

import android.content.ContentProvider;
import android.content.ContentValues;
import android.database.Cursor;
import android.database.MatrixCursor;
import android.net.Uri;
import android.os.Bundle;

import org.json.JSONObject;

/**
 * Termux / debian:  content call --uri content://labs.dynogator.dslvzpdi.cli --method exec --arg 'sdr tune 98.1'
 */
public final class DslvCliProvider extends ContentProvider {
    static final String AUTH = "labs.dynogator.dslvzpdi.cli";

    @Override
    public boolean onCreate() {
        return true;
    }

    @Override
    public Bundle call(String method, String arg, Bundle extras) {
        Bundle b = new Bundle();
        NativeHost h = NativeHost.INSTANCE;
        if (h == null || h.cli == null) {
            b.putString("result", "{\"ok\":false,\"error\":\"DSLV-ZPDI not running\"}");
            b.putString("text", "Open DSLV-ZPDI, then retry.");
            return b;
        }
        String cmd = arg;
        if ((cmd == null || cmd.isEmpty()) && extras != null) cmd = extras.getString("cmd", extras.getString("arg"));
        if ("tools".equals(method)) cmd = "tools";
        if ("help".equals(method)) cmd = "help";
        if ("status".equals(method)) cmd = "status --json";
        JSONObject r = h.cli.exec(cmd == null ? "help" : cmd);
        b.putString("result", r.toString());
        b.putString("text", r.optString("text"));
        b.putBoolean("ok", r.optBoolean("ok", true));
        return b;
    }

    @Override
    public Cursor query(Uri uri, String[] projection, String selection, String[] selectionArgs, String sortOrder) {
        String cmd = uri.getLastPathSegment();
        if (cmd == null || "cli".equals(cmd) || "exec".equals(cmd)) {
            cmd = selection != null ? selection : "help";
        } else {
            cmd = cmd.replace('/', ' ');
        }
        if (selectionArgs != null && selectionArgs.length > 0) cmd = selectionArgs[0];
        NativeHost h = NativeHost.INSTANCE;
        MatrixCursor c = new MatrixCursor(new String[]{"ok", "text", "json"});
        if (h == null || h.cli == null) {
            c.addRow(new Object[]{"false", "DSLV-ZPDI not running", "{\"ok\":false}"});
            return c;
        }
        JSONObject r = h.cli.exec(cmd);
        c.addRow(new Object[]{r.optBoolean("ok", true) ? "true" : "false", r.optString("text"), r.toString()});
        return c;
    }

    @Override
    public String getType(Uri uri) {
        return "vnd.android.cursor.item/vnd.labs.dynogator.dslvzpdi.cli";
    }

    @Override
    public Uri insert(Uri uri, ContentValues values) {
        return null;
    }

    @Override
    public int delete(Uri uri, String selection, String[] selectionArgs) {
        return 0;
    }

    @Override
    public int update(Uri uri, ContentValues values, String selection, String[] selectionArgs) {
        return 0;
    }
}
