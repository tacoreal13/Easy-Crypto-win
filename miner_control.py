#!/usr/bin/env python3
"""
Miner Control (Windows) - GPU power slider + CPU start/stop
-------------------------------------------------------------
Reads config.json (created by install.ps1) and gives you a GUI to:
  - Drag a slider to change Rigel's GPU power limit (kills + restarts
    Rigel with the new value, opens its own console window)
  - Start/stop XMRig independently (separate hardware, no conflict)

Requires admin rights to actually change the GPU power limit, so this
script re-launches itself elevated via UAC on startup if needed - you'll
see one UAC prompt when you open it, not one per slider move.

USAGE:
    python miner_control.py
"""

import ctypes
import json
import os
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.json")
RIGEL_PATH = os.path.join(SCRIPT_DIR, "bin", "rigel", "rigel.exe")
XMRIG_PATH = os.path.join(SCRIPT_DIR, "bin", "xmrig", "xmrig.exe")


# ============================= Elevation =============================

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def relaunch_as_admin():
    """Re-run this same script elevated, then exit the current (non-admin) process."""
    params = " ".join(f'"{a}"' for a in sys.argv)
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, f'"{sys.argv[0]}" {params}', None, 1
    )
    sys.exit(0)


# ============================= Config =============================

def load_config():
    if not os.path.exists(CONFIG_PATH):
        messagebox.showerror(
            "Missing config.json",
            f"Couldn't find config.json in:\n{SCRIPT_DIR}\n\n"
            "Run install.ps1 first, or copy config.example.json to config.json "
            "and fill in your wallet address.",
        )
        sys.exit(1)
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


# ============================= Process helpers =============================

CREATE_NEW_CONSOLE = 0x00000010


def launch_in_console(cmd_list, title):
    """Launch a command in its own visible console window that stays open
    after the process exits (so crash errors are readable), and return the
    Popen handle - its .pid is the actual console process, so taskkill /T
    reliably kills the whole tree (console + miner).
    """
    quoted = " ".join(f'"{c}"' if " " in c else c for c in cmd_list)
    # /k keeps the window open; the extra echo shows the exit code once the
    # miner process ends, similar to a crash log instead of a vanishing window
    shell_line = f'title {title} && {quoted} & echo. & echo --- process exited --- & pause'
    return subprocess.Popen(
        ["cmd", "/k", shell_line],
        creationflags=CREATE_NEW_CONSOLE,
    )


def kill_process_tree(proc):
    if proc is None or proc.poll() is not None:
        return
    try:
        subprocess.run(
            ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
            capture_output=True,
        )
    except Exception:
        pass


# ============================= Main App =============================

