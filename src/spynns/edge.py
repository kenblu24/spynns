from .spike import Spike


class Edge:
    def __init__(self, net, parent, child, weight, delay):
        self.net = net
        self.weight = weight
        self.delay = delay
        self.parent = parent
        self.child = child  # destination for spikes

        if self.delay <= 0:
            raise ValueError(f"Delay must be strictly positive (delay > 0). Got {delay} instead.")

    def fire(self):
        self.net.schedule(Spike(
            amplitude=self.weight,
            time=self.net.time + self.delay,
            source=self,
            destination=self.child,
        ))

    def __repr__(self):
        child_id = f"{id(self.child):x}"[-4:]
        return f"<Edge w: {self.weight}, d: {self.delay}, dest: {child_id}>"
