"""dslv-zpdi Tier-1 provenance verifier.

Opens the HDF5 stream in SWMR-read mode (so it is safe to run while the
daemon is writing), samples N rows, and re-hashes each payload to confirm
the stored SHA-256 digest matches.

The daemon hashes the canonical-JSON bytes *before* embedding the digest
into the in-memory body, and persists those pre-hash bytes verbatim in
the HDF5 `payload` column. Verification is therefore a direct hash of
the stored bytes — no field stripping required.

Exit codes:
  0  all sampled rows verified
  1  one or more rows failed verification
  2  dataset empty or unreadable
"""

from __future__ import annotations

import argparse
import hashlib
import os
import random
import sys
from pathlib import Path

import h5py

DEFAULT_HDF5_PATH = Path(os.environ.get("ZPDI_HDF5_PATH", "./data/zpdi_stream.h5"))
DATASET_NAME = "payloads"


def _recompute_digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _pick_indices(total: int, sample: int, mode: str, seed: int | None) -> list[int]:
    if sample >= total:
        return list(range(total))
    if mode == "sequential":
        # Evenly spaced across the dataset — better coverage than "first N".
        step = total / sample
        return [int(i * step) for i in range(sample)]
    rng = random.Random(seed)
    return sorted(rng.sample(range(total), sample))


def verify(path: Path, sample: int, mode: str, seed: int | None) -> int:
    if not path.exists():
        print(f"FAIL: HDF5 file not found at {path}", file=sys.stderr)
        return 2

    try:
        f = h5py.File(path, "r", libver="latest", swmr=True)
    except OSError as exc:
        # SWMR read can fail if the file was never opened SWMR-write; retry
        # without the flag so the verifier still works on a quiesced file.
        try:
            f = h5py.File(path, "r")
            print(f"note: opened without SWMR ({exc})", file=sys.stderr)
        except OSError as exc2:
            print(f"FAIL: cannot open {path}: {exc2}", file=sys.stderr)
            return 2

    with f:
        if DATASET_NAME not in f:
            print(f"FAIL: dataset '{DATASET_NAME}' missing", file=sys.stderr)
            return 2
        dset = f[DATASET_NAME]
        total = dset.shape[0]
        if total == 0:
            print("FAIL: dataset is empty — run the daemon first", file=sys.stderr)
            return 2

        indices = _pick_indices(total, sample, mode, seed)
        mismatches: list[tuple[int, str, str]] = []
        for idx in indices:
            row = dset[idx]
            stored = row["sha256"].decode("ascii")
            raw: bytes = row["payload"]
            recomputed = _recompute_digest(raw)
            if stored != recomputed:
                mismatches.append((idx, stored, recomputed))

    checked = len(indices)
    bad = len(mismatches)
    good = checked - bad
    pct = (good / checked * 100.0) if checked else 0.0

    print(f"dataset: {path}")
    print(f"rows total:    {total}")
    print(f"rows sampled:  {checked} ({mode})")
    print(f"rows verified: {good}")
    print(f"rows failed:   {bad}")
    print(f"integrity:     {pct:.4f}%")

    if bad:
        print("\nmismatches (idx, stored, recomputed):", file=sys.stderr)
        for idx, stored, recomputed in mismatches[:10]:
            print(f"  {idx}  stored={stored}  recomputed={recomputed}", file=sys.stderr)
        if bad > 10:
            print(f"  ... and {bad - 10} more", file=sys.stderr)
        print("RESULT: FAIL", file=sys.stderr)
        return 1

    print("RESULT: PASS")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Verify SHA-256 provenance of dslv-zpdi HDF5 stream")
    p.add_argument("--path", type=Path, default=DEFAULT_HDF5_PATH, help="HDF5 file path")
    p.add_argument("-n", "--sample", type=int, default=100, help="rows to sample (capped at dataset size)")
    p.add_argument("--mode", choices=("random", "sequential"), default="random",
                   help="sampling strategy (sequential = evenly spaced)")
    p.add_argument("--seed", type=int, default=None, help="seed for reproducible random sampling")
    args = p.parse_args(argv)
    return verify(args.path, args.sample, args.mode, args.seed)


if __name__ == "__main__":
    sys.exit(main())
