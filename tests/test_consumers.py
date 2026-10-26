"""
================================================================================
  DBMS MINI PROJECT: ELECTRICITY BILLING AND CONSUMPTION MANAGEMENT SYSTEM
  CONSUMER VALIDATION & SEARCH TESTS
================================================================================
"""

import pytest

VALID_CONNECTION_TYPES = {"DOMESTIC", "COMMERCIAL", "INDUSTRIAL"}
VALID_STATUSES = {"ACTIVE", "INACTIVE"}

def validate_consumer_input(data, existing_consumers=None):
    """Validates consumer creation input."""
    if not data.get("consumer_number"):
        raise ValueError("Consumer number is mandatory.")
    if not data.get("full_name"):
        raise ValueError("Full name is mandatory.")
    if not data.get("meter_number"):
        raise ValueError("Meter number is mandatory.")
    if not data.get("phone_number"):
        raise ValueError("Phone number is mandatory.")

    conn_type = data.get("connection_type", "DOMESTIC").upper()
    if conn_type not in VALID_CONNECTION_TYPES:
        raise ValueError(f"Invalid connection type '{conn_type}'. Must be one of {VALID_CONNECTION_TYPES}.")

    status = data.get("account_status", "ACTIVE").upper()
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid account status '{status}'. Must be one of {VALID_STATUSES}.")

    if existing_consumers:
        c_num = data["consumer_number"].upper()
        m_num = data["meter_number"].upper()
        for ec in existing_consumers:
            if ec.get("consumer_number", "").upper() == c_num:
                raise ValueError(f"Duplicate consumer number '{c_num}'.")
            if ec.get("meter_number", "").upper() == m_num:
                raise ValueError(f"Duplicate meter hardware identifier '{m_num}'.")

    return True

def test_consumer_validation_success():
    """Verify clean consumer input passes validation."""
    data = {
        "consumer_number": "CONS-1001",
        "full_name": "Test Consumer",
        "address": "123 Main St",
        "city": "Chennai",
        "phone_number": "9840112345",
        "email": "test@example.com",
        "meter_number": "MTR-5001",
        "connection_type": "DOMESTIC",
        "account_status": "ACTIVE"
    }
    assert validate_consumer_input(data) is True

def test_reject_duplicate_consumer_number():
    """Requirement 19.2: Reject duplicate consumer numbers."""
    existing = [{"consumer_number": "CONS-1001", "meter_number": "MTR-5001"}]
    new_data = {
        "consumer_number": "CONS-1001",
        "full_name": "Another Person",
        "meter_number": "MTR-9999",
        "phone_number": "9840000000"
    }
    with pytest.raises(ValueError, match="Duplicate consumer number"):
        validate_consumer_input(new_data, existing)

def test_reject_duplicate_meter_number():
    """Requirement 19.2: Reject duplicate meter hardware numbers."""
    existing = [{"consumer_number": "CONS-1001", "meter_number": "MTR-5001"}]
    new_data = {
        "consumer_number": "CONS-1002",
        "full_name": "Another Person",
        "meter_number": "MTR-5001",
        "phone_number": "9840000000"
    }
    with pytest.raises(ValueError, match="Duplicate meter hardware"):
        validate_consumer_input(new_data, existing)

def test_reject_invalid_connection_type():
    """Verify CHECK constraint logic on connection type."""
    data = {
        "consumer_number": "CONS-1005",
        "full_name": "Test Person",
        "meter_number": "MTR-5005",
        "phone_number": "9840000000",
        "connection_type": "INVALID_TYPE"
    }
    with pytest.raises(ValueError, match="Invalid connection type"):
        validate_consumer_input(data)
