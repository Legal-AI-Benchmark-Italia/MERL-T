#!/usr/bin/env python3
"""
Main script for the NER-Giuridico system.
Provides a unified interface for all system functionalities.

Usage:
    python main.py <command> [options]

Commands:
    server      Start the API server
    annotate    Start the annotation interface
    process     Process text or files with NER
    batch       Process multiple files in batch mode
    train       Train NER models from annotations
    convert     Convert between annotation formats
    entities    Manage entity types
    test        Run system tests
"""

import os
import sys
import json
import logging
import argparse
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('ner_giuridico.log')
    ]
)

logger = logging.getLogger(__name__)

def find_project_root():
    """Find the project root directory."""
    current_dir = Path(__file__).resolve().parent
    
    # If we're already in the src directory, the parent is the root
    if current_dir.name == 'src':
        return current_dir.parent
    
    # Otherwise, look for a directory containing both 'src' and 'config'
    while current_dir != current_dir.parent:
        if (current_dir / 'src').exists() and (current_dir / 'config').exists():
            return current_dir
        current_dir = current_dir.parent
    
    # If we can't find a matching structure, use the current directory
    logger.warning("Could not determine project root. Using current directory.")
    return Path(__file__).resolve().parent

# Add the project root to the Python path
project_root = find_project_root()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Now import the modules (after path setup)
try:
    from src.config import config
    from src.api import start_server
    from src.ner import NERGiuridico, DynamicNERGiuridico
    from src.entities.entity_manager import get_entity_manager
except ImportError as e:
    logger.error(f"Error importing modules: {e}")
    logger.error("Make sure you're running this script from the project root directory.")
    sys.exit(1)

def cmd_server(args):
    """Start the API server."""
    # Update configuration if host and port are specified
    if args.host:
        config.set('api.host', args.host)
    if args.port:
        config.set('api.port', args.port)
    
    logger.info(f"Starting NER-Giuridico API server on {config.get('api.host')}:{config.get('api.port')}")
    start_server()

def cmd_annotate(args):
    """Start the annotation interface."""
    # Add the project root to sys.path
    sys.path.insert(0, str(project_root))
    
    # Change directory to the annotation directory
    os.chdir(str(project_root / "src" / "annotation"))
    
    # Now import and run the app
    try:
        from src.annotation.app import app
        app.run(host=args.host or '0.0.0.0', port=args.port or 8080, debug=True)
    except ImportError as e:
        logger.error(f"Error importing annotation app: {e}")
        return 1
    
    return 0

def cmd_process(args):
    """Process text with NER."""
    if not args.text and not args.file:
        logger.error("Either --text or --file must be specified")
        return 1
    
    # Initialize the NER system
    if args.dynamic:
        logger.info("Using dynamic NER system")
        ner = DynamicNERGiuridico()
    else:
        logger.info("Using standard NER system")
        ner = NERGiuridico()
    
    # Process the text
    if args.text:
        logger.info("Processing provided text")
        result = ner.process(args.text)
    else:
        logger.info(f"Processing text from file {args.file}")
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                text = f.read()
            result = ner.process(text)
        except Exception as e:
            logger.error(f"Error reading file {args.file}: {e}")
            return 1
    
    # Save or print the results
    if args.output:
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            logger.info(f"Results saved to {args.output}")
        except Exception as e:
            logger.error(f"Error saving results to {args.output}: {e}")
            return 1
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    return 0

def cmd_batch(args):
    """Process multiple files in batch mode."""
    # Verify that the input directory exists
    if not os.path.isdir(args.dir):
        logger.error(f"Input directory {args.dir} does not exist")
        return 1
    
    # Create the output directory if it doesn't exist
    os.makedirs(args.output, exist_ok=True)
    
    # Initialize the NER system
    if args.dynamic:
        logger.info("Using dynamic NER system")
        ner = DynamicNERGiuridico()
    else:
        logger.info("Using standard NER system")
        ner = NERGiuridico()
    
    # Find all files with the specified extension
    import glob
    files = glob.glob(os.path.join(args.dir, f"*.{args.ext}"))
    logger.info(f"Found {len(files)} files to process")
    
    # Process each file
    processed = 0
    for file_path in files:
        file_name = os.path.basename(file_path)
        logger.info(f"Processing file {file_name}")
        
        try:
            # Read the text from the file
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            # Process the text
            result = ner.process(text)
            
            # Save the results
            output_file = os.path.join(args.output, f"{os.path.splitext(file_name)[0]}.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Results saved to {output_file}")
            processed += 1
        except Exception as e:
            logger.error(f"Error processing file {file_name}: {e}")
    
    logger.info(f"Batch processing completed. Processed {processed} out of {len(files)} files.")
    return 0

