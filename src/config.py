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
        self.device_combobox = ttk.Combobox(
            self.root, textvariable=self.device_var, values=device_options, state="readonly", width=40
        )
        self.device_combobox.current(0)
        self.device_combobox.grid(row=row, column=1, padx=10, pady=10)

        # Profile selection
        row += 1
        tk.Label(self.root, text="Select profile:").grid(
            row=row, column=0, padx=10, pady=10, sticky="w"
        )
        self.profile_var = tk.StringVar()
        self.profile_combobox = ttk.Combobox(
            self.root, textvariable=self.profile_var, values=[], state="readonly", width=20
        )
        self.profile_combobox.grid(row=row, column=1, padx=10, pady=10)

        # デバイス選択時にプロファイルを更新
        self.device_combobox.bind("<<ComboboxSelected>>", self.on_device_selected)
        # 初期化時にも一度呼ぶ
        self.on_device_selected()
        # デフォルトで640x480 @ 30fpsがあれば選択
        default_profile = "640x480 @ 30fps"
        profiles = self.profile_combobox["values"]
        if default_profile in profiles:
            self.profile_combobox.set(default_profile)
        elif profiles:
            self.profile_combobox.current(0)

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
        # OSC address entries
        row += 1
        tk.Label(self.root, text="OSC Right Addr:").grid(row=row, column=0, padx=10, pady=5, sticky="w")
        self.osc_right_entry = tk.Entry(self.root)
        self.osc_right_entry.insert(0, "/eye/right")
        self.osc_right_entry.grid(row=row, column=1, padx=10, pady=5)
        self.osc_right_var = tk.IntVar(value=1)
        osc_right_cb = tk.Checkbutton(self.root, variable=self.osc_right_var, command=self.toggle_osc_right_entry)
        osc_right_cb.grid(row=row, column=2, padx=5, pady=5)
        row += 1
        tk.Label(self.root, text="OSC Left Addr:").grid(row=row, column=0, padx=10, pady=5, sticky="w")
        self.osc_left_entry = tk.Entry(self.root)
        self.osc_left_entry.insert(0, "/eye/left")
        self.osc_left_entry.grid(row=row, column=1, padx=10, pady=5)
        self.osc_left_var = tk.IntVar(value=1)
        osc_left_cb = tk.Checkbutton(self.root, variable=self.osc_left_var, command=self.toggle_osc_left_entry)
        osc_left_cb.grid(row=row, column=2, padx=5, pady=5)
        row += 1
        tk.Label(self.root, text="OSC Center Addr:").grid(row=row, column=0, padx=10, pady=5, sticky="w")
        self.osc_center_entry = tk.Entry(self.root)
        self.osc_center_entry.insert(0, "/eye/center")
        self.osc_center_entry.grid(row=row, column=1, padx=10, pady=5)
        self.osc_center_var = tk.IntVar(value=1)
        osc_center_cb = tk.Checkbutton(self.root, variable=self.osc_center_var, command=self.toggle_osc_center_entry)
        osc_center_cb.grid(row=row, column=2, padx=5, pady=5)

        # Buttons
        row += 1
        btn_frame = tk.Frame(self.root)
        btn_frame.grid(row=row, column=0, columnspan=2, pady=10)
        tk.Button(btn_frame, text="Start", command=self.on_start, width=10).pack(side="left", padx=10)
        tk.Button(btn_frame, text="Exit", command=self.on_exit, width=10).pack(side="left", padx=10)
        # 初期状態でエントリの有効/無効を反映
        self._init_osc_entry_states()

    def toggle_osc_right_entry(self):
        state = "normal" if self.osc_right_var.get() else "disabled"
        self.osc_right_entry.config(state=state)

    def toggle_osc_left_entry(self):
        state = "normal" if self.osc_left_var.get() else "disabled"
        self.osc_left_entry.config(state=state)

    def toggle_osc_center_entry(self):
        state = "normal" if self.osc_center_var.get() else "disabled"
        self.osc_center_entry.config(state=state)

    # 初期状態も反映
    def _init_osc_entry_states(self):
        self.toggle_osc_right_entry()
        self.toggle_osc_left_entry()
        self.toggle_osc_center_entry()

    def on_device_selected(self, event=None):
        try:
            idx = self.device_combobox.current()
            serial = self.device_serials[idx]
            profiles = self.get_available_profiles(serial)
            self.profile_combobox["values"] = profiles
            if profiles:
                self.profile_combobox.current(0)
            else:
                self.profile_var.set("")
        except Exception:
            self.profile_combobox["values"] = []
            self.profile_var.set("")
    def get_available_profiles(self, serial):
        # カラーとデプス両方で同時に利用できるプロファイルのみを抽出
        ctx = rs.context()
        for device in ctx.query_devices():
            if device.get_info(rs.camera_info.serial_number) == serial:
                color_profiles = set()
                depth_profiles = set()
                for s in device.sensors:
                    try:
                        # カラーセンサー
                        if s.get_info(rs.camera_info.name).lower().find('rgb') != -1 or s.get_info(rs.camera_info.name).lower().find('color') != -1:
                            for p in s.get_stream_profiles():
                                try:
                                    v = p.as_video_stream_profile()
                                    width = v.width()
                                    height = v.height()
                                    fps = p.fps()
                                    color_profiles.add((width, height, fps))
                                except Exception:
                                    continue
                        # デプスセンサー
                        if s.is_depth_sensor():
                            for p in s.get_stream_profiles():
                                try:
                                    v = p.as_video_stream_profile()
                                    width = v.width()
                                    height = v.height()
                                    fps = p.fps()
                                    depth_profiles.add((width, height, fps))
                                except Exception:
                                    continue
                    except Exception:
                        continue
                # 両方で使えるプロファイルのみ
                common_profiles = color_profiles & depth_profiles
                profiles = [f"{w}x{h} @ {f}fps" for (w, h, f) in sorted(common_profiles)]
                return profiles
        return []

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
        # OSCアドレスも保存
        self.config["osc_right_addr"] = self.osc_right_entry.get().strip()
        self.config["osc_left_addr"] = self.osc_left_entry.get().strip()
        self.config["osc_center_addr"] = self.osc_center_entry.get().strip()
        self.config["osc_right_enable"] = bool(self.osc_right_var.get())
        self.config["osc_left_enable"] = bool(self.osc_left_var.get())
        self.config["osc_center_enable"] = bool(self.osc_center_var.get())
        self.root.destroy()

    def on_exit(self):
        self.root.destroy()
        exit(0)

    def show(self):
        self.root.mainloop()
        return self.config
