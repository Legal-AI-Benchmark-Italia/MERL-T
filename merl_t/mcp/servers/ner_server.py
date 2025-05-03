"""
NER MCP Server

Provides legal NER capabilities via MCP protocol.
"""

import asyncio
import json
from typing import Any, Dict, List, Optional

from loguru import logger

from merl_t.mcp.base import BaseMCPServer
from merl_t.mcp.protocol import (
    ServerInfo, ServerCapabilities, ToolDefinition,
    ResourceDefinition, JsonRpcResponse, JsonRpcError,
    ExecuteToolParams
)

from merl_t.core.ner import NERSystem, EntityType


class NerServer(BaseMCPServer):
    """
    MCP Server for Legal Named Entity Recognition.
    
    Exposes tools for:
    - Extracting legal entities from text
    - Retrieving entity information
    - Normalizing references
    """
    
    def __init__(
        self,
        model_name: str = "dbmdz/bert-base-italian-xxl-cased",
        spacy_model: str = "it_core_news_lg",
        use_gpu: bool = True
    ):
        """
        Initialize the NER MCP server.
        
        Args:
            model_name: Transformer model name or path
            spacy_model: spaCy model name for preprocessing
            use_gpu: Whether to use GPU for transformer inference
        """
        # Initialize server info
        server_info = ServerInfo(
            name="MERL-T Legal NER",
            version="0.1.0",
            vendor="LAIBIT",
            display_name="Legal NER",
            description="Named Entity Recognition for legal Italian texts",
        )
        
        # Initialize base MCP server
        super().__init__(server_info)
        
        # Initialize NER system
        try:
            logger.info("Initializing NER system")
            self.ner_system = NERSystem(
                model_name=model_name,
                spacy_model=spacy_model,
                use_gpu=use_gpu
            )
            logger.info("NER system initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize NER system: {e}")
            self.ner_system = None
        
        # Register tools and resources
        self._register_tools()
        self._register_resources()
        
        # Map to store document IDs for sessions
        self._session_docs: Dict[str, str] = {}
    
    def _register_tools(self):
        """Register NER tools with the MCP server."""
        # Extract entities tool
        self.register_tool(
            ToolDefinition(
                name="extract_entities",
                display_name="Extract Legal Entities",
                description="Extract legal entities from Italian text",
                input_schema={
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "The text to analyze"
                        },
                        "confidence_threshold": {
                            "type": "number",
                            "description": "Confidence threshold (0.0-1.0) for entity extraction",
                            "minimum": 0.0,
                            "maximum": 1.0,
                            "default": 0.7
                        }
                    },
                    "required": ["text"]
                }
            ),
            self.handle_extract_entities
        )
        
        # Get entities by type tool
        self.register_tool(
            ToolDefinition(
                name="get_entities_by_type",
                display_name="Get Entities by Type",
                description="Retrieve previously extracted entities of a specific type",
                input_schema={
                    "type": "object",
                    "properties": {
                        "entity_type": {
                            "type": "string",
                            "description": "Entity type to filter by",
                            "enum": [et.value for et in EntityType]
                        }
                    },
                    "required": ["entity_type"]
                }
            ),
            self.handle_get_entities_by_type
        )
        
        # Get entity by ID tool
        self.register_tool(
            ToolDefinition(
                name="get_entity_by_id",
                display_name="Get Entity by ID",
                description="Retrieve a specific entity by its ID",
                input_schema={
                    "type": "object",
                    "properties": {
                        "entity_id": {
                            "type": "string",
                            "description": "Entity ID"
                        }
                    },
                    "required": ["entity_id"]
                }
            ),
            self.handle_get_entity_by_id
        )
        
        # Normalize text tool
        self.register_tool(
            ToolDefinition(
                name="normalize_text",
                display_name="Normalize Legal Text",
                description="Normalize legal text by standardizing citations and references",
                input_schema={
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "The text to normalize"
                        }
                    },
                    "required": ["text"]
                }
            ),
            self.handle_normalize_text
        )
    
    def _register_resources(self):
        """Register NER resources with the MCP server."""
        # Entity types resource
        self.register_resource(
            ResourceDefinition(
                name="entity_types",
                display_name="Legal Entity Types",
                description="List of supported legal entity types",
                read_only=True
            ),
            read_handler=self.handle_read_entity_types
        )
        
        # Entities resource for the current session
        self.register_resource(
            ResourceDefinition(
                name="entities",
                display_name="Extracted Entities",
                description="Entities extracted in the current session",
                read_only=True
            ),
            read_handler=self.handle_read_entities
        )
    
    def _get_doc_id(self, client_id: str) -> str:
        """
        Get document ID for a client session.
        
        Args:
            client_id: Client session ID
            
        Returns:
            Document ID
        """
        if client_id not in self._session_docs:
            self._session_docs[client_id] = f"session_{client_id}"
        return self._session_docs[client_id]
    
    async def handle_extract_entities(self, params: Dict[str, Any], client_id: str) -> Dict[str, Any]:
        """
        Handle extract_entities tool execution.
        
        Args:
            params: Tool parameters
            client_id: Client session ID
            
        Returns:
            Extracted entities
        """
        if not self.ner_system:
            raise JsonRpcError(
                code=-32603,
                message="NER system is not initialized"
            )
        
        text = params.get("text", "")
        if not text:
            raise JsonRpcError(
                code=-32602,
                message="Text parameter is required"
            )
        
        # Get document ID for this session
        doc_id = self._get_doc_id(client_id)
        
        # Override confidence threshold if provided
        if "confidence_threshold" in params:
            original_threshold = self.ner_system.recognizer.confidence_threshold
            self.ner_system.recognizer.confidence_threshold = params["confidence_threshold"]
        
        try:
            # Process text with NER system
            result = self.ner_system.process(text, doc_id)
            
            # Prepare simplified response
            entity_count = result.get("entity_count", 0)
            entities_by_type = result.get("entities_by_type", {})
            
            # Create summary of entities by type
            entity_summary = []
            for entity_type, entities in entities_by_type.items():
                entity_summary.append({
                    "type": entity_type,
                    "count": len(entities),
                    "examples": [e["text"] for e in entities[:3]]
                })
            
            return {
                "success": True,
                "entity_count": entity_count,
                "entity_summary": entity_summary,
                "has_entities": entity_count > 0,
                "message": f"Found {entity_count} legal entities"
            }
        except Exception as e:
            logger.error(f"Error extracting entities: {e}")
            raise JsonRpcError(
                code=-32603,
                message=f"Error extracting entities: {str(e)}"
            )
        finally:
            # Restore original threshold if changed
            if "confidence_threshold" in params:
                self.ner_system.recognizer.confidence_threshold = original_threshold
    
    async def handle_get_entities_by_type(self, params: Dict[str, Any], client_id: str) -> Dict[str, Any]:
        """
        Handle get_entities_by_type tool execution.
        
        Args:
            params: Tool parameters
            client_id: Client session ID
            
        Returns:
            Entities of the specified type
        """
        if not self.ner_system:
            raise JsonRpcError(
                code=-32603,
                message="NER system is not initialized"
            )
        
        entity_type = params.get("entity_type")
        if not entity_type:
            raise JsonRpcError(
                code=-32602,
                message="Entity type parameter is required"
            )
        
        # Get document ID for this session
        doc_id = self._get_doc_id(client_id)
        
        try:
            # Get entities of the specified type
            entities = self.ner_system.get_entities_by_type(entity_type, doc_id)
            
            return {
                "success": True,
                "entity_type": entity_type,
                "count": len(entities),
                "entities": entities
            }
        except Exception as e:
            logger.error(f"Error getting entities by type: {e}")
            raise JsonRpcError(
                code=-32603,
                message=f"Error getting entities by type: {str(e)}"
            )
    
    async def handle_get_entity_by_id(self, params: Dict[str, Any], client_id: str) -> Dict[str, Any]:
        """
        Handle get_entity_by_id tool execution.
        
        Args:
            params: Tool parameters
            client_id: Client session ID
            
        Returns:
            Entity information
        """
        if not self.ner_system:
            raise JsonRpcError(
                code=-32603,
                message="NER system is not initialized"
            )
        
        entity_id = params.get("entity_id")
        if not entity_id:
            raise JsonRpcError(
                code=-32602,
                message="Entity ID parameter is required"
            )
        
        # Get document ID for this session
        doc_id = self._get_doc_id(client_id)
        
        try:
            # Get entity by ID
            entity = self.ner_system.get_entity_by_id(entity_id, doc_id)
            
            if not entity:
                return {
                    "success": False,
                    "message": f"Entity with ID {entity_id} not found"
                }
            
            return {
                "success": True,
                "entity_id": entity_id,
                "entity": entity
            }
        except Exception as e:
            logger.error(f"Error getting entity by ID: {e}")
            raise JsonRpcError(
                code=-32603,
                message=f"Error getting entity by ID: {str(e)}"
            )
    
    async def handle_normalize_text(self, params: Dict[str, Any], client_id: str) -> Dict[str, Any]:
        """
        Handle normalize_text tool execution.
        
        Args:
            params: Tool parameters
            client_id: Client session ID
            
        Returns:
            Normalized text
        """
        if not self.ner_system:
            raise JsonRpcError(
                code=-32603,
                message="NER system is not initialized"
            )
        
        text = params.get("text", "")
        if not text:
            raise JsonRpcError(
                code=-32602,
                message="Text parameter is required"
            )
        
        try:
            # Only normalize the text, don't extract entities
            result = self.ner_system.preprocessor.process(text)
            normalized_text = result.get("normalized_text", text)
            legal_references = result.get("legal_references", [])
            
            return {
                "success": True,
                "original_text": text,
                "normalized_text": normalized_text,
                "reference_count": len(legal_references),
                "references": legal_references
            }
        except Exception as e:
            logger.error(f"Error normalizing text: {e}")
            raise JsonRpcError(
                code=-32603,
                message=f"Error normalizing text: {str(e)}"
            )
    
    async def handle_read_entity_types(self, params: Optional[Dict[str, Any]], client_id: str) -> Dict[str, Any]:
        """
        Handle read_entity_types resource request.
        
        Args:
            params: Resource parameters
            client_id: Client session ID
            
        Returns:
            Entity types information
        """
        # Create a list of entity types with descriptions
        entity_types = []
        for et in EntityType:
            entity_types.append({
                "name": et.value,
                "description": et.__doc__ or "",
                "examples": self._get_entity_type_examples(et)
            })
        
        return {
            "entity_types": entity_types,
            "total": len(entity_types)
        }
    
    async def handle_read_entities(self, params: Optional[Dict[str, Any]], client_id: str) -> Dict[str, Any]:
        """
        Handle read_entities resource request.
        
        Args:
            params: Resource parameters
            client_id: Client session ID
            
        Returns:
            Entities information
        """
        if not self.ner_system:
            return {
                "entities": [],
                "total": 0,
                "message": "NER system is not initialized"
            }
        
        # Get document ID for this session
        doc_id = self._get_doc_id(client_id)
        
        # Get all entities for this document
        entities = self.ner_system.entity_manager.get_all_entities(doc_id)
        
        # Convert to dictionary format
        entity_dicts = [
            {"id": entity_id, **entity.to_dict()}
            for entity_id, entity in entities
        ]
        
        return {
            "entities": entity_dicts,
            "total": len(entity_dicts)
        }
    
    def _get_entity_type_examples(self, entity_type: EntityType) -> List[str]:
        """
        Get examples for an entity type.
        
        Args:
            entity_type: Entity type
            
        Returns:
            List of example strings
        """
        examples = {
            EntityType.ARTICOLO_CODICE: ["art. 2043 c.c.", "art. 575 c.p.", "art. 115 c.p.c."],
            EntityType.ARTICOLO_LEGGE: ["art. 5 legge 241/1990", "art. 3 d.lgs. 50/2016"],
            EntityType.LEGGE: ["legge 241/1990", "d.lgs. 50/2016", "Costituzione"],
            EntityType.DECRETO: ["d.lgs. 196/2003", "d.l. 18/2020", "DPCM 11 marzo 2020"],
            EntityType.SENTENZA: ["Cass. civ. 1234/2020", "Corte Cost. 115/2018", "Cons. Stato 456/2019"],
            EntityType.PRECEDENTE: ["come stabilito in Cass. 1234/2020", "secondo TAR Lazio 567/2021"],
            EntityType.PRINCIPIO_GIURIDICO: ["legittimo affidamento", "buona fede", "proporzionalità"],
            EntityType.ISTITUTO_GIURIDICO: ["responsabilità extracontrattuale", "diritto di recesso"],
            EntityType.BENE_GIURIDICO: ["diritto alla salute", "libertà personale", "privacy"],
            EntityType.PARTE_PROCESSUALE: ["attore", "convenuto", "ricorrente", "imputato"],
            EntityType.ORGANO_GIUDIZIARIO: ["Tribunale di Milano", "Corte d'Appello di Roma"],
            EntityType.TERMINE_GIURIDICO: ["anatocismo", "negozio giuridico", "enfiteusi"],
            EntityType.DATA_GIURIDICA: ["entro il 31 dicembre 2023", "in data 15/03/2022"],
        }
        
        return examples.get(entity_type, ["Esempio non disponibile"])

# --- Main execution (Example for testing) ---
async def main():
    server = NerServer()
    # The start method needs a proper transport implementation
    # await server.start()
    print("NER Server initialized but start() needs a real transport.")
    print("Registered tools:", list(server._tools.keys()))
    print("Registered resources:", list(server._resources.keys()))

if __name__ == "__main__":
    # This allows running the server directly for testing, but needs
    # a proper async loop and transport mechanism.
    # Example: Use asyncio streams for stdio

    # A basic example - running the server to check initialization
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer stopping...") 