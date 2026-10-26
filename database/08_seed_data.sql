/*
================================================================================
  DBMS MINI PROJECT: ELECTRICITY BILLING AND CONSUMPTION MANAGEMENT SYSTEM
  SCRIPT 08: SEED DEMONSTRATION DATA
================================================================================
  Purpose:
    Populates the database with realistic, high-quality demonstration records:
    - 2 System Users (Admin & Billing Operator)
    - 3 Active Tariffs (Domestic, Commercial, Industrial) with Progressive Slabs
    - 18 Registered Electricity Consumers across diverse categories
    - Historical Meter Readings across 4 billing cycles (2026-07 to 2026-10)
    - Associated Bills, Itemized Slab Breakdowns, and Payment Transactions
    - Partial Payments, Unpaid Invoices, and Payment Reversals for Auditing

  Academic / Viva Note:
    - All mathematical calculations for units consumed, slab rates, fixed charges,
      and taxes adhere strictly to relational constraints and database triggers.
================================================================================
*/

-- -----------------------------------------------------------------------------
-- 1. SYSTEM USERS
-- -----------------------------------------------------------------------------
INSERT INTO users (username, password_hash, full_name, role, email) VALUES
('admin', 'scrypt:32768:8:1$NqVEoxTyINsyg12S$71c83c544fc495bf794a8859059b0cf24accf22f7d00cab8ff9fc1b3dd2a736c96ef9f19271d69d4482e393a85dd076cc70ac5e5d448aa061aa4f61d860bddcf', 'Chief Engineer Sharma', 'ADMIN', 'admin.power@utility.org'),
('operator', 'scrypt:32768:8:1$yLKx3Iaqhab5C39v$792c773ef2d446376305ec61c3a29434142aa25659bcea1176c697c3d6a3c993c90aad663ca9b7eb8546203d184afe97c043127e13c35cfdab9dfc3e9e23dee6', 'Kavitha Ramanathan', 'OPERATOR', 'kavitha.ops@utility.org')
ON CONFLICT (username) DO NOTHING;

-- -----------------------------------------------------------------------------
-- 2. TARIFF MASTER & PROGRESSIVE SLABS
-- -----------------------------------------------------------------------------
-- Tariff 1: Domestic Low-Tension Tariff (LT-1)
INSERT INTO tariffs (tariff_id, tariff_name, connection_type, fixed_charge, effective_from, is_active) VALUES
(1, 'Domestic Residential Standard (LT-1)', 'DOMESTIC', 100.00, '2026-01-01', TRUE)
ON CONFLICT (tariff_id) DO NOTHING;

INSERT INTO tariff_slabs (tariff_id, slab_number, min_units, max_units, rate_per_unit, slab_description) VALUES
(1, 1, 0, 100, 2.00, 'Slab 1: Lifeline Consumption (0 - 100 units)'),
(1, 2, 100, 200, 3.00, 'Slab 2: Normal Domestic (101 - 200 units)'),
(1, 3, 200, NULL, 5.00, 'Slab 3: Higher Domestic (> 200 units)')
ON CONFLICT (tariff_id, slab_number) DO NOTHING;

-- Tariff 2: Commercial Tariff (LT-2)
INSERT INTO tariffs (tariff_id, tariff_name, connection_type, fixed_charge, effective_from, is_active) VALUES
(2, 'Commercial Retail & Office (LT-2)', 'COMMERCIAL', 250.00, '2026-01-01', TRUE)
ON CONFLICT (tariff_id) DO NOTHING;

INSERT INTO tariff_slabs (tariff_id, slab_number, min_units, max_units, rate_per_unit, slab_description) VALUES
(2, 1, 0, 150, 4.50, 'Commercial Base (0 - 150 units)'),
(2, 2, 150, 300, 6.50, 'Commercial Mid-Tier (151 - 300 units)'),
(2, 3, 300, NULL, 8.50, 'Commercial Heavy Tier (> 300 units)')
ON CONFLICT (tariff_id, slab_number) DO NOTHING;

