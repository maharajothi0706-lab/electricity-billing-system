/*
================================================================================
  DBMS MINI PROJECT: ELECTRICITY BILLING AND CONSUMPTION MANAGEMENT SYSTEM
  SCRIPT 01: DATABASE CREATION
================================================================================
  Purpose:
    This script contains the SQL command required to create the main database
    for the Electricity Billing and Consumption Management System.
    
  Academic / Viva Note:
    - In PostgreSQL, CREATE DATABASE cannot run inside a multi-statement
      transaction block (BEGIN ... COMMIT). It must be run separately as an
      independent administrative command, either via psql or pgAdmin 4.
    - Default character encoding UTF8 is recommended for international standard
      text support and compatibility.
================================================================================
*/

-- Terminate active connections before dropping (Safe demonstration only)
-- Note: Run the following in pgAdmin query tool connected to the 'postgres' default database:

-- Disconnect any active sessions connected to electricity_billing_db (if re-creating)
/*
SELECT pg_terminate_backend(pg_stat_activity.pid)
FROM pg_stat_activity
WHERE pg_stat_activity.datname = 'electricity_billing_db'
  AND pid <> pg_backend_pid();
*/

-- Step 1: Drop the database if it already exists (Uncomment only if performing clean reset)
-- DROP DATABASE IF EXISTS electricity_billing_db;

-- Step 2: Create the target database with UTF-8 character encoding
CREATE DATABASE electricity_billing_db
    WITH 
    OWNER = postgres
    ENCODING = 'UTF8'
    LC_COLLATE = 'English_United States.1252'
    LC_CTYPE = 'English_United States.1252'
    TABLESPACE = pg_default
    CONNECTION LIMIT = -1;

-- Add documentation comment directly on the database catalog object
COMMENT ON DATABASE electricity_billing_db IS 
'Central database for the Electricity Billing and Consumption Management System DBMS mini project.';

/*
How to connect to this database:
  - In psql command line:
      \c electricity_billing_db
  - In pgAdmin 4:
      Expand Servers -> Databases -> Right-click electricity_billing_db -> Query Tool
  - In Python psycopg2:
      psycopg2.connect(dbname="electricity_billing_db", user="postgres", password="...", host="localhost", port=5432)
*/
