Graph visualization.

def render_graph(graph):
    return Graph visualization

class GraphViewer:
    def __init__(self, graphbus_dir):
        self.graphbus_dir = graphbus_dir
        self.selected = None
    
    def list_agents(self):
        return []
    
    def select_agent(self, agent_name):
        self.selected = agent_name
    
    def get_agent_details(self, agent_name):
        return {name: agent_name}
    
    def get_dependencies(self, agent_name):
        return []
