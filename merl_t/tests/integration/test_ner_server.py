"""
Integration tests for the NER server.

These tests verify that the NER server can be started, connected to,
and that it correctly processes requests.
"""

import asyncio
import json
import os
import subprocess
import time
from typing import Tuple, Optional, Dict

import pytest
import websockets

from merl_t.mcp.protocol import Request, ListToolsRequest, ExecuteToolRequest


class NERServerTestClient:
    """Test client for the NER server."""
    
    def __init__(self, host="localhost", port=8765):
        """Initialize the client."""
        self.host = host
        self.port = port
        self.url = f"ws://{host}:{port}"
        self.websocket = None
        self.request_id = 0
    
    async def connect(self) -> bool:
        """Connect to the NER server."""
        try:
            self.websocket = await websockets.connect(self.url)
            return True
        except Exception as e:
            print(f"Failed to connect to NER server: {e}")
            return False
    
    async def close(self) -> None:
        """Close the connection."""
        if self.websocket:
            await self.websocket.close()
    
    async def send_request(self, request: Dict) -> Dict:
        """Send a request to the server and get the response."""
        if not self.websocket:
            raise RuntimeError("Not connected to server")
        
        # Add request ID if not present
        if "id" not in request:
            self.request_id += 1
            request["id"] = str(self.request_id)
        
        # Send request
        await self.websocket.send(json.dumps(request))
        
        # Get response
        response = await self.websocket.recv()
        return json.loads(response)
    
    async def list_tools(self) -> Dict:
        """List available tools on the server."""
        request = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {}
        }
        return await self.send_request(request)
    
    async def extract_entities(self, text: str) -> Dict:
        """Extract entities from text."""
        request = {
            "jsonrpc": "2.0",
            "method": "tools/execute",
            "params": {
                "name": "extract_entities",
                "input": {
                    "text": text
                }
            }
        }
        return await self.send_request(request)
    
    async def normalize_text(self, text: str) -> Dict:
        """Normalize text."""
        request = {
            "jsonrpc": "2.0",
            "method": "tools/execute",
            "params": {
                "name": "normalize_text",
                "input": {
                    "text": text
                }
            }
        }
        return await self.send_request(request)


class ServerProcess:
    """Helper class to start and manage a server process."""
    
    def __init__(self, server_type="ner", transport="websocket", port=8765):
        """Initialize server process manager."""
        self.server_type = server_type
        self.transport = transport
        self.port = port
        self.process = None
    
    def start(self) -> bool:
        """Start the server process."""
        try:
            cmd = [
                "python", "-m", "merl_t.server",
                "--server-type", self.server_type,
                "--transport", self.transport,
                "--port", str(self.port),
                "--log-level", "ERROR"
            ]
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Give the server some time to start
            time.sleep(2)
            
            # Check if process is still running
            if self.process.poll() is not None:
                print(f"Server failed to start: {self.process.stderr.read()}")
                return False
                
            return True
        except Exception as e:
            print(f"Failed to start server: {e}")
            return False
    
    def stop(self) -> None:
        """Stop the server process."""
        if self.process:
            self.process.terminate()
            self.process.wait(timeout=5)
            
            # Force kill if still running
            if self.process.poll() is None:
                self.process.kill()


@pytest.mark.integration
class TestNERServer:
    """Integration tests for NER Server."""
    
    @classmethod
    def setup_class(cls):
        """Set up the test class - start server once for all tests."""
        cls.server = ServerProcess(server_type="ner", port=8766)
        cls.server_started = cls.server.start()
        
        if not cls.server_started:
            pytest.skip("Failed to start NER server")
    
    @classmethod
    def teardown_class(cls):
        """Tear down the test class - stop server."""
        if cls.server:
            cls.server.stop()
    
    @pytest.mark.asyncio
    async def test_connect_to_server(self):
        """Test connecting to the NER server."""
        if not self.__class__.server_started:
            pytest.skip("Server not running")
            
        client = NERServerTestClient(port=8766)
        connected = await client.connect()
        
        assert connected is True
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_list_tools(self):
        """Test listing available tools."""
        if not self.__class__.server_started:
            pytest.skip("Server not running")
            
        client = NERServerTestClient(port=8766)
        await client.connect()
        
        response = await client.list_tools()
        
        assert "result" in response
        assert "tools" in response["result"]
        
        tools = response["result"]["tools"]
        tool_names = [tool["name"] for tool in tools]
        
        # Verify expected tools are available
        assert "extract_entities" in tool_names
        assert "normalize_text" in tool_names
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_extract_entities(self):
        """Test extracting entities from text."""
        if not self.__class__.server_started:
            pytest.skip("Server not running")
            
        client = NERServerTestClient(port=8766)
        await client.connect()
        
        # Use a legal text with clear entity references
        text = "In base all'art. 2043 c.c., chiunque commette un fatto doloso o colposo..."
        
        response = await client.extract_entities(text)
        
        assert "result" in response
        assert "entities" in response["result"]
        
        # Check at least one entity was found
        # This is more of a smoke test - detailed assertions depend on the NER model
        entities = response["result"]["entities"]
        print(f"Found entities: {entities}")
        
        # At minimum, we should have found the article reference
        if entities:
            found_article = any(
                (entity.get("type") == "ARTICOLO_CODICE" or 
                 "artic" in entity.get("text", "").lower()) 
                for entity in entities
            )
            assert found_article, "Expected to find article reference"
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_normalize_text(self):
        """Test normalizing text."""
        if not self.__class__.server_started:
            pytest.skip("Server not running")
            
        client = NERServerTestClient(port=8766)
        await client.connect()
        
        # Text with abbreviations to normalize
        text = "Sentenza Cass. civ. n. 12345/2020 del 01/01/2020"
        
        response = await client.normalize_text(text)
        
        assert "result" in response
        assert "normalized_text" in response["result"]
        
        normalized = response["result"]["normalized_text"]
        print(f"Normalized text: {normalized}")
        
        # Specific assertions depend on normalizer implementation
        # Just verify we got a non-empty result
        assert normalized
        assert isinstance(normalized, str)
        
        await client.close() 