"""LangGraph node factories for AgentBuilder workflow execution.

Each factory follows the pattern:
    make_<type>_node(node_id, node_data, [session]) -> async callable

The returned callable accepts a WorkflowState dict and returns a partial
state update dict.  All factories are exported from this package for
convenient import by the workflow compiler.
"""

from app.nodes.agent import make_agent_node
from app.nodes.chat_input import make_chat_input_node
from app.nodes.chat_output import make_chat_output_node
from app.nodes.knowledge_base import make_knowledge_base_node
from app.nodes.llm import make_llm_node
from app.nodes.prompt_template import make_prompt_template_node
from app.nodes.utils import get_input_text

__all__ = [
    "make_chat_input_node",
    "make_chat_output_node",
    "make_llm_node",
    "make_agent_node",
    "make_knowledge_base_node",
    "make_prompt_template_node",
    "get_input_text",
]
