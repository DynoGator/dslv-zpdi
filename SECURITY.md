# Security Policy

~~~
   .============================================================.
   |  ROBCO INDUSTRIES (TM) TERMLINK PROTOCOL                   |
   |  =======================================================   |
   |  > AUTHORIZED PERSONNEL ONLY                               |
   |  > TIMING AUTHORITY: LBE-1421 GPSDO                        |
   |  > ATTEMPTS REMAINING: 3                                   |
   |  > HINT: THE PASSWORD IS NOT "hunter2"                     |
   |                                                            |
   |  UNAUTHORIZED ACCESS WILL BE LOGGED, TIMESTAMPED WITH      |
   |  ATOMIC PRECISION, AND MOCKED AT THE NEXT STANDUP.         |
   '============================================================'
~~~


DSLV-ZPDI is an institutional-grade RF/metrology field instrument. Data integrity
and evidence trustworthiness are first-class security properties, alongside the
usual software concerns.

## Supported Versions

Security fixes are applied to the latest released minor line on `main`.

| Version | Supported |
| ------- | --------- |
| 5.0.x   | Yes       |
| < 5.0   | No        |

## Reporting a Vulnerability

**Do not open a public issue for security vulnerabilities.**

Report privately via GitHub's **Private Vulnerability Reporting**:
`Security` tab → `Report a vulnerability` on
<https://github.com/DynoGator/dslv-zpdi>. If that is unavailable, email the
maintainer at the address in `pyproject.toml`.

Please include:

- Affected revision (`python -c "import dslv_zpdi; print(dslv_zpdi.__version__)"`)
  and commit SHA.
- Component (Layer 1 ingestion, Layer 2 core, Layer 3 telemetry, node receiver,
  dashboard, installer, tooling).
- Whether the issue affects simulator mode, hardware mode, or both.
- Reproduction steps and impact.

Expect an acknowledgement within 7 days and a remediation plan or status update
within 30 days.

## In Scope

- Authentication/integrity of the node receiver API (`/api/v1/ingest*`).
- HDF5 evidence-integrity controls (HMAC attestation, signed manifests, checksum
  branches).
- Trust-scoring and quarantine bypass for Tier 2 / mobile-node data.
- Credential or secret handling in installers, config, and tooling.
- Dependency vulnerabilities surfaced by Dependabot.
- Container vulnerabilities surfaced by the Docker/Trivy workflow.
- Code scanning findings surfaced by CodeQL.

## Out of Scope

- Findings that require physical access to the Tier 1 node or its GPSDO/SDR
  hardware.
- Theoretical-physics or measurement-methodology disagreements (these belong in
  the spec/discussion process, not the security tracker).
- Denial of service against a self-hosted single-node deployment.

## Handling Sensitive Data

When attaching logs or captures to a report, **redact** precise GPS coordinates,
device serials, Wi-Fi/hotspot credentials, and any HMAC keys. Never attach raw
`.h5`/`.hdf5` field captures to a public channel.

## 🍄 OPHIOCORDYCEPS DIRECTIVE (OpSec)

```text
       .-.
      (o.o)
      |=0=|
      |   |
      '~~~'
     /     \ 
    /       \
   /  \   /  \
  /    \ /    \
       | | 
       | |
      /   \
    .'     '.
   /         \
  '-----------'
```

*When the Ophiocordyceps Unilateralis spore takes hold, the host is no longer in control.*

Listen up, script kiddies. If you try to run an exploit against our Layer 3 Telemetry or breach the mainframe via the PiRepo hotspot, you will trigger our intrusion countermeasures. We will bypass your firewalls, reroute your IP through 7 proxies, and drop a zero-day payload right onto your SSD. Our architecture is an extension of the hive mind. We are legion. Expect us. Hack the planet! 🕶️💻
