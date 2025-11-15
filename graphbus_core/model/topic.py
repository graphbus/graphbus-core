"""
Pub/Sub topic primitives
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Topic:
    """
    A pub/sub topic that agents can publish to or subscribe from.
    """
    name: str  # e.g. "/Order/Created", "/Hello/MessageGenerated"

    def __str__(self) -> str:
        return self.name


@dataclass
class Subscription:
    """
    A subscription linking a node to a topic.
    """
    node_name: str
    topic: Topic
    handler_name: str  # method to call when event arrives

    def to_dict(self) -> dict:
        return {
            "node_name": self.node_name,
            "topic": self.topic.name,
            "handler_name": self.handler_name
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Subscription":
        return cls(
            node_name=data["node_name"],
            topic=Topic(data["topic"]),
            handler_name=data["handler_name"]
        )
