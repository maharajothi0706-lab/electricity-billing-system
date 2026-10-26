"""
================================================================================
  DBMS MINI PROJECT: ELECTRICITY BILLING AND CONSUMPTION MANAGEMENT SYSTEM
  FLASK ENDPOINT & ROUTE TESTS
================================================================================
"""

def test_login_page_renders(client):
    """Test that login page loads with HTTP 200."""
    response = client.get("/login")
    assert response.status_code == 200
    assert b"POWER GRID UTILITY" in response.data

def test_unauthenticated_redirect(client):
    """Test that protected dashboard redirects unauthenticated user to login."""
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]

def test_authenticated_session_dashboard(client):
    """Test that logged in user can access dashboard."""
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["username"] = "admin"
        sess["full_name"] = "Administrator"
        sess["role"] = "ADMIN"

    response = client.get("/")
    assert response.status_code == 200
    assert b"Executive Operational Dashboard" in response.data

def test_tariffs_page_renders(client):
    """Test that tariffs page loads with simulator."""
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["role"] = "ADMIN"

    response = client.get("/tariffs/")
    assert response.status_code == 200
    assert b"Interactive Progressive Slab Calculator" in response.data

def test_reports_page_renders(client):
    """Test that reports page renders properly."""
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["role"] = "ADMIN"

    response = client.get("/reports/")
    assert response.status_code == 200
    assert b"Utility Analytical Reports" in response.data

def test_sql_guide_page_renders(client):
    """Test that DBMS viva / SQL guide page renders with Mermaid and queries."""
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["role"] = "ADMIN"

    response = client.get("/sql-guide/")
    assert response.status_code == 200
    assert b"DBMS Mini Project Knowledge Base" in response.data
    assert b"erDiagram" in response.data
