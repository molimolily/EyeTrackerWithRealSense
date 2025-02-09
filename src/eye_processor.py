import math
import numpy as np
from filterpy.kalman import KalmanFilter

class MovingAverageProcessor():
    def __init__(self, window=5, threshold=0.15, max_dt=0.5):
        self.window = window
        self.threshold = threshold  # maximum allowed deviation per coordinate
        self.max_dt = max_dt        # maximum allowed time delta before reset
        self.history_right = []
        self.history_left = []

    def process(self, eye_pos, dt):
        if dt > self.max_dt:
            # Reset history if time delta is too large.
            self.history_right = []
            self.history_left = []
        right, left = eye_pos
        # Process right eye
        if self.history_right:
            current_avg_r = [sum(c)/len(self.history_right) for c in zip(*self.history_right)]
            right = [r if abs(r - avg) <= self.threshold else avg 
                     for r, avg in zip(right, current_avg_r)]
        # Process left eye
        if self.history_left:
            current_avg_l = [sum(c)/len(self.history_left) for c in zip(*self.history_left)]
            left = [l if abs(l - avg) <= self.threshold else avg 
                     for l, avg in zip(left, current_avg_l)]
        self.history_right.append(right)
        self.history_left.append(left)
        if len(self.history_right) > self.window:
            self.history_right.pop(0)
            self.history_left.pop(0)
        avg_right = [sum(c)/len(self.history_right) for c in zip(*self.history_right)]
        avg_left = [sum(c)/len(self.history_left) for c in zip(*self.history_left)]
        return (avg_right, avg_left)

class KalmanFilterProcessor():
    def __init__(self, dt=1.0, threshold=0.15, max_dt=0.5):
        self.dt = dt
        self.threshold = threshold  # maximum allowed deviation per coordinate
        self.max_dt = max_dt        # maximum allowed time delta before reset
        self.filter_right = self._init_filter()
        self.filter_left = self._init_filter()
        self.initialized = False

    def _init_filter(self):
        kf = KalmanFilter(dim_x=6, dim_z=3)
        kf.F = np.array([
            [1, 0, 0, self.dt, 0,       0],
            [0, 1, 0, 0,       self.dt, 0],
            [0, 0, 1, 0,       0,       self.dt],
            [0, 0, 0, 1,       0,       0],
            [0, 0, 0, 0,       1,       0],
            [0, 0, 0, 0,       0,       1]
        ])
        kf.H = np.array([
            [1, 0, 0, 0, 0, 0],
            [0, 1, 0, 0, 0, 0],
            [0, 0, 1, 0, 0, 0]
        ])
        # Adjusted: lower measurement noise for x,y, and slightly higher for z.
        kf.R = np.diag([0.002, 0.002, 0.004])
        kf.P *= 10.0
        # Increased process noise for faster adaptation.
        kf.Q = np.eye(6) * 0.0001
        return kf

    def update_dt(self, dt):
        self.dt = dt
        F = np.array([
            [1, 0, 0, dt, 0, 0],
            [0, 1, 0, 0, dt, 0],
            [0, 0, 1, 0, 0, dt],
            [0, 0, 0, 1, 0, 0],
            [0, 0, 0, 0, 1, 0],
            [0, 0, 0, 0, 0, 1]
        ])
        self.filter_right.F = F.copy()
        self.filter_left.F = F.copy()

    def process(self, eye_pos, dt):
        if dt > self.max_dt:
            # Reset filters if time delta too high.
            right, left = eye_pos
            right = np.array(right)
            left = np.array(left)
            self.filter_right.x = np.array([right[0], right[1], right[2], 0, 0, 0])
            self.filter_left.x = np.array([left[0], left[1], left[2], 0, 0, 0])
            self.initialized = True
            return (right.tolist(), left.tolist())
        self.update_dt(dt)
        right, left = eye_pos
        right = np.array(right)
        left = np.array(left)
        if not self.initialized:
            self.filter_right.x = np.array([right[0], right[1], right[2], 0, 0, 0])
            self.filter_left.x = np.array([left[0], left[1], left[2], 0, 0, 0])
            self.initialized = True
            filtered_right = right
            filtered_left = left
        else:
            self.filter_right.predict()
            self.filter_left.predict()
            pred_right = self.filter_right.x[:3]
            pred_left = self.filter_left.x[:3]
            right_corr = [r if abs(r - p) <= self.threshold else p 
                          for r, p in zip(right, pred_right)]
            left_corr = [l if abs(l - p) <= self.threshold else p 
                         for l, p in zip(left, pred_left)]
            self.filter_right.update(np.array(right_corr))
            self.filter_left.update(np.array(left_corr))
            filtered_right = self.filter_right.x[:3]
            filtered_left = self.filter_left.x[:3]
        return (filtered_right.tolist(), filtered_left.tolist())

