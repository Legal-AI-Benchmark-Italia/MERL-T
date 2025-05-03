"""
Common test fixtures for MERL-T tests.

This file contains pytest fixtures that can be used across multiple test files.
"""

import os
import pytest
from unittest.mock import MagicMock, patch

from merl_t.config import get_config_manager
from merl_t.orchestrator.main import Orchestrator


@pytest.fixture
def config_manager():
    """Return a config manager instance."""
    return get_config_manager()


@pytest.fixture
def mock_config_manager():
    """Return a mocked config manager."""
    mock_manager = MagicMock()
    
    # Setup some common config responses
    def get_mock(key, default=None):
        config = {
            "general.log_level": "ERROR",
            "ner.model_name": "test-model",
            "ner.use_gpu": False,
            "mcp.defaults.transport": "websocket",
            "mcp.defaults.host": "localhost",
            "mcp.defaults.websocket_port": 8765,
        }
        return config.get(key, default)
    
    mock_manager.get = get_mock
    
    # Mock get_server_config
    def get_server_config_mock(server_type):
        configs = {
            "ner": {
                "enabled": True,
                "host": "localhost",
                "websocket_port": 8765,
                "model_name": "test-model",
                "use_gpu": False
            },
            "visualex": {
                "enabled": True,
                "host": "localhost",
                "websocket_port": 8766
            },
            "knowledge_graph": {
                "enabled": True,
                "host": "localhost", 
                "websocket_port": 8767
            }
        }
        return configs.get(server_type, {})
    
    mock_manager.get_server_config = get_server_config_mock
    
    return mock_manager


@pytest.fixture
def orchestrator():
    """Return an Orchestrator instance."""
    return Orchestrator(
        name="Test Orchestrator",
        description="Orchestrator for testing",
        version="test"
    )


@pytest.fixture
def mock_orchestrator():
    """Return a mocked Orchestrator instance."""
    with patch('merl_t.orchestrator.main.Orchestrator') as mock:
        mock_instance = mock.return_value
        mock_instance.name = "Mock Orchestrator"
        mock_instance.description = "Mocked Orchestrator for testing"
        mock_instance.version = "test"
        mock_instance.process_query = MagicMock()
        yield mock_instance


@pytest.fixture
def test_data_dir():
    """Return the path to the test data directory."""
    # Path is relative to the conftest.py file
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "data")
    
    # Create the directory if it doesn't exist
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    
    return data_dir 