#!/usr/bin/env python3
"""
tools/lbe1421_simulator.py

A software simulator for the Leo Bodnar LBE-1421 GPSDO data output.
This provides a PTY emitting NMEA GGA sentences and a fake sysfs file for PPS edges,
allowing the DSLV-ZPDI pipeline to function in SIM MODE without physical timing hardware.
Useful for development pipelines or legacy SDR integration without a GPSDO attached.
"""

import os
import pty
import time
import threading

def calculate_checksum(sentence: str) -> str:
    """Calculate the NMEA checksum."""
    checksum = 0
    for char in sentence:
        checksum ^= ord(char)
    return f"{checksum:02X}"

def pps_thread(stop_event: threading.Event, assert_path: str):
    """Simulates the kernel PPS sysfs assert file."""
    seq = 0
    with open(assert_path, "w") as f:
        while not stop_event.is_set():
            now = time.time()
            sec = int(now)
            nsec = int((now - sec) * 1e9)
            # Format: <sec>.<nsec>#<sequence>\n
            line = f"{sec}.{nsec:09d}#{seq}\n"
            
            # Write to file and flush
            f.seek(0)
            f.write(line)
            f.flush()
            os.fsync(f.fileno())
            
            seq += 1
            # Sleep until next second
            next_sec = sec + 1
            time.sleep(max(0, next_sec - time.time()))

def nmea_thread(stop_event: threading.Event, master_fd: int):
    """Simulates the USB-C virtual serial port emitting NMEA GGA."""
    while not stop_event.is_set():
        now = time.gmtime()
        # $GNGGA,hhmmss.ss,llll.ll,a,yyyyy.yy,a,x,xx,x.x,x.x,M,x.x,M,x.x,xxxx*hh
        time_str = time.strftime("%H%M%S.00", now)
        # Fake coordinates, 1=GPS fix, 12 sats, 0.8 HDOP
        body = f"GNGGA,{time_str},5130.0000,N,00000.0000,E,1,12,0.8,50.0,M,,,,"
        checksum = calculate_checksum(body)
        sentence = f"${body}*{checksum}\r\n"
        
        try:
            os.write(master_fd, sentence.encode('ascii'))
        except OSError:
            break
            
        time.sleep(1.0)

def main():
    print("================================")
    print("===   LBE-1421 SIM MODE      ===")
    print("================================")
    
    # 1. Setup PTY for NMEA
    master_fd, slave_fd = pty.openpty()
    slave_name = os.ttyname(slave_fd)
    try:
        os.unlink("/tmp/sim_nmea")
    except OSError:
        pass
    os.symlink(slave_name, "/tmp/sim_nmea")
    print(f"[NMEA] Virtual serial port created at: {slave_name} -> /tmp/sim_nmea")
    print(f"       => Configure your node profile with: nmea_port='/tmp/sim_nmea'\n")

    # 2. Setup fake sysfs for PPS
    pps_dir = "/tmp/sim_pps0"
    os.makedirs(pps_dir, exist_ok=True)
    assert_path = os.path.join(pps_dir, "assert")
    print(f"[PPS]  Virtual sysfs assert file created at: {assert_path}")
    print(f"       => Configure your node profile with: pps_device='/tmp/sim_pps0'\n")
    
    stop_event = threading.Event()
    
    t_pps = threading.Thread(target=pps_thread, args=(stop_event, assert_path), daemon=True)
    t_nmea = threading.Thread(target=nmea_thread, args=(stop_event, master_fd), daemon=True)
    
    t_pps.start()
    t_nmea.start()
    
    print("Sim Mode active. The pipeline will now ingest simulated timing metadata.")
    print("Press Ctrl+C to destroy the simulator when physical hardware arrives.")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nDestroying Sim Mode...")
        stop_event.set()
        os.close(master_fd)
        os.close(slave_fd)
        print("Cleanup complete.")

if __name__ == "__main__":
    main()
