from .edge import Edge
from .spike import Spike


class Node:
    def __init__(self, net, threshold=0, leak=None, refractory=0.1):
        self.net = net
        self.charge = 0
        self.threshold = threshold  # if charge > threshold, fire.
        self.leak = None if leak == -1 else leak  # None or -1 disables leak.
        self.refractory: float | callable = refractory
        self.intake = []  # waiting area for incoming spikes to be dealt with for the current moment
        self.output_edges = []  # outgoing connections
        self.history = []  # times of fires [-1] is most recent fire.
        # history may be wiped by external methods.
        self._t_lastfire: float | None = None  # but this should never be cleared (would break refractory)
        self._t_lastcheck = 0

        self.callback_prestep_fire = lambda x: None
        self.callback_prestep_integrate = lambda x: None

        self.net.nodeset.add(self)

    def step_fire(self):
        # check if this neuron meets the criteria to fire, and record if it do.
        self.callback_prestep_fire(self)

        charged_up = self.charge > self.threshold

        if self._t_lastfire is None:  # if never fired before...
            refractory_period_passed = True  # ignore refractory period.
        elif callable(self.refractory):  # allow for custom refractory function
            refractory_period_passed: bool = self.refractory(self)
        else:  # prevent firing if within refractory period.
            refractory_period_passed = self.net.time > self._t_lastfire + self.refractory

        if charged_up and refractory_period_passed:
            self.fire()

    def step_integrate(self):
        self.callback_prestep_integrate(self)
        # apply leak. charge = 2^(-t/tau) where t is elapsed time.
        if self.leak is not None:
            dt = self.net.time - self._t_lastcheck  # elapsed time
            self.charge = self.charge * 2 ** (-dt / (2 ** self.leak))
        # add/integrate charge from spikes in intake
        self.charge += sum([spike.amplitude for spike in self.intake])
        # this function does not clear the intake or consume the spikes.
        # that is the responsibility of the caller (i.e. spynns.network.runtil)
        # this allows for inheritance to easily extend functionality here.
        self._t_lastcheck = self.net.time

    def clear_intake(self):
        self.intake = []

    def fire(self):
        self.history.append(self.net.time)  # record time of fire
        self._t_last_fire = self.net.time  # remember time of fire for refractory
        for edge in self.output_edges:
            edge.fire()  # send spikes out
        self.charge = 0  # reset charge

    def clear_history(self):
        self.history = []

    def apply_spike(self, amplitude, delay=0):
        # queue a spike to be sent to this neuron
        self.net.schedule(Spike(
            amplitude=amplitude,
            time=self.net.time + delay,
            source=None,
            destination=self,
        ))

    def add_output(self, child, weight, delay, **kwargs):
        # connect from this node to a destination node
        edge = Edge(self.net, self, child, weight, delay, **kwargs)
        self.output_edges.append(edge)
        return edge

    @property
    def fires(self):
        # the number of fires from this neuron
        return len(self.history)

    @property
    def t_lastfire(self):
        # get time of most recent fire
        try:
            return self.history[-1]
        except IndexError:
            return float('nan')  # if no fires in history, return NaN

    @property
    def t_fires(self):
        # indexes of fires
        return self.history

    def __repr__(self):
        connected = [e.__repr__() for e in self.output_edges]
        return f"Node at {id(self):x} w/ Threshold: {self.threshold}, Leak: {self.leak}, refract: {self.refractory}, connections: {connected}"
