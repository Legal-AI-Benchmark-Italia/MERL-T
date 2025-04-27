#!/usr/bin/env python3
"""
Main script for the NER-Giuridico system.
Provides a unified command-line interface for all system functionalities.

Usage:
    python main.py <command> [options]

Command Groups:
    server      - API and annotation server management
    process     - Text processing commands
    entity      - Entity management
    train       - Model training and evaluation
    convert     - Data conversion utilities
    knowledge   - Knowledge graph integration
    utils       - Utility commands
"""

import os
import sys
import json
import logging
import argparse
import subprocess
import traceback
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import faulthandler

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('ner_giuridico.log')
    ]
)

logger = logging.getLogger("NER-Giuridico")

def find_project_root():
    """Find the project root directory based on directory structure."""
    current_dir = Path(__file__).resolve().parent
    
    # Look up to 5 levels for src and config directories
    for _ in range(5):
        # Check if we have a valid project structure
        if (current_dir / "src").exists() or (current_dir / "ner_giuridico").exists():
            return current_dir
        
        # Move up one level
        parent = current_dir.parent
        if parent == current_dir:  # Reached filesystem root
            break
        current_dir = parent
    
    # If we're in a subdirectory of the project, try to find the root
    if "ner-giuridico" in str(current_dir) or "ner_giuridico" in str(current_dir):
        parts = Path(current_dir).parts
        for i in range(len(parts), 0, -1):
            potential_root = Path(*parts[:i])
            if (potential_root / "src").exists() or (potential_root / "ner_giuridico").exists():
                return potential_root
    
    # If we can't find a suitable root, use the current directory
    logger.warning("Could not determine project root. Using current directory.")
    return Path(__file__).resolve().parent

# Determine project root and add to Python path
PROJECT_ROOT = find_project_root()
sys.path.insert(0, str(PROJECT_ROOT))

# Try multiple import paths to handle different project structures
try:
    # Assume the script is run relative to the project root or the new structure is in PYTHONPATH
    from src.core.ner_giuridico.config import config
    from src.core.ner_giuridico.ner import NERGiuridico, DynamicNERGiuridico
    from src.core.ner_giuridico.api import start_server
    from src.core.ner_giuridico.entities.entity_manager import get_entity_manager
    from src.core.annotation.app import app as annotation_app
    IMPORT_PATH = "new_structure"

# except ImportError: # Removed fallback logic as it's likely incorrect now
#     # Try importing from src
#     from ner_giuridico.config import config
#     from ner_giuridico.ner import NERGiuridico, DynamicNERGiuridico
#     from ner_giuridico.api import start_server
#     from ner_giuridico.entities.entity_manager import get_entity_manager
#     from ner_giuridico.annotation.app import app as annotation_app
#     IMPORT_PATH = "src" # This path likely doesn't exist anymore

except ImportError as e:
    logger.error(f"Error importing modules: {e}")
    logger.error("Make sure you're running this script from the project root directory (MERL-T).")
    logger.info("Continuing with limited functionality. Some commands may not work.")
    IMPORT_PATH = None

# Attempt to import optional modules
try:
    if IMPORT_PATH == "new_structure":
        from src.core.ner_giuridico.utils.converter import (
            convert_annotations_to_spacy_format,
            convert_annotations_to_ner_format,
            convert_spacy_to_conll,
            save_annotations_for_training
        )
        from src.core.ner_giuridico.training.ner_trainer import train_from_annotations
    # Removed fallback logic
    # elif IMPORT_PATH == "src":
    #     from ner_giuridico.utils.converter import (
    #         convert_annotations_to_spacy_format,
    #         convert_annotations_to_ner_format,
    #         convert_spacy_to_conll,
    #         save_annotations_for_training
    #     )
    #     from ner_giuridico.training.ner_trainer import train_from_annotations
    OPTIONAL_MODULES_LOADED = True
except ImportError:
    logger.warning("Some optional modules could not be imported. Related commands may not be available.")
    OPTIONAL_MODULES_LOADED = False

