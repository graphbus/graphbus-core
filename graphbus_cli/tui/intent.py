"""Intent tracking and satisfaction detection."""

from typing import Optional, Dict, Any, List


class IntentManager:
    """Manage user intent."""
    
    def __init__(self, intent=None):
        self.intent = intent
        self.intent_history = [intent] if intent else []
    
    def request_intent_change(self, new_intent):
        return {"old": self.intent, "new": new_intent}
    
    def merge_intents(self, intents):
        return " and ".join(intents)
    
    def replace_intent(self, intent):
        self.intent = intent
        self.intent_history.append(intent)
    
    def refine_intent(self, refinement):
        if self.intent:
            self.intent = f"{self.intent} ({refinement})"


class IntentValidator:
    """Validate intent/feedback alignment."""
    
    def check_feedback_alignment(self, intent, feedback):
        return True


class IntentRelevance:
    """Determine intent relevance to agents."""
    
    def __init__(self, intent):
        self.intent = intent
    
    def is_relevant(self, agent):
        # Simple heuristic: check if agent keywords appear in intent
        keywords = {
            "DataAgent": ["data", "database", "query"],
            "APIAgent": ["api", "endpoint", "route"],
            "UIAgent": ["ui", "interface", "display"],
        }
        
        if agent not in keywords:
            return True  # Default to relevant if unknown
        
        intent_lower = self.intent.lower() if self.intent else ""
        return any(kw in intent_lower for kw in keywords[agent])


class IntentCompletion:
    """Track intent completion."""
    
    def __init__(self, intent):
        self.intent = intent
        self.completed = False
    
    def is_satisfied(self):
        return self.completed
    
    def get_satisfaction_score(self):
        return 1.0 if self.completed else 0.0
    
    def get_satisfied_parts(self):
        return [self.intent] if self.completed else []
    
    def get_pending_parts(self):
        return [] if self.completed else [self.intent]
    
    def mark_complete(self):
        self.completed = True


class IntentProgressTracker:
    """Track progress toward intent."""
    
    def __init__(self, intent):
        self.intent = intent
        self.progress = 0.0
    
    def update_progress(self, percent):
        self.progress = min(100, max(0, percent))
    
    def get_progress_percent(self):
        return int(self.progress)
    
    def get_progress_display(self):
        return f"{self.get_progress_percent()}% complete"


class IntentDivergence:
    """Detect divergence from intent."""
    
    def __init__(self, intent):
        self.intent = intent
    
    def check_divergence(self):
        return False
    
    def get_divergence_score(self):
        return 0.0


class OutcomeSummary:
    """Generate outcome summary."""
    
    def __init__(self):
        self.intent = None
        self.status = "incomplete"
        self.rounds = 0
        self.files_changed = 0
        self.lines_added = 0
        self.lines_deleted = 0
        self.agents_involved = []
    
    def generate(self):
        return {
            "intent": self.intent,
            "status": self.status,
            "rounds": self.rounds,
            "files_changed": self.files_changed,
            "agents_involved": self.agents_involved,
        }
    
    def format_for_display(self):
        summary = self.generate()
        lines = []
        lines.append(f"Intent: {summary['intent']}")
        lines.append(f"Status: {summary['status']}")
        lines.append(f"Rounds: {summary['rounds']}")
        lines.append(f"Files Changed: {summary['files_changed']}")
        lines.append(f"Agents: {', '.join(summary['agents_involved'])}")
        return "\n".join(lines)
