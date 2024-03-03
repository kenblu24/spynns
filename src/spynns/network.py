from .edge import Edge
from .node import Node

DEFAULT_DATA = {
    "Associated_Data": {
        "application": {
        },
        "label": None,
        "processor": {
            "Leak_Enable": True,
            "Max_Leak": 4,
            "Min_Leak": -1,
            "Max_Weight": 127,
            "Min_Weight": -127,
            "Max_Threshold": 127,
            "Min_Threshold": 0,
            "Max_Synapse_Delay": 300,
            "Min_Synapse_Delay": 0,
            "Max_Axon_Delay": 0,
            "Min_Axon_Delay": 0,
        }
    }
}

DEFAULT_NETWORK_PROPERTIES = {"network_properties": []}

DEFAULT_NODE_PROPERTIES = {"node_properties": [
    {
        "index": 0,
        "name": "Threshold",
        "max_value": 127.0,
        "min_value": 0.0,
        "size": 1,
        "type": 73
    },
    {
        "index": 1,
        "name": "Leak",
        "max_value": 4.0,
        "min_value": -1.0,
        "size": 1,
        "type": 73
    },
    {
        "index": 2,
        "name": "Delay",
        "max_value": 0.0,
        "min_value": 0.0,
        "size": 1,
        "type": 73
    },
]}

DEFAULT_EDGE_PROPERTIES = {"edge_properties": [
    {
        "index": 0,
        "name": "Weight",
        "max_value": 127.0,
        "min_value": -127.0,
        "size": 1,
        "type": 73
    },
    {
        "index": 1,
        "name": "Delay",
        "max_value": 300.0,
        "min_value": 0.0,
        "size": 1,
        "type": 73
    },
]}

DEFAULT_CASPIAN_PROPERTIES = {"Properties": {
    **DEFAULT_NETWORK_PROPERTIES,
    **DEFAULT_NODE_PROPERTIES,
    **DEFAULT_EDGE_PROPERTIES
}}


def get_key(dict_view, item):
    for key, value in dict_view:
        if value == item:
            return key  # this isn't optimal but whatever


class Network:
    def __init__(self):
        self.time = 0
        self.nodeset = set()
        self.queue = []

    def runfor(self, t, **kwargs):
        return self.runtil(self.time + t, **kwargs)

    def runtil(self, t, clear_histories=True):
        if clear_histories:
            self.clear_histories()
        if t < self.time:
            raise ValueError(f"Cannot reverse time. (called with t={t}, which is before current time {self.net.time})")
        while True:
            if self.queue:
                t_next = min(self.queue, key=lambda s: s.time).time
            else:
                break
            if t_next < t:
                spikes = self.collect_at(self.queue, t_next)
            else:
                break

            self.time = t_next  # SET NETWORK TIME

            nodes_to_update = set()  # avoid duplicate update calls
            for spike in spikes:
                nodes_to_update.add(spike.destination)  # process them later
                spike.destination.intake.append(spike)  # add spike to node
                self.queue.remove(spike)

            for node in nodes_to_update:
                node.step_integrate()
                node.clear_intake()
            for node in nodes_to_update:
                node.step_fire()

        self.time = t

    def clear_histories(self):
        for node in self.nodeset:
            node.clear_history()

    @staticmethod
    def collect_before(queue, t):
        # collect spikes in queue before a certain time
        q = [s for s in queue if s.time < t]
        return sorted(q, key=lambda s: s.time)

    @staticmethod
    def collect_at(queue, t):
        return [s for s in queue if s.time == t]

    def schedule(self, *spikes):
        self.queue += spikes


def charges(nodes):
    return [node.charge for node in nodes]


def fires(nodes):
    return [node.fires for node in nodes]


def lastfires(nodes):
    return [node.t_lastfire for node in nodes]


def vectors(nodes):
    return [node.t_fires for node in nodes]


def _connect(parent, child, weight=0, delay=0, **kwargs):
    edge = Edge(child, weight, delay, **kwargs)
    parent.output_edges.append(edge)
    return edge


def make_layer(n) -> list[Node]:
    return [Node() for _ in range(n)]


def network_from_json(j: dict) -> (dict[Node], list[Node], list[Node]):
    # read a Tennlab json network and create it.
    def mapping(props: list[dict]):
        return {prop['name']: prop['index'] for prop in props}

    # get mapping of property name to index in 'values' list i.e. m_n['Delay'] -> 1
    # need this because the network json represents the node/edge params as an
    # unordered list i.e. 'values': [127, -1, 0] <-- threshold, leak, delay
    m_n = node_mapping = mapping(j['Properties']['node_properties'])
    m_e = edge_mapping = mapping(j['Properties']['edge_properties'])

    # make nodes from json
    j_nodes = sorted(j['Nodes'], key=lambda v: v['id'])
    nodes = [(n['id'], n['values']) for n in j_nodes]
    nodes = {idx: Node(
        threshold=v[m_n["Threshold"]],
        delay=v[m_n["Delay"]],
        leak=v[m_n["Leak"]],
    ) for idx, v in nodes}

    # make connections from json
    for edge in j['Edges']:
        connect(
            nodes[edge['from']],
            nodes[edge['to']],
            weight=edge['values'][m_e['Weight']],
            delay=edge['values'][m_e['Delay']],
        )

    inputs = [nodes[i] for i in j['Inputs']]
    outputs = [nodes[i] for i in j['Outputs']]
    return nodes, inputs, outputs  # node is a dict so as to preserve the ids
    # use list(nodes.values()) to make it a list for casPYan functions


def to_tennlab(
    nodes,
    inputs,
    outputs,
    data=DEFAULT_DATA,  # use {} instead of None
    properties: dict = DEFAULT_CASPIAN_PROPERTIES,
) -> dict:
    d = {}

    if isinstance(nodes, list):
        nodes = dict(enumerate(nodes)).items()
    elif isinstance(nodes, dict):
        nodes = nodes.items()

    def mapping(props: list[dict]):
        return {prop['index']: prop['name'] for prop in props}

    def node_dict(node):
        delay, leak = node.delay, node.leak
        return {
            'Threshold': node.threshold,
            'Delay': 0 if delay is None else delay,
            'Leak': -1 if leak is None else leak
        }

    def edge_dict(edge):
        return {
            'Weight': edge.weight,
            'Delay': edge.delay
        }

    m_n = node_mapping = mapping(properties['Properties']['node_properties'])
    m_e = edge_mapping = mapping(properties['Properties']['edge_properties'])

    j_nodes = [
        {
            'id': i,
            'values': [
                node_dict(node)[m_n[0]],
                node_dict(node)[m_n[1]],
                node_dict(node)[m_n[2]]
            ]
        }
        for i, node in nodes
    ]

    def edges(nodes):
        for parent_id, node in nodes:
            for edge in node.output_edges:
                yield parent_id, get_key(nodes, edge.output_node), edge

    j_edges = [
        {
            'from': parent_id,
            'to': child_id,
            'values': [
                edge_dict(edge)[m_e[0]],
                edge_dict(edge)[m_e[1]],
            ]
        }
        for parent_id, child_id, edge in edges(nodes)
    ]

    input_ids = [get_key(nodes, node) for node in inputs]
    output_ids = [get_key(nodes, node) for node in outputs]

    d.update(data)
    d.update(properties)
    d.update({'Nodes': j_nodes})
    d.update({'Inputs': input_ids})
    d.update({'Outputs': output_ids})
    d.update({'Edges': j_edges})
    d.update({'Network_Values': []})

    return d
