"""
Base Agent Implementation for A2A Protocol

Defines the abstract base class for all A2A agents in the MERL-T system.
"""

import asyncio
import json
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Union, Callable, Awaitable

from loguru import logger

from .protocol import (
    A2ASession, AgentCard, Artifact, ContentType, Message, Part, Role, Task,
    create_text_message, create_text_artifact
)

# Type aliases
TaskHandler = Callable[[Task], Awaitable[Union[Message, Artifact, List[Union[Message, Artifact]]]]]


class BaseAgent(ABC):
    """
    Abstract base class for all A2A agents in MERL-T.
    
    Implements core functionality for agent messaging, task handling,
    and session management.
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        version: str = "0.1.0",
        creator: str = "LAIBIT",
    ):
        """
        Initialize a new A2A agent.
        
        Args:
            name: Human-readable name of the agent
            description: Detailed description of agent capabilities
            version: Agent version string
            creator: Name of the agent creator
        """
        self.id = str(uuid.uuid4())
        self._name = name
        self._description = description
        self._version = version
        self._creator = creator
        
        # Default supported content types
        self._input_modes = [ContentType.TEXT, ContentType.JSON, ContentType.MARKDOWN]
        self._output_modes = [ContentType.TEXT, ContentType.JSON, ContentType.MARKDOWN]
        
        # Agent skills
        self._skills: List[Dict[str, Any]] = []
        
        # Task handlers registry
        self._task_handlers: Dict[str, TaskHandler] = {}
        
        # Active sessions
        self._sessions: Dict[str, A2ASession] = {}
        
        logger.info(f"Agent {self._name} ({self.id}) initialized")
    
    @property
    def agent_card(self) -> AgentCard:
        """Get the agent card describing this agent's capabilities."""
        return AgentCard(
            name=self._name,
            description=self._description,
            version=self._version,
            creator=self._creator,
            input_modes=self._input_modes,
            output_modes=self._output_modes,
            skills=self._skills
        )
    
    def register_skill(
        self,
        name: str,
        description: str,
        handler: TaskHandler,
        tags: List[str] = None,
        examples: List[str] = None,
    ) -> None:
        """
        Register a new skill with the agent.
        
        Args:
            name: Name of the skill
            description: Description of the skill
            handler: Async function to handle tasks for this skill
            tags: Optional list of tags categorizing the skill
            examples: Optional list of example queries for this skill
        """
        skill_id = str(uuid.uuid4())
        
        # Add to skills list
        self._skills.append({
            "id": skill_id,
            "name": name,
            "description": description,
            "tags": tags or [],
            "examples": examples or []
        })
        
        # Register handler
        self._task_handlers[skill_id] = handler
        
        logger.info(f"Registered skill '{name}' with id {skill_id}")
    
    def create_session(self) -> str:
        """
        Create a new session with this agent.
        
        Returns:
            Session ID string
        """
        session_id = str(uuid.uuid4())
        self._sessions[session_id] = A2ASession(
            id=session_id,
            agent_id=self.id,
            created_at=str(datetime.now().isoformat()),
            updated_at=str(datetime.now().isoformat())
        )
        return session_id
    
    def get_session(self, session_id: str) -> Optional[A2ASession]:
        """
        Get a session by ID.
        
        Args:
            session_id: The session ID
            
        Returns:
            The session or None if not found
        """
        return self._sessions.get(session_id)
    
    async def process_task(self, task: Task) -> List[Union[Message, Artifact]]:
        """
        Process a task, routing it to the appropriate skill handler.
        
        This method is responsible for parsing the task, determining the
        appropriate skill to handle it, and invoking the handler.
        
        Args:
            task: The task to process
            
        Returns:
            List of messages and artifacts produced by the task
        """
        logger.info(f"Processing task {task.id}")
        
        # Default response if we can't match a skill
        default_msg = create_text_message(
            role=Role.AGENT,
            text=f"I'm sorry, but I don't have the necessary skills to handle this task."
        )
        
        # Placeholder: In a real implementation, we would analyze the task 
        # and route to the appropriate skill handler
        # For now, we'll just log a warning
        logger.warning(f"No skill handler matched for task {task.id}")
        
        return [default_msg]
    
    @abstractmethod
    async def handle_message(self, message: Message, session_id: str) -> List[Union[Message, Artifact]]:
        """
        Handle an incoming message within a session.
        
        This method should be implemented by subclasses to handle
        processing messages specific to the agent's domain.
        
        Args:
            message: The incoming message
            session_id: The session ID
            
        Returns:
            List of messages and artifacts to send in response
        """
        pass
    
    def __str__(self) -> str:
        """String representation of the agent."""
        return f"{self._name} ({self.id})" 