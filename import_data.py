import os
import json
import pandas as pd
import numpy as np
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
import subprocess

import mysql.connector
from mysql.connector import pooling, Error
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging framework
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('phonepe_extraction.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DataType:
    TRANSACTION = 'transaction'
    USER = 'user'
    INSURANCE = 'insurance'
    ALL = [TRANSACTION, USER, INSURANCE]


class TableType:
    """Constants for table types"""
    MAP = 'map'
    TOP = 'top'
    AGGREGATED = 'aggregated'


class PhonePeDataExtractor:
    
    def __init__(self):
        """Initialize data extractor with enhanced configuration"""
        self.data_dir = Path("pulse-master/data")
        self.connection_pool = None
        self.failed_records = []
        self.batch_size = 1000  # Commit every 1000 records for optimal performance
        
        # Initialize connection pool
        self._setup_connection_pool()
    
    def create_tables(self):
        """
        Create all required database tables with exact schema.
        Tables will be created if they don't exist.
        """
        connection = self.get_connection()
        cursor = connection.cursor()
        
        tables = {
            "aggregated_transaction_record": """
                CREATE TABLE IF NOT EXISTS aggregated_transaction_record (
                    STATE VARCHAR(50),
                    YEAR SMALLINT,
                    QUARTER INT,
                    TRANSACTION_TYPE CHAR(50),
                    TRANSACTION_COUNT BIGINT,
                    TRANSACTION_AMOUNT FLOAT
                )
            """,
            
            "aggregated_insurance_record": """
                CREATE TABLE IF NOT EXISTS aggregated_insurance_record (
                    STATE VARCHAR(50),
                    YEAR SMALLINT,
                    QUARTER INT,
                    INSURANCE_COUNT BIGINT,
                    INSURANCE_AMOUNT FLOAT
                )
            """,
            
            "aggregated_user_record": """
                CREATE TABLE IF NOT EXISTS aggregated_user_record (
                    STATE VARCHAR(50),
                    YEAR SMALLINT,
                    QUARTER INT,
                    APPS_OPEN BIGINT,
                    REGISTERED_USERS BIGINT,
                    DEVICE_BRAND CHAR(50),
                    DEVICE_COUNT BIGINT,
                    DEVICE_PERCENTAGE DECIMAL(3,2)
                )
            """,
            
            "map_insurance_record": """
                CREATE TABLE IF NOT EXISTS map_insurance_record (
                    STATE VARCHAR(50),
                    DISTRICT VARCHAR(50),
                    YEAR SMALLINT,
                    QUARTER INT,
                    INSURANCE_COUNT BIGINT,
                    INSURANCE_AMOUNT FLOAT
                )
            """,
            
            "map_transaction_record": """
                CREATE TABLE IF NOT EXISTS map_transaction_record (
                    STATE VARCHAR(50),
                    DISTRICT VARCHAR(50),
                    YEAR SMALLINT,
                    QUARTER INT,
                    TRANSACTION_COUNT BIGINT,
                    TRANSACTION_AMOUNT FLOAT
                )
            """,
            
            "map_user_record": """
                CREATE TABLE IF NOT EXISTS map_user_record (
                    STATE VARCHAR(50),
                    DISTRICT VARCHAR(50),
                    YEAR SMALLINT,
                    QUARTER INT,
                    REGISTERED_USERS BIGINT,
                    APPS_OPEN BIGINT
                )
            """,
            
            "top_insurance_record": """
                CREATE TABLE IF NOT EXISTS top_insurance_record (
                    STATE VARCHAR(50),
                    YEAR SMALLINT,
                    QUARTER INT,
                    ENTITY_TYPE CHAR(50),
                    ENTITY_NAME CHAR(50),
                    INSURANCE_COUNT BIGINT,
                    INSURANCE_AMOUNT FLOAT
                )
            """,
            
            "top_transaction_record": """
                CREATE TABLE IF NOT EXISTS top_transaction_record (
                    STATE VARCHAR(50),
                    YEAR SMALLINT,
                    QUARTER INT,
                    ENTITY_TYPE CHAR(50),
                    ENTITY_NAME CHAR(50),
                    TRANSACTION_COUNT BIGINT,
                    TRANSACTION_AMOUNT FLOAT
                )
            """,
            
            "top_user_record": """
                CREATE TABLE IF NOT EXISTS top_user_record (
                    STATE VARCHAR(50),
                    YEAR SMALLINT,
                    QUARTER INT,
                    ENTITY_TYPE CHAR(50),
                    ENTITY_NAME CHAR(50),
                    REGISTERED_USERS BIGINT
                )
            """
        }
        
        try:
            logger.info("🔨 Creating database tables...")
            for table_name, create_sql in tables.items():
                try:
                    cursor.execute(create_sql)
                    logger.info(f"  ✅ Table created/verified: {table_name}")
                except Error as e:
                    logger.error(f"  ❌ Failed to create table {table_name}: {e}")
                    raise
            
            connection.commit()
            logger.info("✅ All tables created successfully!")
            
        except Exception as e:
            logger.error(f"❌ Table creation failed: {e}")
            connection.rollback()
            raise
        finally:
            cursor.close()
            connection.close()
            
    def _setup_connection_pool(self):
        try:
            self.connection_pool = pooling.MySQLConnectionPool(
                pool_name="phonepe_pool",
                pool_size=5,
                pool_reset_session=True,
                host=os.getenv('MYSQL_HOST', '127.0.0.1'),
                port=int(os.getenv('MYSQL_PORT', 3306)),
                user=os.getenv('MYSQL_USER', 'root'),
                password=os.getenv('MYSQL_PASSWORD','Surya@123'),
                database=os.getenv('MYSQL_DB', 'phonepe_pulse_database')
            )
            logger.info("✅ Database connection pool created successfully")
        except Error as e:
            logger.error(f"❌ Failed to create connection pool: {e}")
            raise
    
    def get_connection(self):
        """Get a connection from the pool"""
        try:
            return self.connection_pool.get_connection()
        except Error as e:
            logger.error(f"Failed to get connection from pool: {e}")
            raise
    
    def setup_repository(self) -> bool:
        """
        Clone or update PhonePe Pulse repository.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if Path("pulse-master").exists():
                result = subprocess.run(
                    ["git", "pull"],
                    cwd="pulse-master",
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    logger.info("✅ Repository updated successfully")
                else:
                    logger.warning(f"⚠️ Git pull warning: {result.stderr}")
            else:
                logger.info("📥 Cloning PhonePe Pulse repository...")
                result = subprocess.run([
                    "git", "clone",
                    "https://github.com/PhonePe/pulse.git",
                    "pulse-master"
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    logger.info("✅ Repository cloned successfully")
                else:
                    logger.error(f"❌ Git clone failed: {result.stderr}")
                    return False
            
            self.analyze_repository_structure()
            return True
            
        except Exception as e:
            logger.error(f"❌ Repository setup failed: {e}")
            return False
    
    def analyze_repository_structure(self):
        """Analyze and log repository structure"""
        try:
            logger.info("\n📁 Repository Structure:")
            data_types = [TableType.AGGREGATED, TableType.MAP, TableType.TOP]
            categories = DataType.ALL
            
            for data_type in data_types:
                for category in categories:
                    path = self.data_dir / data_type / category
                    if path.exists():
                        file_count = sum(1 for _ in path.rglob('*.json'))
                        logger.info(f"  {data_type}/{category}: {file_count} files")
        except Exception as e:
            logger.warning(f"Could not analyze structure: {e}")
    
    def clean_state_name(self, state_name: str) -> Optional[str]:
        """
        Clean and standardize state names.
        
        Args:
            state_name: Raw state name from file/folder
            
        Returns:
            Cleaned state name or None if invalid
        """
        if not state_name or not isinstance(state_name, str):
            return None
        
        # Remove unwanted characters and standardize
        cleaned = state_name.strip().lower()
        cleaned = cleaned.replace('-', ' ').replace('_', ' ')
        cleaned = ' '.join(word.capitalize() for word in cleaned.split())
        
        # Handle specific state mappings
        state_mappings = {
            'Andaman And Nicobar Islands': 'Andaman & Nicobar Islands',
            'Dadra And Nagar Haveli And Daman And Diu': 'Dadra & Nagar Haveli and Daman & Diu',
            'Jammu And Kashmir': 'Jammu & Kashmir',
            'Nct Of Delhi': 'Delhi',
            'Delhi': 'Delhi',
            'Andaman And Nicobar': 'Andaman & Nicobar Islands'
        }
        
        return state_mappings.get(cleaned, cleaned)
    
    def clean_district_name(self, district_name: str) -> Optional[str]:
        if not district_name or not isinstance(district_name, str):
            return None
        
        cleaned = district_name.strip()
        cleaned = cleaned.replace('-', ' ').replace('_', ' ')
        cleaned = ' '.join(word.capitalize() for word in cleaned.split())
        
        return cleaned if len(cleaned) > 1 else None
    
    def convert_scientific_notation(self, value: Any) -> float:
        
        if pd.isna(value) or value is None:
            return 0.0
        
        if isinstance(value, (int, float)):
            return float(value)
        
        if isinstance(value, str):
            value = value.strip()
            if not value or value.lower() in ['null', 'none', 'nan']:
                return 0.0
        
        try:
            return float(value)
        except (ValueError, TypeError) as e:
            logger.warning(f"Could not convert '{value}' to float: {e}")
            return 0.0
    
    def extract_map_data(self, data_type: str):
       
        path = self.data_dir / TableType.MAP / data_type / "hover" / "country" / "india" / "state"
        
        if not path.exists():
            logger.warning(f"Path does not exist: {path}")
            return
        
        connection = self.get_connection()
        cursor = connection.cursor()
        
        # Batch storage for records
        batch_records = []
        record_count = 0
        
        try:
            for state_path in path.iterdir():
                if not state_path.is_dir():
                    continue
                
                state_name = self.clean_state_name(state_path.name)
                if not state_name:
                    continue
                
                for year_path in state_path.iterdir():
                    if not year_path.name.isdigit():
                        continue
                    
                    year = int(year_path.name)
                    
                    for json_file in year_path.glob('*.json'):
                        quarter = int(json_file.stem)
                        
                        try:
                            with open(json_file, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                            
                            if 'data' not in data:
                                continue
                            
                            # Handle different map data structures
                            hover_data = data['data'].get('hoverDataList', [])
                            if not hover_data and 'hoverData' in data['data']:
                                hover_data = data['data']['hoverData']
                            if not hover_data and isinstance(data['data'], list):
                                hover_data = data['data']
                            
                            # Process hover data
                            for district_data in hover_data:
                                # Handle dict-based hover data (map user data structure)
                                if 'name' not in district_data and isinstance(hover_data, dict):
                                    district_name = self.clean_district_name(district_data)
                                    if not district_name or data_type != DataType.USER:
                                        continue
                                    
                                    user_data = hover_data[district_data]
                                    record = (
                                        state_name, district_name, year, quarter,
                                        int(user_data.get('registeredUsers', 0)),
                                        int(user_data.get('appOpens', 0))
                                    )
                                    batch_records.append(record)
                                    continue
                                
                                if not isinstance(district_data, dict):
                                    continue
                                
                                district_name = district_data.get('name', '').strip()
                                district_name = self.clean_district_name(district_name)
                                
                                if not district_name:
                                    continue
                                
                                # Extract metrics
                                if 'metric' in district_data:
                                    metrics = district_data['metric']
                                    if not isinstance(metrics, list):
                                        metrics = [metrics]
                                    
                                    for metric in metrics:
                                        if metric is None:
                                            continue
                                        
                                        # Prepare record based on data type
                                        if data_type == DataType.TRANSACTION:
                                            record = (
                                                state_name, district_name, year, quarter,
                                                int(metric.get('count', 0)),
                                                self.convert_scientific_notation(metric.get('amount', 0))
                                            )
                                            batch_records.append(record)
                                        
                                        elif data_type == DataType.USER:
                                            record = (
                                                state_name, district_name, year, quarter,
                                                int(metric.get('registeredUsers', 0)),
                                                int(metric.get('appOpens', 0))
                                            )
                                            batch_records.append(record)
                                        
                                        elif data_type == DataType.INSURANCE:
                                            record = (
                                                state_name, district_name, year, quarter,
                                                int(metric.get('count', 0)),
                                                self.convert_scientific_notation(metric.get('amount', 0))
                                            )
                                            batch_records.append(record)
                                        
                                        # Batch insert when batch size reached
                                        if len(batch_records) >= self.batch_size:
                                            self._batch_insert_map_data(cursor, data_type, batch_records)
                                            connection.commit()
                                            record_count += len(batch_records)
                                            logger.info(f"Inserted {record_count} {data_type} records")
                                            batch_records = []
                        
                        except Exception as e:
                            logger.error(f"Error processing file {json_file}: {e}")
            
            # Insert remaining records
            if batch_records:
                self._batch_insert_map_data(cursor, data_type, batch_records)
                connection.commit()
                record_count += len(batch_records)
            
            logger.info(f"✅ Completed map {data_type} extraction: {record_count} total records")
        
        except Exception as e:
            logger.error(f"Error in extract_map_data for {data_type}: {e}")
            connection.rollback()
        
        finally:
            cursor.close()
            connection.close()
    
    def _batch_insert_map_data(self, cursor, data_type: str, records: List[Tuple]):
        """
        Batch insert map data records using executemany().
        
        Args:
            cursor: Database cursor
            data_type: Type of data being inserted
            records: List of record tuples
        """
        if not records:
            return
        
        try:
            if data_type == DataType.TRANSACTION:
                cursor.executemany(
                    """INSERT INTO MAP_TRANSACTION_RECORD 
                       (STATE, DISTRICT, YEAR, QUARTER, TRANSACTION_COUNT, TRANSACTION_AMOUNT) 
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    records
                )
            elif data_type == DataType.USER:
                cursor.executemany(
                    """INSERT INTO MAP_USER_RECORD 
                       (STATE, DISTRICT, YEAR, QUARTER, REGISTERED_USERS, APPS_OPEN) 
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    records
                )
            elif data_type == DataType.INSURANCE:
                cursor.executemany(
                    """INSERT INTO MAP_INSURANCE_RECORD 
                       (STATE, DISTRICT, YEAR, QUARTER, INSURANCE_COUNT, INSURANCE_AMOUNT) 
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    records
                )
        except Error as e:
            raise
    
    def extract_top_data(self, data_type: str):
        """
        Extract top data for a given data type using batch inserts.
        
        Args:
            data_type: Type of data ('transaction', 'user', or 'insurance')
        """
        path = self.data_dir / TableType.TOP / data_type / "country" / "india" / "state"
        
        if not path.exists():
            logger.warning(f"Path does not exist: {path}")
            return
        
        connection = self.get_connection()
        cursor = connection.cursor()
        
        # Batch storage
        batch_records = []
        record_count = 0
        
        try:
            for state_path in path.iterdir():
                state_name = self.clean_state_name(state_path.name)
                if not state_name:
                    continue
                
                for year_path in state_path.iterdir():
                    if not year_path.name.isdigit():
                        continue
                    
                    year = int(year_path.name)
                    
                    for json_file in year_path.glob('*.json'):
                        quarter = int(json_file.stem)
                        
                        try:
                            with open(json_file, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                            
                            if 'data' not in data:
                                continue
                            
                            # Process different entity types
                            for entity_type in ['states', 'districts', 'pincodes']:
                                if entity_type in data['data']:
                                    entities = data['data'][entity_type]
                                    if not entities:
                                        continue
                                    
                                    for rank, entity_data in enumerate(entities, 1):
                                        # Determine entity name key
                                        name_key = 'name' if data_type == DataType.USER else 'entityName'
                                        entity_name = entity_data.get(name_key, '')
                                        
                                        if not entity_name:
                                            continue
                                        
                                        # Clean entity name based on type
                                        if entity_type == 'pincodes':
                                            if not (entity_name.isdigit() and len(entity_name) == 6):
                                                continue
                                        else:
                                            if entity_type == 'states':
                                                entity_name = self.clean_state_name(entity_name)
                                            elif entity_type == 'districts':
                                                entity_name = self.clean_district_name(entity_name)
                                            
                                            if not entity_name:
                                                continue
                                        
                                        # Handle user data without metric
                                        if 'metric' not in entity_data and data_type == DataType.USER:
                                            record = (
                                                state_name, year, quarter, entity_type[:-1],
                                                entity_name, int(entity_data.get('registeredUsers', 0))
                                            )
                                            batch_records.append(record)
                                            continue
                                        
                                        # Extract metrics
                                        if 'metric' in entity_data:
                                            metric = entity_data['metric']
                                            
                                            if data_type == DataType.TRANSACTION:
                                                record = (
                                                    state_name, year, quarter, entity_type[:-1],
                                                    entity_name, int(metric.get('count', 0)),
                                                    self.convert_scientific_notation(metric.get('amount', 0))
                                                )
                                                batch_records.append(record)
                                            
                                            elif data_type == DataType.USER:
                                                record = (
                                                    state_name, year, quarter, entity_type[:-1],
                                                    entity_name, int(metric.get('registeredUsers', 0))
                                                )
                                                batch_records.append(record)
                                            
                                            elif data_type == DataType.INSURANCE:
                                                record = (
                                                    state_name, year, quarter, entity_type[:-1],
                                                    entity_name, int(metric.get('count', 0)),
                                                    self.convert_scientific_notation(metric.get('amount', 0))
                                                )
                                                batch_records.append(record)
                                        
                                        # Batch insert
                                        if len(batch_records) >= self.batch_size:
                                            self._batch_insert_top_data(cursor, data_type, batch_records)
                                            connection.commit()
                                            record_count += len(batch_records)
                                            logger.info(f"Inserted {record_count} top {data_type} records")
                                            batch_records = []
                        
                        except Exception as e:
                            raise Exception(f"Error processing file {json_file}: {e}")
            
            # Insert remaining records
            if batch_records:
                self._batch_insert_top_data(cursor, data_type, batch_records)
                connection.commit()
                record_count += len(batch_records)
            
        
        except Exception as e:
            logger.error(f"Error in extract_top_data for {data_type}: {e}")
            connection.rollback()
        
        finally:
            cursor.close()
            connection.close()
    
    def _batch_insert_top_data(self, cursor, data_type: str, records: List[Tuple]):
        """
        Batch insert top data records using executemany().
        
        Args:
            cursor: Database cursor
            data_type: Type of data being inserted
            records: List of record tuples
        """
        if not records:
            return
        
        try:
            if data_type == DataType.TRANSACTION:
                cursor.executemany(
                    """INSERT INTO TOP_TRANSACTION_RECORD 
                       (STATE, YEAR, QUARTER, ENTITY_TYPE, ENTITY_NAME, TRANSACTION_COUNT, TRANSACTION_AMOUNT) 
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    records
                )
            elif data_type == DataType.USER:
                cursor.executemany(
                    """INSERT INTO TOP_USER_RECORD 
                       (STATE, YEAR, QUARTER, ENTITY_TYPE, ENTITY_NAME, REGISTERED_USERS) 
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    records
                )
            elif data_type == DataType.INSURANCE:
                cursor.executemany(
                    """INSERT INTO TOP_INSURANCE_RECORD 
                       (STATE, YEAR, QUARTER, ENTITY_TYPE, ENTITY_NAME, INSURANCE_COUNT, INSURANCE_AMOUNT) 
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    records
                )
        except Error as e:
            raise
    
    def insert_transaction_data(self):
        """Extract and insert aggregated transaction data using batch inserts"""
        base_path = self.data_dir / TableType.AGGREGATED / DataType.TRANSACTION / "country" / "india" / "state"
        
        connection = self.get_connection()
        cursor = connection.cursor()
        batch_records = []
        
        try:
            for state_path in base_path.iterdir():
                if not state_path.is_dir():
                    continue
                
                state_name = self.clean_state_name(state_path.name)
                
                for year_path in state_path.iterdir():
                    if not year_path.name.isdigit():
                        continue
                    
                    year = int(year_path.name)
                    
                    for json_file in year_path.glob('*.json'):
                        quarter = int(json_file.stem)
                        
                        try:
                            with open(json_file, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                            
                            if 'data' in data and 'transactionData' in data['data']:
                                for transaction in data['data']['transactionData']:
                                    transaction_name = transaction.get('name', '').strip()
                                    if not transaction_name:
                                        continue
                                    
                                    if 'paymentInstruments' in transaction:
                                        for instrument in transaction['paymentInstruments']:
                                            record = (
                                                state_name, year, quarter, transaction_name,
                                                int(instrument.get('count', 0)),
                                                float(instrument.get('amount', 0))
                                            )
                                            batch_records.append(record)
                                            
                                            if len(batch_records) >= self.batch_size:
                                                cursor.executemany(
                                                    """INSERT INTO AGGREGATED_TRANSACTION_RECORD 
                                                       (STATE, YEAR, QUARTER, TRANSACTION_TYPE, TRANSACTION_COUNT, TRANSACTION_AMOUNT) 
                                                       VALUES (%s, %s, %s, %s, %s, %s)""",
                                                    batch_records
                                                )
                                                connection.commit()
                                                batch_records = []
                        
                        except Exception as e:
                            logger.error(f"Error processing transaction file {json_file}: {e}")
            
            # Insert remaining
            if batch_records:
                cursor.executemany(
                    """INSERT INTO AGGREGATED_TRANSACTION_RECORD 
                       (STATE, YEAR, QUARTER, TRANSACTION_TYPE, TRANSACTION_COUNT, TRANSACTION_AMOUNT) 
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    batch_records
                )
                connection.commit()
                    
        except Exception as e:
            connection.rollback()
        
        finally:
            cursor.close()
            connection.close()
    
    def insert_user_data(self):
        """Extract and insert aggregated user data using batch inserts"""
        base_path = self.data_dir / TableType.AGGREGATED / DataType.USER / "country" / "india" / "state"
        
        connection = self.get_connection()
        cursor = connection.cursor()
        batch_records = []
        
        try:
            for state_path in base_path.iterdir():
                if not state_path.is_dir():
                    continue
                
                state_name = self.clean_state_name(state_path.name)
                
                for year_path in state_path.iterdir():
                    if not year_path.name.isdigit():
                        continue
                    
                    year = int(year_path.name)
                    
                    for json_file in year_path.glob('*.json'):
                        quarter = int(json_file.stem)
                        
                        try:
                            with open(json_file, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                            
                            base_registered_users = 0
                            base_app_opens = 0
                            
                            if 'data' in data and 'aggregated' in data['data']:
                                agg = data['data']['aggregated']
                                base_registered_users = int(agg.get('registeredUsers', 0))
                                base_app_opens = int(agg.get('appOpens', 0))
                                
                                # Insert base record
                                record = (
                                    state_name, year, quarter, base_app_opens,
                                    base_registered_users, None, None, None
                                )
                                batch_records.append(record)
                            
                            # Insert device data
                            if 'data' in data and 'usersByDevice' in data['data']:
                                devices = data['data']['usersByDevice']
                                if devices:
                                    for device in devices:
                                        device_brand = device.get('brand', '').strip()
                                        if not device_brand:
                                            continue
                                        
                                        record = (
                                            state_name, year, quarter, base_app_opens,
                                            base_registered_users, device_brand,
                                            int(device.get('count', 0)),
                                            float(device.get('percentage', 0.0))
                                        )
                                        batch_records.append(record)
                            
                            # Batch insert
                            if len(batch_records) >= self.batch_size:
                                cursor.executemany(
                                    """INSERT INTO AGGREGATED_USER_RECORD 
                                       (STATE, YEAR, QUARTER, APPS_OPEN, REGISTERED_USERS, DEVICE_BRAND, DEVICE_COUNT, DEVICE_PERCENTAGE) 
                                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                                    batch_records
                                )
                                connection.commit()
                                batch_records = []
                        
                        except Exception as e:
                            logger.error(f"Error processing user file {json_file}: {e}")
            
            # Insert remaining
            if batch_records:
                cursor.executemany(
                    """INSERT INTO AGGREGATED_USER_RECORD 
                       (STATE, YEAR, QUARTER, APPS_OPEN, REGISTERED_USERS, DEVICE_BRAND, DEVICE_COUNT, DEVICE_PERCENTAGE) 
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                    batch_records
                )
                connection.commit()
            
        
        except Exception as e:
            connection.rollback()
        
        finally:
            cursor.close()
            connection.close()
    
    def insert_insurance_data(self):
        """Extract and insert aggregated insurance data using batch inserts"""
        base_path = self.data_dir / TableType.AGGREGATED / DataType.INSURANCE / "country" / "india" / "state"
        
        connection = self.get_connection()
        cursor = connection.cursor()
        batch_records = []
        
        try:
            for state_path in base_path.iterdir():
                if not state_path.is_dir():
                    continue
                
                state_name = self.clean_state_name(state_path.name)
                
                for year_path in state_path.iterdir():
                    if not year_path.name.isdigit():
                        continue
                    
                    year = int(year_path.name)
                    
                    for json_file in year_path.glob('*.json'):
                        quarter = int(json_file.stem)
                        
                        try:
                            with open(json_file, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                            
                            if 'data' in data:
                                insurance_data = data['data']
                                
                                if isinstance(insurance_data, dict):
                                    if 'count' in insurance_data or 'amount' in insurance_data:
                                        record = (
                                            state_name, year, quarter,
                                            int(insurance_data.get('count', 0)),
                                            float(insurance_data.get('amount', 0))
                                        )
                                        batch_records.append(record)
                                    
                                    elif 'transactionData' in insurance_data:
                                        for transaction in insurance_data['transactionData']:
                                            if 'insurance' in transaction.get('name', '').lower():
                                                if 'paymentInstruments' in transaction:
                                                    for instrument in transaction['paymentInstruments']:
                                                        record = (
                                                            state_name, year, quarter,
                                                            int(instrument.get('count', 0)),
                                                            float(instrument.get('amount', 0))
                                                        )
                                                        batch_records.append(record)
                                
                                # Batch insert
                                if len(batch_records) >= self.batch_size:
                                    cursor.executemany(
                                        """INSERT INTO AGGREGATED_INSURANCE_RECORD 
                                           (STATE, YEAR, QUARTER, INSURANCE_COUNT, INSURANCE_AMOUNT) 
                                           VALUES (%s, %s, %s, %s, %s)""",
                                        batch_records
                                    )
                                    connection.commit()
                                    batch_records = []
                        
                        except Exception as e:
                            logger.error(f"Error processing insurance file {json_file}: {e}")
            
            # Insert remaining
            if batch_records:
                cursor.executemany(
                    """INSERT INTO AGGREGATED_INSURANCE_RECORD 
                       (STATE, YEAR, QUARTER, INSURANCE_COUNT, INSURANCE_AMOUNT) 
                       VALUES (%s, %s, %s, %s, %s)""",
                    batch_records
                )
                connection.commit()
                    
        except Exception as e:
            connection.rollback()
        
        finally:
            cursor.close()
            connection.close()
    
    def extract_all_data(self):
        """
        Main execution method to run all extraction steps.
        """
        try:
            
            # Aggregated data
            self.create_tables()
            self.insert_transaction_data()
            self.insert_user_data()
            self.insert_insurance_data()
            
            # Map data
            for data_type in DataType.ALL:
                logger.info(f"\nProcessing map {data_type} data...")
                self.extract_map_data(data_type)
            
            # Top data
            for data_type in DataType.ALL:
                logger.info(f"\nProcessing top {data_type} data...")
                self.extract_top_data(data_type)
            
            logger.info("\n🎉 Step 1 completed successfully!")
            
            
        
        except Exception as e:
            raise


# Usage example
if __name__ == "__main__":
    extractor = PhonePeDataExtractor()
    extractor.extract_all_data()