# Define the command structure
COMMANDS = {
    # Server commands
    "server": {
        "help": "Start the API server",
        "func": "cmd_server",
    },
    "annotate": {
        "help": "Start the annotation interface",
        "func": "cmd_annotate",
    },
    
    # Processing commands
    "process": {
        "help": "Process text with NER",
        "func": "cmd_process",
    },
    "batch": {
        "help": "Process multiple files in batch mode",
        "func": "cmd_batch",
    },
    
    # Entity management commands
    "entities": {
        "help": "Manage entity types",
        "func": "cmd_entities",
    },
    
    # Training commands
    "train": {
        "help": "Train NER models from annotated data",
        "func": "cmd_train",
    },
    "evaluate": {
        "help": "Evaluate NER models on test data",
        "func": "cmd_evaluate",
    },
    
    # Conversion commands
    "convert": {
        "help": "Convert between annotation formats",
        "func": "cmd_convert",
    },
    "export": {
        "help": "Export models in deployable formats",
        "func": "cmd_export",
    },
    
    # Knowledge graph commands
    "graph": {
        "help": "Interact with the knowledge graph",
        "func": "cmd_graph",
    },
    
    # Utility commands
    "test": {
        "help": "Run system tests",
        "func": "cmd_test",
    },
    "setup": {
        "help": "Set up the system environment",
        "func": "cmd_setup",
    },
    "version": {
        "help": "Display version information",
        "func": "cmd_version",
    }
}

# Command implementations
def cmd_server(args):
    """Start the API server."""
    if IMPORT_PATH is None:
        logger.error("API server functionality not available due to import errors.")
        return 1
    
    # Update configuration if host and port are specified
    if args.host:
        config.set('api.host', args.host)
    if args.port:
        config.set('api.port', args.port)
    
    logger.info(f"Starting NER-Giuridico API server on {config.get('api.host')}:{config.get('api.port')}")
    
    try:
        # Start in a separate process if requested
        if args.daemon:
            # Updated module path
            cmd = [sys.executable, "-m", "src.core.ner_giuridico.api"]
            # Removed fallback logic
            # if IMPORT_PATH == "src":
            #     cmd = [sys.executable, "-m", "src.ner_giuridico.api"]
                
            subprocess.Popen(cmd, start_new_session=True)
            logger.info("API server started in background")
            return 0
        else:
            # Start in the current process
            start_server()
            return 0
    except KeyboardInterrupt:
        logger.info("API server stopped by user")
        return 0
    except Exception as e:
        logger.error(f"Error starting API server: {e}")
        return 1

def cmd_annotate(args):
    """Start the annotation interface."""
    if IMPORT_PATH is None:
        logger.error("Annotation interface not available due to import errors.")
        return 1
    
    # Prepare Flask app arguments
    flask_args = {
        'host': args.host or '0.0.0.0',
        'port': args.port or 8080,
        'debug': args.debug
    }
    
    try:
        logger.info(f"Starting annotation interface on {flask_args['host']}:{flask_args['port']}")
        
        if args.daemon:
            # Start in a separate process
            # Updated module path
            cmd = [sys.executable, "-m", "src.core.ner_giuridico.annotation.app"]
            # Removed fallback logic
            # if IMPORT_PATH == "src":
            #     cmd = [sys.executable, "-m", "src.ner_giuridico.annotation.app"]
                
            subprocess.Popen(cmd, start_new_session=True)
            logger.info("Annotation interface started in background")
            return 0
        else:
            # Start in the current process
            annotation_app.run(**flask_args)
            return 0
    except KeyboardInterrupt:
        logger.info("Annotation interface stopped by user")
        return 0
    except Exception as e:
        logger.error(f"Error starting annotation interface: {e}")
        return 1