def cmd_train(args):
    """Train NER models from annotations."""
    # Verify that the annotations file exists
    if not os.path.exists(args.annotations):
        logger.error(f"Annotations file {args.annotations} does not exist")
        return 1
    
    # Import the training module
    try:
        from src.training.ner_trainer import NERTrainer, train_from_annotations
    except ImportError:
        try:
            # Try an alternative path
            sys.path.append(str(project_root / "src" / "data_lab" / "ner"))
            from src.training.ner_trainer import NERTrainer, train_from_annotations
        except ImportError as e:
            logger.error(f"Error importing training module: {e}")
            logger.error("Make sure the training module is properly installed.")
            return 1
    
    # Load the annotations
    try:
        with open(args.annotations, 'r', encoding='utf-8') as f:
            annotations_data = json.load(f)
    except Exception as e:
        logger.error(f"Error loading annotations from {args.annotations}: {e}")
        return 1
    
    # Determine the output directory
    output_dir = args.output or os.path.join(project_root, "models", args.model_type)
    os.makedirs(output_dir, exist_ok=True)
    
    # Train the model
    logger.info(f"Training {args.model_type} model from {args.annotations}")
    result = train_from_annotations(
        annotations_file=args.annotations,
        output_dir=output_dir,
        model_type=args.model_type,
        base_model=args.base_model
    )
    
    if result["success"]:
        logger.info(f"Training successful! Model saved at: {result['model_path']}")
        logger.info(f"Integration with NER system: {'Success' if result['integration_success'] else 'Failed'}")
        
        if not result['integration_success']:
            logger.warning("The model was not automatically integrated with the NER system.")
            logger.warning("You can manually integrate it by updating the config.yaml file.")
        
        return 0
    else:
        logger.error(f"Training failed: {result.get('error', 'Unknown error')}")
        return 1

def cmd_convert(args):
    """Convert between annotation formats."""
    # Import the converter module
    try:
        from src.utils.converter import (
            convert_annotations_to_spacy_format,
            convert_annotations_to_ner_format,
            convert_spacy_to_conll,
            save_annotations_for_training
        )
    except ImportError:
        try:
            # Try an alternative path
            sys.path.append(str(project_root / "src" / "data_lab" / "ner"))
            from src.utils.converter import (
                convert_annotations_to_spacy_format,
                convert_annotations_to_ner_format,
                convert_spacy_to_conll,
                save_annotations_for_training
            )
        except ImportError as e:
            logger.error(f"Error importing converter module: {e}")
            logger.error("Make sure the converter module is properly installed.")
            return 1
    
    # Verify that the input file exists
    if not os.path.exists(args.input):
        logger.error(f"Input file {args.input} does not exist")
        return 1
    
    # Load the input data
    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            input_data = json.load(f)
    except Exception as e:
        logger.error(f"Error loading data from {args.input}: {e}")
        return 1
    
    # Determine the input format
    if args.input_format == 'custom':
        # Custom format from the annotation tool
        if not args.documents:
            logger.error("--documents must be specified when using custom format")
            return 1
        
        # Load the documents
        try:
            with open(args.documents, 'r', encoding='utf-8') as f:
                documents_data = json.load(f)
        except Exception as e:
            logger.error(f"Error loading documents from {args.documents}: {e}")
            return 1
        
        # Convert based on the output format
        if args.output_format == 'spacy':
            converted_data = convert_annotations_to_spacy_format(input_data, documents_data)
        elif args.output_format == 'ner':
            converted_data = convert_annotations_to_ner_format(input_data, documents_data)
        else:
            logger.error(f"Unsupported output format: {args.output_format}")
            return 1
    elif args.input_format == 'spacy' and args.output_format == 'conll':
        # Convert spaCy to CoNLL
        if convert_spacy_to_conll(input_data, args.output):
            logger.info(f"Converted data saved to {args.output}")
            return 0
        else:
            logger.error("Conversion failed")
            return 1
    else:
        # Direct format conversion not implemented yet
        logger.error(f"Direct conversion from {args.input_format} to {args.output_format} not implemented yet")
        return 1
    
    # Save the converted data
    try:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(converted_data, f, indent=2, ensure_ascii=False)
        logger.info(f"Converted data saved to {args.output}")
    except Exception as e:
        logger.error(f"Error saving converted data to {args.output}: {e}")
        return 1
    
    return 0

