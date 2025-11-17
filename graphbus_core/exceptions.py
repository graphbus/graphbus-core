"""
GraphBus-specific exception types for better error handling
"""


class GraphBusError(Exception):
    """Base exception for all GraphBus errors"""
    pass


class AgentError(GraphBusError):
    """Base exception for agent-related errors"""
    pass


class LLMError(AgentError):
    """Errors related to LLM operations"""
    pass


class LLMResponseError(LLMError):
    """LLM response was invalid or could not be parsed"""
    def __init__(self, message: str, raw_response: str = None):
        super().__init__(message)
        self.raw_response = raw_response


class IntentRelevanceError(AgentError):
    """Failed to check intent relevance"""
    pass


class CodeAnalysisError(AgentError):
    """Failed to analyze code"""
    pass


class ProposalGenerationError(AgentError):
    """Failed to generate proposal"""
    pass


class EvaluationError(AgentError):
    """Failed to evaluate proposal"""
    pass


class NegotiationError(GraphBusError):
    """Base exception for negotiation-related errors"""
    pass


class ConvergenceError(NegotiationError):
    """Negotiation failed to converge"""
    pass


class BuildError(GraphBusError):
    """Errors during build process"""
    pass


class ValidationError(GraphBusError):
    """Validation failures"""
    pass


class RefactoringValidationError(ValidationError):
    """Refactoring validation failed"""
    def __init__(self, message: str, validation_result: dict = None):
        super().__init__(message)
        self.validation_result = validation_result


class ContractValidationError(ValidationError):
    """Contract validation failed"""
    def __init__(self, message: str, breaking_changes: list = None):
        super().__init__(message)
        self.breaking_changes = breaking_changes or []


class GitWorkflowError(GraphBusError):
    """Errors in git workflow operations"""
    pass


class SessionError(GraphBusError):
    """Errors in negotiation session management"""
    pass