-- Tariff 3: Industrial High Tension (HT-1)
INSERT INTO tariffs (tariff_id, tariff_name, connection_type, fixed_charge, effective_from, is_active) VALUES
(3, 'Industrial Manufacturing (HT-1)', 'INDUSTRIAL', 600.00, '2026-01-01', TRUE)
ON CONFLICT (tariff_id) DO NOTHING;

INSERT INTO tariff_slabs (tariff_id, slab_number, min_units, max_units, rate_per_unit, slab_description) VALUES
(3, 1, 0, 500, 7.00, 'Industrial Baseline (0 - 500 units)'),
(3, 2, 500, NULL, 9.50, 'Industrial High Draw (> 500 units)')
ON CONFLICT (tariff_id, slab_number) DO NOTHING;

-- Reset sequence for tariffs and slabs
SELECT setval('tariffs_tariff_id_seq', (SELECT MAX(tariff_id) FROM tariffs));
SELECT setval('tariff_slabs_slab_id_seq', (SELECT MAX(slab_id) FROM tariff_slabs));

-- -----------------------------------------------------------------------------
-- 3. REGISTERED CONSUMERS (18 Consumers across types)
-- -----------------------------------------------------------------------------
INSERT INTO consumers (consumer_id, consumer_number, full_name, address, city, phone_number, email, meter_number, connection_type, connection_date, account_status) VALUES
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
ON CONFLICT (consumer_id) DO NOTHING;

SELECT setval('consumers_consumer_id_seq', (SELECT MAX(consumer_id) FROM consumers));

-- -----------------------------------------------------------------------------
-- 4. METER READINGS (Multiple Billing Periods: July, Aug, Sep, Oct 2026)
-- -----------------------------------------------------------------------------
-- July 2026 Readings (Period 2026-07)
INSERT INTO meter_readings (reading_id, consumer_id, reading_month, previous_reading, current_reading, units_consumed, reading_date, is_billed) VALUES
(1,  1,  '2026-07', 1200.00, 1340.00, 140.00, '2026-07-31', TRUE),
(2,  2,  '2026-07',  850.00,  940.00,  90.00, '2026-07-31', TRUE),
(3,  3,  '2026-07', 2100.00, 2350.00, 250.00, '2026-07-31', TRUE),
(4,  4,  '2026-07', 1500.00, 1680.00, 180.00, '2026-07-31', TRUE),
(5,  12, '2026-07', 4500.00, 4850.00, 350.00, '2026-07-31', TRUE),
(6,  16, '2026-07', 8900.00, 9750.00, 850.00, '2026-07-31', TRUE);

-- August 2026 Readings (Period 2026-08)
INSERT INTO meter_readings (reading_id, consumer_id, reading_month, previous_reading, current_reading, units_consumed, reading_date, is_billed) VALUES
(7,  1,  '2026-08', 1340.00, 1500.00, 160.00, '2026-08-31', TRUE),
(8,  2,  '2026-08',  940.00, 1025.00,  85.00, '2026-08-31', TRUE),
(9,  3,  '2026-08', 2350.00, 2630.00, 280.00, '2026-08-31', TRUE),
(10, 4,  '2026-08', 1680.00, 1870.00, 190.00, '2026-08-31', TRUE),
(11, 12, '2026-08', 4850.00, 5260.00, 410.00, '2026-08-31', TRUE),
(12, 16, '2026-08', 9750.00, 10700.00, 950.00, '2026-08-31', TRUE);

