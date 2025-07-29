import time

class FPSTimer:
    def __init__(self, max_samples=30):
        self.times = []
        self.max_samples = max_samples
        self.last_time = None

    def update(self):
        now = time.time()
        if self.last_time is not None:
            dt = now - self.last_time
            self.times.append(dt)
            if len(self.times) > self.max_samples:
                self.times.pop(0)
        self.last_time = now

    def get_fps(self):
        total = sum(self.times)
        return len(self.times) / total if total > 0 else 0