class MinerController:
    def __init__(self, root, config):
        self.root = root
        self.config = config
        self.root.title("Miner Control (Windows)")
        self.root.geometry("560x600")

        self.gpu_process = None
        self.cpu_process = None
        self.restart_lock = threading.Lock()

        gpu_cfg = config.get("gpu", {})
        self.gpu_enabled = gpu_cfg.get("enabled", False) and os.path.exists(RIGEL_PATH)
        cpu_cfg = config.get("cpu", {})
        self.cpu_enabled = cpu_cfg.get("enabled", False) and os.path.exists(XMRIG_PATH)

        self._build_ui()

        if self.gpu_enabled:
            self.start_gpu(gpu_cfg.get("default_power_limit", 100))

    # ---------------- UI ----------------

    def _build_ui(self):
        pad = {"padx": 10, "pady": 6}

        if not self.gpu_enabled and not self.cpu_enabled:
            ttk.Label(
                self.root,
                text="Neither GPU nor CPU mining is enabled/installed.\n"
                     "Check config.json and make sure bin\\rigel\\rigel.exe "
                     "or bin\\xmrig\\xmrig.exe exists.",
                foreground="red",
                justify="left",
            ).pack(**pad)

        if self.gpu_enabled:
            gpu_cfg = self.config["gpu"]
            ttk.Label(self.root, text="GPU Mining (Rigel)", font=("Segoe UI", 14, "bold")).pack(**pad)

            self.gpu_value_label = ttk.Label(self.root, text=f"{gpu_cfg.get('default_power_limit', 100)} W", font=("Segoe UI", 20))
            self.gpu_value_label.pack(**pad)

            self.gpu_slider = ttk.Scale(
                self.root,
                from_=gpu_cfg.get("min_power_limit", 60),
                to=gpu_cfg.get("max_power_limit", 130),
                orient="horizontal",
                command=self._on_slide,
                length=440,
            )
            self.gpu_slider.set(gpu_cfg.get("default_power_limit", 100))
            self.gpu_slider.pack(**pad)
            self.gpu_slider.bind("<ButtonRelease-1>", self._on_release)

            self.gpu_status_label = ttk.Label(self.root, text="Starting Rigel...", foreground="blue")
            self.gpu_status_label.pack(**pad)

            gpu_btn_frame = ttk.Frame(self.root)
            gpu_btn_frame.pack(**pad)
            ttk.Button(gpu_btn_frame, text="Stop GPU Miner", command=self.stop_gpu).pack(side="left", padx=5)
            ttk.Button(gpu_btn_frame, text="Restart Now", command=lambda: self.restart_gpu(int(self.gpu_slider.get()))).pack(side="left", padx=5)

            ttk.Separator(self.root, orient="horizontal").pack(fill="x", padx=10, pady=10)

        if self.cpu_enabled:
            ttk.Label(self.root, text="CPU Mining (XMRig)", font=("Segoe UI", 14, "bold")).pack(**pad)
            self.cpu_status_label = ttk.Label(self.root, text="XMRig not running", foreground="gray")
            self.cpu_status_label.pack(**pad)

            cpu_btn_frame = ttk.Frame(self.root)
            cpu_btn_frame.pack(**pad)
            ttk.Button(cpu_btn_frame, text="Start XMRig", command=self.start_cpu).pack(side="left", padx=5)
            ttk.Button(cpu_btn_frame, text="Stop XMRig", command=self.stop_cpu).pack(side="left", padx=5)

            ttk.Separator(self.root, orient="horizontal").pack(fill="x", padx=10, pady=10)

        ttk.Label(self.root, text="Miner output appears in their own console windows.").pack(**pad)
        self.log = scrolledtext.ScrolledText(self.root, height=10, width=64, state="disabled", bg="black", fg="#00ff88")
        self.log.pack(padx=10, pady=(0, 10))

    def _log_line(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _on_slide(self, value):
        self.gpu_value_label.config(text=f"{int(float(value))} W")

    def _on_release(self, event):
        self.restart_gpu(int(self.gpu_slider.get()))

    # ---------------- GPU (Rigel) ----------------

    def build_gpu_command(self, pl):
        gpu_cfg = self.config["gpu"]
        return [
            RIGEL_PATH,
            "-a", gpu_cfg["algorithm"],
            "-o", gpu_cfg["pool"],
            "-u", f'{gpu_cfg["wallet"]}.{self.config.get("worker_name", "WindowsRig")}',
            "-p", gpu_cfg.get("password", "x"),
            "--pl", str(pl),
            "--temp-limit", gpu_cfg.get("temp_limit", "tc[75-80]"),
        ]

    def start_gpu(self, pl):
        cmd = self.build_gpu_command(pl)
        self._log_line(f"$ {' '.join(cmd)}")
        self.gpu_process = launch_in_console(cmd, "Rigel-GPU-Miner")
        self.gpu_status_label.config(text=f"Running at {pl} W (see Rigel's window)", foreground="green")

    def stop_gpu(self):
        if self.gpu_process:
            self.gpu_status_label.config(text="Stopping...", foreground="orange")
            kill_process_tree(self.gpu_process)
            self.gpu_status_label.config(text="Stopped", foreground="red")
            self._log_line("[GPU miner stopped]")

    def restart_gpu(self, new_pl):
        def work():
            with self.restart_lock:
                self.root.after(0, self.gpu_status_label.config, {"text": f"Restarting at {new_pl} W...", "foreground": "orange"})
                if self.gpu_process:
                    kill_process_tree(self.gpu_process)
                time.sleep(0.5)
                self.root.after(0, self.start_gpu, new_pl)
        threading.Thread(target=work, daemon=True).start()

    # ---------------- CPU (XMRig) ----------------

    def build_cpu_command(self):
        cpu_cfg = self.config["cpu"]
        cmd = [
            XMRIG_PATH,
            "-o", cpu_cfg["pool"],
            "-a", cpu_cfg.get("algo", "rx/0"),
            "-u", f'{cpu_cfg["wallet"]}.{self.config.get("worker_name", "WindowsRig")}',
            "-p", cpu_cfg.get("password", "x"),
        ]
        if cpu_cfg.get("tls", True):
            cmd.append("--tls")
        return cmd

    def start_cpu(self):
        if self.cpu_process and self.cpu_process.poll() is None:
            self._log_line("[XMRig already running]")
            return
        cmd = self.build_cpu_command()
        self._log_line(f"$ {' '.join(cmd)}")
        self.cpu_process = launch_in_console(cmd, "XMRig-CPU-Miner")
        self.cpu_status_label.config(text="XMRig running (see its own window)", foreground="green")

    def stop_cpu(self):
        if self.cpu_process:
            self.cpu_status_label.config(text="Stopping...", foreground="orange")
            kill_process_tree(self.cpu_process)
            self.cpu_status_label.config(text="XMRig stopped", foreground="gray")
            self._log_line("[XMRig stopped]")

    def on_close(self):
        self.stop_gpu()
        self.stop_cpu()
        self.root.destroy()


if __name__ == "__main__":
    if not is_admin():
        relaunch_as_admin()
        sys.exit(0)

    cfg = load_config()
    root = tk.Tk()
    app = MinerController(root, cfg)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
