"""
================================================================================
  DBMS MINI PROJECT: ELECTRICITY BILLING AND CONSUMPTION MANAGEMENT SYSTEM
  TEST FIXTURES & CONFIGURATION (pytest)
================================================================================
"""

import pytest
from app import create_app

class TestConfig:
    TESTING = True
    SECRET_KEY = "test-secret-key-12345"
    DB_HOST = "localhost"
    DB_PORT = 5432
    DB_NAME = "electricity_billing_db"
    DB_USER = "postgres"
    DB_PASSWORD = "postgres"

@pytest.fixture
def app():
    app = create_app(TestConfig)
    return app

@pytest.fixture
def client(app):
    return app.test_client()
