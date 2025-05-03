import asyncio
import json
import uuid
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Tuple, Union, Awaitable

from loguru import logger

from .protocol import (
    InitializeParams, InitializeResult, JsonRpcRequest, JsonRpcResponse,
    JsonRpcError, ServerCapabilities, ServerInfo, ToolDefinition,
    ResourceDefinition, ExecuteToolParams
)

# Type definitions for handlers
MessageHandler = Callable[[Union[Dict[str, Any], List[Any]]], Awaitable[Any]]
ToolHandler = Callable[[Dict[str, Any]], Awaitable[Any]] # arguments -> result
ResourceHandler = Callable[[Optional[Dict[str, Any]]], Awaitable[Any]] # params -> result

class BaseMCPServer(ABC):
    """Abstract Base Class for an MCP Server."""

    def __init__(self, server_info: ServerInfo):
        self.server_info = server_info
        self._message_handlers: Dict[str, MessageHandler] = {}
        self._tool_handlers: Dict[str, ToolHandler] = {}
        self._resource_handlers: Dict[str, ResourceHandler] = {}
        self._tools: Dict[str, ToolDefinition] = {}
        self._resources: Dict[str, ResourceDefinition] = {}
        self._initialized = False
        self._client_capabilities: Optional[Any] = None # Store client caps after init

        # Register standard MCP methods
        self.register_message_handler("initialize", self._handle_initialize)
        self.register_message_handler("shutdown", self._handle_shutdown)
        self.register_message_handler("exit", self._handle_exit)
        self.register_message_handler("mcp/getTools", self._handle_get_tools)
        self.register_message_handler("mcp/getResources", self._handle_get_resources)
        self.register_message_handler("tool/execute", self._handle_execute_tool)
        self.register_message_handler("resource/get", self._handle_get_resource)

    @abstractmethod
    async def start(self):
        """Start the server's communication listener."""
        pass

    @abstractmethod
    async def stop(self):
        """Stop the server's communication listener."""
        pass

    @abstractmethod
    async def _send_response(self, response: JsonRpcResponse):
        """Send a JSON-RPC response to the client."""
        pass

    @abstractmethod
    async def _send_notification(self, method: str, params: Optional[Any]):
        """Send a JSON-RPC notification to the client."""
        pass

    @abstractmethod
    def get_server_capabilities(self) -> ServerCapabilities:
        """Return the capabilities of this server."""
        pass

    def register_message_handler(self, method: str, handler: MessageHandler):
        self._message_handlers[method] = handler

    def register_tool(self, definition: ToolDefinition, handler: ToolHandler):
        if not self.get_server_capabilities().tools:
            raise ValueError("Server does not declare tool capability.")
        self._tools[definition.name] = definition
        self._tool_handlers[definition.name] = handler
        print(f"Tool registered: {definition.name}")


    def register_resource(self, definition: ResourceDefinition, handler: ResourceHandler):
        if not self.get_server_capabilities().resources:
            raise ValueError("Server does not declare resource capability.")
        self._resources[definition.name] = definition
        self._resource_handlers[definition.name] = handler
        print(f"Resource registered: {definition.name}")


    async def handle_message(self, message_data: bytes):
        """Handle a raw incoming message."""
        try:
            message = json.loads(message_data.decode('utf-8'))
            request = JsonRpcRequest(**message)
        except (json.JSONDecodeError, TypeError, KeyError) as e:
            # Send parse error / invalid request
            await self._send_response(JsonRpcResponse(
                error=JsonRpcError(-32700, "Parse error", str(e)).to_dict(),
                id=None
            ))
            return
        except Exception as e:
             await self._send_response(JsonRpcResponse(
                error=JsonRpcError(-32603, "Internal error on parse", str(e)).to_dict(),
                id=getattr(request, 'id', None)
            ))
             return


        response = await self._process_request(request)
        if response:
            await self._send_response(response)

    async def _process_request(self, request: JsonRpcRequest) -> Optional[JsonRpcResponse]:
        """Process a parsed JSON-RPC request."""
        if not hasattr(request, 'method') or not isinstance(request.method, str):
             return JsonRpcResponse(
                error=JsonRpcError(-32600, "Invalid Request", "Method missing or invalid").to_dict(),
                id=getattr(request, 'id', None)
            )

        # Check initialization state for non-initialize methods
        if request.method != "initialize" and not self._initialized:
            return JsonRpcResponse(
                error=JsonRpcError(-32002, "Server not initialized").to_dict(),
                id=request.id
            )

        handler = self._message_handlers.get(request.method)
        if not handler:
            return JsonRpcResponse(
                error=JsonRpcError(-32601, "Method not found", request.method).to_dict(),
                id=request.id
            )

        try:
            result = await handler(request.params)
             # Only send response if request had an ID (it's not a notification)
            if request.id is not None:
                return JsonRpcResponse(result=result, id=request.id)
            else:
                return None # It was a notification, no response needed
        except Exception as e:
            # Log the exception traceback here for debugging
            print(f"Error processing method {request.method}: {e}")
            # traceback.print_exc()
            return JsonRpcResponse(
                error=JsonRpcError(-32603, "Internal error", str(e)).to_dict(),
                id=request.id
            )

    # --- Standard MCP Handlers ---
    async def _handle_initialize(self, params: Optional[Dict[str, Any]]) -> InitializeResult:
        if self._initialized:
             raise JsonRpcError(-32002, "Server already initialized") # Error defined by LSP/MCP

        init_params = InitializeParams(**params) if params else InitializeParams()
        self._client_capabilities = init_params.capabilities # Store for later use
        # Perform version/capability negotiation if needed here

        self._initialized = True
        print("Server Initialized")
        return InitializeResult(
            server_info=self.server_info,
            capabilities=self.get_server_capabilities()
        )

    async def _handle_shutdown(self, params: Optional[Any]) -> None:
        print("Shutdown requested")
        # Prepare for exit, clean up resources if necessary
        # According to LSP spec, server must wait for 'exit' notification after this.
        return None # Shutdown should respond with null result

    async def _handle_exit(self, params: Optional[Any]):
        print("Exit notification received")
        # Server should exit process.
        # For simplicity here, we might just call stop. In real app, might use sys.exit()
        await self.stop()
        # No response for notifications

    async def _handle_get_tools(self, params: Optional[Any]) -> List[Dict]:
         if not self.get_server_capabilities().tools:
             raise JsonRpcError(-32601, "Method not found", "Server does not support tools")
         return [tool.__dict__ for tool in self._tools.values()]


    async def _handle_get_resources(self, params: Optional[Any]) -> List[Dict]:
        if not self.get_server_capabilities().resources:
             raise JsonRpcError(-32601, "Method not found", "Server does not support resources")
        return [res.__dict__ for res in self._resources.values()]

    async def _handle_execute_tool(self, params: Optional[Dict[str, Any]]) -> Any:
        if not self.get_server_capabilities().tools:
             raise JsonRpcError(-32601, "Method not found", "Server does not support tools")
        if not params:
             raise JsonRpcError(-32602, "Invalid params", "Parameters required for tool/execute")

        exec_params = ExecuteToolParams(**params)
        handler = self._tool_handlers.get(exec_params.name)
        if not handler:
             raise JsonRpcError(-32601, "Tool not found", exec_params.name) # Or a more specific tool error code

        # Add validation of arguments against tool definition here if needed
        print(f"Executing tool: {exec_params.name} with args: {exec_params.arguments}")
        result = await handler(exec_params.arguments)
        print(f"Tool {exec_params.name} result: {result}")
        return result # Result structure depends on the tool

    async def _handle_get_resource(self, params: Optional[Dict[str, Any]]) -> Any:
        if not self.get_server_capabilities().resources:
            raise JsonRpcError(-32601, "Method not found", "Server does not support resources")
        if not params or 'name' not in params:
            raise JsonRpcError(-32602, "Invalid params", "'name' required for resource/get")

        resource_name = params['name']
        handler = self._resource_handlers.get(resource_name)
        if not handler:
            raise JsonRpcError(-32601, "Resource not found", resource_name)

        # Pass other params if needed by the handler
        resource_params = {k: v for k, v in params.items() if k != 'name'}
        print(f"Getting resource: {resource_name} with params: {resource_params}")
        result = await handler(resource_params if resource_params else None)
        print(f"Resource {resource_name} result: {result}")
        return result # Result structure depends on the resource


