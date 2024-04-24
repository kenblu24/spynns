from .node import Node as BaseNode
# from .network import Network as BaseNetwork
from .spike import Spike
from .edge import Edge

# typing:
from typing import override


class EgoSpike(Spike):
    pass


class PlasticNode(BaseNode):
    T_ACT = 0.5
    LTP_MAX = LTD_MAX = 0.5

    def __init__(self, *args, **kwargs, ):
        super().__init__(*args, **kwargs)
        # self.relevance = []
        # self.ego = []
        # self.hardening = 0
        # self._t_lastego = 0
        self.old_spikes = []

    @override
    def step_fire(self):
        super().step_fire()

    # def adjust(self):
    #     for es in self.ego:
    #         pass

    @override
    def step_integrate(self):
        # self.adjust()
        # self.ego += [s for s in self.intake if isinstance(s, EgoSpike)]
        # self.intake = [s for s in self.intake if not isinstance(s, EgoSpike)]
        super().step_integrate()
        t_lastfire = self._t_lastfire if self._t_lastfire is not None else 0
        for spike in self.intake:
            dt = spike.time - t_lastfire
            if 0 < dt < self.T_ACT and spike.source is not None:
                spike.source.weight -= max(0.01 / dt, self.LTD_MAX)
        self.old_spikes += self.intake

    @override
    def fire(self):
        super().fire()
        for spike in self.old_spikes:
            dt = spike.time - self.net.time
            if -self.T_ACT < dt and spike.source is not None:
                if dt == 0:
                    potentiation = self.LTP_MAX
                else:
                    potentiation = max(0.01 / dt, self.LTP_MAX)
                spike.source.weight -= potentiation
        self.old_spikes = []  # clear

    @override
    def clear_intake(self):
        super().clear_intake()

        def spike_is_recent(spike):
            dt = spike.time - self.net.time
            return -self.T_ACT < dt

        self.old_spikes = list(filter(spike_is_recent, self.old_spikes))

    # def apply_target(self, amplitude, delay=0):
    #     # queue a training spike to be sent to this neuron
    #     self.net.schedule(EgoSpike(
    #         amplitude=amplitude,
    #         time=self.net.time + delay,
    #         source=None,
    #         destination=self,
    #     ))


class PlasticEdge(Edge):
    @override
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @override
    def fire(self):
        super().fire()


# class Network(BaseNetwork):
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)

#     def runtil(self, t, clear_histories=True):
#         if clear_histories:  # by default, clear history to prevent memory leak
#             self.clear_histories()
#         if t < self.time:  # sanity check. Only move forward in time...
#             raise ValueError(f"Cannot reverse time. (called with t={t}, which is before current time {self.net.time})")
#         while True:
#             if self.queue:  # if queue is not empty
#                 # get the time of next spike
#                 t_next = min(self.queue, key=lambda s: s.time).time
#             else:
#                 break
#             if t_next < t:  # only continue up until end time `t`
#                 # gather spikes that arrive at t_next
#                 spikes = self.collect_at(self.queue, t_next)
#             else:
#                 break
#             # -------
#             self.time = t_next  # SET NETWORK TIME
#             # -------
#             nodes_to_update = set()  # avoid duplicate update calls
#             for spike in spikes:
#                 nodes_to_update.add(spike.destination)  # process them later
#                 spike.destination.intake.append(spike)  # add spike to node
#                 self.queue.remove(spike)

#             # process them now
#             for node in nodes_to_update:
#                 node.step_integrate()  # integrate
#                 node.clear_intake()  # clear
#             for node in nodes_to_update:
#                 node.step_fire()  # fire if conditions are met
#         # -------
#         self.time = t  # set the network time even if no spikes
#         -------

#