class KalmanFilterAccelProcessor():
    def __init__(self, dt=1.0, threshold=0.15, max_dt=0.5):
        self.dt = dt
        self.threshold = threshold      # 各座標ごとの閾値
        self.max_dt = max_dt            # dtがこれを超えた場合はリセット
        self.filter_right = self._init_filter()
        self.filter_left = self._init_filter()
        self.initialized = False

    def _init_filter(self):
        dim_x = 9
        kf = KalmanFilter(dim_x=dim_x, dim_z=3)
        dt = self.dt
        dt2 = 0.5 * dt * dt
        kf.F = np.array([
            [1, 0, 0,    dt, 0,  0,   dt2, 0,   0],
            [0, 1, 0,    0,  dt, 0,   0,   dt2, 0],
            [0, 0, 1,    0,  0,  dt,  0,   0,   dt2],
            [0, 0, 0,    1,  0,  0,   dt,  0,   0],
            [0, 0, 0,    0,  1,  0,   0,   dt,  0],
            [0, 0, 0,    0,  0,  1,   0,   0,   dt],
            [0, 0, 0,    0,  0,  0,   1,   0,   0],
            [0, 0, 0,    0,  0,  0,   0,   1,   0],
            [0, 0, 0,    0,  0,  0,   0,   0,   1]
        ])
        # 測定は位置のみなので、Hは3×9で左上が単位行列
        kf.H = np.hstack([np.eye(3), np.zeros((3, 6))])
        # x, yは比較的精度が高いと仮定
        kf.R = np.diag([0.05, 0.05, 0.05])
        kf.P *= 10.0
        # プロセスノイズは実際の加速度のばらつきを考慮して調整
        kf.Q = np.eye(dim_x) * 0.001
        return kf

    def update_dt(self, dt):
        self.dt = dt
        dt2 = 0.5 * dt * dt
        F = np.array([
            [1, 0, 0,    dt, 0,  0,   dt2, 0,   0],
            [0, 1, 0,    0,  dt, 0,   0,   dt2, 0],
            [0, 0, 1,    0,  0,  dt,  0,   0,   dt2],
            [0, 0, 0,    1,  0,  0,   dt,  0,   0],
            [0, 0, 0,    0,  1,  0,   0,   dt,  0],
            [0, 0, 0,    0,  0,  1,   0,   0,   dt],
            [0, 0, 0,    0,  0,  0,   1,   0,   0],
            [0, 0, 0,    0,  0,  0,   0,   1,   0],
            [0, 0, 0,    0,  0,  0,   0,   0,   1]
        ])
        self.filter_right.F = F.copy()
        self.filter_left.F = F.copy()

    def process(self, eye_pos, dt):
        if dt > self.max_dt:
            # dtが大きすぎる場合はフィルタをリセット
            right, left = eye_pos
            right = np.array(right)
            left = np.array(left)
            self.filter_right.x = np.array([right[0], right[1], right[2], 0, 0, 0, 0, 0, 0])
            self.filter_left.x = np.array([left[0], left[1], left[2], 0, 0, 0, 0, 0, 0])
            self.initialized = True
            return (right.tolist(), left.tolist())
        self.update_dt(dt)
        right, left = eye_pos
        right = np.array(right)
        left = np.array(left)
        if not self.initialized:
            self.filter_right.x = np.array([right[0], right[1], right[2], 0, 0, 0, 0, 0, 0])
            self.filter_left.x = np.array([left[0], left[1], left[2], 0, 0, 0, 0, 0, 0])
            self.initialized = True
            filtered_right = right
            filtered_left = left
        else:
            self.filter_right.predict()
            self.filter_left.predict()
            pred_right = self.filter_right.x[:3]
            pred_left = self.filter_left.x[:3]
            right_corr = [r if abs(r - p) <= self.threshold else p 
                          for r, p in zip(right, pred_right)]
            left_corr = [l if abs(l - p) <= self.threshold else p 
                         for l, p in zip(left, pred_left)]
            self.filter_right.update(np.array(right_corr))
            self.filter_left.update(np.array(left_corr))
            filtered_right = self.filter_right.x[:3]
            filtered_left = self.filter_left.x[:3]
        return (filtered_right.tolist(), filtered_left.tolist())

class OneEuroFilterProcesser():
    def __init__(self, min_cutoff=1.0, beta=0.0, d_cutoff=1.0):
        self.min_cutoff = min_cutoff  # 基本のカットオフ周波数
        self.beta = beta              # 速度依存で調整する係数
        self.d_cutoff = d_cutoff      # 微分値の低域通過カットオフ周波数
        self.t = None               # 内部の時刻
        # 各目、各軸ごとにOneEuroFilterインスタンスを生成（x,y,z）
        self.filters_right = [self.OneEuroFilter(min_cutoff, beta, d_cutoff) for _ in range(3)]
        self.filters_left = [self.OneEuroFilter(min_cutoff, beta, d_cutoff) for _ in range(3)]

    class OneEuroFilter:
        def __init__(self, min_cutoff, beta, d_cutoff):
            self.min_cutoff = min_cutoff
            self.beta = beta
            self.d_cutoff = d_cutoff
            self.x_prev = None
            self.dx_prev = 0.0
            self.t_prev = None

        def alpha(self, cutoff, dt):
            import math
            tau = 1.0 / (2 * math.pi * cutoff)
            return 1.0 / (1.0 + tau / dt)

        def filter(self, x, t):
            if self.t_prev is None:
                self.t_prev = t
                self.x_prev = x
                return x
            dt = t - self.t_prev
            self.t_prev = t
            dx = (x - self.x_prev) / dt if dt > 0 else 0.0
            alpha_d = self.alpha(self.d_cutoff, dt)
            dx_hat = alpha_d * dx + (1 - alpha_d) * self.dx_prev
            self.dx_prev = dx_hat
            cutoff = self.min_cutoff + self.beta * abs(dx_hat)
            alpha_x = self.alpha(cutoff, dt)
            x_hat = alpha_x * x + (1 - alpha_x) * self.x_prev
            self.x_prev = x_hat
            return x_hat

    def process(self, eye_pos, dt):
        if self.t is None:
            self.t = 0.0
        self.t += dt
        right, left = eye_pos
        filtered_right = []
        filtered_left = []
        for i in range(3):
            filtered_right.append(self.filters_right[i].filter(right[i], self.t))
            filtered_left.append(self.filters_left[i].filter(left[i], self.t))
        return (filtered_right, filtered_left)
