import mysql.connector
from datetime import datetime
import json
from pathlib import Path

class DatabaseManager:
    def __init__(self, db_config):
        self.config = db_config
        self.conn = None
        self.cursor = None

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
            # If database doesn't exist, try to connect without db to create it
            if err.errno == 1049:  # Unknown database
                return self.create_database()
            print(f"❌ Error de conexión a BD: {err}")
            return False

    def create_database(self):
        """Creates the database if it doesn't exist"""
        try:
            # Connect without database
            temp_conn = mysql.connector.connect(
                host=self.config.get('host', 'localhost'),
                user=self.config.get('user', 'root'),
                password=self.config.get('password', ''),
                port=self.config.get('port', 3306)
            )
            cursor = temp_conn.cursor()
            db_name = self.config.get('database', 'boe_monitor')
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
            print(f"✅ Base de datos '{db_name}' creada.")
            temp_conn.close()
            # Retry connection
            return self.connect()
        except mysql.connector.Error as err:
            print(f"❌ Error al crear BD: {err}")
            return False

    def init_tables(self):
        """Initialize database tables"""
        if not self.conn:
            if not self.connect():
                return False

        try:
            # Table: publications
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS publications (
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

            # Table: execution_logs
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS execution_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    execution_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status VARCHAR(50),
                    items_found INT DEFAULT 0,
                    new_items INT DEFAULT 0,
                    removed_items INT DEFAULT 0,
                    message TEXT
                )
            """)
            
            print("✅ Tablas inicializadas correctamente.")
            return True
        except mysql.connector.Error as err:
            print(f"❌ Error al crear tablas: {err}")
            return False

    def save_publication(self, item, date_obj):
        """Saves a single publication if it doesn't exist"""
        if not self.conn:
            self.connect()
            
        try:
            if not self.cursor:
                 if not self.connect():
                     return False
            
            # Check for duplicates (same title and date)
            # Using MD5 of title for efficient querying if titles are long, 
            # but for now simple checking is fine for this scale
            
            check_sql = "SELECT id FROM publications WHERE boe_date = %s AND title = %s LIMIT 1"
            self.cursor.execute(check_sql, (date_obj, item['titulo']))
            if self.cursor.fetchone():
                return False  # Already exists

            sql = """
                INSERT INTO publications 
                (boe_date, title, section, department, rank_type, url_pdf) 
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            values = (
                date_obj,
                item['titulo'],
                item['seccion'],
                item['departamento'],
                item['rango'],
                item['url']
            )
            self.cursor.execute(sql, values)
            return True
        except mysql.connector.Error as err:
            print(f"Error saving publication: {err}")
            return False

    def get_publications_by_date(self, date_obj):
        """Get all publications for a specific date"""
        if not self.conn:
            self.connect()
            
        try:
            if not self.cursor:
                 if not self.connect():
                     return []
            
            sql = """
                SELECT title as titulo, section as seccion, 
                       department as departamento, rank_type as rango, 
                       url_pdf as url
                FROM publications 
                WHERE boe_date = %s
            """
            self.cursor.execute(sql, (date_obj,))
            return self.cursor.fetchall()
        except mysql.connector.Error as err:
            print(f"Error fetching publications: {err}")
            return []

    def log_execution(self, status, items_found, new_items, removed_items, message=""):
        """Log execution stats"""
        if not self.conn:
            self.connect()
            
        try:
            if not self.cursor:
                 # Don't try too hard for logs
                 if not self.connect():
                     return

            sql = """
                INSERT INTO execution_logs 
                (status, items_found, new_items, removed_items, message) 
                VALUES (%s, %s, %s, %s, %s)
            """
            self.cursor.execute(sql, (status, items_found, new_items, removed_items, message))
        except mysql.connector.Error as err:
            print(f"Error logging execution: {err}")

    def close(self):
        if self.conn:
            self.conn.close()