class BaseMCPHost:
    """
    Base class for MCP host implementations.
    
    Responsible for establishing connections to MCP servers and
    managing client sessions.
    """
    
    def __init__(self):
        """Initialize the MCP host."""
        # Dictionary of connected servers
        self._servers: Dict[str, Dict[str, Any]] = {}
        
        # Session management
        self._sessions: Dict[str, Dict[str, Any]] = {}
        
        logger.info("MCP Host initialized")
    
    async def connect_server(
        self, 
        url: str,
        server_type: str = "unknown",
        transport: str = "websocket"
    ) -> str:
        """
        Connect to an MCP server.
        
        Args:
            url: Server URL
            server_type: Type of server (for logging)
            transport: Transport type to use
            
        Returns:
            Server ID if successful
        """
        server_id = str(uuid.uuid4())
        
        # In a real implementation, this would establish a connection
        # and perform initialization
        logger.info(f"Connected to {server_type} server at {url}")
        
        # Store server information
        self._servers[server_id] = {
            "url": url,
            "type": server_type,
            "transport": transport,
            "connected": True,
            "capabilities": {},
            "tools": {},
            "resources": {}
        }
        
        return server_id
    
    async def disconnect_server(self, server_id: str) -> bool:
        """
        Disconnect from an MCP server.
        
        Args:
            server_id: Server ID
            
        Returns:
            True if successful
        """
        if server_id not in self._servers:
            return False
        
        # In a real implementation, this would close the connection
        logger.info(f"Disconnected from server {server_id}")
        
        # Remove server information
        del self._servers[server_id]
        
        return True
    
    async def execute_tool(
        self,
        server_id: str,
        tool_name: str,
        params: Dict[str, Any],
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a tool on an MCP server.
        
        Args:
            server_id: Server ID
            tool_name: Tool name
            params: Tool parameters
            session_id: Optional session ID
            
        Returns:
            Tool execution result
        """
        if server_id not in self._servers:
            raise ValueError(f"Unknown server ID: {server_id}")
        
        # In a real implementation, this would send an executeToolRequest
        # to the server and await the response
        logger.info(f"Executing tool {tool_name} on server {server_id}")
        
        # Placeholder
        return {
            "result": "not_implemented",
            "message": "Host implementation is a placeholder"
        }
    
    async def read_resource(
        self,
        server_id: str,
        resource_name: str,
        params: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Read a resource from an MCP server.
        
        Args:
            server_id: Server ID
            resource_name: Resource name
            params: Optional resource parameters
            session_id: Optional session ID
            
        Returns:
            Resource content
        """
        if server_id not in self._servers:
            raise ValueError(f"Unknown server ID: {server_id}")
        
        # In a real implementation, this would send a readResourceRequest
        # to the server and await the response
        logger.info(f"Reading resource {resource_name} from server {server_id}")
        
        # Placeholder
        return {
            "result": "not_implemented",
            "message": "Host implementation is a placeholder"
        }
    
    def get_connected_servers(self) -> List[Dict[str, Any]]:
        """
        Get information about all connected servers.
        
        Returns:
            List of server information dictionaries
        """
        return [
            {
                "id": server_id,
                "type": info["type"],
                "url": info["url"],
                "connected": info["connected"]
            }
            for server_id, info in self._servers.items()
        ] 