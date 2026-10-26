"""
================================================================================
  DBMS MINI PROJECT: ELECTRICITY BILLING AND CONSUMPTION MANAGEMENT SYSTEM
  DATABASE INITIALIZATION AND SEEDING SCRIPT
================================================================================
  Usage:
    python init_db.py
    
  This script:
    1. Checks if PostgreSQL server is reachable.
    2. Automatically creates the database `electricity_billing_db` if not present.
    3. Executes DDL scripts 02 through 07 (Schema, Indexes, Functions, Procedures, Triggers, Views).
    4. Executes seed data script 08 to insert realistic demonstration records.
================================================================================
"""

import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from config import Config

SCRIPTS = [
    ("02_schema.sql", "Creating Relational Tables (3NF Schema)"),
    ("03_constraints_indexes.sql", "Building B-Tree Performance Indexes"),
    ("04_functions.sql", "Compiling Stored PL/pgSQL Functions"),
    ("05_procedures.sql", "Compiling Stored Procedures"),
    ("06_triggers.sql", "Configuring Business Integrity Triggers"),
    ("07_views.sql", "Creating Analytical Reporting Views"),
    ("08_seed_data.sql", "Seeding Sample Utility Consumers, Readings & Bills")
]

def ensure_database_exists():
    """Connects to default 'postgres' database to ensure target database exists."""
    print("Connecting to PostgreSQL administrative server...")
    try:
        conn = psycopg2.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            dbname="postgres",
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            connect_timeout=5
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (Config.DB_NAME,))
            if not cur.fetchone():
                print(f"Creating database '{Config.DB_NAME}'...")
                cur.execute(f'CREATE DATABASE "{Config.DB_NAME}" WITH ENCODING "UTF8";')
                print(f"Database '{Config.DB_NAME}' created successfully.")
            else:
                print(f"Database '{Config.DB_NAME}' already exists.")
        conn.close()
        return True
    except Exception as e:
        print(f"\n[ERROR] Could not connect to PostgreSQL server: {e}")
        print("\nPlease verify:")
        print("  1. PostgreSQL service is running on your machine.")
        print(f"  2. Credentials in .env (host={Config.DB_HOST}, port={Config.DB_PORT}, user={Config.DB_USER}) are correct.")
        return False

def run_sql_scripts():
    """Executes all initialization scripts in sequence on electricity_billing_db."""
    db_dir = os.path.join(os.path.dirname(__file__), "database")
    
    try:
        conn = psycopg2.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            dbname=Config.DB_NAME,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD
        )
        conn.autocommit = True
        cur = conn.cursor()

        print("\nStarting schema creation and data seeding...")
        for script_name, description in SCRIPTS:
            script_path = os.path.join(db_dir, script_name)
            if not os.path.exists(script_path):
                print(f"Script file not found: {script_path}")
                continue

            print(f"-> {script_name}: {description}...")
            with open(script_path, "r", encoding="utf-8") as f:
                sql_content = f.read()

            try:
                cur.execute(sql_content)
                print(f"   [OK] {script_name} executed successfully.")
            except Exception as script_err:
                print(f"   [FAILED] Error in {script_name}: {script_err}")
                conn.close()
                return False

        cur.close()
        conn.close()
        print("\nAll database objects and seed data initialized successfully!")
        print("You can now start the web application by running: python app.py")
        return True

    except Exception as e:
        print(f"[ERROR] Failed to run initialization scripts: {e}")
        return False

if __name__ == "__main__":
    print("=" * 70)
    print("  ELECTRICITY BILLING SYSTEM - DATABASE INITIALIZER")
    print("=" * 70)
    if ensure_database_exists():
        run_sql_scripts()
    else:
        sys.exit(1)