def cmd_process(args):
    """Process text with NER."""
    if IMPORT_PATH is None:
        logger.error("NER processing not available due to import errors.")
        return 1
    
    if not args.text and not args.file:
        logger.error("Either --text or --file must be specified")
        return 1
    
    try:
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
            if args.verbose:
                print(f"Text: {args.text}")
            result = ner.process(args.text)
        else:
            logger.info(f"Processing text from file {args.file}")
            try:
                with open(args.file, 'r', encoding='utf-8') as f:
                    text = f.read()
                if args.verbose:
                    print(f"Read {len(text)} characters from {args.file}")
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
            # Print a summary if requested
            if args.summary:
                print("\nRecognized Entities:")
                for entity in result["entities"]:
                    print(f"- {entity['text']} ({entity['type']})")
                    if args.verbose and entity.get('normalized_text'):
                        print(f"  Normalized: {entity['normalized_text']}")
                        if entity.get('metadata'):
                            print(f"  Metadata: {entity['metadata']}")
                
                print("\nStructured References:")
                for ref_type, refs in result["references"].items():
                    if refs:
                        print(f"\n{ref_type.capitalize()}:")
                        for ref in refs:
                            print(f"- {ref.get('normalized_text', ref.get('text', 'Unknown'))}")
            else:
                # Print the full result as JSON
                print(json.dumps(result, indent=2, ensure_ascii=False))
        
        return 0
    except Exception as e:
        logger.error(f"Error processing text: {e}")
        if args.verbose:
            traceback.print_exc()
        return 1

def cmd_batch(args):
    """Process multiple files in batch mode."""
    if IMPORT_PATH is None:
        logger.error("NER processing not available due to import errors.")
        return 1
    
    # Verify that the input directory exists
    if not os.path.isdir(args.dir):
        logger.error(f"Input directory {args.dir} does not exist")
        return 1
    
    # Create the output directory if it doesn't exist
    os.makedirs(args.output, exist_ok=True)
    
    try:
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
        
        if not files:
            logger.warning(f"No files with extension .{args.ext} found in {args.dir}")
            return 0
        
        # Process files according to parallelism setting
        if args.parallel > 1:
            successful = _batch_process_parallel(ner, files, args.output, args.verbose, args.parallel)
        else:
            successful = _batch_process_sequential(ner, files, args.output, args.verbose)
        
        logger.info(f"Batch processing completed. Processed {successful} out of {len(files)} files.")
        
        # Return 0 if all files were processed successfully, 1 otherwise
        return 0 if successful == len(files) else 1
    
    except Exception as e:
        logger.error(f"Error in batch processing: {e}")
        if args.verbose:
            traceback.print_exc()
        return 1

def _batch_process_sequential(ner, files, output_dir, verbose):
    """Process files sequentially with progress bar."""
    successful = 0
    
    # Create a progress bar
    with tqdm(total=len(files), desc="Processing files") as pbar:
        for file_path in files:
            file_name = os.path.basename(file_path)
            
            try:
                # Read the text from the file
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
                
                # Process the text
                result = ner.process(text)
                
                # Save the results
                output_file = os.path.join(output_dir, f"{os.path.splitext(file_name)[0]}.json")
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
                
                successful += 1
                if verbose:
                    tqdm.write(f"Processed {file_name}: Found {len(result['entities'])} entities")
            
            except Exception as e:
                if verbose:
                    tqdm.write(f"Error processing file {file_name}: {e}")
            
            # Update the progress bar
            pbar.update(1)
    
    return successful

def _batch_process_parallel(ner, files, output_dir, verbose, max_workers):
    """Process files in parallel with progress bar."""
    successful = 0
    
    # Define a processing function
    def process_file(file_path):
        file_name = os.path.basename(file_path)
        try:
            # Read the text from the file
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            # Process the text
            result = ner.process(text)
            
            # Save the results
            output_file = os.path.join(output_dir, f"{os.path.splitext(file_name)[0]}.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            return (True, file_name, len(result['entities']))
        except Exception as e:
            return (False, file_name, str(e))
    
    # Process files in parallel with progress bar
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_file, file_path): file_path for file_path in files}
        
        with tqdm(total=len(files), desc="Processing files") as pbar:
            for future in as_completed(futures):
                result = future.result()
                if result[0]:  # Success
                    successful += 1
                    if verbose:
                        tqdm.write(f"Processed {result[1]}: Found {result[2]} entities")
                else:  # Error
                    if verbose:
                        tqdm.write(f"Error processing {result[1]}: {result[2]}")
                
                pbar.update(1)
    
    return successful

