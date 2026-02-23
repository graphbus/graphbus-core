"""Task manager for async agent dispatch."""

from typing import Optional, Dict, Any


class TaskManager:
    """Manages async execution of agent tasks."""
    
    def __init__(self, timeout_per_agent: int = 30):
        self.timeout_per_agent = timeout_per_agent
    
    def spawn(self, agent):
        """Spawn an agent as async task."""
        raise NotImplementedError
    
    def spawn_agent(self, agent):
        """Alias for spawn."""
        return self.spawn(agent)
    
    def run_concurrently(self, agents):
        """Run multiple agents concurrently."""
        raise NotImplementedError
    
    def execute_agents(self, agents):
        """Alias for run_concurrently."""
        return self.run_concurrently(agents)
    
    def cancel(self, task_id):
        """Cancel a task."""
        raise NotImplementedError
    
    def cancel_task(self, task_id):
        """Alias for cancel."""
        return self.cancel(task_id)
    
    def prepare_agent_context(self, agent, round_num):
        """Prepare context for agent execution."""
        raise NotImplementedError
