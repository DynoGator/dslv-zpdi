# Pixel 9 Pro XL — Native C2 Node (v5.7.0)

**Device:** GrapheneOS Pixel 9 Pro XL
**Package:** `labs.dynogator.dslvzpdi`
**Role:** Tier-2 C2 master + onboard sensors. Alpha Pi remains Tier-1 timing/SDR/HDF5 authority.

## Architecture

The native APK replaces the old Termux:API sensor bridge, Python `zpdi_mobile_node.py` publisher, PWA on `:8085`, and Flask dashboard on `:8080`.

```
Pixel
├── APK (must stay running / unrestricted battery)
│   ├── SensorHub + USB SDR
│   ├── telemetry  0.0.0.0:8777   GET /telemetry  /health
│   ├── C2 / CLI   0.0.0.0:8444   /api/v1/status  POST /api/v1/command  /cli/*
│   └── WebView dashboard
├── Termux
│   ├── dslv CLI  → 127.0.0.1:8444
│   ├── Termux:Boot  ~/.termux/boot/90-dslv-pixel-c2.sh
│   └── allow-external-apps = true  (APK RUN_COMMAND)
└── Debian proot
    └── /usr/local/bin/dslv  (same CLI, for agents)
```

Sideload **is required**. GrapheneOS will not install this from Play. The signed APK is `dslv-zpdi-mobile/public/releases/DynoGatorLabs-DSLV-ZPDI-5.7.0.apk` (SHA-256 `01b39bf2a665940dedc6fcbf3106b7e8864d230d86ff95f06087921fe96f7cc2`).

Source merged from `DynoGator/scarlet-crisp-orbit-glade` (includes `DynoGator/dslv-zpdi_android` as ancestor commit `2206670`).

## Manual GrapheneOS steps (once)

1. Settings → Apps → Special app access → Install unknown apps → Termux → Allow.
2. Install the 5.7.0 APK (Download/ or `termux-open` that file).
3. Settings → Apps → DSLV-ZPDI → Battery → Unrestricted.
4. Grant Location, Sensors, Nearby devices, Notifications.
5. Settings → System → Developer options → Disable child process restrictions (Termux).
6. Open Termux:Boot once. Confirm `allow-external-apps = true` in `~/.termux/termux.properties`.
