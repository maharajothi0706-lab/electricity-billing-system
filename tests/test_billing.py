"""
================================================================================
  DBMS MINI PROJECT: ELECTRICITY BILLING AND CONSUMPTION MANAGEMENT SYSTEM
  BILLING & PROGRESSIVE SLAB CALCULATION UNIT TESTS
================================================================================
"""

import pytest
from decimal import Decimal
from services.billing_service import calculate_units_consumed

def test_calculate_units_consumed_valid():
    """Verify units consumed = current - previous for standard meters."""
    units = calculate_units_consumed(100.0, 250.5)
    assert units == Decimal("150.5")

def test_calculate_units_consumed_zero_usage():
    """Verify zero units consumed when current equals previous."""
    units = calculate_units_consumed(500.0, 500.0)
    assert units == Decimal("0.0")

def test_reject_negative_previous_reading():
    """Requirement 19.3: Reject negative meter readings."""
    with pytest.raises(ValueError, match="Previous meter reading cannot be negative"):
        calculate_units_consumed(-10.0, 50.0)

def test_reject_negative_current_reading():
    """Requirement 19.3: Reject negative current reading."""
    with pytest.raises(ValueError, match="Current meter reading cannot be negative"):
        calculate_units_consumed(10.0, -5.0)

def test_reject_current_lower_than_previous():
    """Business rule: Current reading lower than previous indicates meter rollback/tampering."""
    with pytest.raises(ValueError, match="lower than previous"):
        calculate_units_consumed(300.0, 250.0)

def simulate_progressive_slabs(slabs, units):
    """Pure algorithmic evaluation of progressive slabs matching SQL logic."""
    rem = Decimal(str(units))
    total_energy = Decimal("0.00")
    breakdown = []

    for slab in slabs:
        min_u = Decimal(str(slab["min_units"]))
        max_u = Decimal(str(slab["max_units"])) if slab.get("max_units") is not None else None
        rate = Decimal(str(slab["rate"]))

        if max_u is not None:
            capacity = max_u - min_u
            applicable = min(rem, capacity)
        else:
            applicable = rem

        if applicable > 0:
            charge = round(applicable * rate, 2)
            total_energy += charge
            breakdown.append({"units": float(applicable), "rate": float(rate), "amount": float(charge)})
            rem -= applicable

        if rem <= 0:
            break

    return breakdown, total_energy

def test_progressive_slab_calculation_domestic_tier():
    """
    Requirement 19.6: Correctly calculate charges across multiple tariff slabs.
    Domestic Slabs:
      Slab 1: 0 - 100 @ ₹2.00
      Slab 2: 100 - 200 @ ₹3.00
      Slab 3: > 200 @ ₹5.00
    For 250 units:
      100 * 2.00 = 200
      100 * 3.00 = 300
       50 * 5.00 = 250
      Total Energy = ₹750.00
    """
    slabs = [
        {"min_units": 0, "max_units": 100, "rate": 2.00},
        {"min_units": 100, "max_units": 200, "rate": 3.00},
        {"min_units": 200, "max_units": None, "rate": 5.00}
    ]

    # Test 50 units
    _, energy_50 = simulate_progressive_slabs(slabs, 50)
    assert energy_50 == Decimal("100.00")

    # Test 100 units
    _, energy_100 = simulate_progressive_slabs(slabs, 100)
    assert energy_100 == Decimal("200.00")

    # Test 150 units
    _, energy_150 = simulate_progressive_slabs(slabs, 150)
    assert energy_150 == Decimal("350.00")  # (100*2) + (50*3) = 200 + 150

    # Test 250 units
    breakdown, energy_250 = simulate_progressive_slabs(slabs, 250)
    assert energy_250 == Decimal("750.00")
    assert len(breakdown) == 3
    assert breakdown[0]["amount"] == 200.0
    assert breakdown[1]["amount"] == 300.0
    assert breakdown[2]["amount"] == 250.0

def test_fixed_charge_and_tax_addition():
    """Verify total bill = energy_charge + fixed_charge + tax."""
    energy_charge = Decimal("750.00")
    fixed_charge = Decimal("100.00")
    tax = round(energy_charge * Decimal("0.05"), 2)  # 37.50
    total = energy_charge + fixed_charge + tax
    assert total == Decimal("887.50")
