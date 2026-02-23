Model tier editor.

class ModelEditor:
    def __init__(self, graphbus_dir):
        self.graphbus_dir = graphbus_dir
        self.selected = None
    
    def list_agents(self):
        return []
    
    def select_agent(self, agent_name):
        self.selected = agent_name
    
    def get_override_options(self, agent_name):
        return [light, medium, heavy]
    
    def apply_override(self, agent_name, tier, model):
        pass
    
    def revert_override(self, agent_name):
        pass
    
    def get_agent_status(self, agent_name):
        return {}