-- September 2026 Readings (Period 2026-09)
INSERT INTO meter_readings (reading_id, consumer_id, reading_month, previous_reading, current_reading, units_consumed, reading_date, is_billed) VALUES
(13, 1,  '2026-09', 1500.00, 1675.00, 175.00, '2026-09-30', TRUE),
(14, 2,  '2026-09', 1025.00, 1120.00,  95.00, '2026-09-30', TRUE),
(15, 3,  '2026-09', 2630.00, 2940.00, 310.00, '2026-09-30', TRUE),
(16, 4,  '2026-09', 1870.00, 2085.00, 215.00, '2026-09-30', TRUE),
(17, 5,  '2026-09',  600.00,  730.00, 130.00, '2026-09-30', TRUE),
(18, 6,  '2026-09', 1100.00, 1260.00, 160.00, '2026-09-30', TRUE),
(19, 7,  '2026-09',  450.00,  530.00,  80.00, '2026-09-30', TRUE),
(20, 8,  '2026-09',  800.00,  990.00, 190.00, '2026-09-30', TRUE),
(21, 9,  '2026-09',  950.00, 1110.00, 160.00, '2026-09-30', TRUE),
(22, 10, '2026-09', 1300.00, 1540.00, 240.00, '2026-09-30', TRUE),
(23, 12, '2026-09', 5260.00, 5690.00, 430.00, '2026-09-30', TRUE),
(24, 13, '2026-09', 3100.00, 3380.00, 280.00, '2026-09-30', TRUE),
(25, 14, '2026-09', 2200.00, 2390.00, 190.00, '2026-09-30', TRUE),
(26, 15, '2026-09', 4100.00, 4620.00, 520.00, '2026-09-30', TRUE),
(27, 16, '2026-09', 10700.00, 11800.00, 1100.00, '2026-09-30', TRUE),
(28, 17, '2026-09', 7500.00, 8350.00, 850.00, '2026-09-30', TRUE),
(29, 18, '2026-09', 6200.00, 6920.00, 720.00, '2026-09-30', TRUE);

-- October 2026 Readings (Period 2026-10) - Recent / Unbilled mix for live demonstration
INSERT INTO meter_readings (reading_id, consumer_id, reading_month, previous_reading, current_reading, units_consumed, reading_date, is_billed) VALUES
(30, 1,  '2026-10', 1675.00, 1865.00, 190.00, '2026-10-25', TRUE),
(31, 2,  '2026-10', 1120.00, 1205.00,  85.00, '2026-10-25', TRUE),
(32, 3,  '2026-10', 2940.00, 3420.00, 480.00, '2026-10-25', TRUE), -- Anomaly spike!
(33, 4,  '2026-10', 2085.00, 2315.00, 230.00, '2026-10-25', TRUE),
(34, 5,  '2026-10',  730.00,  890.00, 160.00, '2026-10-25', FALSE), -- Pending unbilled
(35, 6,  '2026-10', 1260.00, 1435.00, 175.00, '2026-10-25', FALSE), -- Pending unbilled
(36, 12, '2026-10', 5690.00, 6150.00, 460.00, '2026-10-25', TRUE),
(37, 16, '2026-10', 11800.00, 13150.00, 1350.00, '2026-10-25', TRUE);

SELECT setval('meter_readings_reading_id_seq', (SELECT MAX(reading_id) FROM meter_readings));

-- -----------------------------------------------------------------------------
-- 5. GENERATED BILLS (Accurate Progressive Math Snapshots)
-- -----------------------------------------------------------------------------
-- Bill 1: Consumer 1, July (140 units Domestic: 100*2 + 40*3 = 320 energy + 100 fixed + 16 tax = ₹436.00)
INSERT INTO bills (bill_id, bill_number, consumer_id, meter_reading_id, billing_period, units_consumed, energy_charge, fixed_charge, tax_amount, total_amount, amount_paid, outstanding_amount, bill_date, due_date, payment_status) VALUES
(1, 'BILL-202607-0001', 1, 1, '2026-07', 140.00, 320.00, 100.00, 16.00, 436.00, 436.00, 0.00, '2026-08-01', '2026-08-16', 'PAID'),
-- Bill 2: Consumer 2, July (90 units Domestic: 90*2 = 180 energy + 100 fixed + 0 tax = ₹280.00)
(2, 'BILL-202607-0002', 2, 2, '2026-07', 90.00, 180.00, 100.00, 0.00, 280.00, 280.00, 0.00, '2026-08-01', '2026-08-16', 'PAID'),
-- Bill 3: Consumer 3, July (250 units Domestic: 100*2 + 100*3 + 50*5 = 750 energy + 100 fixed + 37.50 tax = ₹887.50)
(3, 'BILL-202607-0003', 3, 3, '2026-07', 250.00, 750.00, 100.00, 37.50, 887.50, 887.50, 0.00, '2026-08-01', '2026-08-16', 'PAID'),
-- Bill 4: Consumer 12, July (Commercial 350 units: 150*4.5 + 150*6.5 + 50*8.5 = 675 + 975 + 425 = 2075 energy + 250 fixed + 103.75 tax = ₹2428.75)
(4, 'BILL-202607-0004', 12, 5, '2026-07', 350.00, 2075.00, 250.00, 103.75, 2428.75, 2428.75, 0.00, '2026-08-01', '2026-08-16', 'PAID'),

