# core/utils/errors.py

"""
Custom exception hierarchy for orchestration system.
"""

from typing import Optional, Any, Dict


class OrchestrationError(Exception):
    """Base exception for all orchestration errors"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message)
        self.details = kwargs


class NodeError(OrchestrationError):
    """Exception raised by a node"""
    
    def __init__(
        self,
        message: str,
        node_name: str,
        original_error: Optional[Exception] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.node_name = node_name
        self.original_error = original_error


class WorkflowError(OrchestrationError):
    """Exception raised by a workflow"""
    
    def __init__(
        self,
        message: str,
        workflow_name: str,
        failed_node: Optional[str] = None,
        original_error: Optional[Exception] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.workflow_name = workflow_name
        self.failed_node = failed_node
        self.original_error = original_error


class ValidationError(OrchestrationError):
    """Exception for validation failures"""
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.field = field
        self.value = value


class TimeoutError(OrchestrationError):
    """Exception for timeout failures"""
    
    def __init__(
        self,
        message: str,
        timeout_seconds: float,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.timeout_seconds = timeout_seconds


class CachingError(OrchestrationError):
    """Exception for caching failures"""
    
    def __init__(
        self,
        message: str,
        cache_key: Optional[str] = None,
        operation: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.cache_key = cache_key
        self.operation = operation