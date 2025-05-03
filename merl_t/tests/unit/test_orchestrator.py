"""
Unit tests for the Orchestrator component.
"""

import asyncio
import unittest
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from merl_t.orchestrator.main import Orchestrator
from merl_t.config import get_config_manager


class TestOrchestratorInitialization(unittest.TestCase):
    """Tests for Orchestrator initialization."""
    
    def test_init_with_defaults(self):
        """Test initialization with default parameters."""
        orchestrator = Orchestrator()
        self.assertIsNotNone(orchestrator)
        self.assertIsInstance(orchestrator.config_manager, type(get_config_manager()))
        
    def test_init_with_custom_name(self):
        """Test initialization with custom name."""
        custom_name = "Custom Orchestrator"
        orchestrator = Orchestrator(name=custom_name)
        self.assertEqual(orchestrator.name, custom_name)
        
    def test_init_with_custom_description(self):
        """Test initialization with custom description."""
        custom_desc = "Custom description for testing"
        orchestrator = Orchestrator(description=custom_desc)
        self.assertEqual(orchestrator.description, custom_desc)
        
    def test_init_with_custom_version(self):
        """Test initialization with custom version."""
        custom_version = "1.2.3-test"
        orchestrator = Orchestrator(version=custom_version)
        self.assertEqual(orchestrator.version, custom_version)


@pytest.mark.asyncio
class TestOrchestratorMethods:
    """Tests for Orchestrator methods using pytest-asyncio."""
    
    async def test_process_query_basic(self):
        """Test process_query with basic query."""
        orchestrator = Orchestrator()
        
        # Mock connect_to_server to avoid actual connection attempts
        orchestrator.connect_to_server = AsyncMock(return_value="mock-server-id")
        
        result = await orchestrator.process_query("Test query")
        
        assert result["query"] == "Test query"
        assert result["status"] == "not_implemented"
        assert "message" in result
        assert "connected_servers" in result
    
    async def test_process_query_with_connection_error(self):
        """Test process_query with connection error."""
        orchestrator = Orchestrator()
        
        # Mock connect_to_server to simulate error
        orchestrator.connect_to_server = AsyncMock(side_effect=Exception("Connection error"))
        
        result = await orchestrator.process_query("Test query")
        
        assert result["query"] == "Test query"
        assert result["status"] == "error"
        assert "error" in result
        assert "message" in result
    
    async def test_connect_to_server_success(self):
        """Test connect_to_server with successful connection."""
        orchestrator = Orchestrator()
        
        # Mock config_manager to return a valid server config
        orchestrator.config_manager.get_server_config = MagicMock(
            return_value={"enabled": True, "host": "localhost", "websocket_port": 8765}
        )
        
        # Mock connect_server to avoid actual connection
        orchestrator.connect_server = AsyncMock(return_value="mock-server-id")
        
        server_id = await orchestrator.connect_to_server("ner")
        
        assert server_id == "mock-server-id"
    
    async def test_connect_to_server_disabled(self):
        """Test connect_to_server with disabled server."""
        orchestrator = Orchestrator()
        
        # Mock config_manager to return a disabled server config
        orchestrator.config_manager.get_server_config = MagicMock(
            return_value={"enabled": False}
        )
        
        server_id = await orchestrator.connect_to_server("ner")
        
        assert server_id is None
    
    async def test_connect_to_server_connection_refused(self):
        """Test connect_to_server with connection refused."""
        orchestrator = Orchestrator()
        
        # Mock config_manager to return a valid server config
        orchestrator.config_manager.get_server_config = MagicMock(
            return_value={"enabled": True, "host": "localhost", "websocket_port": 8765}
        )
        
        # Mock connect_server to simulate connection refused
        orchestrator.connect_server = AsyncMock(side_effect=ConnectionRefusedError("Connection refused"))
        
        server_id = await orchestrator.connect_to_server("ner")
        
        assert server_id is None
    
    async def test_connect_to_server_timeout(self):
        """Test connect_to_server with timeout."""
        orchestrator = Orchestrator()
        
        # Mock config_manager to return a valid server config
        orchestrator.config_manager.get_server_config = MagicMock(
            return_value={"enabled": True, "host": "localhost", "websocket_port": 8765}
        )
        
        # Mock connect_server to simulate timeout
        orchestrator.connect_server = AsyncMock(side_effect=asyncio.TimeoutError("Connection timeout"))
        
        server_id = await orchestrator.connect_to_server("ner")
        
        assert server_id is None 