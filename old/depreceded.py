import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import cv2
import numpy as np
import mediapipe
import pyrealsense2 as rs
import time

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
            tk.messagebox.showerror("Error", "No RealSense devices found")
            self.root.destroy()
            exit(0)
        self.device_serials = device_serials
        row = 0
        tk.Label(self.root, text="Select RealSense device:").grid(row=row, column=0, padx=10, pady=10, sticky="w")
        self.device_var = tk.StringVar()
        device_combobox = ttk.Combobox(self.root, textvariable=self.device_var, values=device_options, state="readonly", width=40)
        device_combobox.current(0)
        device_combobox.grid(row=row, column=1, padx=10, pady=10)
        # Profile selection
        row += 1
        tk.Label(self.root, text="Select profile:").grid(row=row, column=0, padx=10, pady=10, sticky="w")
        profiles = ["640x480 @ 30fps", "640x480 @ 60fps", "1280x720 @ 30fps"]
        self.profile_var = tk.StringVar()
        profile_combobox = ttk.Combobox(self.root, textvariable=self.profile_var, values=profiles, state="readonly", width=20)
        profile_combobox.current(0)
        profile_combobox.grid(row=row, column=1, padx=10, pady=10)
        # Flip checkbox
        row += 1
        tk.Label(self.root, text="Flip image:").grid(row=row, column=0, padx=10, pady=10, sticky="w")
        self.flip_var = tk.IntVar()
        flip_checkbox = tk.Checkbutton(self.root, variable=self.flip_var)
        flip_checkbox.grid(row=row, column=1, padx=10, pady=10)
        # IP address entry
        row += 1
        tk.Label(self.root, text="IP address:").grid(row=row, column=0, padx=10, pady=10, sticky="w")
        self.ip_entry = tk.Entry(self.root)
        self.ip_entry.insert(0, "127.0.0.1")
        self.ip_entry.grid(row=row, column=1, padx=10, pady=10)
        # Port entry
        row += 1
        tk.Label(self.root, text="Port:").grid(row=row, column=0, padx=10, pady=10, sticky="w")
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
        self.config["ip"] = self.ip_entry.get().strip()
        self.config["port"] = self.port_entry.get().strip()
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

class FPSTimer:
    def __init__(self, max_samples=30):
        self.times = []
        self.max_samples = max_samples
    def update(self, dt):
        self.times.append(dt)
        if len(self.times) > self.max_samples:
            self.times.pop(0)
    def get_fps(self):
        total = sum(self.times)
        if total > 0:
            return len(self.times) / total
        return 0

class RealSenseModel:
    def __init__(self, serial, flip, width, height, fps):
        self.flip = flip
        self.fps_timer = FPSTimer(max_samples=30)
        self.pipeline = rs.pipeline()
        self.config = rs.config()
        self.config.enable_device(serial)
        self.config.enable_stream(rs.stream.depth, width, height, rs.format.z16, fps)
        self.config.enable_stream(rs.stream.color, width, height, rs.format.rgb8, fps)
        self.profile = self.pipeline.start(self.config)
        self.align = rs.align(rs.stream.color)

        mp_face_mesh = mediapipe.solutions.face_mesh
        self.face_mesh = mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self.mp_drawing = mediapipe.solutions.drawing_utils
        self.mp_drawing_styles = mediapipe.solutions.drawing_styles

    def process_frame(self):
        start_time = cv2.getTickCount()
        frames = self.pipeline.wait_for_frames()
        aligned_frames = self.align.process(frames)
        depth_frame = aligned_frames.get_depth_frame()
        color_frame = aligned_frames.get_color_frame()
        if not depth_frame or not color_frame:
            return None, None
        color_frame = np.asanyarray(color_frame.get_data())
        if self.flip:
            color_frame = cv2.flip(color_frame, -1)
        results = self.face_mesh.process(color_frame)
        if results.multi_face_landmarks:
            for face_landmarks in results.multi_face_landmarks:
                self.mp_drawing.draw_landmarks(
                    image=color_frame,
                    landmark_list=face_landmarks,
                    connections=mediapipe.solutions.face_mesh.FACEMESH_TESSELATION,
                    landmark_drawing_spec=None,
                    connection_drawing_spec=self.mp_drawing_styles.get_default_face_mesh_tesselation_style()
                )
                self.mp_drawing.draw_landmarks(
                    image=color_frame,
                    landmark_list=face_landmarks,
                    connections=mediapipe.solutions.face_mesh.FACEMESH_CONTOURS,
                    landmark_drawing_spec=None,
                    connection_drawing_spec=self.mp_drawing_styles.get_default_face_mesh_contours_style()
                )
                self.mp_drawing.draw_landmarks(
                    image=color_frame,
                    landmark_list=face_landmarks,
                    connections=mediapipe.solutions.face_mesh.FACEMESH_IRISES,
                    landmark_drawing_spec=None,
                    connection_drawing_spec=self.mp_drawing_styles.get_default_face_mesh_iris_connections_style()
                )
        end_time = cv2.getTickCount()
        dt = (end_time - start_time) / cv2.getTickFrequency()
        self.fps_timer.update(dt)
        avg_fps = self.fps_timer.get_fps()
        return color_frame, avg_fps

    def close(self):
        self.pipeline.stop()
        print("Pipeline stopped")
        
        self.face_mesh.close()
        print("Face mesh closed")

