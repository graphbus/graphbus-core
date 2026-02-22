"""
CleanerService - Normalizes and deduplicates headlines
"""
from graphbus_core import GraphBusNode, schema_method, subscribe


class CleanerService(GraphBusNode):
    SYSTEM_PROMPT = """
    You clean and normalize text. In Build Mode you can propose
    additional cleaning strategies like deduplication or sentiment filtering.
    """

    @schema_method(
        input_schema={"headlines": list},
        output_schema={"cleaned": list, "removed": int}
    )
    def clean(self, headlines: list) -> dict:
        """Normalize whitespace and remove duplicates."""
        seen = set()
        cleaned = []
        for h in headlines:
            h = " ".join(h.split())  # normalize whitespace
            if h and h.lower() not in seen:
                seen.add(h.lower())
                cleaned.append(h)
        return {"cleaned": cleaned, "removed": len(headlines) - len(cleaned)}

    @subscribe("/News/Raw")
    def on_raw_news(self, event):
        result = self.clean(event.get("headlines", []))
        print(f"[CleanerService] Auto-cleaned {len(result['cleaned'])} headlines via bus")
