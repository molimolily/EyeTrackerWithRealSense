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
        return len(self.times) / total if total > 0 else 0
