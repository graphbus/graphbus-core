Intent tracking.

class IntentManager:
    def __init__(self, intent=None):
        self.intent = intent

class IntentCompletion:
    def __init__(self, intent):
        self.intent = intent
    def generate(self):
        raise NotImplementedError

class OutcomeSummary:
    def generate(self):
        raise NotImplementedError
