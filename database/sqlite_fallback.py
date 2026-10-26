"""
================================================================================
  DBMS MINI PROJECT: ELECTRICITY BILLING AND CONSUMPTION MANAGEMENT SYSTEM
  OFFLINE RESILIENCE & FALLBACK ADAPTER (SQLite3)
================================================================================
  Enables zero-downtime demonstration when PostgreSQL service is stopped or not
  yet installed on the host machine. Automatically synchronizes tables,
  seed data, views, and integrity rules.
================================================================================
"""

import os
import sqlite3

SQLITE_PATH = os.path.join(os.path.dirname(__file__), "electricity_billing.sqlite3")

def init_sqlite_database():
    """Initializes local SQLite database with all 3NF tables, views, and seed data."""
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 1. Users Table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        full_name TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'OPERATOR' CHECK (role IN ('ADMIN', 'OPERATOR')),
        email TEXT UNIQUE NOT NULL,
        is_active BOOLEAN NOT NULL DEFAULT 1,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. Consumers Table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS consumers (
        consumer_id INTEGER PRIMARY KEY AUTOINCREMENT,
        consumer_number TEXT UNIQUE NOT NULL,
        full_name TEXT NOT NULL,
        address TEXT NOT NULL,
        city TEXT NOT NULL DEFAULT 'Metropolis',
        phone_number TEXT NOT NULL,
        email TEXT NOT NULL,
        meter_number TEXT UNIQUE NOT NULL,
        connection_type TEXT NOT NULL DEFAULT 'DOMESTIC' CHECK (connection_type IN ('DOMESTIC', 'COMMERCIAL', 'INDUSTRIAL')),
        connection_date DATE NOT NULL DEFAULT (CURRENT_DATE),
        account_status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (account_status IN ('ACTIVE', 'INACTIVE')),
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 3. Tariffs Table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS tariffs (
        tariff_id INTEGER PRIMARY KEY AUTOINCREMENT,
        tariff_name TEXT NOT NULL,
        connection_type TEXT NOT NULL,
        fixed_charge REAL NOT NULL DEFAULT 0.00,
        effective_from DATE NOT NULL,
        effective_to DATE,
        is_active BOOLEAN NOT NULL DEFAULT 1,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 4. Tariff Slabs Table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS tariff_slabs (
        slab_id INTEGER PRIMARY KEY AUTOINCREMENT,
        tariff_id INTEGER NOT NULL REFERENCES tariffs(tariff_id) ON DELETE CASCADE,
        slab_number INTEGER NOT NULL,
        min_units REAL NOT NULL,
        max_units REAL,
        rate_per_unit REAL NOT NULL,
        slab_description TEXT,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (tariff_id, slab_number)
    );
    """)

    # 5. Meter Readings Table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS meter_readings (
        reading_id INTEGER PRIMARY KEY AUTOINCREMENT,
        consumer_id INTEGER NOT NULL REFERENCES consumers(consumer_id),
        reading_month TEXT NOT NULL,
        previous_reading REAL NOT NULL,
        current_reading REAL NOT NULL,
        units_consumed REAL NOT NULL,
        reading_date DATE NOT NULL DEFAULT (CURRENT_DATE),
        reading_remarks TEXT,
        is_billed BOOLEAN NOT NULL DEFAULT 0,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (consumer_id, reading_month)
    );
    """)

    # 6. Bills Table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS bills (
        bill_id INTEGER PRIMARY KEY AUTOINCREMENT,
        bill_number TEXT UNIQUE NOT NULL,
        consumer_id INTEGER NOT NULL REFERENCES consumers(consumer_id),
        meter_reading_id INTEGER UNIQUE NOT NULL REFERENCES meter_readings(reading_id),
        billing_period TEXT NOT NULL,
        units_consumed REAL NOT NULL,
        energy_charge REAL NOT NULL DEFAULT 0.00,
        fixed_charge REAL NOT NULL DEFAULT 0.00,
        tax_amount REAL NOT NULL DEFAULT 0.00,
        total_amount REAL NOT NULL,
        amount_paid REAL NOT NULL DEFAULT 0.00,
        outstanding_amount REAL NOT NULL,
        bill_date DATE NOT NULL DEFAULT (CURRENT_DATE),
        due_date DATE NOT NULL,
        payment_status TEXT NOT NULL DEFAULT 'UNPAID' CHECK (payment_status IN ('UNPAID', 'PARTIALLY PAID', 'PAID')),
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 7. Bill Items Table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS bill_items (
        item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        bill_id INTEGER NOT NULL REFERENCES bills(bill_id) ON DELETE CASCADE,
        item_type TEXT NOT NULL,
        description TEXT NOT NULL,
        units REAL NOT NULL DEFAULT 0.00,
        rate REAL NOT NULL DEFAULT 0.00,
        amount REAL NOT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 8. Payments Table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        bill_id INTEGER NOT NULL REFERENCES bills(bill_id),
        payment_reference TEXT UNIQUE NOT NULL,
        payment_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        amount_paid REAL NOT NULL,
        payment_method TEXT NOT NULL,
        payment_status TEXT NOT NULL DEFAULT 'SUCCESS' CHECK (payment_status IN ('SUCCESS', 'CANCELLED')),
        remarks TEXT,
        recorded_by TEXT NOT NULL DEFAULT 'SYSTEM',
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 9. Payment Reversals Table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS payment_reversals (
        reversal_id INTEGER PRIMARY KEY AUTOINCREMENT,
        payment_id INTEGER NOT NULL REFERENCES payments(payment_id),
        bill_id INTEGER NOT NULL REFERENCES bills(bill_id),
        reversal_reason TEXT NOT NULL,
        reversed_amount REAL NOT NULL,
        reversed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        reversed_by TEXT NOT NULL
    );
    """)

    # 10. Database Views
    cur.execute("DROP VIEW IF EXISTS consumer_billing_summary;")
    cur.execute("""
    CREATE VIEW consumer_billing_summary AS
    WITH consumer_bills_agg AS (
        SELECT 
            b.consumer_id,
            COUNT(b.bill_id) AS total_bills_count,
            COALESCE(SUM(b.units_consumed), 0.00) AS total_units_consumed,
            COALESCE(SUM(b.total_amount), 0.00) AS total_billed_amount,
            COALESCE(SUM(b.amount_paid), 0.00) AS total_paid_amount,
            COALESCE(SUM(b.outstanding_amount), 0.00) AS total_outstanding_amount
        FROM bills b
        GROUP BY b.consumer_id
    ),
    consumer_unpaid_agg AS (
        SELECT 
            b.consumer_id,
            COUNT(b.bill_id) AS unpaid_bills_count
        FROM bills b
        WHERE b.payment_status IN ('UNPAID', 'PARTIALLY PAID')
        GROUP BY b.consumer_id
    )
    SELECT 
        c.consumer_id,
        c.consumer_number,
        c.full_name,
        c.phone_number,
        c.email,
        c.city,
        c.connection_type,
        c.meter_number,
        c.account_status,
        c.connection_date,
        COALESCE(ba.total_bills_count, 0) AS total_bills_count,
        COALESCE(ba.total_units_consumed, 0.00) AS total_units_consumed,
        COALESCE(ba.total_billed_amount, 0.00) AS total_billed_amount,
        COALESCE(ba.total_paid_amount, 0.00) AS total_paid_amount,
        COALESCE(ba.total_outstanding_amount, 0.00) AS total_outstanding_amount,
        COALESCE(ua.unpaid_bills_count, 0) AS unpaid_bills_count
    FROM consumers c
    LEFT JOIN consumer_bills_agg ba ON c.consumer_id = ba.consumer_id
    LEFT JOIN consumer_unpaid_agg ua ON c.consumer_id = ua.consumer_id;
    """)

    cur.execute("DROP VIEW IF EXISTS monthly_consumption_summary;")
    cur.execute("""
    CREATE VIEW monthly_consumption_summary AS
    SELECT 
        mr.reading_month,
        COUNT(DISTINCT mr.consumer_id) AS active_consumers_read,
        SUM(mr.units_consumed) AS total_units_consumed,
        ROUND(AVG(mr.units_consumed), 2) AS average_units_consumed,
        MIN(mr.units_consumed) AS minimum_units_consumed,
        MAX(mr.units_consumed) AS maximum_units_consumed
    FROM meter_readings mr
    GROUP BY mr.reading_month
    ORDER BY mr.reading_month DESC;
    """)

    cur.execute("DROP VIEW IF EXISTS v_revenue_by_month;")
    cur.execute("""
    CREATE VIEW v_revenue_by_month AS
    SELECT 
        b.billing_period,
        COUNT(b.bill_id) AS total_bills_issued,
        SUM(b.units_consumed) AS total_units_billed,
        SUM(b.energy_charge) AS total_energy_charge,
        SUM(b.fixed_charge) AS total_fixed_charge,
        SUM(b.total_amount) AS total_billed_amount,
        SUM(b.amount_paid) AS total_collected_amount,
        SUM(b.outstanding_amount) AS total_outstanding_amount,
        CASE 
            WHEN SUM(b.total_amount) > 0 
            THEN ROUND((SUM(b.amount_paid) / SUM(b.total_amount) * 100.0), 2)
            ELSE 0.00 
        END AS collection_efficiency_percentage
    FROM bills b
    GROUP BY b.billing_period
    ORDER BY b.billing_period DESC;
    """)

    cur.execute("DROP VIEW IF EXISTS v_top_consumers;")
    cur.execute("""
    CREATE VIEW v_top_consumers AS
    SELECT 
        c.consumer_id,
        c.consumer_number,
        c.full_name,
        c.connection_type,
        c.meter_number,
        SUM(mr.units_consumed) AS lifetime_units_consumed,
        ROUND(AVG(mr.units_consumed), 2) AS avg_monthly_units,
        DENSE_RANK() OVER (ORDER BY SUM(mr.units_consumed) DESC) AS consumption_rank
    FROM consumers c
    JOIN meter_readings mr ON c.consumer_id = mr.consumer_id
    WHERE c.account_status = 'ACTIVE'
    GROUP BY c.consumer_id, c.consumer_number, c.full_name, c.connection_type, c.meter_number
    ORDER BY lifetime_units_consumed DESC;
    """)

    cur.execute("DROP VIEW IF EXISTS v_unpaid_bills;")
    cur.execute("""
    CREATE VIEW v_unpaid_bills AS
    SELECT 
        b.bill_id,
        b.bill_number,
        b.billing_period,
        c.consumer_id,
        c.consumer_number,
        c.full_name,
        c.phone_number,
        c.connection_type,
        b.units_consumed,
        b.total_amount,
        b.amount_paid,
        b.outstanding_amount,
        b.bill_date,
        b.due_date,
        b.payment_status,
        CASE 
            WHEN date('now') > b.due_date THEN 1 
            ELSE 0 
        END AS is_overdue,
        MAX(0, CAST(julianday('now') - julianday(b.due_date) AS INTEGER)) AS days_overdue
    FROM bills b
    JOIN consumers c ON b.consumer_id = c.consumer_id
    WHERE b.payment_status IN ('UNPAID', 'PARTIALLY PAID')
    ORDER BY b.due_date ASC;
    """)

    # Seed data if users table is empty
    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        seed_sqlite_data(cur)

    conn.commit()
    conn.close()

def seed_sqlite_data(cur):
    """Populates realistic demonstration records."""
    # Users
    cur.executemany(
        "INSERT INTO users (username, password_hash, full_name, role, email) VALUES (?, ?, ?, ?, ?)",
        [
            ('admin', 'scrypt:32768:8:1$NqVEoxTyINsyg12S$71c83c544fc495bf794a8859059b0cf24accf22f7d00cab8ff9fc1b3dd2a736c96ef9f19271d69d4482e393a85dd076cc70ac5e5d448aa061aa4f61d860bddcf', 'Chief Engineer Sharma', 'ADMIN', 'admin.power@utility.org'),
            ('operator', 'scrypt:32768:8:1$yLKx3Iaqhab5C39v$792c773ef2d446376305ec61c3a29434142aa25659bcea1176c697c3d6a3c993c90aad663ca9b7eb8546203d184afe97c043127e13c35cfdab9dfc3e9e23dee6', 'Kavitha Ramanathan', 'OPERATOR', 'kavitha.ops@utility.org')
        ]
    )

    # Tariffs
    cur.executemany(
        "INSERT INTO tariffs (tariff_id, tariff_name, connection_type, fixed_charge, effective_from, is_active) VALUES (?, ?, ?, ?, ?, ?)",
        [
            (1, 'Domestic Residential Standard (LT-1)', 'DOMESTIC', 100.00, '2026-01-01', 1),
            (2, 'Commercial Retail & Office (LT-2)', 'COMMERCIAL', 250.00, '2026-01-01', 1),
            (3, 'Industrial Manufacturing (HT-1)', 'INDUSTRIAL', 600.00, '2026-01-01', 1)
        ]
    )

    # Slabs
    cur.executemany(
        "INSERT INTO tariff_slabs (tariff_id, slab_number, min_units, max_units, rate_per_unit, slab_description) VALUES (?, ?, ?, ?, ?, ?)",
        [
            (1, 1, 0, 100, 2.00, 'Slab 1: Lifeline Consumption (0 - 100 units)'),
            (1, 2, 100, 200, 3.00, 'Slab 2: Normal Domestic (101 - 200 units)'),
            (1, 3, 200, None, 5.00, 'Slab 3: Higher Domestic (> 200 units)'),
            (2, 1, 0, 150, 4.50, 'Commercial Base (0 - 150 units)'),
            (2, 2, 150, 300, 6.50, 'Commercial Mid-Tier (151 - 300 units)'),
            (2, 3, 300, None, 8.50, 'Commercial Heavy Tier (> 300 units)'),
            (3, 1, 0, 500, 7.00, 'Industrial Baseline (0 - 500 units)'),
            (3, 2, 500, None, 9.50, 'Industrial High Draw (> 500 units)')
        ]
    )

    # 18 Consumers
    cur.executemany(
        "INSERT INTO consumers (consumer_id, consumer_number, full_name, address, city, phone_number, email, meter_number, connection_type, connection_date, account_status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (1,  'CONS-1001', 'Aarav Sundaram',        '12, Anna Nagar 2nd Avenue',       'Chennai',    '9840112345', 'aarav.s@gmail.com',         'MTR-DOM-5001', 'DOMESTIC',   '2024-03-15', 'ACTIVE'),
            (2,  'CONS-1002', 'Bhavna Kulkarni',       '45/B, Koregaon Park',             'Pune',       '9822019876', 'bhavna.k@gmail.com',        'MTR-DOM-5002', 'DOMESTIC',   '2024-05-10', 'ACTIVE'),
            (3,  'CONS-1003', 'Chirag Sen',            '78, Salt Lake Sector V',          'Kolkata',    '9830543210', 'chirag.sen@outlook.com',    'MTR-DOM-5003', 'DOMESTIC',   '2024-06-20', 'ACTIVE'),
            (4,  'CONS-1004', 'Deepa Venkataraman',    '214, Indiranagar 100ft Road',     'Bengaluru',  '9900887766', 'deepa.venkat@yahoo.com',    'MTR-DOM-5004', 'DOMESTIC',   '2024-07-01', 'ACTIVE'),
            (5,  'CONS-1005', 'Eshwar Murugan',        '8, Gandhi Bazaar Main Road',      'Bengaluru',  '9845123456', 'eshwar.m@gmail.com',        'MTR-DOM-5005', 'DOMESTIC',   '2024-08-12', 'ACTIVE'),
            (6,  'CONS-1006', 'Farhan Akhtar Khan',    '19, Bandra West Hill Road',       'Mumbai',     '9820567890', 'farhan.khan@gmail.com',     'MTR-DOM-5006', 'DOMESTIC',   '2024-09-05', 'ACTIVE'),
            (7,  'CONS-1007', 'Gitanjali Rao',         '55, Malleshwaram 7th Cross',      'Bengaluru',  '9741234567', 'gita.rao@hotmail.com',      'MTR-DOM-5007', 'DOMESTIC',   '2024-10-18', 'ACTIVE'),
            (8,  'CONS-1008', 'Harish Chandra Verma',  '102, Hazratganj Civil Lines',     'Lucknow',    '9415012345', 'hc.verma@physics.in',       'MTR-DOM-5008', 'DOMESTIC',   '2024-11-22', 'ACTIVE'),
            (9,  'CONS-1009', 'Indira Nair',           '34, Panampilly Nagar',            'Kochi',      '9846098765', 'indira.nair@gmail.com',     'MTR-DOM-5009', 'DOMESTIC',   '2025-01-14', 'ACTIVE'),
            (10, 'CONS-1010', 'Jitesh Patel',          '88, C.G. Road Navrangpura',       'Ahmedabad',  '9825123789', 'jitesh.patel@gujarat.in',   'MTR-DOM-5010', 'DOMESTIC',   '2025-02-28', 'ACTIVE'),
            (11, 'CONS-1011', 'Kamal Hassan R.',       '14, T. Nagar North Usman Road',   'Chennai',    '9841234901', 'kamal.hassan@cinema.org',   'MTR-DOM-5011', 'DOMESTIC',   '2025-03-01', 'INACTIVE'),
            (12, 'CONS-2001', 'Surya Supermarket',     'Shop 4-6, MG Road Plaza',         'Bengaluru',  '9880123456', 'accounts@suryamarket.in',   'MTR-COM-6001', 'COMMERCIAL', '2024-01-10', 'ACTIVE'),
            (13, 'CONS-2002', 'Apex Diagnostic Labs', '72, Banjara Hills Road No 3',     'Hyderabad',  '9849012345', 'info@apexdia.com',          'MTR-COM-6002', 'COMMERCIAL', '2024-04-12', 'ACTIVE'),
            (14, 'CONS-2003', 'Metro Cyber Cafe',      '15, Park Street',                 'Kolkata',    '9831112233', 'metrocafe@calcutta.org',    'MTR-COM-6003', 'COMMERCIAL', '2024-07-25', 'ACTIVE'),
            (15, 'CONS-2004', 'Saffron Fine Dining',   '89, Connaught Place Outer Circle','New Delhi',  '9811223344', 'billing@saffrondine.in',    'MTR-COM-6004', 'COMMERCIAL', '2024-09-15', 'ACTIVE'),
            (16, 'CONS-3001', 'Kavery Steel Forgings', 'Plot 45, Peenya Industrial Area', 'Bengaluru',  '9844055667', 'works@kaverysteel.com',     'MTR-IND-7001', 'INDUSTRIAL', '2023-11-05', 'ACTIVE'),
            (17, 'CONS-3002', 'Titan Plastics Ltd',    'Survey 112, Manesar IMT',         'Gurugram',   '9810998877', 'plant@titanplastics.co',    'MTR-IND-7002', 'INDUSTRIAL', '2024-02-18', 'ACTIVE'),
            (18, 'CONS-3003', 'Zenith Agro Processing','MIDC Industrial Estate, Bhosari', 'Pune',       '9823112244', 'energy@zenithagro.in',      'MTR-IND-7003', 'INDUSTRIAL', '2024-05-30', 'ACTIVE')
        ]
    )

    # Meter Readings (4 billing periods)
    readings = [
        (1,  1,  '2026-07', 1200.0, 1340.0, 140.0, '2026-07-31', 1),
        (2,  2,  '2026-07',  850.0,  940.0,  90.0, '2026-07-31', 1),
        (3,  3,  '2026-07', 2100.0, 2350.0, 250.0, '2026-07-31', 1),
        (4,  4,  '2026-07', 1500.0, 1680.0, 180.0, '2026-07-31', 1),
        (5,  12, '2026-07', 4500.0, 4850.0, 350.0, '2026-07-31', 1),
        (6,  16, '2026-07', 8900.0, 9750.0, 850.0, '2026-07-31', 1),
        (7,  1,  '2026-08', 1340.0, 1500.0, 160.0, '2026-08-31', 1),
        (8,  2,  '2026-08',  940.0, 1025.0,  85.0, '2026-08-31', 1),
        (9,  3,  '2026-08', 2350.0, 2630.0, 280.0, '2026-08-31', 1),
        (10, 4,  '2026-08', 1680.0, 1870.0, 190.0, '2026-08-31', 1),
        (11, 12, '2026-08', 4850.0, 5260.0, 410.0, '2026-08-31', 1),
        (12, 16, '2026-08', 9750.0, 10700.0, 950.0, '2026-08-31', 1),
        (13, 1,  '2026-09', 1500.0, 1675.0, 175.0, '2026-09-30', 1),
        (14, 2,  '2026-09', 1025.0, 1120.0,  95.0, '2026-09-30', 1),
        (15, 3,  '2026-09', 2630.0, 2940.0, 310.0, '2026-09-30', 1),
        (16, 4,  '2026-09', 1870.0, 2085.0, 215.0, '2026-09-30', 1),
        (17, 5,  '2026-09',  600.0,  730.0, 130.0, '2026-09-30', 1),
        (18, 6,  '2026-09', 1100.0, 1260.0, 160.0, '2026-09-30', 1),
        (19, 7,  '2026-09',  450.0,  530.0,  80.0, '2026-09-30', 1),
        (20, 8,  '2026-09',  800.0,  990.0, 190.0, '2026-09-30', 1),
        (21, 9,  '2026-09',  950.0, 1110.0, 160.0, '2026-09-30', 1),
        (22, 10, '2026-09', 1300.0, 1540.0, 240.0, '2026-09-30', 1),
        (23, 12, '2026-09', 5260.0, 5690.0, 430.0, '2026-09-30', 1),
        (24, 13, '2026-09', 3100.0, 3380.0, 280.0, '2026-09-30', 1),
        (25, 14, '2026-09', 2200.0, 2390.0, 190.0, '2026-09-30', 1),
        (26, 15, '2026-09', 4100.0, 4620.0, 520.0, '2026-09-30', 1),
        (27, 16, '2026-09', 10700.0, 11800.0, 1100.0, '2026-09-30', 1),
        (28, 17, '2026-09', 7500.0, 8350.0, 850.0, '2026-09-30', 1),
        (29, 18, '2026-09', 6200.0, 6920.0, 720.0, '2026-09-30', 1),
        (30, 1,  '2026-10', 1675.0, 1865.0, 190.0, '2026-10-25', 1),
        (31, 2,  '2026-10', 1120.0, 1205.0,  85.0, '2026-10-25', 1),
        (32, 3,  '2026-10', 2940.0, 3420.0, 480.0, '2026-10-25', 1),
        (33, 4,  '2026-10', 2085.0, 2315.0, 230.0, '2026-10-25', 1),
        (34, 5,  '2026-10',  730.0,  890.0, 160.0, '2026-10-25', 0),
        (35, 6,  '2026-10', 1260.0, 1435.0, 175.0, '2026-10-25', 0),
        (36, 12, '2026-10', 5690.0, 6150.0, 460.0, '2026-10-25', 1),
        (37, 16, '2026-10', 11800.0, 13150.0, 1350.0, '2026-10-25', 1)
    ]
    cur.executemany(
        "INSERT INTO meter_readings (reading_id, consumer_id, reading_month, previous_reading, current_reading, units_consumed, reading_date, is_billed) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        readings
    )

    # Bills
    bills = [
        (1,  'BILL-202607-0001', 1,  1,  '2026-07', 140.0, 320.00,  100.0, 16.00,  436.00,   436.00,   0.00,     '2026-08-01', '2026-08-16', 'PAID'),
        (2,  'BILL-202607-0002', 2,  2,  '2026-07', 90.0,  180.00,  100.0, 0.00,   280.00,   280.00,   0.00,     '2026-08-01', '2026-08-16', 'PAID'),
        (3,  'BILL-202607-0003', 3,  3,  '2026-07', 250.0, 750.00,  100.0, 37.50,  887.50,   887.50,   0.00,     '2026-08-01', '2026-08-16', 'PAID'),
        (4,  'BILL-202607-0004', 12, 5,  '2026-07', 350.0, 2075.00, 250.0, 103.75, 2428.75,  2428.75,  0.00,     '2026-08-01', '2026-08-16', 'PAID'),
        (5,  'BILL-202608-0001', 1,  7,  '2026-08', 160.0, 380.00,  100.0, 19.00,  499.00,   499.00,   0.00,     '2026-09-01', '2026-09-16', 'PAID'),
        (6,  'BILL-202608-0002', 2,  8,  '2026-08', 85.0,  170.00,  100.0, 0.00,   270.00,   270.00,   0.00,     '2026-09-01', '2026-09-16', 'PAID'),
        (7,  'BILL-202608-0003', 3,  9,  '2026-08', 280.0, 900.00,  100.0, 45.00,  1045.00,  1045.00,  0.00,     '2026-09-01', '2026-09-16', 'PAID'),
        (8,  'BILL-202608-0004', 12, 11, '2026-08', 410.0, 2585.00, 250.0, 129.25, 2964.25,  2964.25,  0.00,     '2026-09-01', '2026-09-16', 'PAID'),
        (9,  'BILL-202609-0001', 1,  13, '2026-09', 175.0, 425.00,  100.0, 21.25,  546.25,   546.25,   0.00,     '2026-10-01', '2026-10-16', 'PAID'),
        (10, 'BILL-202609-0002', 2,  14, '2026-09', 95.0,  190.00,  100.0, 0.00,   290.00,   290.00,   0.00,     '2026-10-01', '2026-10-16', 'PAID'),
        (11, 'BILL-202609-0003', 3,  15, '2026-09', 310.0, 1050.00, 100.0, 52.50,  1202.50,  600.00,   602.50,   '2026-10-01', '2026-10-16', 'PARTIALLY PAID'),
        (12, 'BILL-202609-0004', 4,  16, '2026-09', 215.0, 575.00,  100.0, 28.75,  703.75,   0.00,     703.75,   '2026-10-01', '2026-10-16', 'UNPAID'),
        (13, 'BILL-202609-0005', 12, 23, '2026-09', 430.0, 2755.00, 250.0, 137.75, 3142.75,  3142.75,  0.00,     '2026-10-01', '2026-10-16', 'PAID'),
        (14, 'BILL-202609-0006', 16, 27, '2026-09', 1100.0, 9200.00, 600.0, 460.00, 10260.00, 10260.00, 0.00,     '2026-10-01', '2026-10-16', 'PAID'),
        (15, 'BILL-202610-0001', 1,  30, '2026-10', 190.0, 470.00,  100.0, 23.50,  593.50,   0.00,     593.50,   '2026-10-25', '2026-11-10', 'UNPAID'),
        (16, 'BILL-202610-0002', 2,  31, '2026-10', 85.0,  170.00,  100.0, 0.00,   270.00,   270.00,   0.00,     '2026-10-25', '2026-11-10', 'PAID'),
        (17, 'BILL-202610-0003', 3,  32, '2026-10', 480.0, 1900.00, 100.0, 95.00,  2095.00,  0.00,     2095.00,  '2026-10-25', '2026-11-10', 'UNPAID'),
        (18, 'BILL-202610-0004', 12, 36, '2026-10', 460.0, 3010.00, 250.0, 150.50, 3410.50,  1500.00,  1910.50,  '2026-10-25', '2026-11-10', 'PARTIALLY PAID'),
        (19, 'BILL-202610-0005', 16, 37, '2026-10', 1350.0, 11575.00, 600.0, 578.75, 12753.75, 0.00,    12753.75, '2026-10-25', '2026-11-10', 'UNPAID')
    ]
    cur.executemany(
        "INSERT INTO bills (bill_id, bill_number, consumer_id, meter_reading_id, billing_period, units_consumed, energy_charge, fixed_charge, tax_amount, total_amount, amount_paid, outstanding_amount, bill_date, due_date, payment_status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        bills
    )

    # Bill items for Bill 1 & Bill 3
    items = [
        (1, 'SLAB_CHARGE', 'Slab 1 (0 - 100 units @ ₹2.00)', 100.0, 2.0, 200.0),
        (1, 'SLAB_CHARGE', 'Slab 2 (101 - 200 units @ ₹3.00)', 40.0, 3.0, 120.0),
        (1, 'FIXED_CHARGE', 'Monthly Standing Meter Rent & Maintenance Charge', 0, 0, 100.0),
        (1, 'TAX', 'Electricity Duty & Regulatory Surcharge (5%)', 0, 5.0, 16.0),
        (3, 'SLAB_CHARGE', 'Slab 1 (0 - 100 units @ ₹2.00)', 100.0, 2.0, 200.0),
        (3, 'SLAB_CHARGE', 'Slab 2 (101 - 200 units @ ₹3.00)', 100.0, 3.0, 300.0),
        (3, 'SLAB_CHARGE', 'Slab 3 (> 200 units @ ₹5.00)', 50.0, 5.0, 250.0),
        (3, 'FIXED_CHARGE', 'Monthly Standing Meter Rent & Maintenance Charge', 0, 0, 100.0),
        (3, 'TAX', 'Electricity Duty & Regulatory Surcharge (5%)', 0, 5.0, 37.5)
    ]
    cur.executemany(
        "INSERT INTO bill_items (bill_id, item_type, description, units, rate, amount) VALUES (?, ?, ?, ?, ?, ?)",
        items
    )

    # Payments
    payments = [
        (1,  1,  'RCPT-20260805-0001', '2026-08-05 10:30:00', 436.00,   'UPI',           'SUCCESS', 'UPI ref: 621893821092', 'kavitha.ops'),
        (2,  2,  'RCPT-20260807-0002', '2026-08-07 14:15:00', 280.00,   'CASH',          'SUCCESS', 'Counter cash counter 2', 'kavitha.ops'),
        (3,  3,  'RCPT-20260810-0003', '2026-08-10 11:00:00', 887.50,   'NET_BANKING',   'SUCCESS', 'SBI NetBanking ref 882910', 'system'),
        (4,  4,  'RCPT-20260812-0004', '2026-08-12 16:45:00', 2428.75,  'BANK_TRANSFER', 'SUCCESS', 'NEFT / RTGS HDFC0099', 'system'),
        (5,  5,  'RCPT-20260906-0001', '2026-09-06 09:20:00', 499.00,   'UPI',           'SUCCESS', 'GPay ref: 9021882711', 'kavitha.ops'),
        (6,  6,  'RCPT-20260908-0002', '2026-09-08 12:10:00', 270.00,   'CASH',          'SUCCESS', 'Counter payment', 'kavitha.ops'),
        (7,  7,  'RCPT-20260912-0003', '2026-09-12 15:30:00', 1045.00,  'UPI',           'SUCCESS', 'PhonePe ref: 77263541', 'kavitha.ops'),
        (8,  8,  'RCPT-20260914-0004', '2026-09-14 17:00:00', 2964.25,  'BANK_TRANSFER', 'SUCCESS', 'Corporate NEFT transfer', 'system'),
        (9,  9,  'RCPT-20261005-0001', '2026-10-05 10:15:00', 546.25,   'UPI',           'SUCCESS', 'UPI ref: 8829102983', 'kavitha.ops'),
        (10, 10, 'RCPT-20261007-0002', '2026-10-07 11:45:00', 290.00,   'CASH',          'SUCCESS', 'Counter cash', 'kavitha.ops'),
        (11, 11, 'RCPT-20261010-0003', '2026-10-10 14:00:00', 600.00,   'UPI',           'SUCCESS', 'Partial installment payment', 'kavitha.ops'),
        (12, 13, 'RCPT-20261012-0004', '2026-10-12 16:30:00', 3142.75,  'BANK_TRANSFER', 'SUCCESS', 'Full settlement via RTGS', 'system'),
        (13, 14, 'RCPT-20261014-0005', '2026-10-14 11:20:00', 10260.00, 'BANK_TRANSFER', 'SUCCESS', 'Industrial monthly settlement', 'system'),
        (14, 16, 'RCPT-20261025-0001', '2026-10-25 15:10:00', 270.00,   'UPI',           'SUCCESS', 'Instant UPI payment', 'kavitha.ops'),
        (15, 18, 'RCPT-20261025-0002', '2026-10-25 16:00:00', 1500.00,  'CASH',          'SUCCESS', 'First installment partial cash', 'kavitha.ops'),
        (16, 9,  'RCPT-20261006-9999', '2026-10-06 12:00:00', 546.25,   'CASH',          'CANCELLED', 'Duplicate entry recorded by mistake at counter', 'kavitha.ops')
    ]
    cur.executemany(
        "INSERT INTO payments (payment_id, bill_id, payment_reference, payment_date, amount_paid, payment_method, payment_status, remarks, recorded_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        payments
    )

    # Reversal
    cur.execute(
        "INSERT INTO payment_reversals (reversal_id, payment_id, bill_id, reversal_reason, reversed_amount, reversed_at, reversed_by) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (1, 16, 9, 'Customer paid twice due to counter receipt slip misplacement. Reversal authorized by supervisor.', 546.25, '2026-10-06 14:30:00', 'admin.power')
    )
