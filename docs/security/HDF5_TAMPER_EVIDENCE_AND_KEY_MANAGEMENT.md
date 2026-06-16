# HDF5 Tamper-Evidence and Key Management

## Terminology

DSLV-ZPDI produces **cryptographically authenticated**, **tamper-evident**,
**hash-verified**, **manifest-authenticated**, **chain-of-custody protected**
HDF5 data products.

Do not describe the files as "tamper-proof", "immutable", "unalterable", or
"impossible to modify". A file can always be altered; the objective is to make
unauthorized alteration reliably detectable.

## Protections

### Per-Event Protections

- `content_sha256`: SHA-256 over canonical event content.
- `event_payload_sha256`: SHA-256 over the ingestion payload.
- `previous_event_chain_sha256`: Hash of the previous event in the chain.
- `event_chain_sha256`: Hash chaining all prior evidence.
- `hmac_sha256`: HMAC-SHA256 over the attestation dictionary.

### File-Level Protections

- Atomic finalization: files are written as `.h5.partial`, verified, then
  atomically renamed to `.h5`.
- Detached SHA-256 record: `<filename>.h5.sha256`.
- Detached status record: `<filename>.status.json`.

### Key Management

Production key sources (in resolution order):

1. Root-owned file `/etc/dslv-zpdi/hmac.key` (mode 0600).
2. Environment variable `DSLV_HMAC_KEY_FILE` pointing to a key file.
3. systemd `LoadCredential=hmac_key`.

Development key is only allowed when `allow_development_key=True` or a
`DevelopmentKeyProvider` is explicitly constructed with simulator acknowledgement.

## Prohibitions

- Never commit a production key to Git.
- Never print key material.
- Never include key material in exceptions or HDF5 metadata.
- Never use the development key in field mode.

## Verification

```bash
dslv-zpdi-verify capture.h5 --deep
```

Exit codes:

- 0 valid
- 1 integrity failure
- 2 missing required artifact
- 3 unsupported schema
- 4 key unavailable
- 5 operational error
