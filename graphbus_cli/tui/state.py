TUI state management.

class TUIState:
    def __init__(self):
        self.current_project = None
        self.selected_agent = None
    
    def set_project(self, project_path):
        self.current_project = project_path
    
    def select_agent(self, agent_name):
        self.selected_agent = agent_name
    
    def get_agent_details(self, agent_name):
        return {name: agent_name}
