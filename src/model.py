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
        self.config.enable_stream(rs.stream.depth, width, height, rs.format.z16, fps)
        self.config.enable_stream(rs.stream.color, width, height, rs.format.rgb8, fps)
        self.profile = self.pipeline.start(self.config)
        self.align = rs.align(rs.stream.color)
        self.intrinsics = self.pipeline.get_active_profile().get_stream(rs.stream.color).as_video_stream_profile().get_intrinsics()
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
        # self.dec_filter = rs.decimation_filter()
        # self.spat_filter = rs.spatial_filter()
        # self.spat_filter.set_option(rs.option.filter_magnitude, 2)
        # self.spat_filter.set_option(rs.option.filter_smooth_alpha, 0.5)
        # self.spat_filter.set_option(rs.option.filter_smooth_delta, 20)
        self.temp_filter = rs.temporal_filter()
        self.temp_filter.set_option(rs.option.filter_smooth_alpha, 0.4)
        self.temp_filter.set_option(rs.option.filter_smooth_delta, 30)


    def process_frame(self):
        frames = self.pipeline.wait_for_frames()
        aligned_frames = self.align.process(frames)
        depth_frame = aligned_frames.get_depth_frame()
        color_frame = aligned_frames.get_color_frame()
        if not depth_frame or not color_frame:
            return None, None
        #depth_frame = self.dec_filter.process(depth_frame).as_depth_frame()
        #depth_frame = self.spat_filter.process(depth_frame).as_depth_frame()
        # depth_frame = self.temp_filter.process(depth_frame).as_depth_frame()
        color_frame = np.asanyarray(color_frame.get_data())
        if self.flip:
            color_frame = cv2.flip(color_frame, -1)
        results = self.face_mesh.process(color_frame)
        eye_pos = None
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

        return color_frame, eye_pos
    
    def keypoint_to_pixel(self, keypoint):
        width, height = self.width, self.height
        x = np.clip(int(keypoint.x * width), 0, width - 1)
        y = np.clip(int(keypoint.y * height), 0, height - 1)
        return (x, y)
    
    def get_depth_at_pixel(self, x, y, depth_frame):
        if self.flip:
            x = np.clip(self.width - 1 - x, 0, self.width - 1)
            y = np.clip(self.height - 1 - y, 0, self.height - 1)
        depth_value = depth_frame.get_distance(x, y)
        return depth_value
    
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
