"""
================================================================================
  DBMS MINI PROJECT: ELECTRICITY BILLING AND CONSUMPTION MANAGEMENT SYSTEM
  CENTRAL FLASK APPLICATION (app.py)
================================================================================
"""

import os
from datetime import datetime
from flask import Flask, render_template, request, session, redirect, url_for, flash
from config import Config
from database.db import test_connection, execute_query_one

# Import Blueprints
from routes.auth import auth_bp, login_required
from routes.dashboard import dashboard_bp
from routes.consumers import consumers_bp
from routes.readings import readings_bp
from routes.bills import bills_bp
from routes.payments import payments_bp
from routes.tariffs import tariffs_bp
from routes.reports import reports_bp
from routes.sql_guide import sql_guide_bp

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(consumers_bp)
    app.register_blueprint(readings_bp)
    app.register_blueprint(bills_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(tariffs_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(sql_guide_bp)

    # Context Processor for Global Template Variables
    @app.context_processor
    def inject_global_data():
        is_conn, db_info = test_connection()
        return {
            "current_year": datetime.now().year,
            "db_connected": is_conn,
            "db_info": db_info if is_conn else "Disconnected",
            "current_user_name": session.get("full_name", "Guest"),
            "current_user_role": session.get("role", "VISITOR"),
            "is_logged_in": "user_id" in session
        }

    # Template Custom Filters
    @app.template_filter("currency")
    def currency_filter(value):
        try:
            return f"₹{float(value):,.2f}"
        except (ValueError, TypeError):
            return "₹0.00"

    @app.template_filter("date_format")
    def date_filter(value, fmt="%d %b %Y"):
        if not value:
            return "N/A"
        if isinstance(value, str):
            try:
                dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
                return dt.strftime(fmt)
            except Exception:
                return value
        if hasattr(value, "strftime"):
            return value.strftime(fmt)
        return str(value)

    # Settings Route
    @app.route("/settings")
    @login_required
    def settings():
        is_conn, db_version = test_connection()
        return render_template(
            "settings.html",
            db_connected=is_conn,
            db_version=db_version,
            config=Config
        )

    # Global Error Handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("base.html", error_message="Page Not Found (404)"), 404

    @app.errorhandler(500)
    def internal_error(e):
        return render_template("base.html", error_message=f"Internal Server Error: {str(e)}"), 500

    return app

app = create_app()

if __name__ == "__main__":
    print(f"Starting Electricity Billing System on http://127.0.0.1:{Config.PORT}")
    app.run(host="0.0.0.0", port=Config.PORT, debug=Config.DEBUG)
