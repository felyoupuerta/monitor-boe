#!/usr/bin/env python3
import mysql.connector
from datetime import datetime, date as _date
import json
from pathlib import Path

class DatabaseManager:
    def __init__(self, db_config, country_code='es'):
        self.config = db_config
        self.conn = None
        self.cursor = None
        self.country_code = country_code.lower()
        self.table_publications = f"publications_{self.country_code}"
        self.table_logs = f"execution_logs_{self.country_code}"

    def connect(self):
        """Establishes connection to the database"""
        try:
            self.conn = mysql.connector.connect(
                host=self.config.get('host', 'localhost'),
                user=self.config.get('user', 'root'),
                password=self.config.get('password', ''),
                database=self.config.get('database', 'boe_monitor'),
                port=self.config.get('port', 3306),
                autocommit=True
            )
            self.cursor = self.conn.cursor(dictionary=True)
            return True
        except mysql.connector.Error as err:
            if err.errno == 1049:  # Unknown database
                return self.create_database()
            print(f"Error de conexión a BD: {err}")
            return False

    def create_database(self):
        
        try:
            temp_conn = mysql.connector.connect(
                host=self.config.get('host', 'localhost'),
                user=self.config.get('user', 'root'),
                password=self.config.get('password', ''),
                port=self.config.get('port', 3306)
            )
            cursor = temp_conn.cursor()
            db_name = self.config.get('database', 'boe_monitor')
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
            print(f"Base de datos '{db_name}' creada.")
            temp_conn.close()
            return self.connect()
        except mysql.connector.Error as err:
            print(f"Error al crear BD: {err}")
            return False

    def init_tables(self):
        
        if not self.conn:
            if not self.connect():
                return False

        try:
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
                )
            """)

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
            
            print(f"Tablas inicializadas para '{self.country_code}'.")
            return True
        except mysql.connector.Error as err:
            print(f"Error al crear tablas: {err}")
            return False

    def save_publication(self, item, date_obj):
        """Saves a single publication if it doesn't exist"""
        if not self.conn:
            self.connect()
            
        try:
            if not self.cursor:
                 if not self.connect():
                     return False
           
            if isinstance(date_obj, _date):
                date_param = date_obj
            elif isinstance(date_obj, datetime):
                date_param = date_obj.date()
            else:
                date_param = date_obj

            title = item.get('titulo', '')

            check_sql = f"SELECT id FROM {self.table_publications} WHERE boe_date = %s AND title = %s LIMIT 1"
            self.cursor.execute(check_sql, (date_param, title))
            found = self.cursor.fetchone()
            if found:
                return False

            sql = f"""
                INSERT INTO {self.table_publications} 
                (boe_date, title, section, department, rank_type, url_pdf) 
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            values = (
                date_param,
                title,
                item.get('seccion', ''),
                item.get('departamento', ''),
                item.get('rango', ''),
                item.get('url', '')
            )
            try:
                self.cursor.execute(sql, values)
                return True
            except Exception as e:
                print(f"Error inserting publication: {e}")
                return False
        except mysql.connector.Error as err:
            print(f"Error saving publication: {err}")
            return False

    def get_publications_by_date(self, date_obj):
        """Obtener publicaciones de una fecha específica"""
        if not self.conn:
            self.connect()
            
        try:
            if not self.cursor:
                 if not self.connect():
                     return []
            
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
            print(f"Error fetching publications: {err}")
            return []

    def log_execution(self, status, items_found, new_items, removed_items, message=""):
        """LOG de estadisticas de ejecución"""
        if not self.conn:
            self.connect()
            
        try:
            if not self.cursor:
                 if not self.connect():
                     return

            sql = f"""
                INSERT INTO {self.table_logs} 
                (status, items_found, new_items, removed_items, message) 
                VALUES (%s, %s, %s, %s, %s)
            """
            self.cursor.execute(sql, (status, items_found, new_items, removed_items, message))
        except mysql.connector.Error as err:
            print(f"Error logging execution: {err}")

    def close(self):
        if self.conn:
            self.conn.close()

