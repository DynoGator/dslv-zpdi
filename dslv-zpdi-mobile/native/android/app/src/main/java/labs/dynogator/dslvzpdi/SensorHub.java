package labs.dynogator.dslvzpdi;

import android.Manifest;
import android.content.Context;
import android.content.pm.PackageManager;
import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;
import android.location.Location;
import android.location.LocationListener;
import android.location.LocationManager;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;

import org.json.JSONArray;
import org.json.JSONObject;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Locale;

/**
 * Pixel 9 Pro XL onboard sensors at SENSOR_DELAY_GAME (~50 Hz).
 * No HIGH_SAMPLING_RATE. SPEC-016 hardware_tier=2.
 */
public final class SensorHub implements SensorEventListener, LocationListener {
    private final Context ctx;
    private final SensorManager sm;
    private final LocationManager lm;
    private final Handler main = new Handler(Looper.getMainLooper());
    private final Object lock = new Object();

    private float ax, ay, az;
    private float gx, gy, gz;
    private float mx, my, mz;
    private float pressureHpa = Float.NaN;
    private float lightLux = Float.NaN;
    private float tempC = Float.NaN;
    private float headingDeg;
    private double lat = Double.NaN, lon = Double.NaN, alt = Double.NaN, accM = Double.NaN;
    private boolean magOk, accOk, gyroOk, baroOk, locOk;
    private volatile boolean running;

    SensorHub(Context ctx) {
        this.ctx = ctx.getApplicationContext();
        this.sm = (SensorManager) ctx.getSystemService(Context.SENSOR_SERVICE);
        this.lm = (LocationManager) ctx.getSystemService(Context.LOCATION_SERVICE);
        mx = 12.4f;
        my = -38.2f;
        mz = 31.6f;
    }

    void start() {
        if (running) return;
        running = true;
        main.post(() -> {
            listen(Sensor.TYPE_ACCELEROMETER);
            listen(Sensor.TYPE_GYROSCOPE);
            listen(Sensor.TYPE_MAGNETIC_FIELD);
            listen(Sensor.TYPE_PRESSURE);
            listen(Sensor.TYPE_LIGHT);
            listen(Sensor.TYPE_AMBIENT_TEMPERATURE);
            listen(Sensor.TYPE_ROTATION_VECTOR);
            listen(Sensor.TYPE_GRAVITY);
            startGps();
        });
    }

    void stop() {
        running = false;
        try {
            sm.unregisterListener(this);
        } catch (Exception ignored) {
        }
        try {
            lm.removeUpdates(this);
        } catch (Exception ignored) {
        }
    }

    private void listen(int type) {
        Sensor s = sm.getDefaultSensor(type);
        if (s != null) sm.registerListener(this, s, SensorManager.SENSOR_DELAY_GAME);
    }

