import select
import sys
import termios
import threading
import time
import tty
from pathlib import Path

import cv2
from rich.align import Align
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

try:
    from dashboard.sdr_state import SDRStateManager
except ImportError:
    try:
        from sdr_state import SDRStateManager
    except ImportError:
        from tools.dashboard.sdr_state import SDRStateManager

class CamRecorder:
    def __init__(self, fps=1.0, out_dir="output/cam"):
        self.fps = fps
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.running = False
        self.thread = None
        self.cap = None
        self.frames_saved = 0

    def start(self):
        if self.running:
            return
        self.running = True
        self.cap = cv2.VideoCapture(0)
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
        if self.cap:
            self.cap.release()
        cv2.destroyAllWindows()

    def _loop(self):
        last_save = 0
        while self.running and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                # Small window pop-up active on the main monitor
                small_frame = cv2.resize(frame, (320, 240))
                cv2.imshow("DSLV-ZPDI Tamper-Evident Cam", small_frame)
                cv2.waitKey(1)

                # Save frame for tamper evidence at specified FPS
                now = time.time()
                if now - last_save >= (1.0 / self.fps):
                    last_save = now
                    ts = time.strftime("%Y%m%d_%H%M%S")
                    ms = int((now % 1) * 1000)
                    fname = self.out_dir / f"cam_tamper_{ts}_{ms:03d}.jpg"
                    cv2.imwrite(str(fname), frame)
                    self.frames_saved += 1
            else:
                time.sleep(0.1)

class CamApp:
    def __init__(self):
        self.console = Console()
        self.running = True
        self.paused = False

        self.fps_setting = 1.0 # 1 frame per second
        self.cam_active = False
        self.recorder = None
        self.logs = []

        self.state_mgr = SDRStateManager(owner_name="cam_app.py")
        self._keyboard_mode = None
        self._orig_attrs = None

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

    def _build_layout(self) -> Layout:
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=3)
        )
        layout["main"].split_row(
            Layout(name="controls", ratio=1),
            Layout(name="logs", ratio=1)
        )
        return layout

    def _render(self) -> Layout:
        layout = self._build_layout()

        # Header
        status_str = "ACTIVE (RECORDING & POPUP)" if self.cam_active else "OFF (STANDBY)"
        status_style = "bold bright_green blink" if self.cam_active else "dim bright_black"
        header_text = Text()
        header_text.append("▓▓ DSLV-ZPDI CAMERA / TAMPER-EVIDENT MODULE ▓▓\n", style="bold bright_cyan")
        header_text.append("STATUS: ", style="bright_white")
        header_text.append(status_str, style=status_style)
        layout["header"].update(Panel(Align.center(header_text), style="bright_blue"))

        # Controls
        ctrl_table = Table.grid(padding=(0, 2))
        ctrl_table.add_column(style="bright_yellow")
        ctrl_table.add_column(style="bright_white")
        ctrl_table.add_row("[C] Toggle Camera", "ON" if self.cam_active else "OFF")
        ctrl_table.add_row("[F] Frames Per Sec", f"{self.fps_setting:.1f} FPS")
        saved = self.recorder.frames_saved if self.recorder else 0
        ctrl_table.add_row("Frames Saved", str(saved))
        layout["controls"].update(Panel(ctrl_table, title="[bold bright_white]CAMERA CONTROLS", border_style="bright_cyan"))

        # Logs
        log_text = Text("\n".join(self.logs), style="dim bright_white")
        layout["logs"].update(Panel(log_text, title="[bold bright_white]MODULE LOGS", border_style="bright_black"))

        # Footer
        footer_text = Text()
        footer_text.append("Q: Quit | C: Toggle Camera | F/f: Adjust FPS ±", style="bold bright_white")
        layout["footer"].update(Panel(Align.center(footer_text), style="bright_black"))

        return layout

    def run(self):
        self._enter_raw()
        try:
            with Live(self._render(), screen=True, refresh_per_second=10) as live:
                while self.running:
                    key = self._read_key()
                    if key:
                        if key.lower() == 'q':
                            self.running = False
                        elif key.lower() == 'c':
                            self.cam_active = not self.cam_active
                            if self.cam_active:
                                self.recorder = CamRecorder(fps=self.fps_setting)
                                self.recorder.start()
                                self.logs.insert(0, f"[{time.strftime('%H:%M:%S')}] Camera ON - Popup active, Recording at {self.fps_setting} FPS")
                            else:
                                if self.recorder:
                                    self.recorder.stop()
                                    self.recorder = None
                                self.logs.insert(0, f"[{time.strftime('%H:%M:%S')}] Camera OFF - Standby mode")
                        elif key == 'F':
                            self.fps_setting = min(30.0, self.fps_setting + 0.5)
                            if self.recorder:
                                self.recorder.fps = self.fps_setting
                        elif key == 'f':
                            self.fps_setting = max(0.1, self.fps_setting - 0.5)
                            if self.recorder:
                                self.recorder.fps = self.fps_setting

                    if len(self.logs) > 15:
                        self.logs = self.logs[:15]

                    live.update(self._render())
                    if sys.stdin.isatty():
                        select.select([sys.stdin], [], [], 0.1)
                    else:
                        time.sleep(0.1)
        finally:
            if self.recorder:
                self.recorder.stop()
            self._exit_raw()

if __name__ == "__main__":
    app = CamApp()
    app.run()