def cmd_entities(args):
    """Manage entity types."""
    # Get the entity manager
    entity_manager = get_entity_manager()
    
    if args.action == 'list':
        # List all entity types
        all_entities = entity_manager.get_all_entity_types()
        
        if args.category:
            # Filter by category
            filtered_entities = {}
            for name, info in all_entities.items():
                if info.get('category') == args.category:
                    filtered_entities[name] = info
            all_entities = filtered_entities
        
        # Print the entities
        print(f"Found {len(all_entities)} entity types:")
        for name, info in all_entities.items():
            category = info.get('category', 'unknown')
            display_name = info.get('display_name', name)
            color = info.get('color', '#CCCCCC')
            print(f"- {name} ({display_name}, {category}, {color})")
    
    elif args.action == 'add':
        # Add a new entity type
        if not args.name or not args.display_name or not args.category or not args.color:
            logger.error("All of --name, --display_name, --category, and --color must be specified")
            return 1
        
        # Parse the metadata schema if provided
        metadata_schema = {}
        if args.metadata_schema:
            try:
                metadata_schema = json.loads(args.metadata_schema)
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON for metadata schema: {args.metadata_schema}")
                return 1
        
        # Parse the patterns if provided
        patterns = []
        if args.patterns:
            try:
                patterns = json.loads(args.patterns)
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON for patterns: {args.patterns}")
                return 1
        
        # Add the entity type
        success = entity_manager.add_entity_type(
            name=args.name,
            display_name=args.display_name,
            category=args.category,
            color=args.color,
            metadata_schema=metadata_schema,
            patterns=patterns
        )
        
        if success:
            logger.info(f"Entity type {args.name} added successfully")
            
            # Save the entities if requested
            if args.save:
                entity_manager.save_entities(args.save)
                logger.info(f"Entity types saved to {args.save}")
        else:
            logger.error(f"Failed to add entity type {args.name}")
            return 1
    
    elif args.action == 'remove':
        # Remove an entity type
        if not args.name:
            logger.error("--name must be specified")
            return 1
        
        # Remove the entity type
        success = entity_manager.remove_entity_type(args.name)
        
        if success:
            logger.info(f"Entity type {args.name} removed successfully")
            
            # Save the entities if requested
            if args.save:
                entity_manager.save_entities(args.save)
                logger.info(f"Entity types saved to {args.save}")
        else:
            logger.error(f"Failed to remove entity type {args.name}")
            return 1
    
    elif args.action == 'update':
        # Update an entity type
        if not args.name:
            logger.error("--name must be specified")
            return 1
        
        # Parse the metadata schema if provided
        metadata_schema = None
        if args.metadata_schema:
            try:
                metadata_schema = json.loads(args.metadata_schema)
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON for metadata schema: {args.metadata_schema}")
                return 1
        
        # Parse the patterns if provided
        patterns = None
        if args.patterns:
            try:
                patterns = json.loads(args.patterns)
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON for patterns: {args.patterns}")
                return 1
        
        # Update the entity type
        success = entity_manager.update_entity_type(
            name=args.name,
            display_name=args.display_name,
            color=args.color,
            metadata_schema=metadata_schema,
            patterns=patterns
        )
        
        if success:
            logger.info(f"Entity type {args.name} updated successfully")
            
            # Save the entities if requested
            if args.save:
                entity_manager.save_entities(args.save)
                logger.info(f"Entity types saved to {args.save}")
        else:
            logger.error(f"Failed to update entity type {args.name}")
            return 1
    
    else:
        logger.error(f"Unknown action: {args.action}")
        return 1
    
    return 0

def cmd_test(args):
    """Run system tests."""
    # Import the test module
    try:
        sys.path.append(str(project_root / "src" / "data_lab" / "ner"))
        from tests import run_all_tests
    except ImportError:
        logger.error("Test module not found. Make sure the test module is properly installed.")
        return 1
    
    # Run the tests
    logger.info("Running system tests...")
    results = run_all_tests()
    
    # Print the results
    logger.info("\n=== Test Results ===")
    for test, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        logger.info(f"{test}: {status}")
    
    # Check if all tests passed
    all_passed = all(results.values())
    
    if all_passed:
        logger.info("\n✅ All tests passed!")
        return 0
    else:
        logger.error("\n❌ Some tests failed!")
        return 1

