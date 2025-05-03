"""
Agent-to-Agent (A2A) Protocol definitions for MERL-T

Implements core A2A data structures based on Google's A2A protocol specification.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union

class ContentType(str, Enum):
    """Content types supported in A2A messages and artifacts."""
    TEXT = "text/plain"
    JSON = "application/json"
    HTML = "text/html"
    XML = "application/xml"
    PDF = "application/pdf"
    IMAGE = "image/png"  # Default image type
    FORM = "application/x-www-form-urlencoded"
    MARKDOWN = "text/markdown"


class Role(str, Enum):
    """Possible roles in A2A communication."""
    USER = "user"
    AGENT = "agent"


@dataclass
class Part:
    """A single content part within a Message or Artifact."""
    content_type: ContentType
    content: Union[str, Dict[str, Any], List[Any], bytes]
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class Message:
    """
    A message in A2A protocol containing context, instructions, or status.
    Messages are used for communication not directly related to final artifacts.
    """
    role: Role
    parts: List[Part]
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class Artifact:
    """
    An artifact in A2A protocol representing a finalized output.
    Artifacts are immutable results produced by agents.
    """
    name: Optional[str] = None
    description: Optional[str] = None
    parts: List[Part] = field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None
    index: int = 0
    append: bool = False
    last_chunk: bool = True


@dataclass
class Task:
    """
    A task in A2A protocol representing a request to be fulfilled.
    Tasks can generate multiple Messages and Artifacts.
    """
    id: str
    messages: List[Message] = field(default_factory=list)
    artifacts: List[Artifact] = field(default_factory=list)
    completed: bool = False
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class AgentCard:
    """
    An agent card in A2A protocol describing an agent's capabilities.
    Used for agent discovery and metadata exchange.
    """
    name: str
    description: str
    version: str
    creator: str
    input_modes: List[ContentType] = field(default_factory=list)
    output_modes: List[ContentType] = field(default_factory=list)
    skills: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class A2ASession:
    """
    A session in A2A protocol tracking state between agents.
    """
    id: str
    agent_id: str
    tasks: List[Task] = field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# Helper functions for creating common message types
def create_text_message(role: Role, text: str, metadata: Optional[Dict[str, Any]] = None) -> Message:
    """Create a simple text message."""
    part = Part(content_type=ContentType.TEXT, content=text)
    return Message(role=role, parts=[part], metadata=metadata)


def create_text_artifact(name: str, text: str, metadata: Optional[Dict[str, Any]] = None) -> Artifact:
    """Create a simple text artifact."""
    part = Part(content_type=ContentType.TEXT, content=text)
    return Artifact(name=name, parts=[part], metadata=metadata) 