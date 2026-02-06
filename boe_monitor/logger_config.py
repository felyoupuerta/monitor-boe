#!/usr/bin/env python3
"""
Configuración centralizada del logger para BOE Monitor.
Proporciona logging consistente a toda la aplicación.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime


def setup_logger(name: str = "boe_monitor", log_dir: str = "./logs") -> logging.Logger:
    """
    Configura y retorna un logger con salida a consola y archivo.
    
    Argumentos:
        name: Nombre del logger (por defecto "boe_monitor")
        log_dir: Directorio donde guardar los logs (por defecto "./logs")
    
    Returns:
        Logger configurado
    """
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    logger = logging.getLogger(name)
    
    if logger.hasHandlers():
        return logger
    
    logger.setLevel(logging.DEBUG)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_path / f"boe_monitor_{timestamp}.log"
    
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger
