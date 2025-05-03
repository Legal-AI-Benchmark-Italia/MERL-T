"""
Agent-to-Agent Protocol Implementation for MERL-T

Provides tools for agent communication using Google's A2A protocol.
"""

from .protocol import (
    ContentType, Role, Part, Message, Artifact, Task,
    AgentCard, A2ASession, create_text_message, create_text_artifact
)
from .base import BaseAgent

__all__ = [
    'ContentType', 'Role', 'Part', 'Message', 'Artifact', 'Task',
    'AgentCard', 'A2ASession', 'create_text_message', 'create_text_artifact',
    'BaseAgent'
] 