#!/usr/bin/env python3
import mysql.connector
from mysql.connector import pooling
from datetime import datetime, date as _date
import logging
import time

class DatabaseManager:
    def __init__(self, db_config, country_code='es'):
        self.config = db_config
        self.logger = logging.getLogger(__name__)
        self.conn = None
        self.cursor = None
        self.country_code = country_code.lower()
        self.table_publications = f"publications_{self.country_code}"
        self.table_logs = f"execution_logs_{self.country_code}"
        
        # Configuración de pool para reconexión automática
        self.db_config_safe = self.config.copy()
        self.db_config_safe['autocommit'] = True

    def connect(self):
        """Establishes connection to the database with retry logic"""
        try:
            # Intentar reconectar si existe conexión pero no responde
            if self.conn and self.conn.is_connected():
                return True

            self.conn = mysql.connector.connect(**self.db_config_safe)
            self.cursor = self.conn.cursor(dictionary=True)
            return True
            
        except mysql.connector.Error as err:
            if err.errno == 1049:  # Unknown database
                self.logger.warning(f"Base de datos no encontrada, intentando crearla...")
                return self.create_database()
            self.logger.error(f"Error de conexión a BD: {err}")
            return False

    def create_database(self):
        try:
            # Conexión temporal sin especificar DB para poder crearla
            temp_config = self.db_config_safe.copy()
            if 'database' in temp_config:
                del temp_config['database']
                
            temp_conn = mysql.connector.connect(**temp_config)
            cursor = temp_conn.cursor()
            db_name = self.config.get('database', 'boe_monitor')
            
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
            self.logger.info(f"Base de datos '{db_name}' creada/verificada.")
            
            cursor.close()
            temp_conn.close()
            return self.connect()
        except mysql.connector.Error as err:
            self.logger.critical(f"Error fatal al crear BD: {err}")
            return False

    def init_tables(self):
        if not self.connect():
            return False

        try:
            # Tabla de publicaciones optimizada
            self.cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.table_publications} (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    boe_date DATE NOT NULL,
                    title MEDIUMTEXT NOT NULL,
                    section VARCHAR(255),
                    department VARCHAR(255),
                    rank_type VARCHAR(255),
                    url_pdf VARCHAR(512),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_date (boe_date),
                    INDEX idx_title (title(50))
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
            """)

            # Tabla de logs
            self.cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.table_logs} (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    execution_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status VARCHAR(50),
                    items_found INT DEFAULT 0,
                    new_items INT DEFAULT 0,
                    removed_items INT DEFAULT 0,
                    message TEXT
                )
            """)
            
            self.logger.info(f"Tablas inicializadas para '{self.country_code}'.")
            return True
        except mysql.connector.Error as err:
            self.logger.error(f"Error al inicializar tablas: {err}")
            return False

    def save_publication(self, item, date_obj):
        """Saves a single publication if it doesn't exist"""
        if not self.connect():
            return False
            
        try:
            if isinstance(date_obj, _date):
                date_param = date_obj
            elif isinstance(date_obj, datetime):
                date_param = date_obj.date()
            else:
                date_param = date_obj

            title = item.get('titulo', '')
            # Truncar título si es excesivamente largo para evitar errores
            if len(title) > 16000: title = title[:16000]

            check_sql = f"SELECT id FROM {self.table_publications} WHERE boe_date = %s AND title = %s LIMIT 1"
            self.cursor.execute(check_sql, (date_param, title))
            
            if self.cursor.fetchone():
                return False

            sql = f"""
                INSERT INTO {self.table_publications} 
                (boe_date, title, section, department, rank_type, url_pdf) 
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            values = (
                date_param,
                title,
                item.get('seccion', '')[:255],
                item.get('departamento', '')[:255],
                item.get('rango', '')[:255],
                item.get('url', '')[:512]
            )
            self.cursor.execute(sql, values)
            return True
            
        except mysql.connector.Error as err:
            self.logger.error(f"Error guardando publicación: {err}")
            return False

    def get_publications_by_date(self, date_obj):
        if not self.connect():
            return []
            
        try:
            sql = f"""
                SELECT title as titulo, section as seccion, 
                       department as departamento, rank_type as rango, 
                       url_pdf as url
                FROM {self.table_publications} 
                WHERE boe_date = %s
            """
            self.cursor.execute(sql, (date_obj,))
            return self.cursor.fetchall()
        except mysql.connector.Error as err:
            self.logger.error(f"Error recuperando publicaciones: {err}")
            return []

    def log_execution(self, status, items_found, new_items, removed_items, message=""):
        if not self.connect():
            return
            
        try:
            sql = f"""
                INSERT INTO {self.table_logs} 
                (status, items_found, new_items, removed_items, message) 
                VALUES (%s, %s, %s, %s, %s)
            """
            self.cursor.execute(sql, (status, items_found, new_items, removed_items, message))
        except mysql.connector.Error as err:
            self.logger.error(f"Error escribiendo log en BD: {err}")

    def close(self):
        if self.conn and self.conn.is_connected():
            self.conn.close()