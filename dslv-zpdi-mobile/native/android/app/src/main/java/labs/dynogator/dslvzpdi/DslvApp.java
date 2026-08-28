package labs.dynogator.dslvzpdi;

import android.app.Application;
import android.webkit.WebView;

public class DslvApp extends Application {
    @Override
    public void onCreate() {
        super.onCreate();
        WebView.setWebContentsDebuggingEnabled(false);
    }
}