-- August Bills
(5, 'BILL-202608-0001', 1, 7, '2026-08', 160.00, 380.00, 100.00, 19.00, 499.00, 499.00, 0.00, '2026-09-01', '2026-09-16', 'PAID'),
(6, 'BILL-202608-0002', 2, 8, '2026-08', 85.00, 170.00, 100.00, 0.00, 270.00, 270.00, 0.00, '2026-09-01', '2026-09-16', 'PAID'),
(7, 'BILL-202608-0003', 3, 9, '2026-08', 280.00, 900.00, 100.00, 45.00, 1045.00, 1045.00, 0.00, '2026-09-01', '2026-09-16', 'PAID'),
(8, 'BILL-202608-0004', 12, 11, '2026-08', 410.00, 2585.00, 250.00, 129.25, 2964.25, 2964.25, 0.00, '2026-09-01', '2026-09-16', 'PAID'),

-- September Bills
(9,  'BILL-202609-0001', 1,  13, '2026-09', 175.00,  425.00, 100.00,  21.25,  546.25, 546.25,    0.00, '2026-10-01', '2026-10-16', 'PAID'),
(10, 'BILL-202609-0002', 2,  14, '2026-09',  95.00,  190.00, 100.00,   0.00,  290.00, 290.00,    0.00, '2026-10-01', '2026-10-16', 'PAID'),
(11, 'BILL-202609-0003', 3,  15, '2026-09', 310.00, 1050.00, 100.00,  52.50, 1202.50, 600.00,  602.50, '2026-10-01', '2026-10-16', 'PARTIALLY PAID'),
(12, 'BILL-202609-0004', 4,  16, '2026-09', 215.00,  575.00, 100.00,  28.75,  703.75,   0.00,  703.75, '2026-10-01', '2026-10-16', 'UNPAID'),
(13, 'BILL-202609-0005', 12, 23, '2026-09', 430.00, 2755.00, 250.00, 137.75, 3142.75, 3142.75,    0.00, '2026-10-01', '2026-10-16', 'PAID'),
(14, 'BILL-202609-0006', 16, 27, '2026-09', 1100.00, 9200.00, 600.00, 460.00, 10260.00, 10260.00,  0.00, '2026-10-01', '2026-10-16', 'PAID'),

-- October Bills (Latest billing cycle)
(15, 'BILL-202610-0001', 1,  30, '2026-10', 190.00,  470.00, 100.00,  23.50,  593.50,   0.00,  593.50, '2026-10-25', '2026-11-10', 'UNPAID'),
(16, 'BILL-202610-0002', 2,  31, '2026-10',  85.00,  170.00, 100.00,   0.00,  270.00, 270.00,    0.00, '2026-10-25', '2026-11-10', 'PAID'),
(17, 'BILL-202610-0003', 3,  32, '2026-10', 480.00, 1900.00, 100.00,  95.00, 2095.00,   0.00, 2095.00, '2026-10-25', '2026-11-10', 'UNPAID'),
(18, 'BILL-202610-0004', 12, 36, '2026-10', 460.00, 3010.00, 250.00, 150.50, 3410.50, 1500.00, 1910.50, '2026-10-25', '2026-11-10', 'PARTIALLY PAID'),
(19, 'BILL-202610-0005', 16, 37, '2026-10', 1350.00, 11575.00, 600.00, 578.75, 12753.75, 0.00, 12753.75, '2026-10-25', '2026-11-10', 'UNPAID')
ON CONFLICT (bill_id) DO NOTHING;

SELECT setval('bills_bill_id_seq', (SELECT MAX(bill_id) FROM bills));

