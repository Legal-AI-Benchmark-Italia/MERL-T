"""
Configuration Management for MERL-T

Handles loading, validation, and access to configuration settings.
"""

from .config_manager import ConfigManager, get_config_manager

__all__ = ['ConfigManager', 'get_config_manager'] 