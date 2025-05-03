"""
Unit tests for the configuration manager.
"""

import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

import pytest
import yaml

from merl_t.config import get_config_manager, ConfigManager


class TestConfigManager(unittest.TestCase):
    """Tests for ConfigManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a fresh config manager for each test
        self.config_manager = ConfigManager()
    
    def test_get_config_manager_singleton(self):
        """Test that get_config_manager returns a singleton instance."""
        manager1 = get_config_manager()
        manager2 = get_config_manager()
        
        self.assertIs(manager1, manager2)
    
    def test_get_with_default(self):
        """Test getting a config value with a default."""
        # A key that shouldn't exist in the default config
        key = "test.nonexistent.key"
        default = "default-value"
        
        value = self.config_manager.get(key, default)
        
        self.assertEqual(value, default)
    
    def test_get_nested_key(self):
        """Test getting a nested config value."""
        # Set a nested config value
        self.config_manager.config = {
            "outer": {
                "inner": {
                    "value": "test-value"
                }
            }
        }
        
        value = self.config_manager.get("outer.inner.value")
        
        self.assertEqual(value, "test-value")
    
    def test_get_missing_nested_key(self):
        """Test getting a missing nested config value."""
        # Set a config with no nested structure
        self.config_manager.config = {"simple": "value"}
        
        value = self.config_manager.get("outer.inner.value", "default")
        
        self.assertEqual(value, "default")
    
    def test_get_server_config(self):
        """Test getting a server configuration."""
        # Set a sample server config
        self.config_manager.config = {
            "servers": {
                "test-server": {
                    "enabled": True,
                    "host": "localhost",
                    "port": 8765
                }
            }
        }
        
        config = self.config_manager.get_server_config("test-server")
        
        self.assertEqual(config["enabled"], True)
        self.assertEqual(config["host"], "localhost")
        self.assertEqual(config["port"], 8765)
    
    def test_get_nonexistent_server_config(self):
        """Test getting a nonexistent server configuration."""
        # Set an empty servers config
        self.config_manager.config = {"servers": {}}
        
        config = self.config_manager.get_server_config("nonexistent")
        
        self.assertEqual(config, {})
    
    def test_get_section(self):
        """Test getting a config section."""
        # Set a sample config with sections
        self.config_manager.config = {
            "section1": {
                "key1": "value1",
                "key2": "value2"
            },
            "section2": {
                "key3": "value3"
            }
        }
        
        section = self.config_manager.get_section("section1")
        
        self.assertEqual(section["key1"], "value1")
        self.assertEqual(section["key2"], "value2")
    
    def test_get_nonexistent_section(self):
        """Test getting a nonexistent config section."""
        # Set a config with no matching section
        self.config_manager.config = {"other": {}}
        
        section = self.config_manager.get_section("nonexistent")
        
        self.assertEqual(section, {})
    
    def test_load_from_file(self):
        """Test loading config from a file."""
        # Create a temp file with sample YAML
        config_data = {
            "test": {
                "key": "value",
                "nested": {
                    "subkey": "subvalue"
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as temp:
            yaml.dump(config_data, temp)
            temp_path = temp.name
        
        try:
            # Load the config
            self.config_manager.load_from_file(temp_path)
            
            # Test that values were loaded
            self.assertEqual(
                self.config_manager.get("test.key"), 
                "value"
            )
            self.assertEqual(
                self.config_manager.get("test.nested.subkey"), 
                "subvalue"
            )
        finally:
            # Clean up the temp file
            os.unlink(temp_path)
    
    @patch('os.path.exists')
    def test_load_nonexistent_file(self, mock_exists):
        """Test loading config from a nonexistent file."""
        # Mock os.path.exists to return False
        mock_exists.return_value = False
        
        with self.assertLogs(level='ERROR') as log:
            self.config_manager.load_from_file("nonexistent.yaml")
            
            # Check that an error was logged
            self.assertIn("ERROR", log.output[0])
            self.assertIn("nonexistent.yaml", log.output[0])
    
    @patch('os.environ')
    def test_load_from_env(self, mock_environ):
        """Test loading config from environment variables."""
        # Mock environment variables
        mock_environ.get.side_effect = lambda key, default=None: {
            "src_CONFIG_FILE": None,
            "src_TEST_KEY": "env-value",
            "src_TEST_BOOLEAN": "true",
            "src_TEST_NUMBER": "42"
        }.get(key, default)
        
        mock_environ.items.return_value = [
            ("src_TEST_KEY", "env-value"),
            ("src_TEST_BOOLEAN", "true"),
            ("src_TEST_NUMBER", "42"),
            ("OTHER_VAR", "other-value")
        ]
        
        # Load from environment
        self.config_manager.load_from_env()
        
        # Test that values were loaded and converted to appropriate types
        self.assertEqual(self.config_manager.get("test.key"), "env-value")
        self.assertEqual(self.config_manager.get("test.boolean"), True)
        self.assertEqual(self.config_manager.get("test.number"), 42)
        
        # Other variables should not be loaded
        self.assertIsNone(self.config_manager.get("other.var"))
    
    def test_merge_configs(self):
        """Test merging configs."""
        # Create base and overlay configs
        base = {
            "common": {
                "key1": "base-value1",
                "key2": "base-value2"
            },
            "base_only": {
                "key": "base-only-value"
            }
        }
        
        overlay = {
            "common": {
                "key1": "overlay-value1",
                "key3": "overlay-value3"
            },
            "overlay_only": {
                "key": "overlay-only-value"
            }
        }
        
        # Merge configs
        merged = self.config_manager._merge_configs(base, overlay)
        
        # Check that values were merged correctly
        self.assertEqual(merged["common"]["key1"], "overlay-value1")  # Overlaid
        self.assertEqual(merged["common"]["key2"], "base-value2")     # Preserved from base
        self.assertEqual(merged["common"]["key3"], "overlay-value3")  # Added from overlay
        self.assertEqual(merged["base_only"]["key"], "base-only-value")      # Preserved section
        self.assertEqual(merged["overlay_only"]["key"], "overlay-only-value")  # Added section 