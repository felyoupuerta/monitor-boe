#!/usr/bin/env python3
"""
Gestor de base de datos para BOE Monitor.
Maneja la persistencia de publicaciones y detección de cambios.
"""

import mysql.connector
import hashlib
from typing import Dict, Optional, Tuple
from logger_config import setup_logger

logger = setup_logger(__name__)


class DatabaseManager:
    """
    Gestor de base de datos para publicaciones del BOE.
    Valida duplicados y cambios basándose en hash de contenido.
    """
    
    def __init__(self, db_config: Dict, country_code: str = 'es'):
        """
        Inicializa el gestor de base de datos.
        
        Args:
            db_config: Diccionario con configuración de conexión
            country_code: Código del país (por defecto 'es')
        """
        self.config = db_config
        self.country_code = country_code.lower()
        self.table = f"publications_{self.country_code}"
        self.conn = None
        self.logger = logger
    
    def connect(self) -> None:
        """Establece conexión con la base de datos."""
        try:
            self.conn = mysql.connector.connect(**self.config, autocommit=True)
            self.logger.debug(f"Conexión exitosa a BD para país: {self.country_code}")
        except mysql.connector.Error as e:
            self.logger.error(f"Error de conexión a BD: {e}")
            raise
    
    def init_tables(self) -> None:
        """Crea tabla si no existe. Migra columnas si falta content_hash."""
        self.connect()
        try:
            cursor = self.conn.cursor()
            create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS {self.table} (
                id INT AUTO_INCREMENT PRIMARY KEY,
                boe_date DATE NOT NULL,
                title TEXT NOT NULL,
                section VARCHAR(255),
                department VARCHAR(255),
                url_pdf VARCHAR(512),
                content_hash VARCHAR(64),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY unique_publication (boe_date, content_hash),
                INDEX idx_date (boe_date),
                INDEX idx_hash (content_hash)
            )
            """
            cursor.execute(create_table_sql)
            
            cursor.execute(f"SHOW COLUMNS FROM {self.table} LIKE 'content_hash'")
            if not cursor.fetchone():
                self.logger.info(f"Migrando tabla {self.table}: agregando content_hash")
                cursor.execute(f"ALTER TABLE {self.table} ADD COLUMN content_hash VARCHAR(64) AFTER url_pdf")
                try:
                    cursor.execute(f"ALTER TABLE {self.table} ADD UNIQUE KEY unique_publication (boe_date, content_hash)")
                except:
                    pass
                try:
                    cursor.execute(f"ALTER TABLE {self.table} ADD INDEX idx_hash (content_hash)")
                except:
                    pass
                self.logger.info(f"Migración completada para {self.table}")
            
            self.logger.info(f"Tabla '{self.table}' lista")
        except mysql.connector.Error as e:
            self.logger.error(f"Error al crear tabla: {e}")
            raise
        finally:
            if cursor:
                cursor.close()
    
    def _generate_content_hash(self, item: Dict) -> str:
        """
        Genera hash SHA256 del contenido de la publicación.
        El hash incluye título, sección y departamento para detectar cambios.
        
        Args:
            item: Diccionario con datos de la publicación
        
        Returns:
            Hash SHA256 en hexadecimal
        """
        content = f"{item.get('titulo', '')}{item.get('seccion', '')}{item.get('departamento', '')}"
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def publication_exists(self, item: Dict, date_obj) -> bool:
        """
        Verifica si una publicación ya existe en la BD.
        
        Args:
            item: Diccionario con datos de la publicación
            date_obj: Fecha de la publicación
        
        Returns:
            True si existe, False en caso contrario
        """
        content_hash = self._generate_content_hash(item)
        cursor = self.conn.cursor()
        try:
            query = f"SELECT id FROM {self.table} WHERE boe_date=%s AND content_hash=%s"
            cursor.execute(query, (date_obj, content_hash))
            return cursor.fetchone() is not None
        except mysql.connector.Error as e:
            self.logger.error(f"Error al verificar publicación: {e}")
            return False
        finally:
            if cursor:
                cursor.close()
    
    def save_publication(self, item: Dict, date_obj) -> bool:
        """
        Guarda una nueva publicación en la BD si no existe.
        
        Args:
            item: Diccionario con datos de la publicación
            date_obj: Fecha de la publicación
        
        Returns:
            True si se guardó, False si ya existía
        """
        if self.publication_exists(item, date_obj):
            return False
        
        content_hash = self._generate_content_hash(item)
        cursor = self.conn.cursor()
        
        try:
            insert_sql = f"""
            INSERT INTO {self.table} 
            (boe_date, title, section, department, url_pdf, content_hash) 
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            cursor.execute(insert_sql, (
                date_obj,
                item.get('titulo', ''),
                item.get('seccion', ''),
                item.get('departamento', ''),
                item.get('url', ''),
                content_hash
            ))
            
            self.logger.debug(f"Publicación guardada: {item.get('titulo', '')[:50]}...")
            return True
            
        except mysql.connector.Error as e:
            if "Duplicate entry" in str(e):
                self.logger.debug("Publicación duplicada (esperada)")
                return False
            else:
                self.logger.error(f"Error al guardar publicación: {e}")
                return False
        finally:
            if cursor:
                cursor.close()
    
    def get_publications_by_date(self, date_obj, country_filter: Optional[str] = None) -> list:
        """
        Obtiene todas las publicaciones de una fecha específica.
        
        Args:
            date_obj: Fecha a consultar
            country_filter: Opcional, para validación
        
        Returns:
            Lista de publicaciones
        """
        cursor = self.conn.cursor(dictionary=True)
        try:
            query = f"SELECT * FROM {self.table} WHERE boe_date=%s ORDER BY id DESC"
            cursor.execute(query, (date_obj,))
            return cursor.fetchall()
        except mysql.connector.Error as e:
            self.logger.error(f"Error al obtener publicaciones: {e}")
            return []
        finally:
            if cursor:
                cursor.close()
    
    def close(self) -> None:
        """Cierra la conexión con la base de datos."""
        if self.conn:
            self.conn.close()
            self.logger.debug("Conexión a BD cerrada")
