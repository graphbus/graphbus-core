"""Negotiation tracking and display."""

from typing import Dict, Any, Optional


def load_negotiation_summary(graphbus_dir):
    """Load negotiation summary."""
    return None


def format_negotiation_display(status):
    """Format negotiation status for display."""
    lines = []
    lines.append(f"Status: {status.get('status')}")
    lines.append(f"Round: {status.get('round')}")
    lines.append(f"Proposals: {status.get('proposals')}")
    lines.append(f"Accepted: {status.get('accepted')}")
    return "\n".join(lines)
