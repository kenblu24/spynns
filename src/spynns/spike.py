from typing import Any, NamedTuple, TYPE_CHECKING

# typing:
# if TYPE_CHECKING:
#     from .node import Node


class Spike(NamedTuple):
    amplitude: float
    time: float
    source: Any
    destination: Any
