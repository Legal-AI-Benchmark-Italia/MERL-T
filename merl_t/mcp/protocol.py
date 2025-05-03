from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union, Literal

# Basic JSON-RPC 2.0 Structures
JsonRpcId = Union[str, int, None]

@dataclass
class JsonRpcRequest:
    method: str
    jsonrpc: str = "2.0"
    params: Optional[Union[Dict[str, Any], List[Any]]] = None
    id: Optional[JsonRpcId] = None # If id is omitted, it's a Notification

@dataclass
class JsonRpcError:
    code: int
    message: str
    data: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {"code": self.code, "message": self.message}
        if self.data is not None:
            d["data"] = self.data
        return d

@dataclass
class JsonRpcResponse:
    id: JsonRpcId
    jsonrpc: str = "2.0"
    result: Optional[Any] = None
    error: Optional[Dict] = None # Should be JsonRpcError.to_dict() compatible

# MCP Specific Structures

@dataclass
class ClientInfo:
    name: str
    version: Optional[str] = None
    # Add other relevant client info fields

@dataclass
class ServerInfo:
    name: str
    version: Optional[str] = None
    # Add other relevant server info fields (e.g., vendor)

@dataclass
class ServerCapabilities:
    # Define supported features. Based on MCP specs.
    resources: bool = False
    prompts: bool = False
    tools: bool = False
    sampling: bool = False # If server supports client-initiated sampling
    logging: bool = False
    # Add other capabilities as needed (configuration, progress, cancellation)

@dataclass
class InitializeParams:
    client_info: Optional[ClientInfo] = None
    capabilities: Optional[Any] = None # Client capabilities structure (can be detailed later)
    # root_uri: Optional[str] = None # Example from LSP, adapt as needed for MCP
    # process_id: Optional[int] = None

@dataclass
class InitializeResult:
    server_info: ServerInfo
    capabilities: ServerCapabilities

# MCP Feature Definitions

# Based on https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/#documentFilter
# We might need a similar concept if resources are URI-based
# @dataclass
# class ResourceFilter:
#     pattern: str # Glob pattern
#     scheme: Optional[str] = None

@dataclass
class ResourceDefinition:
    name: str
    description: Optional[str] = None
    schema_: Optional[Dict[str, Any]] = field(default=None, metadata={'alias': 'schema'})
    # filters: Optional[List[ResourceFilter]] = None # If resources are URI based

@dataclass
class ToolDefinition:
    name: str
    description: Optional[str] = None
    # JSON Schema for input parameters
    parameters_schema: Optional[Dict[str, Any]] = field(default=None, metadata={'alias': 'parametersSchema'})
    # JSON Schema for the result/output
    result_schema: Optional[Dict[str, Any]] = field(default=None, metadata={'alias': 'resultSchema'})


@dataclass
class ExecuteToolParams:
    name: str
    arguments: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LoggingMessageParams:
    level: int # Or an Enum: DEBUG=0, INFO=1, NOTICE=2, WARNING=3, ERROR=4, CRITICAL=5, ALERT=6, EMERGENCY=7
    data: Any # The log message/data
    logger: Optional[str] = None

LoggingLevel = Literal[0, 1, 2, 3, 4, 5, 6, 7]

@dataclass
class LoggingMessageNotification:
    level: LoggingLevel
    data: Any # The log message/data
    logger: Optional[str] = None 