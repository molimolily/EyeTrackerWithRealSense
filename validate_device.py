import pyrealsense2 as rs

ctx = rs.context()
devices = ctx.query_devices()
print("Found devices:", [dev.get_info(rs.camera_info.name) for dev in devices])