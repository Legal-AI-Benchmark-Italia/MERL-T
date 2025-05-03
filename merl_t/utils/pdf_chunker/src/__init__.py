#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Chunker - Moduli interni per l'elaborazione dei PDF.

Questo pacchetto contiene i moduli principali per:
- Elaborazione dei PDF
- Gestione parallela
- Monitoraggio delle risorse
- Tracciamento del progresso
- Gestione dell'output
"""

from .config import Config
from .processor import PDFProcessor
from .parallel import ParallelExecutor
from .cpu_monitor import CPUMonitor
from .progress_tracker import ProgressTracker
from .output_manager import OutputManager
from .utils import setup_logging, find_pdf_files

__all__ = [
    'Config',
    'PDFProcessor',
    'ParallelExecutor',
    'CPUMonitor',
    'ProgressTracker',
    'OutputManager',
    'setup_logging',
    'find_pdf_files'
]
