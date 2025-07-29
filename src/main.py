import pyrealsense2 as rs
from config import ConfigWindow
from model import RealSenseModel
from view import RealSenseView
from controller import Controller
from osc_sender import OSCSender
import sys

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
        try:
            device_usb = device.get_info(rs.camera_info.usb_type_descriptor)
        except Exception:
            device_usb = " --"
        info_text = f"{width}x{height} @ {fps}fps, {ip_addr} / {port}, USB{device_usb}"

        view = RealSenseView(f"Eyetracker {device_name} (S/N:{selected_serial})", info_text)
        osc_sender = OSCSender(
            ip_addr, port,
            right_addr=config.get("osc_right_addr", "/eye/right"),
            left_addr=config.get("osc_left_addr", "/eye/left"),
            center_addr=config.get("osc_center_addr", "/eye/center"),
            right_enable=config.get("osc_right_enable", True),
            left_enable=config.get("osc_left_enable", True),
            center_enable=config.get("osc_center_enable", True)
        )
        controller = Controller(model, view, info_text, osc_sender)

        def on_close():
            controller.stop()
            print("Window closed")

        view.protocol("WM_DELETE_WINDOW", on_close)
        controller.update_loop()
        view.mainloop()
    except Exception as e:
        print("error:", e)
        sys.exit(1)  # 変更

if __name__ == "__main__":
    main()