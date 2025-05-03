#!/usr/bin/env python
"""
Annotation System Example

Demonstrates how to use the Annotation system through the MCP client.
"""

import asyncio
import json
import sys
import os
# Non modifichiamo il sys.path, assumiamo che PYTHONPATH includa la radice del progetto
# o che il progetto sia installato correttamente

from merl_t.core.annotation import AnnotationClient


async def show_annotation_stats():
    """Display basic annotation system statistics."""
    print("\n=== Annotation System Statistics ===")
    client = AnnotationClient()
    
    try:
        stats = await client.get_annotation_stats()
        print(f"Total documents: {stats.get('total_documents', 0)}")
        print(f"Total annotations: {stats.get('total_annotations', 0)}")
        print(f"Active users: {stats.get('active_users', 0)}")
        
        print("\nDocuments by status:")
        for status, count in stats.get('documents_by_status', {}).items():
            print(f"  - {status}: {count}")
    
    except Exception as e:
        print(f"Error getting annotation stats: {e}")


async def list_annotated_documents():
    """List documents available for annotation."""
    print("\n=== Available Documents ===")
    client = AnnotationClient()
    
    try:
        # Get pending documents
        pending_docs = await client.list_documents(status="pending")
        print(f"\nPending documents ({len(pending_docs)}):")
        for doc in pending_docs[:5]:  # Show first 5
            print(f"  - {doc.get('title', 'Untitled')} (ID: {doc.get('id', 'unknown')})")
        
        if len(pending_docs) > 5:
            print(f"    ... and {len(pending_docs) - 5} more")
        
        # Get completed documents
        completed_docs = await client.list_documents(status="completed")
        print(f"\nCompleted documents ({len(completed_docs)}):")
        for doc in completed_docs[:5]:  # Show first 5
            print(f"  - {doc.get('title', 'Untitled')} (ID: {doc.get('id', 'unknown')})")
        
        if len(completed_docs) > 5:
            print(f"    ... and {len(completed_docs) - 5} more")
    
    except Exception as e:
        print(f"Error listing documents: {e}")


async def list_entity_types():
    """List entity types for annotation."""
    print("\n=== Available Entity Types ===")
    client = AnnotationClient()
    
    try:
        entities = await client.list_entity_types()
        
        # Group by category
        categories = {}
        for entity in entities:
            category = entity.get('category', 'unknown')
            if category not in categories:
                categories[category] = []
            categories[category].append(entity)
        
        # Print by category
        for category, entities in categories.items():
            print(f"\n{category.capitalize()} ({len(entities)}):")
            for entity in entities:
                print(f"  - {entity.get('display_name', 'Unknown')} ({entity.get('name', 'unknown')})")
    
    except Exception as e:
        print(f"Error listing entity types: {e}")


async def view_annotations_for_document(doc_id=None):
    """View annotations for a specific document."""
    client = AnnotationClient()
    
    if doc_id is None:
        # Get the first document if none specified
        try:
            docs = await client.list_documents()
            if not docs:
                print("No documents available")
                return
            doc_id = docs[0].get('id')
            print(f"\n=== Annotations for document: {docs[0].get('title', 'Untitled')} ===")
        except Exception as e:
            print(f"Error getting documents: {e}")
            return
    
    try:
        annotations = await client.get_annotations(doc_id)
        
        print(f"Found {len(annotations)} annotations:")
        
        # Group annotations by type
        by_type = {}
        for ann in annotations:
            entity_type = ann.get('type', 'unknown')
            if entity_type not in by_type:
                by_type[entity_type] = []
            by_type[entity_type].append(ann)
        
        # Print annotations grouped by type
        for entity_type, anns in by_type.items():
            print(f"\n{entity_type} ({len(anns)}):")
            for i, ann in enumerate(anns[:3], 1):  # Show first 3 of each type
                print(f"  {i}. \"{ann.get('text', '')}\" (positions: {ann.get('start_offset', 0)}-{ann.get('end_offset', 0)})")
            
            if len(anns) > 3:
                print(f"    ... and {len(anns) - 3} more")
    
    except Exception as e:
        print(f"Error getting annotations: {e}")


async def view_graph_chunks():
    """View knowledge graph chunks waiting for validation."""
    print("\n=== Knowledge Graph Chunks for Validation ===")
    client = AnnotationClient()
    
    try:
        # Get pending chunks
        pending_chunks = await client.get_graph_chunks(status="pending")
        
        print(f"Found {len(pending_chunks)} pending chunks:")
        for i, chunk in enumerate(pending_chunks[:5], 1):  # Show first 5
            print(f"\n{i}. {chunk.get('title', 'Untitled')} (ID: {chunk.get('id', 'unknown')})")
            print(f"   Type: {chunk.get('chunk_type', 'unknown')}")
            print(f"   Created: {chunk.get('date_created', 'unknown')}")
    
    except Exception as e:
        print(f"Error getting graph chunks: {e}")


async def open_annotation_interface():
    """Open the annotation web interface in the default browser."""
    print("\n=== Opening Annotation Web Interface ===")
    client = AnnotationClient()
    
    try:
        url = await client.get_annotation_url()
        print(f"Annotation interface available at: {url}")
        
        success = await client.open_web_interface()
        if success:
            print("Web browser opened successfully")
        else:
            print("Failed to open web browser automatically")
            print(f"Please open {url} manually in your browser")
    
    except Exception as e:
        print(f"Error opening annotation interface: {e}")


async def main():
    """Run the example."""
    print("=== Annotation System Example ===")
    print("This example demonstrates the use of the annotation system through MCP")
    
    try:
        await show_annotation_stats()
        await list_annotated_documents()
        await list_entity_types()
        await view_annotations_for_document()
        await view_graph_chunks()
        
        # Ask user if they want to open the web interface
        print("\nDo you want to open the annotation web interface? [y/N] ", end="")
        response = input().strip().lower()
        if response in ['y', 'yes']:
            await open_annotation_interface()
    
    except Exception as e:
        print(f"Error in example: {e}")
    
    print("\nExample completed")


if __name__ == "__main__":
    asyncio.run(main()) 