-- -----------------------------------------------------------------------------
-- 6. BILL ITEMS (Progressive Slab Breakdown Snapshots)
-- -----------------------------------------------------------------------------
-- Line items for Bill 1 (140 units)
INSERT INTO bill_items (bill_id, item_type, description, units, rate, amount) VALUES
(1, 'SLAB_CHARGE',  'Slab 1 (0 - 100 units @ ₹2.00)', 100.00, 2.00, 200.00),
(1, 'SLAB_CHARGE',  'Slab 2 (101 - 200 units @ ₹3.00)', 40.00, 3.00, 120.00),
(1, 'FIXED_CHARGE', 'Monthly Standing Meter Rent & Maintenance Charge', 0.00, 0.00, 100.00),
(1, 'TAX',          'Electricity Duty & Regulatory Surcharge (5%)', 0.00, 5.00, 16.00);

-- Line items for Bill 3 (250 units)
INSERT INTO bill_items (bill_id, item_type, description, units, rate, amount) VALUES
(3, 'SLAB_CHARGE',  'Slab 1 (0 - 100 units @ ₹2.00)', 100.00, 2.00, 200.00),
(3, 'SLAB_CHARGE',  'Slab 2 (101 - 200 units @ ₹3.00)', 100.00, 3.00, 300.00),
(3, 'SLAB_CHARGE',  'Slab 3 (> 200 units @ ₹5.00)', 50.00, 5.00, 250.00),
(3, 'FIXED_CHARGE', 'Monthly Standing Meter Rent & Maintenance Charge', 0.00, 0.00, 100.00),
(3, 'TAX',          'Electricity Duty & Regulatory Surcharge (5%)', 0.00, 5.00, 37.50);

-- Line items for Bill 15 (190 units)
INSERT INTO bill_items (bill_id, item_type, description, units, rate, amount) VALUES
(15, 'SLAB_CHARGE',  'Slab 1 (0 - 100 units @ ₹2.00)', 100.00, 2.00, 200.00),
(15, 'SLAB_CHARGE',  'Slab 2 (101 - 200 units @ ₹3.00)', 90.00, 3.00, 270.00),
(15, 'FIXED_CHARGE', 'Monthly Standing Meter Rent & Maintenance Charge', 0.00, 0.00, 100.00),
(15, 'TAX',          'Electricity Duty & Regulatory Surcharge (5%)', 0.00, 5.00, 23.50);

-- Line items for Bill 16 (85 units)
INSERT INTO bill_items (bill_id, item_type, description, units, rate, amount) VALUES
(16, 'SLAB_CHARGE',  'Slab 1 (0 - 100 units @ ₹2.00)', 85.00, 2.00, 170.00),
(16, 'FIXED_CHARGE', 'Monthly Standing Meter Rent & Maintenance Charge', 0.00, 0.00, 100.00);

-- Line items for Bill 17 (480 units)
INSERT INTO bill_items (bill_id, item_type, description, units, rate, amount) VALUES
(17, 'SLAB_CHARGE',  'Slab 1 (0 - 100 units @ ₹2.00)', 100.00, 2.00, 200.00),
(17, 'SLAB_CHARGE',  'Slab 2 (101 - 200 units @ ₹3.00)', 100.00, 3.00, 300.00),
(17, 'SLAB_CHARGE',  'Slab 3 (> 200 units @ ₹5.00)', 280.00, 5.00, 1400.00),
(17, 'FIXED_CHARGE', 'Monthly Standing Meter Rent & Maintenance Charge', 0.00, 0.00, 100.00),
(17, 'TAX',          'Electricity Duty & Regulatory Surcharge (5%)', 0.00, 5.00, 95.00);

