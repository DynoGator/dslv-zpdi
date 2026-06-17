# GitHub Discussions Guide

GitHub Discussions is enabled for `DynoGator/dslv-zpdi`.

## Requested Categories

GitHub created the default categories when Discussions were enabled. The API
available in this environment can create discussions but does not expose category
creation. A repository admin should add these project-specific categories in the
GitHub UI:

| Category | Type | Purpose |
| --- | --- | --- |
| Architecture decisions | Open-ended discussion | Propose and review SPEC, HAL, trust-boundary, and release-policy decisions. |
| Hardware troubleshooting | Q&A | Debug PlutoSDR+, LBE-1421, PPS, NMEA, Raspberry Pi, Pixel, power, thermal, and field-node issues. |
| Feature proposals | Open-ended discussion | Discuss planned capabilities before opening implementation issues. |

Until those categories exist, use:

- `Ideas` for feature proposals.
- `Q&A` for hardware troubleshooting.
- `General` for architecture discussions.

## Security Boundary

Do not use Discussions for vulnerabilities, credentials, exact private
coordinates, raw field captures, HMAC keys, device serials, or private RF
recordings. Use GitHub Private Vulnerability Reporting for security or
evidence-integrity issues.