def main():
    """Main function to parse arguments and dispatch commands."""
    parser = argparse.ArgumentParser(description='NER-Giuridico: Named Entity Recognition system for legal Italian text')
    
    # Create subparsers for each command
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # server command
    server_parser = subparsers.add_parser('server', help='Start the API server')
    server_parser.add_argument('--host', type=str, help='Host to bind the server to')
    server_parser.add_argument('--port', type=int, help='Port to bind the server to')
    server_parser.set_defaults(func=cmd_server)
    
    # annotate command
    annotate_parser = subparsers.add_parser('annotate', help='Start the annotation interface')
    annotate_parser.add_argument('--tool', type=str, choices=['label-studio', 'doccano', 'prodigy', 'custom'],
                              help='Annotation tool to use')
    annotate_parser.add_argument('--host', type=str, help='Host to bind the interface to')
    annotate_parser.add_argument('--port', type=int, help='Port to bind the interface to')
    annotate_parser.set_defaults(func=cmd_annotate)
    
    # process command
    process_parser = subparsers.add_parser('process', help='Process text with NER')
    process_parser.add_argument('--text', type=str, help='Text to process')
    process_parser.add_argument('--file', type=str, help='File containing text to process')
    process_parser.add_argument('--output', type=str, help='Output file for the results')
    process_parser.add_argument('--dynamic', action='store_true', help='Use the dynamic NER system')
    process_parser.set_defaults(func=cmd_process)
    
    # batch command
    batch_parser = subparsers.add_parser('batch', help='Process multiple files in batch mode')
    batch_parser.add_argument('--dir', type=str, required=True, help='Directory containing files to process')
    batch_parser.add_argument('--output', type=str, required=True, help='Output directory for the results')
    batch_parser.add_argument('--ext', type=str, default='txt', help='File extension to process')
    batch_parser.add_argument('--dynamic', action='store_true', help='Use the dynamic NER system')
    batch_parser.set_defaults(func=cmd_batch)
    
    # train command
    train_parser = subparsers.add_parser('train', help='Train NER models from annotations')
    train_parser.add_argument('--annotations', type=str, required=True, help='Annotations file')
    train_parser.add_argument('--output', type=str, help='Output directory for the model')
    train_parser.add_argument('--model-type', type=str, choices=['spacy', 'transformer'], 
                            default='transformer', help='Type of model to train')
    train_parser.add_argument('--base-model', type=str, help='Base model for transformer fine-tuning')
    train_parser.set_defaults(func=cmd_train)
    
    # convert command
    convert_parser = subparsers.add_parser('convert', help='Convert between annotation formats')
    convert_parser.add_argument('--input', type=str, required=True, help='Input file')
    convert_parser.add_argument('--output', type=str, required=True, help='Output file')
    convert_parser.add_argument('--input-format', type=str, required=True, 
                              choices=['custom', 'spacy', 'ner', 'conll'],
                              help='Input format')
    convert_parser.add_argument('--output-format', type=str, required=True, 
                              choices=['spacy', 'ner', 'conll'],
                              help='Output format')
    convert_parser.add_argument('--documents', type=str, help='Documents file (for custom format)')
    convert_parser.set_defaults(func=cmd_convert)
    
    # entities command
    entities_parser = subparsers.add_parser('entities', help='Manage entity types')
    entities_parser.add_argument('--action', type=str, required=True, 
                               choices=['list', 'add', 'remove', 'update'],
                               help='Action to perform')
    entities_parser.add_argument('--name', type=str, help='Entity type name')
    entities_parser.add_argument('--display-name', type=str, help='Entity type display name')
    entities_parser.add_argument('--category', type=str, help='Entity type category')
    entities_parser.add_argument('--color', type=str, help='Entity type color')
    entities_parser.add_argument('--metadata-schema', type=str, help='Entity type metadata schema (JSON)')
    entities_parser.add_argument('--patterns', type=str, help='Entity type patterns (JSON)')
    entities_parser.add_argument('--save', type=str, help='File to save entity types to')
    entities_parser.set_defaults(func=cmd_entities)
    
    # test command
    test_parser = subparsers.add_parser('test', help='Run system tests')
    test_parser.set_defaults(func=cmd_test)
    
    # Parse the arguments
    args = parser.parse_args()
    
    if not hasattr(args, 'func'):
        parser.print_help()
        return 1
    
    # Execute the command
    return args.func(args)

if __name__ == "__main__":
    sys.exit(main())