-- -----------------------------------------------------------------------------
-- 7. PAYMENTS LEDGER (Cash, UPI, Bank Transfer)
-- -----------------------------------------------------------------------------
INSERT INTO payments (payment_id, bill_id, payment_reference, payment_date, amount_paid, payment_method, payment_status, remarks, recorded_by) VALUES
(1,  1,  'RCPT-20260805-0001', '2026-08-05 10:30:00+05:30', 436.00,   'UPI',           'SUCCESS',   'UPI ref: 621893821092', 'kavitha.ops'),
(2,  2,  'RCPT-20260807-0002', '2026-08-07 14:15:00+05:30', 280.00,   'CASH',          'SUCCESS',   'Counter cash counter 2', 'kavitha.ops'),
(3,  3,  'RCPT-20260810-0003', '2026-08-10 11:00:00+05:30', 887.50,   'NET_BANKING',   'SUCCESS',   'SBI NetBanking ref 882910', 'system'),
(4,  4,  'RCPT-20260812-0004', '2026-08-12 16:45:00+05:30', 2428.75,  'BANK_TRANSFER', 'SUCCESS',   'NEFT / RTGS HDFC0099', 'system'),
(5,  5,  'RCPT-20260906-0001', '2026-09-06 09:20:00+05:30', 499.00,   'UPI',           'SUCCESS',   'GPay ref: 9021882711', 'kavitha.ops'),
(6,  6,  'RCPT-20260908-0002', '2026-09-08 12:10:00+05:30', 270.00,   'CASH',          'SUCCESS',   'Counter payment', 'kavitha.ops'),
(7,  7,  'RCPT-20260912-0003', '2026-09-12 15:30:00+05:30', 1045.00,  'UPI',           'SUCCESS',   'PhonePe ref: 77263541', 'kavitha.ops'),
(8,  8,  'RCPT-20260914-0004', '2026-09-14 17:00:00+05:30', 2964.25,  'BANK_TRANSFER', 'SUCCESS',   'Corporate NEFT transfer', 'system'),
(9,  9,  'RCPT-20261005-0001', '2026-10-05 10:15:00+05:30', 546.25,   'UPI',           'SUCCESS',   'UPI ref: 8829102983', 'kavitha.ops'),
(10, 10, 'RCPT-20261007-0002', '2026-10-07 11:45:00+05:30', 290.00,   'CASH',          'SUCCESS',   'Counter cash', 'kavitha.ops'),
(11, 11, 'RCPT-20261010-0003', '2026-10-10 14:00:00+05:30', 600.00,   'UPI',           'SUCCESS',   'Partial installment payment', 'kavitha.ops'),
(12, 13, 'RCPT-20261012-0004', '2026-10-12 16:30:00+05:30', 3142.75,  'BANK_TRANSFER', 'SUCCESS',   'Full settlement via RTGS', 'system'),
(13, 14, 'RCPT-20261014-0005', '2026-10-14 11:20:00+05:30', 10260.00, 'BANK_TRANSFER', 'SUCCESS',   'Industrial monthly settlement', 'system'),
(14, 16, 'RCPT-20261025-0001', '2026-10-25 15:10:00+05:30', 270.00,   'UPI',           'SUCCESS',   'Instant UPI payment', 'kavitha.ops'),
(15, 18, 'RCPT-20261025-0002', '2026-10-25 16:00:00+05:30', 1500.00,  'CASH',          'SUCCESS',   'First installment partial cash', 'kavitha.ops')
ON CONFLICT (payment_id) DO NOTHING;

SELECT setval('payments_payment_id_seq', (SELECT MAX(payment_id) FROM payments));

-- -----------------------------------------------------------------------------
-- 8. DEMONSTRATION PAYMENT REVERSAL (Audit Trail Test Record)
-- -----------------------------------------------------------------------------
-- Simulate an erroneous double-payment that was audited and cancelled:
INSERT INTO payments (payment_id, bill_id, payment_reference, payment_date, amount_paid, payment_method, payment_status, remarks, recorded_by) VALUES
(16, 9, 'RCPT-20261006-9999', '2026-10-06 12:00:00+05:30', 546.25, 'CASH', 'CANCELLED', 'Duplicate entry recorded by mistake at counter', 'kavitha.ops')
ON CONFLICT (payment_id) DO NOTHING;

INSERT INTO payment_reversals (reversal_id, payment_id, bill_id, reversal_reason, reversed_amount, reversed_at, reversed_by) VALUES
(1, 16, 9, 'Customer paid twice due to counter receipt slip misplacement. Reversal authorized by supervisor.', 546.25, '2026-10-06 14:30:00+05:30', 'admin.power')
ON CONFLICT (reversal_id) DO NOTHING;

SELECT setval('payments_payment_id_seq', (SELECT MAX(payment_id) FROM payments));
SELECT setval('payment_reversals_reversal_id_seq', (SELECT MAX(reversal_id) FROM payment_reversals));
