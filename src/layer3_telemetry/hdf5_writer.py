import h5py
import json
import hmac
import hashlib
import time
from pathlib import Path
from typing import Optional
from .router import DualStreamRouter, RoutingDecision

class HDF5Writer:
    """SPEC-007 — Institutional telemetry persistence."""
    def __init__(self, output_path: str = "./output/primary", hardware_enclave_key: Optional[bytes] = None):
        self.output_dir = Path(output_path)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.router = DualStreamRouter()
        self.key = hardware_enclave_key or b'dev_key_placeholder'
        self.current_file: Optional[h5py.File] = None
        self.file_rotation_size = 500 * 1024 * 1024 
        
    def ingest(self, json_payload: str) -> bool:
        """SPEC-007 — Process single packet through router."""
        decision = self.router.route(json_payload)
        if decision.stream == "PRIMARY":
            self._write_packet(decision.packet)
            return True
        elif decision.stream == "SECONDARY":
            self._log_secondary(json_payload, decision)
            return False
        return False
    
    def _write_packet(self, packet):
        """SPEC-007 — Write to HDF5 with cryptographic attestation."""
        if not self.current_file or self._file_size_exceeded():
            self._rotate_file()
        
        grp = self.current_file.create_group(f"event_{packet.payload_uuid}")
        grp.create_dataset("r_local", data=packet.r_local)
        grp.create_dataset("r_smooth", data=packet.r_smooth)
        grp.create_dataset("r_global", data=packet.r_global)
        grp.create_dataset("timestamp", data=packet.timestamp)
        
        meta = {
            "node_id": packet.node_id,
            "modality": packet.modality,
            "trust_state": packet.trust_state,
            "event_window_id": packet.event_window_id,
            "written_at": time.time(),
            "file_version": "3.2"
        }
        
        sig = hmac.new(self.key, json.dumps(meta).encode(), hashlib.sha256).hexdigest()
        meta['hmac_sha256'] = sig
        grp.attrs.update(meta)
    
    def _log_secondary(self, json_payload: str, decision: RoutingDecision):
        """SPEC-007 — Append to secondary exploratory log."""
        quarantine_path = self.output_dir.parent / "secondary" / "quarantine.jsonl"
        quarantine_path.parent.mkdir(parents=True, exist_ok=True)
        with open(quarantine_path, 'a') as f:
            log_entry = {
                "timestamp": time.time(),
                "reason": decision.reason,
                "trust_state": decision.trust_state,
                "payload_snippet": json_payload[:200] 
            }
            f.write(json.dumps(log_entry) + '\n')
    
    def _rotate_file(self):
        """SPEC-007 — Rotate HDF5 file to prevent unbounded growth."""
        if self.current_file:
            self.current_file.close()
        filename = f"dspl_zpdi_{time.strftime('%Y%m%d_%H%M%S')}.h5"
        filepath = self.output_dir / filename
        self.current_file = h5py.File(filepath, 'w')
        self.current_file.attrs['system'] = 'DSLV-ZPDI'
        self.current_file.attrs['rev'] = '3.2'
    
    def _file_size_exceeded(self) -> bool:
        """SPEC-007 — Size check for rotation."""
        if not self.current_file:
            return True
        return self.current_file.id.get_filesize() > self.file_rotation_size
    
    def close(self):
        """SPEC-007 — Safely close current HDF5 file."""
        if self.current_file:
            self.current_file.close()