def cmd_entities(args):
    """Manage entity types."""
    if IMPORT_PATH is None:
        logger.error("Entity management not available due to import errors.")
        return 1
    
    try:
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
            
            # Group by category if requested
            if args.group_by_category:
                by_category = {}
                for name, info in all_entities.items():
                    category = info.get('category', 'unknown')
                    if category not in by_category:
                        by_category[category] = []
                    by_category[category].append((name, info))
                
                for category, entities in by_category.items():
                    print(f"\n{category.upper()}:")
                    for name, info in entities:
                        display_name = info.get('display_name', name)
                        color = info.get('color', '#CCCCCC')
                        print(f"  - {name} ({display_name}, {color})")
            else:
                # Print flat list
                for name, info in all_entities.items():
                    category = info.get('category', 'unknown')
                    display_name = info.get('display_name', name)
                    color = info.get('color', '#CCCCCC')
                    print(f"- {name} ({display_name}, {category}, {color})")
            
            # Print details if requested
            if args.details and args.entity_name:
                entity_info = entity_manager.get_entity_type(args.entity_name)
                if entity_info:
                    print(f"\nDetails for {args.entity_name}:")
                    for key, value in entity_info.items():
                        print(f"  {key}: {value}")
                else:
                    print(f"\nEntity {args.entity_name} not found")
        
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
        
        elif args.action == 'export':
            # Export entity types
            if not args.output:
                logger.error("--output must be specified for export")
                return 1
            
            # Export the entities
            success = entity_manager.save_entities(args.output)
            
            if success:
                logger.info(f"Entity types exported to {args.output}")
            else:
                logger.error(f"Failed to export entity types to {args.output}")
                return 1
        
        elif args.action == 'import':
            # Import entity types
            if not args.input:
                logger.error("--input must be specified for import")
                return 1
            
            # Import the entities
            success = entity_manager.load_entities(args.input)
            
            if success:
                logger.info(f"Entity types imported from {args.input}")
            else:
                logger.error(f"Failed to import entity types from {args.input}")
                return 1
        
        else:
            logger.error(f"Unknown action: {args.action}")
            return 1
        
        return 0
    
    except Exception as e:
        logger.error(f"Error in entity management: {e}")
        if args.verbose:
            traceback.print_exc()
        return 1

