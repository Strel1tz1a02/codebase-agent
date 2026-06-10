class CodebaseAgentError(Exception):
    """Base error for codebase-agent domain failures."""


class ConfigurationError(CodebaseAgentError):
    """Raised when project configuration is missing or invalid."""


class ProviderError(CodebaseAgentError):
    """Raised when an LLM or embedding provider cannot be used."""


class ProjectNotFoundError(CodebaseAgentError):
    """Raised when a requested project does not exist."""


class RagIndexNotReadyError(CodebaseAgentError):
    """Raised when the RAG index is required but not built or loaded."""


class PathSafetyError(CodebaseAgentError):
    """Raised when a file path escapes the allowed repository root."""


class ToolExecutionError(CodebaseAgentError):
    """Raised when an Agent tool fails during execution."""


class GraphExecutionError(CodebaseAgentError):
    """Raised when the LangGraph workflow cannot complete."""
