# RadonEye Pro RD200P — BLE GATT Map

**Date:** 2026-06-05
**Source:** ESPHome community reverse-engineering (FTLab/Ecosense RD200 family)
**Device:** EcoSense RadonEye Pro RD200P (NRPP CR-8306 / NRSB 31827)

---

## Discovered Services

| UUID | Type | Notes |
|------|------|-------|
| `00001523-1212-efde-1523-785feabcd123` | Primary Service | FTLab custom service |

## Characteristics

| UUID | Properties | Description |
|------|------------|-------------|
| `00001524-1212-efde-1523-785feabcd123` | Write | Command channel. Write `0x50` to request fresh radon data. |
| `00001525-1212-efde-1523-785feabcd123` | Read/Notify | Data channel. Returns 20-byte payload after `0x50` command. |
| `00001523-1212-efde-1523-785feabcd123` | Read | Possibly device info / serial (unconfirmed). |

## Data Payload (20 bytes, little-endian)

```
[0]     0x50    — Echo of command byte
[1]     0x10    — Status byte
[2:6]   float   — 10-minute moving average radon concentration (Bq/m³)
[6:10]  float   — Day average radon concentration (Bq/m³)
[10:14] float   — Month average radon concentration (Bq/m³)
[14:16] uint16  — Total pulse count (alpha detections)
[16:18] uint16  — 10-minute pulse count
[18:20] (padding / reserved)
```

## Conversion

- **Bq/m³ → pCi/L:** divide by 37.0
- Example: 148.0 Bq/m³ ≈ 4.00 pCi/L

## Connection Notes

- **Address type:** RANDOM (use `BLE_ADDR_TYPE_RANDOM` on ESP32; bleak auto-detects)
- **Scan filter:** Look for names containing "RadonEye", "RD200", or "FTLab"
- **Timing:** After writing `0x50`, wait ~500 ms before reading response
- **Retry:** Device may be busy if companion app is connected; retry after 2 s

## Hardware-Specific Variants

| Variant | Expected Name Prefix | Confirmed |
|---------|---------------------|-----------|
| RD200 (standard) | `RadonEye` | Yes (community) |
| RD200P (Pro) | `RadonEye` or `RD200P` | Assumed same protocol |
| RD200V (VOC) | Unknown | Not tested |

## Updates

When probing a new unit, run:

```python
from dslv_zpdi.layer1_ingestion.radoneye_ingestor import RadonEyeIngestor
import asyncio

ingestor = RadonEyeIngestor()
result = asyncio.run(ingestor.probe())
print(result)
```

Append discovered UUIDs to this document.
