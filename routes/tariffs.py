"""
================================================================================
  DBMS MINI PROJECT: ELECTRICITY BILLING AND CONSUMPTION MANAGEMENT SYSTEM
  TARIFF & PROGRESSIVE SLAB MANAGEMENT BLUEPRINT
================================================================================
"""

from decimal import Decimal
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from routes.auth import login_required, admin_required
from database.db import execute_query, execute_query_one, execute_dml
from services.billing_service import calculate_slab_breakdown

tariffs_bp = Blueprint("tariffs", __name__, url_prefix="/tariffs")

@tariffs_bp.route("/")
@login_required
def index():
    try:
        tariffs = execute_query("SELECT * FROM tariffs ORDER BY tariff_id ASC")
        for t in tariffs:
            t["slabs"] = execute_query(
                "SELECT * FROM tariff_slabs WHERE tariff_id = %s ORDER BY slab_number ASC",
                (t["tariff_id"],)
            )
    except Exception as e:
        flash(f"Database query note: {str(e)}", "warning")
        tariffs = []

    return render_template("tariffs/index.html", tariffs=tariffs)

@tariffs_bp.route("/<int:tariff_id>/edit", methods=["GET", "POST"])
@admin_required
def edit(tariff_id):
    tariff = execute_query_one("SELECT * FROM tariffs WHERE tariff_id = %s", (tariff_id,))
    if not tariff:
        flash("Tariff configuration not found.", "danger")
        return redirect(url_for("tariffs.index"))

    if request.method == "POST":
        tariff_name = request.form.get("tariff_name", "").strip()
        fixed_charge = request.form.get("fixed_charge", "0.00").strip()
        is_active = True if request.form.get("is_active") == "on" else False

        try:
            execute_dml(
                """
                UPDATE tariffs
                SET tariff_name = %s, fixed_charge = %s, is_active = %s
                WHERE tariff_id = %s
                """,
                (tariff_name, Decimal(fixed_charge), is_active, tariff_id)
            )
            flash("Tariff master settings updated successfully.", "success")
            return redirect(url_for("tariffs.index"))
        except Exception as e:
            flash(f"Update failed: {str(e)}", "danger")

    slabs = execute_query(
        "SELECT * FROM tariff_slabs WHERE tariff_id = %s ORDER BY slab_number ASC",
        (tariff_id,)
    )
    return render_template("tariffs/form.html", tariff=tariff, slabs=slabs)

@tariffs_bp.route("/<int:tariff_id>/slab/add", methods=["POST"])
@admin_required
def add_slab(tariff_id):
    min_units = request.form.get("min_units")
    max_units = request.form.get("max_units") or None
    rate_per_unit = request.form.get("rate_per_unit")
    description = request.form.get("description", "").strip()

    try:
        min_u = Decimal(min_units)
        max_u = Decimal(max_units) if max_units else None
        rate = Decimal(rate_per_unit)

        if min_u < 0 or rate < 0:
            flash("Minimum units and unit rate must be positive values.", "danger")
            return redirect(url_for("tariffs.edit", tariff_id=tariff_id))

        if max_u is not None and max_u <= min_u:
            flash("Maximum units must be strictly greater than minimum units.", "danger")
            return redirect(url_for("tariffs.edit", tariff_id=tariff_id))

        # Determine next slab number
        cur_count = execute_query_one(
            "SELECT COUNT(*) + 1 AS next_seq FROM tariff_slabs WHERE tariff_id = %s",
            (tariff_id,)
        )
        slab_num = cur_count["next_seq"] if cur_count else 1

        execute_dml(
            """
            INSERT INTO tariff_slabs (tariff_id, slab_number, min_units, max_units, rate_per_unit, slab_description)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (tariff_id, slab_num, min_u, max_u, rate, description)
        )
        flash(f"Slab #{slab_num} added successfully.", "success")
    except Exception as e:
        flash(f"Failed to add slab: {str(e)}", "danger")

    return redirect(url_for("tariffs.edit", tariff_id=tariff_id))

@tariffs_bp.route("/api/simulate-calc", methods=["POST"])
@login_required
def simulate():
    """Simulates progressive slab calculation interactively for viva/demo testing."""
    data = request.get_json() or {}
    tariff_id = data.get("tariff_id")
    units = data.get("units", 0)

    try:
        t = execute_query_one("SELECT * FROM tariffs WHERE tariff_id = %s", (tariff_id,))
        if not t:
            return jsonify({"error": "Tariff not found"}), 404

        breakdown, energy_charge = calculate_slab_breakdown(tariff_id, Decimal(str(units)))
        fixed_charge = Decimal(str(t["fixed_charge"]))
        tax_amount = (energy_charge * Decimal("0.05")) if (t["connection_type"] != "DOMESTIC" or Decimal(str(units)) > 100) else Decimal("0.00")
        total = energy_charge + fixed_charge + tax_amount

        return jsonify({
            "tariff_name": t["tariff_name"],
            "units": float(units),
            "breakdown": breakdown,
            "energy_charge": float(energy_charge),
            "fixed_charge": float(fixed_charge),
            "tax_amount": float(tax_amount),
            "total_amount": float(total)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400
