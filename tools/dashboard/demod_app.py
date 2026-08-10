import os
import sys
import time
import tty
import termios
import select
import shutil
import argparse
import random
import subprocess
import threading
from typing import Any

import numpy as np

from rich.console import Console, Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.align import Align
from rich.progress import Progress, BarColumn, TextColumn

try:
    from dashboard.sdr_state import SDRStateManager
except ImportError:
    try:
        from sdr_state import SDRStateManager
    except ImportError:
        from tools.dashboard.sdr_state import SDRStateManager


class SDRAudioStreamer:
    """
    Real-time audio streaming engine for DSLV-ZPDI Demodulation.
    Generates simulated RF IQ data, performs FM/AM demodulation and squelch gating,
    and streams 48 kHz 16-bit mono PCM audio to an aplay/ffplay stdin subprocess.
    """
    def __init__(self, app):
        self.app = app
        self.running = False
        self.thread = None
        self.proc = None
        self.player_name = None
        self.sample_rate = 48000
        self.chunk_size = 2048
        self._detect_player()

    def _detect_player(self):
        if shutil.which("aplay"):
            self.player_cmd = ["aplay", "-t", "raw", "-r", str(self.sample_rate), "-c", "1", "-f", "S16_LE", "-q", "-"]
            self.player_name = "aplay (ALSA)"
        elif shutil.which("ffplay"):
            self.player_cmd = ["ffplay", "-nodisp", "-autoexit", "-f", "s16le", "-ar", str(self.sample_rate), "-ac", "1", "-i", "-"]
            self.player_name = "ffplay (FFmpeg)"
        elif shutil.which("pw-play"):
            self.player_cmd = ["pw-play", "--rate", str(self.sample_rate), "--channels", "1", "--format", "s16", "-"]
            self.player_name = "pw-play (PipeWire)"
        else:
            self.player_cmd = None
            self.player_name = None

    def start(self) -> bool:
        if self.running or not self.player_cmd:
            return False
        self.running = True
        try:
            self.proc = subprocess.Popen(
                self.player_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception:
            self.running = False
            return False

        self.thread = threading.Thread(target=self._stream_loop, daemon=True)
        self.thread.start()
        return True

    def stop(self):
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        if self.proc:
            try:
                if self.proc.stdin:
                    self.proc.stdin.close()
                self.proc.terminate()
                self.proc.wait(timeout=0.5)
            except Exception:
                pass
            self.proc = None

    def is_running(self) -> bool:
        return bool(self.running and self.proc and self.proc.poll() is None)

    def _stream_loop(self):
        phase = 0.0
        tone_phase = 0.0
        dt = 1.0 / self.sample_rate

        while self.running:
            if self.app.paused:
                pcm_data = np.zeros(self.chunk_size, dtype=np.int16)
            else:
                profile = getattr(self.app, "profile", "FM Radio")
                squelch_db = getattr(self.app, "squelch", -40.0)
                snr_db = getattr(self.app, "snr", 15.0)

                # Simulated RF IQ generation
                t = np.arange(self.chunk_size) * dt
                
                # Synthetic audio modulation signal (dual tone 440 Hz + 880 Hz)
                audio_mod = 0.5 * np.sin(2 * np.pi * 440.0 * (t + tone_phase)) + 0.3 * np.sin(2 * np.pi * 880.0 * (t + tone_phase))
                tone_phase = (tone_phase + self.chunk_size * dt) % 1.0

                noise_amp = max(0.01, 10.0 ** (-snr_db / 20.0))
                noise_i = np.random.normal(0, noise_amp, self.chunk_size)
                noise_q = np.random.normal(0, noise_amp, self.chunk_size)

                if "FM" in profile or "EMS" in profile:
                    freq_dev = 75000.0 if "Radio" in profile else 5000.0
                    inst_phase = phase + 2 * np.pi * freq_dev * np.cumsum(audio_mod) * dt
                    phase = inst_phase[-1] % (2 * np.pi)
                    iq_clean = np.exp(1j * inst_phase)
                    iq = iq_clean + (noise_i + 1j * noise_q)

                    # Demodulation: Polar discriminator
                    demod_raw = np.angle(iq[1:] * np.conj(iq[:-1]))
                    demod_raw = np.append(demod_raw, demod_raw[-1])
                    audio_out = demod_raw * (self.sample_rate / (2 * np.pi * freq_dev))
                elif "AM" in profile:
                    mod_depth = 0.8
                    carrier = np.exp(1j * 2 * np.pi * 1000.0 * t)
                    iq = (1.0 + mod_depth * audio_mod) * carrier + (noise_i + 1j * noise_q)
                    envelope = np.abs(iq)
                    audio_out = envelope - np.mean(envelope)
                else:
                    audio_out = 0.4 * np.sin(2 * np.pi * 1200.0 * (t + tone_phase))
                    iq = audio_out + 1j * audio_out

                # RSSI power estimate (dB)
                rssi_db = 10.0 * np.log10(np.mean(np.abs(iq) ** 2) + 1e-12)

                # Squelch Gate: mute audio if RSSI < squelch threshold
                if rssi_db < squelch_db or snr_db < 3.0:
                    audio_out = np.zeros_like(audio_out)

                audio_clipped = np.clip(audio_out, -1.0, 1.0)
                pcm_data = (audio_clipped * 24000.0).astype(np.int16)

            try:
                if self.proc and self.proc.stdin:
                    self.proc.stdin.write(pcm_data.tobytes())
                    self.proc.stdin.flush()
            except (BrokenPipeError, OSError):
                break

            time.sleep(self.chunk_size / self.sample_rate)


class DemodApp:
    def __init__(self, profile: str = "ADS-B", rx_only: bool = True, freq_hz: float = None, bw_hz: float = None, gain_db: float = None):
        self.console = Console()
        self.profile = profile
        self.rx_only = rx_only
        self.running = True
        self.paused = False
        
        self._setup_profile()
        
        # Override with synced values if provided
        if freq_hz is not None:
            self.freq_hz = freq_hz
        if bw_hz is not None:
            self.bandwidth_hz = bw_hz
        if gain_db is not None:
            self.gain_db = gain_db
            
        self.squelch = -40.0
        self.snr = 15.0
        
        # Advanced/Restricted capabilities
        self.restricted_unlocked = False
        self.pin_entry_mode = False
        self.pin_buffer = ""
        self.fox_hunt_active = False
        self.hopping_monitor_active = False
        self.vector_data = []

        self.logs = []
        self.decoded_data = []

        self.audio_streamer = None
        self.state_mgr = SDRStateManager(owner_name="demod_app.py")
        self.state_mgr.sync_from_disk(self)

        # Publish state to RAM disk
        self.state_mgr.write_state({
            "center_hz": self.freq_hz,
            "bandwidth_hz": self.bandwidth_hz,
            "gain_db": self.gain_db,
            "squelch_db": self.squelch,
            "demod_profile": self.profile,
            "mimo_tx": not self.rx_only,
            "paused": self.paused,
        })

        self._keyboard_mode = None
        self._orig_attrs = None

        self._setup_profile()

    def _setup_profile(self):
        profile_settings = {
            "ADS-B": {"freq": 1090000000, "bw": 2000000, "gain": 49.6},
            "FM Radio": {"freq": 98100000, "bw": 200000, "gain": 30.0},
            "AM Radio": {"freq": 1000000, "bw": 10000, "gain": 20.0},
            "EMS/Fire": {"freq": 154280000, "bw": 12500, "gain": 40.0},
            "Broadcast TV": {"freq": 473000000, "bw": 6000000, "gain": 35.0},
        }
        if self.profile in profile_settings:
            s = profile_settings[self.profile]
            self.freq_hz = s["freq"]
            self.bandwidth_hz = s["bw"]
            self.gain_db = s["gain"]

    def _enter_raw(self):
        if not sys.stdin.isatty():
            return
        fd = sys.stdin.fileno()
        self._orig_attrs = termios.tcgetattr(fd)
        tty.setcbreak(fd)
        self._keyboard_mode = fd

    def _exit_raw(self):
        if self._orig_attrs is not None and self._keyboard_mode is not None:
            termios.tcsetattr(self._keyboard_mode, termios.TCSADRAIN, self._orig_attrs)

    def _read_key(self) -> str | None:
        if not sys.stdin.isatty():
            return None
        r, _, _ = select.select([sys.stdin], [], [], 0.0)
        if not r:
            return None
        try:
            return sys.stdin.read(1)
        except Exception:
            return None

    def _generate_mock_data(self):
        if self.paused:
            return
            
        self.snr = random.uniform(5.0, 35.0)
        
        if random.random() < 0.1:
            self.logs.insert(0, f"[{time.strftime('%H:%M:%S')}] Signal locked on {self.freq_hz/1e6:.3f} MHz (SNR: {self.snr:.1f} dB)")
            
        if self.profile == "ADS-B" and random.random() < 0.3:
            icao = hex(random.randint(0x100000, 0xFFFFFF))[2:].upper()
            alt = random.randint(100, 400) * 100
            spd = random.randint(150, 500)
            self.decoded_data.insert(0, f"ICAO: {icao} | ALT: {alt}ft | SPD: {spd}kts")
        elif random.random() < 0.2:
            self.decoded_data.insert(0, f"Decoded frame at {time.strftime('%H:%M:%S.%f')[:-3]} - SNR: {self.snr:.1f} dB")
            
        if self.fox_hunt_active and random.random() < 0.4:
            bearing = random.randint(0, 359)
            dist = random.uniform(0.1, 5.0)
            self.vector_data.insert(0, f"TARGET AQUIRED -> TDOA Bearing: {bearing}° | Est Dist: {dist:.1f}km | RSSI: -{random.randint(30, 90)}dBm")
            if len(self.vector_data) > 10:
                self.vector_data = self.vector_data[:10]
            
        if len(self.logs) > 15:
            self.logs = self.logs[:15]
        if len(self.decoded_data) > 15:
            self.decoded_data = self.decoded_data[:15]

    def _build_layout(self) -> Layout:
        layout = Layout()
        try:
            _, term_rows = shutil.get_terminal_size()
        except Exception:
            term_rows = 30

        header_size = 3 if term_rows >= 20 else 1
        footer_size = 3 if term_rows >= 20 else 1

        layout.split_column(
            Layout(name="header", size=header_size),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=footer_size)
        )
        
        layout["main"].split_row(
            Layout(name="left_panel", ratio=1),
            Layout(name="right_panel", ratio=2)
        )
        
        if self.restricted_unlocked:
            layout["left_panel"].split_column(
                Layout(name="controls", ratio=4),
                Layout(name="restricted_controls", ratio=3),
                Layout(name="metrics", ratio=3),
                Layout(name="logs", ratio=4)
            )
            layout["right_panel"].split_column(
                Layout(name="visual", ratio=3),
                Layout(name="vector_data", ratio=2),
                Layout(name="data", ratio=2)
            )
        else:
            layout["left_panel"].split_column(
                Layout(name="controls", ratio=4),
                Layout(name="metrics", ratio=3),
                Layout(name="logs", ratio=4)
            )
            layout["right_panel"].split_column(
                Layout(name="visual", ratio=3),
                Layout(name="data", ratio=2)
            )
            
        return layout

    def _render(self) -> Layout:
        if hasattr(self, "state_mgr"):
            self.state_mgr.sync_from_disk(self)
        self._generate_mock_data()
        layout = self._build_layout()
        
        # Header
        mode_str = "RX ONLY (RESTRICTED)" if self.rx_only else "TX/RX MIMO ENABLED"
        mode_style = "bold bright_green" if self.rx_only else "bold bright_red blink"
        
        header_text = Text()
        header_text.append("▓▓ DSLV-ZPDI ADVANCED DEMODULATION INTERFACE ▓▓\n", style="bold bright_cyan")
        header_text.append(f"PROFILE: {self.profile} | MODE: ", style="bright_white")
        header_text.append(mode_str, style=mode_style)
        layout["header"].update(Panel(Align.center(header_text), style="bright_blue"))
        
        # Controls
        audio_active = bool(self.audio_streamer and self.audio_streamer.is_running())
        if audio_active:
            sink_name = getattr(self.audio_streamer, "player_name", "PCM Sink") or "PCM Sink"
            audio_status = f"[bold bright_green]🔊 STREAMING ({sink_name})[/]"
        else:
            audio_status = "[dim bright_black]🔇 MUTED (Press L)[/]"

        ctrl_table = Table.grid(padding=(0, 2))
        ctrl_table.add_column(style="bright_yellow")
        ctrl_table.add_column(style="bright_white")
        ctrl_table.add_row("[F] Frequency", f"{self.freq_hz/1e6:.3f} MHz")
        ctrl_table.add_row("[B] Bandwidth", f"{self.bandwidth_hz/1e6:.3f} MHz")
        ctrl_table.add_row("[G] Gain", f"{self.gain_db:.1f} dB")
        ctrl_table.add_row("[S] Squelch", f"{self.squelch:.1f} dB")
        ctrl_table.add_row("[L] Audio Output", audio_status)
        ctrl_table.add_row("[SPACE] Pause", "PAUSED" if self.paused else "ACTIVE")
        layout["controls"].update(Panel(ctrl_table, title="[bold bright_white]SDR CONTROLS", border_style="bright_blue"))
        
        if self.restricted_unlocked:
            restr_table = Table.grid(padding=(0, 2))
            restr_table.add_column(style="bold bright_red")
            restr_table.add_column(style="bright_white")
            restr_table.add_row("[T] MIMO TX", "ENABLED" if not self.rx_only else "DISABLED")
            restr_table.add_row("[V] Vector Hunt", "ACTIVE (TDOA/RSSI)" if self.fox_hunt_active else "OFF")
            restr_table.add_row("[H] Freq Hopping", "MONITORING" if self.hopping_monitor_active else "OFF")
            layout["restricted_controls"].update(Panel(restr_table, title="[bold bright_red]RESTRICTED SYSTEMS", border_style="bright_red"))
            
            vector_text = Text("\n".join(self.vector_data), style="bold bright_yellow")
            layout["vector_data"].update(Panel(vector_text, title="[bold bright_red]TARGET VECTORING (TDOA)", border_style="bright_red"))
        
        # Metrics
        metric_table = Table.grid(padding=(0, 2))
        metric_table.add_column(style="bright_cyan")
        metric_table.add_column()
        
        snr_bar = "█" * int(min(20, max(0, self.snr)) / 2) + "░" * (10 - int(min(20, max(0, self.snr)) / 2))
        snr_color = "bright_green" if self.snr > 15 else ("bright_yellow" if self.snr > 8 else "bright_red")
        
        metric_table.add_row("SNR", f"[{snr_color}]{snr_bar} {self.snr:.1f} dB[/]")
        metric_table.add_row("Lock", "[bold bright_green]LOCKED" if self.snr > 8 else "[bold bright_red]SEARCHING")
        metric_table.add_row("Data Rate", f"[{snr_color}]{max(0, (self.snr - 8) * 10):.1f} kbps[/]")
        layout["metrics"].update(Panel(metric_table, title="[bold bright_white]LIVE METRICS", border_style="bright_cyan"))
        
        # Logs
        log_text = Text("\n".join(self.logs), style="dim bright_white")
        layout["logs"].update(Panel(log_text, title="[bold bright_white]SYSTEM LOGS", border_style="bright_black"))
        
        # Visual (Spectrum mock)
        visual_text = Text()
        for i in range(12):
            line = ""
            for j in range(60):
                if not self.paused and self.snr > 10:
                    val = random.random() * (self.snr / 35.0)
                    if abs(j - 30) < 5:
                        val += 0.5
                    if self.hopping_monitor_active and random.random() < 0.05:
                        val += 0.8  # Random hopping spikes
                else:
                    val = random.random() * 0.2
                    
                if val > 0.8: char = "█"; color = "bright_red"
                elif val > 0.6: char = "▆"; color = "bright_yellow"
                elif val > 0.4: char = "▄"; color = "bright_green"
                elif val > 0.2: char = "▂"; color = "bright_cyan"
                else: char = " "; color = "dim bright_black"
                visual_text.append(char, style=color)
            visual_text.append("\n")
        layout["visual"].update(Panel(Align.center(visual_text, vertical="middle"), title="[bold bright_white]BASEBAND SPECTRUM", border_style="bright_green"))
        
        # Data
        data_text = Text("\n".join(self.decoded_data), style="bold bright_green")
        layout["data"].update(Panel(data_text, title="[bold bright_white]DECODED TELEMETRY", border_style="bright_magenta"))
        
        # Footer
        footer_text = Text()
        
        if self.pin_entry_mode:
            footer_text.append(f"RESTRICTED ACCESS: ENTER PIN -> {self.pin_buffer}█", style="bold bright_red blink")
        else:
            footer_text.append(f"[{time.strftime('%H:%M:%S UTC')}]  ", style="dim")
            if self.restricted_unlocked:
                footer_text.append("Q: Quit | S: Squelch | L: Listen | T: TX | V: Vector | H: Hopping", style="bold bright_yellow")
            else:
                footer_text.append("Q: Quit | S/s: Squelch ± | L: Listen On/Off | Space: Pause (Freq/Gain synced with Dashboard)", style="bold bright_white")
        
        layout["footer"].update(Panel(Align.center(footer_text), style="bright_black"))
        
        return layout

    def run(self):
        self._enter_raw()
        try:
            with Live(self._render(), screen=True, refresh_per_second=10) as live:
                while self.running:
                    key = self._read_key()
                    if key:
                        if self.pin_entry_mode:
                            if key in ('\n', '\r'):
                                if self.pin_buffer == "1988":
                                    self.restricted_unlocked = True
                                    self.logs.insert(0, "[SYSTEM] RESTRICTED CAPABILITIES UNLOCKED")
                                else:
                                    self.logs.insert(0, "[SYSTEM] ACCESS DENIED - INVALID PIN")
                                self.pin_entry_mode = False
                                self.pin_buffer = ""
                            elif key.isdigit():
                                self.pin_buffer += key
                            elif key in ('\x7f', '\b'): # Backspace
                                self.pin_buffer = self.pin_buffer[:-1]
                            elif key.lower() == 'q':
                                self.pin_entry_mode = False
                        else:
                            if key.lower() == 'q':
                                self.running = False
                                if self.audio_streamer:
                                    self.audio_streamer.stop()
                            elif key == ' ':
                                self.paused = not self.paused
                                if hasattr(self, "state_mgr"):
                                    self.state_mgr.update_key("paused", self.paused)
                            elif key == '\x18' or key == '*': # Ctrl+X or '*' used as triggers since Ctrl+8 is non-standard
                                self.pin_entry_mode = True
                                self.pin_buffer = ""
                            elif self.restricted_unlocked and (key == 't' or key == 'T'):
                                self.rx_only = not self.rx_only
                                if hasattr(self, "state_mgr"):
                                    self.state_mgr.update_key("mimo_tx", not self.rx_only)
                                self.logs.insert(0, f"[{time.strftime('%H:%M:%S')}] MIMO TX {'Disabled' if self.rx_only else 'ENABLED'}")
                            elif self.restricted_unlocked and (key == 'v' or key == 'V'):
                                self.fox_hunt_active = not self.fox_hunt_active
                                self.logs.insert(0, f"[{time.strftime('%H:%M:%S')}] Vector Fox Hunt {'ACTIVE' if self.fox_hunt_active else 'OFF'}")
                            elif self.restricted_unlocked and (key == 'h' or key == 'H'):
                                self.hopping_monitor_active = not self.hopping_monitor_active
                                self.logs.insert(0, f"[{time.strftime('%H:%M:%S')}] Freq Hopping Monitor {'ACTIVE' if self.hopping_monitor_active else 'OFF'}")
                            elif key == 'S':
                                self.squelch += 1.0
                                if hasattr(self, "state_mgr"):
                                    self.state_mgr.update_key("squelch_db", self.squelch)
                            elif key == 's':
                                self.squelch -= 1.0
                                if hasattr(self, "state_mgr"):
                                    self.state_mgr.update_key("squelch_db", self.squelch)
                            elif key == 'l' or key == 'L':
                                if self.audio_streamer and self.audio_streamer.is_running():
                                    self.audio_streamer.stop()
                                    self.audio_streamer = None
                                    self.logs.insert(0, f"[{time.strftime('%H:%M:%S')}] LISTEN MODE: OFF (Data decoding only)")
                                else:
                                    self.audio_streamer = SDRAudioStreamer(self)
                                    if self.audio_streamer.start():
                                        player_name = self.audio_streamer.player_name or "Audio Sink"
                                        self.logs.insert(0, f"[{time.strftime('%H:%M:%S')}] LISTEN MODE: ACTIVE (Streaming via {player_name})")
                                    else:
                                        self.audio_streamer = None
                                        self.logs.insert(0, f"[{time.strftime('%H:%M:%S')}] LISTEN MODE: FAILED (No supported audio sink found)")
                                if hasattr(self, "state_mgr"):
                                    self.state_mgr.update_key("audio_active", bool(self.audio_streamer and self.audio_streamer.is_running()))
                    
                    live.update(self._render())
                    time.sleep(0.1)
        finally:
            if self.audio_streamer:
                self.audio_streamer.stop()
            self._exit_raw()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="ADS-B", help="Initial demodulation profile")
    parser.add_argument("--tx", action="store_true", help="Enable TX (Warning: Restricted)")
    parser.add_argument("--freq", type=float, default=None, help="Sync frequency with dashboard")
    parser.add_argument("--bw", type=float, default=None, help="Sync bandwidth with dashboard")
    parser.add_argument("--gain", type=float, default=None, help="Sync gain with dashboard")
    args = parser.parse_args()
    
    app = DemodApp(profile=args.profile, rx_only=not args.tx, freq_hz=args.freq, bw_hz=args.bw, gain_db=args.gain)
    app.run()
