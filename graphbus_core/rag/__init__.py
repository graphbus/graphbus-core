"""
Code-graph RAG integration for quorum-based consensus during negotiations.
"""

from graphbus_core.rag.code_graph import (
    CodeGraph,
    CodeGraphBackend,
    CgrBackend,
    LocalBackend,
)
from graphbus_core.rag.quorum import QuorumResolver


def decode_protobuf_to_json(index_bin_path: str, output_json_path: str) -> None:
    """Decode a cgr protobuf index.bin to graph.json.

    Convenience wrapper around :meth:`CgrBackend._decode_protobuf_to_json`.
    Does **not** require the ``cgr`` runtime — only ``codec.schema_pb2`` and
    ``google.protobuf``.
    """
    CgrBackend._decode_protobuf_to_json(index_bin_path, output_json_path)


__all__ = [
    "CodeGraph",
    "CodeGraphBackend",
    "CgrBackend",
    "LocalBackend",
    "QuorumResolver",
    "decode_protobuf_to_json",
]
