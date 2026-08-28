# DSLV-ZPDI Pixel C2 (native Android)

Canonical native command dashboard for the Pixel 9 Pro XL.

- **Package:** `labs.dynogator.dslvzpdi`
- **Version:** 5.7.0
- **APK:** `public/releases/DynoGatorLabs-DSLV-ZPDI-5.7.0.apk`
- **Telemetry:** `http://127.0.0.1:8777/telemetry`
- **C2 / CLI:** `http://127.0.0.1:8444/` (`dslv` in Termux)

This tree replaces the previous Capacitor PWA. Source of truth was merged from
[DynoGator/scarlet-crisp-orbit-glade](https://github.com/DynoGator/scarlet-crisp-orbit-glade)
(which already contained [DynoGator/dslv-zpdi_android](https://github.com/DynoGator/dslv-zpdi_android)).

## Sideload (GrapheneOS)

1. Settings → Apps → Special app access → Install unknown apps → Termux → Allow.
2. Open `public/releases/DynoGatorLabs-DSLV-ZPDI-5.7.0.apk` (or Download/).
3. Grant location / nearby devices / sensors when the app asks.
4. Termux → Settings → Allow external apps (already set on this node).
5. Keep the app unrestricted for battery so :8777 and :8444 stay up.

## Termux CLI

```sh
dslv status --json
dslv sensors --json
dslv help
```