def cmd_train(args):
    """Train NER models from annotated data."""
    if not OPTIONAL_MODULES_LOADED:
        logger.error("Training functionality not available. Make sure all required modules are installed.")
        return 1
    
    # Verify that the annotations file exists
    if not os.path.exists(args.annotations):
        logger.error(f"Annotations file {args.annotations} does not exist")
        return 1
    
    try:
        logger.info(f"Training {args.model_type} model from {args.annotations}")
        
        # Train the model
        result = train_from_annotations(
            annotations_file=args.annotations,
            output_dir=args.output,
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
    
    except Exception as e:
        logger.error(f"Error in model training: {e}")
        if args.verbose:
            traceback.print_exc()
        return 1

def cmd_evaluate(args):
    """Evaluate NER models on test data."""
    if not OPTIONAL_MODULES_LOADED:
        logger.error("Evaluation functionality not available. Make sure all required modules are installed.")
        return 1
    
    # This is a placeholder for the evaluate command
    # You would implement model evaluation logic here
    logger.info("Model evaluation not yet implemented")
    return 0

def cmd_convert(args):
    """Convert between annotation formats."""
    if not OPTIONAL_MODULES_LOADED:
        logger.error("Conversion functionality not available. Make sure all required modules are installed.")
        return 1
    
    # Verify that the input file exists
    if not os.path.exists(args.input):
        logger.error(f"Input file {args.input} does not exist")
        return 1
    
    try:
        # Load the input data
        with open(args.input, 'r', encoding='utf-8') as f:
            input_data = json.load(f)
        
        # Determine the input format and convert accordingly
        if args.input_format == 'custom':
            # Custom format from the annotation tool requires document data
            if not args.documents:
                logger.error("--documents must be specified when using custom format")
                return 1
            
            # Load the documents
            with open(args.documents, 'r', encoding='utf-8') as f:
                documents_data = json.load(f)
            
            # Convert based on the output format
            if args.output_format == 'spacy':
                logger.info(f"Converting from custom to spaCy format")
                converted_data = convert_annotations_to_spacy_format(input_data, documents_data)
            elif args.output_format == 'ner':
                logger.info(f"Converting from custom to NER format")
                converted_data = convert_annotations_to_ner_format(input_data, documents_data)
            else:
                logger.error(f"Unsupported output format: {args.output_format}")
                return 1
        
        elif args.input_format == 'spacy' and args.output_format == 'conll':
            # Convert spaCy to CoNLL format
            logger.info(f"Converting from spaCy to CoNLL format")
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
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(converted_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Converted data saved to {args.output}")
        return 0
    
    except Exception as e:
        logger.error(f"Error in data conversion: {e}")
        if args.verbose:
            traceback.print_exc()
        return 1

def cmd_export(args):
    """Export models in deployable formats."""
    if not OPTIONAL_MODULES_LOADED:
        logger.error("Export functionality not available. Make sure all required modules are installed.")
        return 1
    
    # This is a placeholder for the export command
    # You would implement model export logic here
    logger.info("Model export not yet implemented")
    return 0

def cmd_graph(args):
    """Interact with the knowledge graph."""
    # This is a placeholder for the graph command
    # You would implement knowledge graph interaction logic here
    logger.info("Knowledge graph interaction not yet implemented")
    return 0

def cmd_test(args):
    """Run system tests."""
    try:
        # Import test module
        try:
            from tests.test import run_all_tests
        except ImportError:
            # Try alternative path
            from tests.test import run_all_tests
    
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
    
    except ImportError:
        logger.error("Test module not found. Make sure the test module is properly installed.")
        return 1
    except Exception as e:
        logger.error(f"Error running tests: {e}")
        if args.verbose:
            traceback.print_exc()
        return 1

""" def cmd_setup(args):
    try:
        # Import setup module
        try:
            from setup import main as setup_main
        except ImportError:
            logger.error("Setup module not found.")
            logger.info("Attempting to run setup directly...")
            
            # Try running the setup script directly
            result = subprocess.run([sys.executable, "setup.py", "--all"], 
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode == 0:
                logger.info("Setup completed successfully")
                return 0
            else:
                logger.error("Setup failed")
                if args.verbose:
                    print(result.stdout.decode())
                    print(result.stderr.decode())
                return 1
        
        # Run the setup
        result = setup_main()
        if result == 0:
            logger.info("Setup completed successfully")
            return 0
        else:
            logger.error("Setup failed")
            return 1
    
    except Exception as e:
        logger.error(f"Error in setup: {e}")
        if args.verbose:
            traceback.print_exc()
        return 1
 """

def cmd_version(args):
    """Display version information."""
    try:
        # Try to import the version
        try:
            # Updated import path
            from src.core.ner_giuridico import __version__
            version = __version__
        except (ImportError, AttributeError):
            version = "Unknown"
        
        print(f"NER-Giuridico version: {version}")
        
        # Print Python version
        print(f"Python version: {sys.version}")
        
        # Print dependency versions if verbose
        if args.verbose:
            print("\nDependency versions:")
            
            try:
                import spacy
                print(f"spaCy: {spacy.__version__}")
            except ImportError:
                print("spaCy: Not installed")
                
            try:
                import transformers
                print(f"transformers: {transformers.__version__}")
            except ImportError:
                print("transformers: Not installed")
                      
            try:
                import fastapi
                print(f"FastAPI: {fastapi.__version__}")
            except ImportError:
                print("FastAPI: Not installed")
                
            try:
                import flask
                print(f"Flask: {flask.__version__}")
            except ImportError:
                print("Flask: Not installed")
                
            try:
                import neo4j
                print(f"Neo4j: {neo4j.__version__}")
            except ImportError:
                print("Neo4j: Not installed")
        
        return 0
    
    except Exception as e:
        logger.error(f"Error getting version information: {e}")
        if args.verbose:
            traceback.print_exc()
        return 1

def main():
    """Main function to parse arguments and dispatch commands."""
    parser = argparse.ArgumentParser(
        description='NER-Giuridico: Named Entity Recognition system for legal Italian text',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Command Groups:
  server      - API and annotation server management
  process     - Text processing commands
  entity      - Entity management
  train       - Model training and evaluation
  convert     - Data conversion utilities
  knowledge   - Knowledge graph integration
  utils       - Utility commands
        """
    )
    
    # Global arguments
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output')
    parser.add_argument('--config', type=str, help='Path to configuration file')
    
    # Create subparsers for each command
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # SERVER COMMANDS
    # server command
    server_parser = subparsers.add_parser('server', help='Start the API server')
    server_parser.add_argument('--host', type=str, help='Host to bind the server to')
    server_parser.add_argument('--port', type=int, help='Port to bind the server to')
    server_parser.add_argument('--daemon', action='store_true', help='Run the server as a daemon')
    server_parser.set_defaults(func=cmd_server)
    
    # annotate command
    annotate_parser = subparsers.add_parser('annotate', help='Start the annotation interface')
    annotate_parser.add_argument('--tool', type=str, choices=['label-studio', 'doccano', 'prodigy', 'custom'],
                              help='Annotation tool to use')
    annotate_parser.add_argument('--host', type=str, help='Host to bind the interface to')
    annotate_parser.add_argument('--port', type=int, help='Port to bind the interface to')
    annotate_parser.add_argument('--debug', action='store_true', help='Run in debug mode')
    annotate_parser.add_argument('--daemon', action='store_true', help='Run the interface as a daemon')
    annotate_parser.set_defaults(func=cmd_annotate)
    
    # PROCESSING COMMANDS
    # process command
    process_parser = subparsers.add_parser('process', help='Process text with NER')
    process_parser.add_argument('--text', type=str, help='Text to process')
    process_parser.add_argument('--file', type=str, help='File containing text to process')
    process_parser.add_argument('--output', type=str, help='Output file for the results')
    process_parser.add_argument('--dynamic', action='store_true', help='Use the dynamic NER system')
    process_parser.add_argument('--summary', action='store_true', help='Print a summary of the results')
    process_parser.set_defaults(func=cmd_process)
    
    # batch command
    batch_parser = subparsers.add_parser('batch', help='Process multiple files in batch mode')
    batch_parser.add_argument('--dir', type=str, required=True, help='Directory containing files to process')
    batch_parser.add_argument('--output', type=str, required=True, help='Output directory for the results')
    batch_parser.add_argument('--ext', type=str, default='txt', help='File extension to process')
    batch_parser.add_argument('--dynamic', action='store_true', help='Use the dynamic NER system')
    batch_parser.add_argument('--parallel', type=int, default=1, help='Number of parallel processes to use')
    batch_parser.set_defaults(func=cmd_batch)
    
    # ENTITY MANAGEMENT COMMANDS
    # entities command
    entities_parser = subparsers.add_parser('entities', help='Manage entity types')
    entities_parser.add_argument('--action', type=str, required=True, 
                               choices=['list', 'add', 'remove', 'update', 'export', 'import'],
                               help='Action to perform')
    entities_parser.add_argument('--name', type=str, help='Entity type name')
    entities_parser.add_argument('--display-name', type=str, help='Entity type display name')
    entities_parser.add_argument('--category', type=str, help='Entity type category')
    entities_parser.add_argument('--color', type=str, help='Entity type color')
    entities_parser.add_argument('--metadata-schema', type=str, help='Entity type metadata schema (JSON)')
    entities_parser.add_argument('--patterns', type=str, help='Entity type patterns (JSON)')
    entities_parser.add_argument('--save', type=str, help='File to save entity types to')
    entities_parser.add_argument('--input', type=str, help='File to import entity types from')
    entities_parser.add_argument('--output', type=str, help='File to export entity types to')
    entities_parser.add_argument('--group-by-category', action='store_true', help='Group entity types by category')
    entities_parser.add_argument('--details', action='store_true', help='Show detailed information for a specific entity')
    entities_parser.add_argument('--entity-name', type=str, help='Entity name to show details for')
    entities_parser.set_defaults(func=cmd_entities)
    
    # TRAINING COMMANDS
    # train command
    train_parser = subparsers.add_parser('train', help='Train NER models from annotated data')
    train_parser.add_argument('--annotations', type=str, required=True, help='Annotations file')
    train_parser.add_argument('--output', type=str, help='Output directory for the model')
    train_parser.add_argument('--model-type', type=str, choices=['spacy', 'transformer'], 
                            default='transformer', help='Type of model to train')
    train_parser.add_argument('--base-model', type=str, help='Base model for transformer fine-tuning')
    train_parser.set_defaults(func=cmd_train)
    
    # evaluate command
    evaluate_parser = subparsers.add_parser('evaluate', help='Evaluate NER models on test data')
    evaluate_parser.add_argument('--model', type=str, required=True, help='Model to evaluate')
    evaluate_parser.add_argument('--test-data', type=str, required=True, help='Test data file')
    evaluate_parser.add_argument('--output', type=str, help='Output file for evaluation results')
    evaluate_parser.set_defaults(func=cmd_evaluate)
    
    # CONVERSION COMMANDS
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
    
    # export command
    export_parser = subparsers.add_parser('export', help='Export models in deployable formats')
    export_parser.add_argument('--model', type=str, required=True, help='Model to export')
    export_parser.add_argument('--output', type=str, required=True, help='Output file or directory')
    export_parser.add_argument('--format', type=str, choices=['onnx', 'torchscript', 'zip'], 
                             default='zip', help='Export format')
    export_parser.set_defaults(func=cmd_export)
    
    # KNOWLEDGE GRAPH COMMANDS
    # graph command
    graph_parser = subparsers.add_parser('graph', help='Interact with the knowledge graph')
    graph_parser.add_argument('--action', type=str, required=True, 
                            choices=['query', 'import', 'export', 'update'],
                            help='Action to perform')
    graph_parser.add_argument('--query', type=str, help='Query to execute')
    graph_parser.add_argument('--input', type=str, help='Input file for import')
    graph_parser.add_argument('--output', type=str, help='Output file for export')
    graph_parser.add_argument('--type', type=str, help='Type of entities to query/import/export')
    graph_parser.set_defaults(func=cmd_graph)
    
    # UTILITY COMMANDS
    # test command
    test_parser = subparsers.add_parser('test', help='Run system tests')
    test_parser.set_defaults(func=cmd_test)
    
    # setup command
    setup_parser = subparsers.add_parser('setup', help='Set up the system environment')
    #setup_parser.set_defaults(func=cmd_setup)
    
    # version command
    version_parser = subparsers.add_parser('version', help='Display version information')
    version_parser.set_defaults(func=cmd_version)
    
    # Parse the arguments
    args = parser.parse_args()
    
    # If no command is specified, show help
    if not hasattr(args, 'func'):
        parser.print_help()
        return 1
    
    # Execute the command
    logger.info(f"Esecuzione del comando: {args.command}")
    try:
        result = args.func(args)
        logger.info(f"Comando {args.command} completato con codice di uscita: {result}")
        return result
    except Exception as e:
        logger.error(f"Errore durante l'esecuzione del comando {args.command}: {e}")
        logger.exception("Traceback completo:")
        return 1

if __name__ == "__main__":
    faulthandler.enable()
    sys.exit(main())