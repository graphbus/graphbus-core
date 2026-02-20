"""
FetcherService - Pulls mock news headlines
"""
from graphbus_core import GraphBusNode, schema_method


class FetcherService(GraphBusNode):
    SYSTEM_PROMPT = """
    You fetch news headlines. In Build Mode you can propose improvements
    to how headlines are structured or filtered.
    """

    @schema_method(
        input_schema={"topic": str},
        output_schema={"headlines": list}
    )
    def fetch_headlines(self, topic: str = "technology") -> dict:
        """Return mock headlines for a given topic."""
        mock_data = {
            "technology": [
                "GraphBus framework hits 1000 stars on GitHub",
                "Multi-agent systems reshape software development in 2026",
                "LLM-powered code refactoring now production-ready",
                "  Whitespace-heavy    headline   needs cleaning  ",
            ],
            "default": [
                "Breaking: AI agents now write their own agents",
                "Study shows 80% of developers use AI daily",
            ]
        }
        return {"headlines": mock_data.get(topic, mock_data["default"])}
