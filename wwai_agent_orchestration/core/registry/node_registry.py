# core/registry/node_registry.py

"""
Node Registry for discovering and managing atomic operations.
Nodes are single-purpose functions registered via decorator.

SIMPLIFIED: Removed phase and parallel_group fields.
Only core streaming UI fields remain: display_name, show_node, show_output.
"""

from wwai_agent_orchestration.core.observability.logger import get_logger
from typing import Dict, Callable, Optional, List
from dataclasses import dataclass
from enum import Enum

logger = get_logger(__name__)


class RetryStrategy(Enum):
    """Retry strategies for node execution"""
    NONE = "none"
    SIMPLE = "simple"
    EXPONENTIAL = "exponential"


@dataclass
class NodeMetadata:
    """
    Metadata for a registered node.
    
    SIMPLIFIED: Only essential fields for streaming UI.
    """
    # Core fields
    name: str
    func: Callable
    description: Optional[str] = None
    max_retries: int = 1
    retry_strategy: RetryStrategy = RetryStrategy.SIMPLE
    timeout: Optional[int] = None
    tags: List[str] = None
    
    # ========================================================================
    # STREAMING UI FIELDS
    # ========================================================================
    
    # Human-readable name for UI display (e.g., "Understanding your business")
    # If None, will be auto-generated from node name
    display_name: Optional[str] = None
    
    # Whether to show this node in progress UI
    # Set to False for internal/utility nodes (e.g., snapshot nodes, collectors)
    show_node: bool = True
    
    # Whether to show output summary in UI (Editor detail view)
    show_output: bool = False
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
    
    def get_display_name(self) -> str:
        """
        Get display name with fallback to formatted node name.
        
        Examples:
            - If display_name is set: returns display_name
            - "campaign_intent_synthesizer" → "Campaign Intent Synthesizer"
        """
        if self.display_name:
            return self.display_name
        return self._format_node_name(self.name)
    
    @staticmethod
    def _format_node_name(name: str) -> str:
        """
        Format node name to human-readable string.
        
        "campaign_intent_synthesizer" → "Campaign Intent Synthesizer"
        """
        formatted = name.replace("_", " ").title()
        formatted = formatted.replace(" Smb", " SMB")
        formatted = formatted.replace("L0 ", "L0 ")
        formatted = formatted.replace("L1 ", "L1 ")
        return formatted


class NodeRegistry:
    """
    Central registry for all nodes in the orchestration system.
    Provides decorator-based registration and discovery.
    
    SIMPLIFIED: Removed phase and parallel_group support.
    """
    
    _nodes: Dict[str, NodeMetadata] = {}
    
    @classmethod
    def register(
        cls,
        name: str,
        description: Optional[str] = None,
        max_retries: int = 1,
        retry_strategy: RetryStrategy = RetryStrategy.SIMPLE,
        timeout: Optional[int] = None,
        tags: Optional[List[str]] = None,
        # Streaming UI fields
        display_name: Optional[str] = None,
        show_node: bool = True,
        show_output: bool = False,
    ):
        """
        Decorator to register a node function.
        
        Usage:
            @NodeRegistry.register(
                name="campaign_intent_synthesizer",
                description="Synthesize campaign brief from business data",
                max_retries=1,
                tags=["llm", "synthesis"],
                display_name="Understanding your business",
                show_node=True,
                show_output=True,
            )
            def campaign_intent_synthesizer_node(state: dict, config: dict) -> dict:
                ...
        
        Args:
            name: Unique node identifier
            description: Node description (defaults to docstring)
            max_retries: Maximum retry attempts
            retry_strategy: Retry strategy enum
            timeout: Execution timeout in seconds
            tags: List of tags for categorization
            display_name: Human-readable name for UI (auto-generated if None)
            show_node: Whether to show in progress UI
            show_output: Whether to show output summary in detailed view
        """
        def decorator(func: Callable) -> Callable:
            metadata = NodeMetadata(
                name=name,
                func=func,
                description=description or func.__doc__,
                max_retries=max_retries,
                retry_strategy=retry_strategy,
                timeout=timeout,
                tags=tags or [],
                display_name=display_name,
                show_node=show_node,
                show_output=show_output,
            )
            
            cls._nodes[name] = metadata
            logger.debug(f"Registered node: {name} (show_node={show_node}, show_output={show_output})")
            
            return func
        
        return decorator
    
    @classmethod
    def get(cls, name: str) -> Callable:
        """Get a node function by name"""
        if name not in cls._nodes:
            raise ValueError(f"Node '{name}' not found in registry")
        return cls._nodes[name].func
    
    @classmethod
    def get_metadata(cls, name: str) -> NodeMetadata:
        """Get node metadata by name"""
        if name not in cls._nodes:
            raise ValueError(f"Node '{name}' not found in registry")
        return cls._nodes[name]
    
    @classmethod
    def get_metadata_safe(cls, name: str) -> Optional[NodeMetadata]:
        """Get node metadata by name, returning None if not found."""
        return cls._nodes.get(name)
    
    @classmethod
    def get_display_name(cls, name: str) -> str:
        """Get display name for a node with fallback."""
        metadata = cls._nodes.get(name)
        if metadata:
            return metadata.get_display_name()
        return NodeMetadata._format_node_name(name)
    
    @classmethod
    def should_show_node(cls, name: str) -> bool:
        """Check if node should be shown in progress UI."""
        metadata = cls._nodes.get(name)
        if metadata:
            return metadata.show_node
        return True
    
    @classmethod
    def should_show_output(cls, name: str) -> bool:
        """Check if node should show output summary in UI."""
        metadata = cls._nodes.get(name)
        if metadata:
            return metadata.show_output
        return False
    
    @classmethod
    def list_all(cls) -> List[str]:
        """List all registered node names"""
        return list(cls._nodes.keys())
    
    @classmethod
    def list_visible_nodes(cls) -> List[str]:
        """List all nodes that should be shown in UI (show_node=True)"""
        return [
            name for name, metadata in cls._nodes.items()
            if metadata.show_node
        ]
    
    @classmethod
    def find_by_tag(cls, tag: str) -> List[str]:
        """Find all nodes with a specific tag"""
        return [
            name for name, metadata in cls._nodes.items()
            if tag in metadata.tags
        ]
    
    @classmethod
    def get_all_metadata(cls) -> Dict[str, NodeMetadata]:
        """Get all registered node metadata (for debugging/introspection)"""
        return cls._nodes.copy()
    
    @classmethod
    def clear(cls):
        """Clear all registered nodes (useful for testing)"""
        cls._nodes.clear()