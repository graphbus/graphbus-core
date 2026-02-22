"""
FormatterService - Renders a human-readable digest
"""
from graphbus_core import GraphBusNode, schema_method
from datetime import datetime


class FormatterService(GraphBusNode):
    SYSTEM_PROMPT = """
    You format news digests. In Build Mode you can propose richer output
    formats like markdown, HTML, or priority ordering.
    """

    @schema_method(
        input_schema={"headlines": list, "topic": str},
        output_schema={"digest": str}
    )
    def format_digest(self, headlines: list, topic: str = "technology") -> dict:
        """Render a simple text digest."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        lines = [f"📰 News Digest — {topic.title()} — {now}", "=" * 50]
        for i, h in enumerate(headlines, 1):
            lines.append(f"  {i}. {h}")
        lines.append("=" * 50)
        return {"digest": "\n".join(lines)}