class RealSenseView:
    def __init__(self, title, info_text):
        self.win = tk.Tk()
        self.win.title(title)
        self.win.resizable(False, False)
        self.image_label = tk.Label(self.win)
        self.image_label.pack()
        self.fps_label = tk.Label(self.win, text=info_text, justify="left")
        self.fps_label.pack()

    def update(self, image, info_text):
        im = Image.fromarray(image)
        imgtk = ImageTk.PhotoImage(image=im)
        self.image_label.imgtk = imgtk
        self.image_label.configure(image=imgtk)
        self.fps_label.config(text=info_text)

    def after(self, delay, callback):
        self.win.after(delay, callback)

    def mainloop(self):
        self.win.mainloop()

    def protocol(self, protocol_name, func):
        self.win.protocol(protocol_name, func)

    def destroy(self):
        self.win.destroy()

class Controller:
    def __init__(self, model, view, info_text):
        self.model = model
        self.view = view
        self.info_text = info_text
        self.running = True
        self.last_fps_update = time.time()
        self.current_fps = 0

    def update_loop(self):
        if not self.running:
            return
        frame, avg_fps = self.model.process_frame()
        if frame is not None:
            now = time.time()
            # 0.5秒毎にFPS表示を更新
            if now - self.last_fps_update >= 0.5:
                self.current_fps = avg_fps
                self.last_fps_update = now
            display_text = f"{self.info_text} ({self.current_fps:.1f} fps)"
            self.view.update(frame, display_text)
        self.view.after(1, self.update_loop)

    def stop(self):
        self.running = False
        self.model.close()
        self.view.destroy()

def main():
    try:
        config = ConfigWindow().show()
        selected_serial = config["serial"]
        flip_image = config["flip"]
        ip_addr = config["ip"]
        port = config["port"]
        width = config["width"]
        height = config["height"]
        fps = config["fps"]

        model = RealSenseModel(selected_serial, flip_image, width, height, fps)
        device = model.profile.get_device()
        device_name = device.get_info(rs.camera_info.name)
        device_usb = device.get_info(rs.camera_info.usb_type_descriptor)
        info_text = f"{width}x{height} @ {fps}fps, {ip_addr} / {port}, USB{device_usb}"

        view = RealSenseView(f"Eyetracker {device_name} (S/N:{selected_serial})", info_text)
        controller = Controller(model, view, info_text)

        def on_close():
            controller.stop()
            print("Window closed")

        view.protocol("WM_DELETE_WINDOW", on_close)
        controller.update_loop()
        view.mainloop()
    except Exception as e:
        print("Initialization error:", e)
        exit(1)

if __name__ == "__main__":
    main()