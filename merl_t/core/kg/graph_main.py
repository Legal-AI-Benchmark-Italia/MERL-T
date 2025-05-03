#!/usr/bin/env python3
"""
Knowledge Graph Extraction Tool

Processes text documents and builds a knowledge graph in Neo4j.
"""

import os
import sys
import json
import argparse
import asyncio
import logging
import random
from pathlib import Path
from typing import List, Dict, Any, Optional

from loguru import logger
from merl_t.config import get_config_manager
from merl_t.core.kg.storage import Neo4jGraphStorage
from merl_t.core.kg.extractor import extract_entities


async def process_jsonl_file(
    input_path: str,
    limit: Optional[int] = None,
    shuffle: bool = False,
    config_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Process a JSONL file to extract knowledge graph data.
    
    Args:
        input_path: Path to input JSONL file
        limit: Maximum number of chunks to process
        shuffle: Whether to shuffle chunks
        config_path: Path to configuration file
        
    Returns:
        Dictionary with processing statistics
    """
    # Load configuration
    config = get_config_manager()
    if config_path:
        config.load_from_file(config_path)
    
    # Initialize Neo4j storage
    storage = Neo4jGraphStorage()
    await storage.initialize()
    
    try:
        # Load chunks from JSONL file
        chunks = []
        with open(input_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    try:
                        chunk = json.loads(line)
                        chunks.append(chunk)
                    except json.JSONDecodeError as e:
                        logger.error(f"Error parsing JSON line: {e}")
        
        logger.info(f"Loaded {len(chunks)} chunks from {input_path}")
        
        # Shuffle if requested
        if shuffle:
            random.shuffle(chunks)
            logger.info("Shuffled chunks")
        
        # Limit if requested
        if limit and limit > 0:
            chunks = chunks[:limit]
            logger.info(f"Limited to {limit} chunks")
        
        # Initialize counters
        total_chunks = len(chunks)
        processed_chunks = 0
        extracted_nodes = 0
        extracted_edges = 0
        errors = 0
        
        # Setup LLM client
        await setup_llm_client(config)
        
        # Process each chunk
        for i, chunk in enumerate(chunks):
            try:
                logger.info(f"Processing chunk {i+1}/{total_chunks}")
                
                # Extract text and metadata
                text = chunk.get('text', '')
                metadata = chunk.get('metadata', {})
                
                if not text:
                    logger.warning(f"Empty text in chunk {i+1}, skipping")
                    continue
                
                # Process the chunk with extractor
                source_metadata = {
                    "source_doc_path": chunk.get("relative_path", "unknown_source"),
                    "chunk_id": chunk.get("chunk_id", f"chunk_{i}")
                }
                
                # Create a simple LLM caller function
                async def llm_func(prompt: str):
                    # Simple mock implementation for now
                    # In a real implementation, this would call an LLM API
                    logger.info(f"Would call LLM with a prompt of {len(prompt)} characters")
                    return "This is a mock LLM response for development purposes."
                
                extraction_result = await extract_entities(
                    text=text,
                    source_metadata=source_metadata,
                    knowledge_graph_inst=storage,
                    global_config=config,
                    llm_func=llm_func
                )
                
                # Update stats
                extracted_nodes += extraction_result.get("nodes_count", 0)
                extracted_edges += extraction_result.get("edges_count", 0)
                processed_chunks += 1
                
                logger.info(f"Processed chunk {i+1} with {extracted_nodes} nodes and {extracted_edges} edges")
                
            except Exception as e:
                logger.error(f"Error processing chunk {i+1}: {e}")
                errors += 1
        
        return {
            "total_chunks": total_chunks,
            "processed_chunks": processed_chunks,
            "extracted_nodes": extracted_nodes,
            "extracted_edges": extracted_edges,
            "errors": errors
        }
    
    finally:
        # Close Neo4j connection
        await storage.close()


async def setup_llm_client(config: Dict[str, Any]) -> None:
    """
    Setup the LLM client based on configuration.
    
    Args:
        config: Configuration dictionary
    """
    # This would be implemented to set up the appropriate LLM client
    # based on the configuration (e.g., OpenAI, Anthropic, etc.)
    logger.info("Setting up LLM client (placeholder)")
    pass


async def main():
    """Main entry point for the script."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Knowledge Graph Extraction Tool")
    parser.add_argument(
        "--input-jsonl",
        required=True,
        help="Path to input JSONL file"
    )
    parser.add_argument(
        "--config",
        help="Path to configuration file"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of chunks to process"
    )
    parser.add_argument(
        "--shuffle",
        action="store_true",
        help="Shuffle chunks before processing"
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Process the file
    try:
        logger.info(f"Starting processing of {args.input_jsonl}")
        
        stats = await process_jsonl_file(
            input_path=args.input_jsonl,
            limit=args.limit,
            shuffle=args.shuffle,
            config_path=args.config
        )
        
        logger.info(f"Processing completed: {stats}")
        
        return 0
    except Exception as e:
        logger.error(f"Error in main: {e}")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        sys.exit(130) 