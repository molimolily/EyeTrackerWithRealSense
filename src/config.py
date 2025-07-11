import tkinter as tk
from tkinter import ttk, messagebox
import pyrealsense2 as rs
import ipaddress

def enumerate_devices():
    ctx = rs.context()
    devices = ctx.query_devices()
    device_options = []
    device_serials = []
    for device in devices:
        serial = device.get_info(rs.camera_info.serial_number)
        name = device.get_info(rs.camera_info.name)
        device_options.append(f"{name} ({serial})")
        device_serials.append(serial)
    return device_options, device_serials

class ConfigWindow:
    def __init__(self):
        self.config = {}
        self.root = tk.Tk()
        self.root.title("Configuration")
        self.root.resizable(False, False)
        # Device selection
        device_options, device_serials = enumerate_devices()
        if not device_options:
            messagebox.showerror("Error", "No RealSense devices found")
            self.root.destroy()
            exit(0)
        self.device_serials = device_serials
        row = 0
        tk.Label(self.root, text="Select RealSense device:").grid(
            row=row, column=0, padx=10, pady=10, sticky="w"
        )
        self.device_var = tk.StringVar()
        device_combobox = ttk.Combobox(
            self.root, textvariable=self.device_var, values=device_options, state="readonly", width=40
        )
        device_combobox.current(0)
        device_combobox.grid(row=row, column=1, padx=10, pady=10)
        # Profile selection
        row += 1
        tk.Label(self.root, text="Select profile:").grid(
            row=row, column=0, padx=10, pady=10, sticky="w"
        )
        profiles = ["640x480 @ 30fps", "640x480 @ 60fps", "1280x720 @ 30fps"]
        self.profile_var = tk.StringVar()
        profile_combobox = ttk.Combobox(
            self.root, textvariable=self.profile_var, values=profiles, state="readonly", width=20
        )
        profile_combobox.current(0)
        profile_combobox.grid(row=row, column=1, padx=10, pady=10)
        # Flip checkbox
        row += 1
        tk.Label(self.root, text="Flip image:").grid(
            row=row, column=0, padx=10, pady=10, sticky="w"
        )
        self.flip_var = tk.IntVar()
        tk.Checkbutton(self.root, variable=self.flip_var).grid(row=row, column=1, padx=10, pady=10)
        # IP & Port entries
        row += 1
        tk.Label(self.root, text="IP address:").grid(
            row=row, column=0, padx=10, pady=10, sticky="w"
        )
        self.ip_entry = tk.Entry(self.root)
        self.ip_entry.insert(0, "127.0.0.1")
        self.ip_entry.grid(row=row, column=1, padx=10, pady=10)
        row += 1
        tk.Label(self.root, text="Port:").grid(
            row=row, column=0, padx=10, pady=10, sticky="w"
        )
        self.port_entry = tk.Entry(self.root)
        self.port_entry.insert(0, "8000")
        self.port_entry.grid(row=row, column=1, padx=10, pady=10)
        # Buttons
        row += 1
        btn_frame = tk.Frame(self.root)
        btn_frame.grid(row=row, column=0, columnspan=2, pady=10)
        tk.Button(btn_frame, text="Start", command=self.on_start, width=10).pack(side="left", padx=10)
        tk.Button(btn_frame, text="Exit", command=self.on_exit, width=10).pack(side="left", padx=10)

    def on_start(self):
        try:
            idx = self.device_serials.index(self.device_var.get().split('(')[-1].strip(")"))
        except ValueError:
            messagebox.showerror("Error", "Invalid device selection")
            return
        self.config["serial"] = self.device_serials[idx]
        self.config["flip"] = self.flip_var.get()
        
        # Validate IP address
        ip_str = self.ip_entry.get().strip()
        try:
            ipaddress.ip_address(ip_str)
        except ValueError:
            messagebox.showerror("Error", "Invalid IP address")
            return
        
        # Validate port number
        port_str = self.port_entry.get().strip()
        try:
            port_int = int(port_str)
            if not (1 <= port_int <= 65535):
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Invalid port number")
            return
        
        self.config["ip"] = ip_str
        self.config["port"] = port_int

        profile_str = self.profile_var.get()
        try:
            resolution_part, _, fps_part = profile_str.split()
            width_str, height_str = resolution_part.split("x")
            fps_str = fps_part.replace("fps", "")
            self.config["width"] = int(width_str)
            self.config["height"] = int(height_str)
            self.config["fps"] = int(fps_str)
        except Exception:
            messagebox.showerror("Error", "Invalid profile selection")
            return
        self.root.destroy()

    def on_exit(self):
        self.root.destroy()
        exit(0)

    def show(self):
        self.root.mainloop()
        return self.config
