"""
================================================================================
  DBMS MINI PROJECT: ELECTRICITY BILLING AND CONSUMPTION MANAGEMENT SYSTEM
  METER READING VALIDATION TESTS
================================================================================
"""

import pytest

def validate_meter_reading(consumer_status, reading_month, prev_reading, curr_reading, existing_readings=None):
    """Simulates trigger trg_validate_meter_reading checks."""
    if consumer_status != "ACTIVE":
        raise ValueError("Cannot enter readings for an INACTIVE consumer.")

    if prev_reading < 0 or curr_reading < 0:
        raise ValueError("Meter readings cannot be negative.")

    if curr_reading < prev_reading:
        raise ValueError("Current reading cannot be lower than previous reading.")

    if existing_readings:
        for r in existing_readings:
            if r.get("reading_month") == reading_month:
                raise ValueError(f"Duplicate reading for month '{reading_month}'.")

    return curr_reading - prev_reading

def test_reading_validation_success():
    """Verify valid meter reading computes units accurately."""
    units = validate_meter_reading(
        consumer_status="ACTIVE",
        reading_month="2026-10",
        prev_reading=1200.0,
        curr_reading=1350.0
    )
    assert units == 150.0

def test_reject_inactive_consumer_reading():
    """Requirement 14.D: Trigger prevents entering readings for inactive consumer."""
    with pytest.raises(ValueError, match="INACTIVE consumer"):
        validate_meter_reading(
            consumer_status="INACTIVE",
            reading_month="2026-10",
            prev_reading=100.0,
            curr_reading=200.0
        )

def test_reject_duplicate_month_reading():
    """Requirement 19.4: Prevent duplicate readings for same consumer and month."""
    existing = [{"reading_month": "2026-10", "current_reading": 500.0}]
    with pytest.raises(ValueError, match="Duplicate reading for month"):
        validate_meter_reading(
            consumer_status="ACTIVE",
            reading_month="2026-10",
            prev_reading=500.0,
            curr_reading=600.0,
            existing_readings=existing
        )
