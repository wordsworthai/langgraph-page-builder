# nodes/base.py

"""
Base protocol for nodes.
All nodes follow this signature.
"""

from typing import Protocol, Dict, Any


class NodeFunction(Protocol):
    """
    Protocol for node functions.
    All nodes must accept (state, config) and return state updates.
    """
    
    def __call__(self, state: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute node logic.
        
        Args:
            state: Current workflow state (mutable)
            config: Node configuration (immutable)
            
        Returns:
            Dict with state updates to merge into current state
        """
        ...