import time
from fps_timer import FPSTimer
from eye_processor import MovingAverageProcessor, KalmanFilterProcessor, KalmanFilterAccelProcessor, OneEuroFilterProcesser

class Controller:
    def __init__(self, model, view, info_text, osc_sender):
        self.model = model
        self.view = view
        self.info_text = info_text
        self.running = True
        self.fps_timer = FPSTimer(max_samples=30)
        self.last_fps_update = time.time()
        self.current_fps = 0
        self.osc_sender = osc_sender
        self.moving_average_processor = MovingAverageProcessor(window=5, threshold=0.15, max_dt=0.5)
        self.kalman_filter_processor = KalmanFilterProcessor(threshold=0.10)
        self.kaleman_filter_accel_processor = KalmanFilterAccelProcessor()
        self.one_euro_filter_processor = OneEuroFilterProcesser(min_cutoff=0.3, beta=0.5, d_cutoff=0.3) 

    def update_loop(self):
        if not self.running:
            return
        start = time.time()
        frame, eye_pos = self.model.process_frame()
        now = time.time()
        dt = now - start
        self.fps_timer.update(dt)
        if frame is not None:
            if now - self.last_fps_update >= 0.5:
                self.current_fps = self.fps_timer.get_fps()
                self.last_fps_update = now
            info_text = self.info_text
            fps_text = f"{self.current_fps:.1f} fps"
            eye_pos_text = "eye_pos:"
            if eye_pos is not None:
                right_eye = self.model.deprojection(eye_pos[0][0], eye_pos[0][1], eye_pos[0][2])
                left_eye = self.model.deprojection(eye_pos[1][0], eye_pos[1][1], eye_pos[1][2])
                eye_pos = (right_eye, left_eye)
                # map_eye_pos = self.moving_average_processor.process(eye_pos, dt)
                # kp_eye_pos = self.kalman_filter_processor.process(eye_pos, dt)
                # eye_pos = self.kalman_filter_processor.process(eye_pos, dt)
                # eye_pos = self.moving_average_processor.process(eye_pos, dt)
                # eye_pos = self.kaleman_filter_accel_processor.process(eye_pos, dt)
                # eye_pos = self.one_euro_filter_processor.process(eye_pos, dt)
                self.osc_sender.send(eye_pos)
                eye_pos_text += f"({eye_pos[1][0]:.2f}, {eye_pos[1][1]:.2f}, {eye_pos[1][2]:.2f}), ({eye_pos[0][0]:.2f}, {eye_pos[0][1]:.2f}, {eye_pos[0][2]:.2f})"
            else:
                eye_pos_text += "not detected"
            self.view.update(frame, info_text, fps_text, eye_pos_text)
        self.view.after(1, self.update_loop)

    def stop(self):
        self.running = False
        self.model.close()
        self.view.destroy()
