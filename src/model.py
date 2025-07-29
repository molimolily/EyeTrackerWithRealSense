import cv2
import numpy as np
import mediapipe
import pyrealsense2 as rs

EYE_LANDMARKS = [468, 473]

class RealSenseModel:
    def __init__(self, serial, flip, width, height, fps):
        self.width = width
        self.height = height
        self.flip = flip

        self.pipeline = rs.pipeline()
        self.config = rs.config()
        self.config.enable_device(serial)

        # カラーフォーマットの設定
        COLOR_FORMATS = (rs.format.rgb8, rs.format.bgr8, rs.format.yuyv)
        color_format = None
        for fmt in COLOR_FORMATS:
            try:
                self.config.enable_stream(rs.stream.color, width, height, fmt, fps)
                color_format = fmt
                break
            except RuntimeError:
                continue
        if color_format is None:
            raise RuntimeError("Color stream not available at requested resolution.")
        
        # デプスフォーマットの設定
        self.config.enable_stream(rs.stream.depth, width, height, rs.format.z16, fps)

        self.profile = self.pipeline.start(self.config)
        self.align = rs.align(rs.stream.color)

        # デバイス種別判定（Stereo なら D400）
        dev = self.profile.get_device()
        product_line = dev.get_info(rs.camera_info.product_line)
        self.is_stereo = product_line.upper() == "D400"

        self.intrinsics = (
            self.profile.get_stream(rs.stream.color)
            .as_video_stream_profile()
            .get_intrinsics()
        )

        mp_face_mesh = mediapipe.solutions.face_mesh
        self.face_mesh = mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.9,
        )
        self.mp_drawing = mediapipe.solutions.drawing_utils
        self.mp_drawing_styles = mediapipe.solutions.drawing_styles

        # ---------------- フィルタ構築 ----------------
        self.dec = rs.decimation_filter()
        self.dec.set_option(rs.option.filter_magnitude, 2)

        self.d2disp = rs.disparity_transform(True) if self.is_stereo else None
        self.disp2d = rs.disparity_transform(False) if self.is_stereo else None

        self.spat = rs.spatial_filter()
        self.spat.set_option(rs.option.filter_smooth_alpha, 0.35)
        self.spat.set_option(rs.option.filter_smooth_delta, 20)

        self.temp = rs.temporal_filter()
        self.temp.set_option(rs.option.filter_smooth_alpha, 0.1)
        self.temp.set_option(rs.option.filter_smooth_delta, 40)

        self.hole = rs.hole_filling_filter()
        self.hole.set_option(rs.option.holes_fill, 1)

        # カラーを RGB にするかどうか
        self.color_to_rgb = color_format != rs.format.rgb8


    def process_frame(self):
        try:
            frames = self.pipeline.wait_for_frames()
        except RuntimeError:
            return None, None  # device disconnected?
        
        aligned_frames = self.align.process(frames)
        depth_frame = aligned_frames.get_depth_frame()
        color_frame = aligned_frames.get_color_frame()
        if not depth_frame or not color_frame:
            return None, None
        
        # フィルターを適用
        depth_frame = self.dec.process(depth_frame)
        if self.is_stereo:
            depth_frame = self.d2disp.process(depth_frame)
        depth_frame = self.spat.process(depth_frame)
        depth_frame = self.temp.process(depth_frame)
        if self.is_stereo:
            depth_frame = self.disp2d.process(depth_frame)
        depth_frame = self.hole.process(depth_frame)
        depth_frame = depth_frame.as_depth_frame()
        color_arr = np.asanyarray(color_frame.get_data())
        if self.color_to_rgb:
            if color_frame.get_profile().format == rs.format.yuyv:
                color_arr = cv2.cvtColor(color_arr, cv2.COLOR_YUV2RGB_YUYV)
            else:
                color_arr = cv2.cvtColor(color_arr, cv2.COLOR_BGR2RGB)

        if self.flip:
            color_arr = cv2.flip(color_arr, -1)
        results = self.face_mesh.process(color_arr)
        eye_pos = None
        if results.multi_face_landmarks:
            for face_landmarks in results.multi_face_landmarks:
                self.mp_drawing.draw_landmarks(
                    image=color_arr,
                    landmark_list=face_landmarks,
                    connections=mediapipe.solutions.face_mesh.FACEMESH_TESSELATION,
                    landmark_drawing_spec=None,
                    connection_drawing_spec=self.mp_drawing_styles.get_default_face_mesh_tesselation_style()
                )
                self.mp_drawing.draw_landmarks(
                    image=color_arr,
                    landmark_list=face_landmarks,
                    connections=mediapipe.solutions.face_mesh.FACEMESH_CONTOURS,
                    landmark_drawing_spec=None,
                    connection_drawing_spec=self.mp_drawing_styles.get_default_face_mesh_contours_style()
                )
                self.mp_drawing.draw_landmarks(
                    image=color_arr,
                    landmark_list=face_landmarks,
                    connections=mediapipe.solutions.face_mesh.FACEMESH_IRISES,
                    landmark_drawing_spec=None,
                    connection_drawing_spec=self.mp_drawing_styles.get_default_face_mesh_iris_connections_style()
                )

                eye_right_point = face_landmarks.landmark[EYE_LANDMARKS[0]]
                eye_right_pixel = self.keypoint_to_pixel(eye_right_point)
                # eye_right_normalized = self.transform_pixel_to_normalized(eye_right_pixel[0], eye_right_pixel[1])
                eye_right_depth = self.get_depth_at_pixel(eye_right_pixel[0], eye_right_pixel[1], depth_frame)
                # eye_right_pos = self.deprojection(eye_right_pixel[0], eye_right_pixel[1], eye_right_depth)
                
                eye_left_point = face_landmarks.landmark[EYE_LANDMARKS[1]]
                eye_left_pixel = self.keypoint_to_pixel(eye_left_point)
                # eye_left_normalized = self.transform_pixel_to_normalized(eye_left_pixel[0], eye_left_pixel[1])
                eye_left_depth = self.get_depth_at_pixel(eye_left_pixel[0], eye_left_pixel[1], depth_frame)
                # eye_left_pos = self.deprojection(eye_left_pixel[0], eye_left_pixel[1], eye_left_depth)

                # left hand coordinate system
                # eye_right_pos = (eye_right_pos[0], -eye_right_pos[1], eye_right_pos[2])
                # eye_left_pos = (eye_left_pos[0], -eye_left_pos[1], eye_left_pos[2])
                eye_right_pos = (eye_right_pixel[0], eye_right_pixel[1], eye_right_depth)
                eye_left_pos = (eye_left_pixel[0], eye_left_pixel[1], eye_left_depth)

                eye_pos = (eye_right_pos, eye_left_pos)

        return color_arr, eye_pos

    def keypoint_to_pixel(self, keypoint):
        width, height = self.width, self.height
        x = np.clip(int(keypoint.x * width), 0, width - 1)
        y = np.clip(int(keypoint.y * height), 0, height - 1)
        return (x, y)
    
    def get_depth_at_pixel(self, x, y, depth_frame):
        if self.flip:
            x = np.clip(self.width - 1 - x, 0, self.width - 1)
            y = np.clip(self.height - 1 - y, 0, self.height - 1)

        # --- 解像度スケールを算出 ---
        scale_x = depth_frame.get_width()  / self.width
        scale_y = depth_frame.get_height() / self.height

        dx = int(np.clip(x * scale_x, 0, depth_frame.get_width()  - 1))
        dy = int(np.clip(y * scale_y, 0, depth_frame.get_height() - 1))

        return depth_frame.get_distance(dx, dy)
    
    def transform_pixel_to_normalized(self, x, y):
        intrinsics = self.intrinsics
        x = (x - intrinsics.ppx) / intrinsics.fx
        y = (y - intrinsics.ppy) / intrinsics.fy
        return (x, y)
    
    def deprojection(self, x, y, depth):
        x,y,z = rs.rs2_deproject_pixel_to_point(self.intrinsics, [x, y], depth)
        return (x, -y, z)

    def close(self):
        self.pipeline.stop()
        print("Pipeline stopped")
        self.face_mesh.close()
        print("Face mesh closed")
