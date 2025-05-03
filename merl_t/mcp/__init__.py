"""
Model Context Protocol Implementation for MERL-T

Provides tools for implementing MCP servers and hosts.
"""

from .base import BaseMCPServer, BaseMCPHost
from .client import BaseMCPClient
from .protocol import (
    ServerInfo, ServerCapabilities, ToolDefinition, ResourceDefinition,
    JsonRpcRequest, JsonRpcResponse, JsonRpcError, InitializeParams,
    InitializeResult, ExecuteToolParams
)
from .servers import NerServer

__all__ = [
    'BaseMCPServer', 'BaseMCPHost', 'BaseMCPClient',
    'ServerInfo', 'ServerCapabilities', 'ToolDefinition', 'ResourceDefinition',
    'JsonRpcRequest', 'JsonRpcResponse', 'JsonRpcError', 'InitializeParams',
    'InitializeResult', 'ExecuteToolParams',
    'NerServer'
] 