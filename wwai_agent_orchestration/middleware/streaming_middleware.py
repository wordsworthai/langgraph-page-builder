# middleware/streaming_middleware.py

"""
Streaming middleware for formatting streaming output.
Converts raw LangGraph events into user-friendly format.
"""

from typing import Dict, Any, Generator, Tuple, Optional
from datetime import datetime
from wwai_agent_orchestration.core.observability.logger import get_logger

logger = get_logger(__name__)


class StreamingFormatter:
    """
    Formats raw streaming events into structured output.
    
    Converts LangGraph's raw events into JSON-friendly format
    suitable for web APIs, logs, or terminal display.
    
    NO styling/colors - just clean data structure.
    """
    
    def __init__(self, node_metadata: Optional[Dict[str, Dict[str, Any]]] = None):
        """
        Args:
            node_metadata: Optional dict mapping node names to custom metadata
                          Example: {"template_l0_l1_generation": {"display_name": "Template Generator"}}
        """
        self.node_metadata = node_metadata or {}
    
    def format_stream(
        self,
        raw_stream: Generator[Tuple[str, Any], None, None]
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Format raw LangGraph stream into structured events.
        
        Args:
            raw_stream: Generator from workflow.stream()
            
        Yields:
            Formatted events as dicts:
            
            Node completion:
            {
                "type": "node_complete",
                "node": "template_l0_l1_generation",
                "data": {...},
                "timestamp": "2025-01-15T10:30:00Z"
            }
            
            LLM token:
            {
                "type": "token",
                "node": "section_retriever",
                "task_id": "abc123",
                "content": "Based on",
                "timestamp": "2025-01-15T10:30:00Z"
            }
        """
        for stream_type, chunk in raw_stream:
            if stream_type == "updates":
                yield self._format_node_completion(chunk)
                
            elif stream_type == "messages":
                yield self._format_token_event(chunk)
    
    def _format_node_completion(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """Format node completion event"""
        node_name = list(chunk.keys())[0]
        node_data = chunk[node_name]
        
        event = {
            "type": "node_complete",
            "node": node_name,
            "data": node_data,
            "timestamp": self._get_timestamp()
        }
        
        # Add custom metadata if available
        if node_name in self.node_metadata:
            event["metadata"] = self.node_metadata[node_name]
        
        return event
    
    def _format_token_event(self, chunk: Tuple[Any, Dict]) -> Dict[str, Any]:
        """Format LLM token event"""
        message_chunk, metadata = chunk
        
        node_name = metadata.get("langgraph_node", "unknown")
        task_id = metadata.get("langgraph_task_id", "")
        
        event = {
            "type": "token",
            "node": node_name,
            "task_id": task_id,
            "content": message_chunk.content if hasattr(message_chunk, 'content') else str(message_chunk),
            "timestamp": self._get_timestamp()
        }
        
        # Add custom metadata if available
        if node_name in self.node_metadata:
            event["metadata"] = self.node_metadata[node_name]
        
        return event
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        return datetime.utcnow().isoformat() + "Z"


class StreamingAggregator:
    """
    Aggregates parallel streaming events.
    
    Buffers tokens from parallel nodes and emits them in a structured way.
    Useful when you have multiple LLM calls running in parallel.
    """
    
    def __init__(self, node_metadata: Optional[Dict[str, Dict[str, Any]]] = None):
        """
        Args:
            node_metadata: Optional dict mapping node names to custom metadata
        """
        self.buffers: Dict[str, list] = {}
        self.formatter = StreamingFormatter(node_metadata)
    
    def aggregate_stream(
        self,
        raw_stream: Generator,
        buffer_parallel: bool = False
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Aggregate streaming events.
        
        Args:
            raw_stream: Raw LangGraph stream
            buffer_parallel: If True, buffer parallel node tokens until completion
            
        Yields:
            Aggregated events
        """
        for event in self.formatter.format_stream(raw_stream):
            if buffer_parallel and event['type'] == 'token':
                # Buffer tokens by node+task
                node_key = f"{event['node']}:{event['task_id']}"
                
                if node_key not in self.buffers:
                    self.buffers[node_key] = []
                
                self.buffers[node_key].append(event['content'])
                
                # Emit progress event (consumer can ignore if not needed)
                yield {
                    "type": "progress",
                    "node": event['node'],
                    "task_id": event['task_id'],
                    "tokens_buffered": len(self.buffers[node_key]),
                    "timestamp": event['timestamp']
                }
                
            elif event['type'] == 'node_complete':
                # Flush buffer for this node
                node_name = event['node']
                
                # Find all buffers for this node
                for node_key in list(self.buffers.keys()):
                    if node_key.startswith(node_name + ":"):
                        buffered_content = "".join(self.buffers[node_key])
                        
                        yield {
                            "type": "node_output",
                            "node": node_name,
                            "task_id": node_key.split(":")[-1],
                            "content": buffered_content,
                            "data": event['data'],
                            "timestamp": event['timestamp']
                        }
                        
                        del self.buffers[node_key]
                
                # Also emit completion event
                yield event
                
            else:
                # Pass through other events unchanged
                yield event


# ============================================================================
# Usage Examples
# ============================================================================

# def example_usage_basic():
#     """Basic usage - just format events"""
#     workflow = TemplateRecommendationWorkflow()
#     formatter = StreamingFormatter()
    
#     for event in formatter.format_stream(workflow.stream(query="test")):
#         if event['type'] == 'token':
#             print(event['content'], end='', flush=True)
#         elif event['type'] == 'node_complete':
#             print(f"\n✓ {event['node']} done")


# def example_usage_with_metadata():
#     """Usage with custom node metadata"""
#     node_metadata = {
#         "template_l0_l1_generation": {
#             "display_name": "Template Structure Generator",
#             "description": "Generates 3 template recommendations"
#         },
#         "section_retriever": {
#             "display_name": "Section Mapper",
#             "description": "Maps real sections to template"
#         }
#     }
    
#     workflow = TemplateRecommendationWorkflow()
#     formatter = StreamingFormatter(node_metadata=node_metadata)
    
#     for event in formatter.format_stream(workflow.stream(query="test")):
#         # Event now includes metadata
#         if 'metadata' in event:
#             display_name = event['metadata']['display_name']
#             print(f"\n[{display_name}]")
        
#         if event['type'] == 'token':
#             print(event['content'], end='', flush=True)


# def example_usage_aggregated():
#     """Usage with aggregation for parallel nodes"""
#     workflow = TemplateRecommendationWorkflow()
#     aggregator = StreamingAggregator()
    
#     for event in aggregator.aggregate_stream(
#         workflow.stream(page_url="https://example.com"),
#         buffer_parallel=True  # Buffer parallel section_retriever tokens
#     ):
#         if event['type'] == 'node_output':
#             # Get complete buffered output from parallel node
#             print(f"\n{event['node']} output: {event['content'][:100]}...")