    private void startGps() {
        if (ctx.checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION)
                != PackageManager.PERMISSION_GRANTED) {
            return;
        }
        try {
            lm.requestLocationUpdates(LocationManager.GPS_PROVIDER, 1000, 0, this, Looper.getMainLooper());
        } catch (Exception ignored) {
        }
        try {
            lm.requestLocationUpdates(LocationManager.NETWORK_PROVIDER, 2000, 0, this, Looper.getMainLooper());
        } catch (Exception ignored) {
        }
        try {
            Location last = lm.getLastKnownLocation(LocationManager.GPS_PROVIDER);
            if (last != null) onLocationChanged(last);
        } catch (Exception ignored) {
        }
    }

    @Override
    public void onSensorChanged(SensorEvent e) {
        synchronized (lock) {
            switch (e.sensor.getType()) {
                case Sensor.TYPE_ACCELEROMETER:
                    ax = e.values[0];
                    ay = e.values[1];
                    az = e.values[2];
                    accOk = true;
                    break;
                case Sensor.TYPE_GYROSCOPE:
                    gx = e.values[0];
                    gy = e.values[1];
                    gz = e.values[2];
                    gyroOk = true;
                    break;
                case Sensor.TYPE_MAGNETIC_FIELD:
                    mx = e.values[0];
                    my = e.values[1];
                    mz = e.values[2];
                    magOk = true;
                    headingDeg = heading(mx, my);
                    break;
                case Sensor.TYPE_PRESSURE:
                    pressureHpa = e.values[0];
                    baroOk = true;
                    break;
                case Sensor.TYPE_LIGHT:
                    lightLux = e.values[0];
                    break;
                case Sensor.TYPE_AMBIENT_TEMPERATURE:
                    tempC = e.values[0];
                    break;
                case Sensor.TYPE_ROTATION_VECTOR: {
                    float[] r = new float[9];
                    float[] ori = new float[3];
                    SensorManager.getRotationMatrixFromVector(r, e.values);
                    SensorManager.getOrientation(r, ori);
                    headingDeg = (float) ((Math.toDegrees(ori[0]) + 360.0) % 360.0);
                    break;
                }
                default:
                    break;
            }
        }
    }

    @Override
    public void onAccuracyChanged(Sensor sensor, int accuracy) {
    }

    @Override
    public void onLocationChanged(Location loc) {
        synchronized (lock) {
            lat = loc.getLatitude();
            lon = loc.getLongitude();
            alt = loc.hasAltitude() ? loc.getAltitude() : Double.NaN;
            accM = loc.hasAccuracy() ? loc.getAccuracy() : Double.NaN;
            locOk = true;
        }
    }

    @Override
    @Deprecated
    public void onStatusChanged(String provider, int status, Bundle extras) {
    }

    @Override
    public void onProviderEnabled(String provider) {
    }

    @Override
    public void onProviderDisabled(String provider) {
    }

    JSONObject snapshot() {
        JSONObject o = new JSONObject();
        synchronized (lock) {
            float magAbs = (float) Math.hypot(mx, Math.hypot(my, mz));
            try {
                o.put("available", magOk || accOk || locOk);
                o.put("hardwareTier", 2);
                o.put("magUt", arr(mx, my, mz));
                o.put("magAbs", magAbs);
                o.put("headingDeg", headingDeg);
                o.put("accMs2", arr(ax, ay, az));
                o.put("gyroRads", arr(gx, gy, gz));
                putOpt(o, "lat", lat);
                putOpt(o, "lon", lon);
                putOpt(o, "alt", alt);
                putOpt(o, "accM", accM);
                if (!Float.isNaN(pressureHpa)) o.put("baroHpa", pressureHpa);
                else o.put("baroHpa", JSONObject.NULL);
                if (!Float.isNaN(lightLux)) o.put("lightLux", lightLux);
                else o.put("lightLux", JSONObject.NULL);
                if (!Float.isNaN(tempC)) o.put("tempC", tempC);
                else o.put("tempC", JSONObject.NULL);
                o.put("gpsLock", locOk && !Double.isNaN(lat));
                o.put("magOk", magOk);
                o.put("accOk", accOk);
                o.put("gyroOk", gyroOk);
                o.put("baroOk", baroOk);
                o.put("cameraHash", attestHash());
                o.put("trustScore", trust(magAbs));
                o.put("timestampUtc", System.currentTimeMillis() / 1000.0);
            } catch (Exception ignored) {
            }
        }
        return o;
    }

    float[] imuRow() {
        synchronized (lock) {
            return new float[]{
                    mx, my, mz, ax, ay, az, gx, gy, gz,
                    Float.isNaN(pressureHpa) ? 0 : pressureHpa,
                    (float) (Double.isNaN(lat) ? 0 : lat),
                    (float) (Double.isNaN(lon) ? 0 : lon),
                    (float) (Double.isNaN(alt) ? 0 : alt),
                    headingDeg,
                    Float.isNaN(lightLux) ? 0 : lightLux,
                    Float.isNaN(tempC) ? 0 : tempC
            };
        }
    }

    private double trust(float magAbs) {
        double t = 1.0;
        if (!locOk) t -= 0.3;
        else if (!Double.isNaN(accM) && accM > 50) t -= 0.2;
        if (!magOk) t -= 0.2;
        else if (magAbs < 25 || magAbs > 65) t -= 0.15;
        if (!baroOk) t -= 0.05;
        return Math.max(0, Math.min(1, t));
    }

    private String attestHash() {
        String s;
        synchronized (lock) {
            s = String.format(Locale.US, "sns:%.3f,%.3f,%.3f|%.5f,%.5f|%d",
                    mx, my, mz,
                    Double.isNaN(lat) ? 0 : lat,
                    Double.isNaN(lon) ? 0 : lon,
                    System.currentTimeMillis() / 1000);
        }
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            byte[] d = md.digest(s.getBytes(StandardCharsets.UTF_8));
            return Blake2b.hex(d).substring(0, 12);
        } catch (Exception e) {
            return "000000000000";
        }
    }

    private static float heading(float x, float y) {
        double d = Math.toDegrees(Math.atan2(y, x));
        return (float) ((d + 360.0) % 360.0);
    }

    private static JSONArray arr(float a, float b, float c) {
        JSONArray x = new JSONArray();
        try {
            x.put(a);
            x.put(b);
            x.put(c);
        } catch (Exception ignored) {
        }
        return x;
    }

    private static void putOpt(JSONObject o, String k, double v) throws Exception {
        if (Double.isNaN(v)) o.put(k, JSONObject.NULL);
        else o.put(k, v);
    }
}
