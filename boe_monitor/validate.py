#!/usr/bin/env python3
"""
Script de validación pre-producción.
Verifica que todo esté correctamente configurado.
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from logger_config import setup_logger

logger = setup_logger("validation")


def check_file_exists(filepath: str, description: str) -> bool:
    """Verifica que un archivo existe."""
    path = Path(filepath)
    if path.exists():
        logger.info(f"✓ {description}")
        return True
    else:
        logger.error(f"✗ {description} - No encontrado: {filepath}")
        return False


def check_directory_exists(dirpath: str, description: str) -> bool:
    """Verifica que un directorio existe."""
    path = Path(dirpath)
    if path.exists() and path.is_dir():
        logger.info(f"✓ {description}")
        return True
    else:
        logger.error(f"✗ {description} - No encontrado: {dirpath}")
        return False


def check_config() -> bool:
    """Valida el archivo de configuración."""
    config_path = Path('config.json')
    
    if not config_path.exists():
        logger.error("✗ Configuración - config.json no encontrado")
        return False
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        required_keys = ['recipient_email', 'smtp_config', 'sources', 'db_config']
        for key in required_keys:
            if key not in config:
                logger.error(f"✗ Configuración - Falta: {key}")
                return False
        
        logger.info(f"✓ Configuración válida ({len(config['sources'])} países)")
        return True
        
    except json.JSONDecodeError as e:
        logger.error(f"✗ Configuración - JSON inválido: {e}")
        return False


def check_dependencies() -> bool:
    """Verifica que las dependencias están instaladas."""
    dependencies = [
        ('requests', 'requests'),
        ('bs4', 'beautifulsoup4'),
        ('lxml', 'lxml'),
        ('mysql.connector', 'mysql-connector-python'),
    ]
    
    all_ok = True
    for module_name, package_name in dependencies:
        try:
            __import__(module_name)
            logger.info(f"✓ Dependencia: {package_name}")
        except ImportError:
            logger.error(f"✗ Dependencia faltante: {package_name}")
            all_ok = False
    
    return all_ok


def check_directory_structure() -> bool:
    """Valida la estructura de directorios."""
    checks = [
        ('boe_data', 'Directorio de datos'),
        ('logs', 'Directorio de logs'),
        ('tests', 'Directorio de tests'),
    ]
    
    all_ok = True
    for dirname, description in checks:
        if not check_directory_exists(dirname, description):
            all_ok = False
    
    return all_ok


def check_files() -> bool:
    """Verifica archivos críticos."""
    checks = [
        ('main.py', 'Script principal'),
        ('boe_analyzer.py', 'Analizador'),
        ('db_manager.py', 'Gestor de BD'),
        ('logger_config.py', 'Configuración de logging'),
        ('config.json', 'Configuración'),
        ('requirements.txt', 'Dependencias'),
        ('README.md', 'README'),
        ('DOCUMENTATION.md', 'Documentación'),
        ('config.example.json', 'Configuración de ejemplo'),
        ('tests/test_email.py', 'Test de email'),
    ]
    
    all_ok = True
    for filepath, description in checks:
        if not check_file_exists(filepath, description):
            all_ok = False
    
    return all_ok


def main():
    """Función principal."""
    print("=" * 70)
    print("VALIDACIÓN PRE-PRODUCCIÓN".center(70))
    print("=" * 70)
    print()
    
    checks = [
        ("Archivos críticos", check_files),
        ("Estructura de directorios", check_directory_structure),
        ("Dependencias Python", check_dependencies),
        ("Configuración", check_config),
    ]
    
    results = []
    for description, check_func in checks:
        print(f"\n{description}:")
        print("-" * 70)
        result = check_func()
        results.append(result)
    
    print()
    print("=" * 70)
    
    if all(results):
        logger.info("✓ VALIDACIÓN COMPLETADA EXITOSAMENTE")
        print("\n✓ Proyecto listo para producción".center(70))
        print("\nProximos pasos:")
        print("  1. Ejecutar: python tests/test_email.py")
        print("  2. Verificar: python main.py --list")
        print("  3. Programar: Agregar a cron (Linux) o Task Scheduler (Windows)")
        return 0
    else:
        logger.error("✗ VALIDACIÓN FALLÓ")
        print("\n✗ Hay problemas que deben corregirse".center(70))
        print("\nRevisa los errores arriba.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
