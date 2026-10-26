# DBMS Mini Project: Viva Voce & Laboratory Exam Questions

### Electricity Billing and Consumption Management System
**Academic Reference Guide: 30 Important DBMS Viva Questions with Model Answers**

---

### Q1. What is the objective of this DBMS project?
**Answer:** The objective is to design, normalize, and implement a relational database system for an electricity distribution utility. The system manages electricity consumers, meter readings, progressive slab-based monthly billing, payment recording, and consumption analytics while enforcing business rules via foreign keys, triggers, stored procedures, and views in PostgreSQL.

---

### Q2. What is a Primary Key? Identify the primary keys in your project.
**Answer:** A Primary Key is a minimal set of attributes that uniquely identifies each tuple (record) in a relational table. It cannot contain `NULL` values and automatically creates a unique B-Tree index.
In this project:
- `consumers`: `consumer_id` (Surrogate Primary Key)
- `tariffs`: `tariff_id`
- `tariff_slabs`: `slab_id`
- `meter_readings`: `reading_id`
- `bills`: `bill_id`
- `bill_items`: `item_id`
- `payments`: `payment_id`
- `payment_reversals`: `reversal_id`
- `users`: `user_id`

---

### Q3. What is a Foreign Key? Give an example from your schema.
**Answer:** A Foreign Key is a column or set of columns in one table that references the Primary Key of another table, enforcing referential integrity.
**Example:** `bills.consumer_id` references `consumers(consumer_id)`. We configured this with `ON DELETE RESTRICT` so that a consumer with existing billing records cannot be accidentally deleted from the database.

---

### Q4. What is Database Normalization? What normal form does your schema satisfy?
**Answer:** Normalization is the formal process of organizing attributes and relations to minimize data redundancy and avoid update, insertion, and deletion anomalies.
Our schema satisfies **Third Normal Form (3NF)**:
1. **1NF:** All attribute values are atomic; no repeating groups.
2. **2NF:** It is in 1NF, and all non-prime attributes are fully functionally dependent on the entire primary key (no partial dependencies).
3. **3NF:** It is in 2NF, and no non-prime attribute is transitively dependent on the primary key ($X \rightarrow Y$ implies $X$ is a superkey or $Y$ is a prime attribute).

---

### Q5. Did you intentionally denormalize any part of your schema? Why?
**Answer:** Yes, in financial and billing applications, intentional controlled denormalization is an industry best practice known as an **Audit Snapshot**. In the `bills` and `bill_items` tables, we store the computed energy charge, fixed charge, tax, and itemized slab breakdown at the time of invoice generation.
If tariffs change next year (e.g., rate increases from ₹2 to ₹3.50/unit), historical bills already issued to customers must **remain unchanged**. Recalculating past bills on-the-fly from live tariff tables would corrupt historical accounting records.

---

### Q6. What are the ACID properties in DBMS? How are they enforced in your project?
**Answer:**
- **Atomicity:** All operations in a transaction succeed together or all are rolled back. When generating a bill, inserting the `bills` record, inserting multiple `bill_items`, and updating `meter_readings.is_billed = TRUE` are enclosed in a single transaction.
- **Consistency:** The database transitions from one valid state to another, respecting all constraints (e.g. `current_reading >= previous_reading`, `outstanding_amount = total_amount - amount_paid`).
- **Isolation:** Concurrent transactions execute without interfering. In payment recording, we use `SELECT ... FOR UPDATE` (Pessimistic Row-Level Locking) to prevent concurrent overpayments on the same bill.
- **Durability:** Committed transactions survive crashes via PostgreSQL's Write-Ahead Log (WAL).

---

### Q7. What is the difference between a Function and a Stored Procedure in PostgreSQL?
**Answer:**
- **Function (`CREATE FUNCTION`):** Always returns a value or table. It can be invoked directly inside SQL queries (`SELECT fn_calculate_units_consumed(100, 250);`). It cannot execute transaction control statements (`COMMIT` or `ROLLBACK`).
- **Stored Procedure (`CREATE PROCEDURE`):** Introduced in PostgreSQL 11, invoked using `CALL sp_record_payment(...)`. It does not return an expression value, but can manage transactions internally (`COMMIT` / `ROLLBACK`).

---

### Q8. What is a Database Trigger? Which triggers did you implement?
**Answer:** A trigger is a specialized procedural program that executes automatically in response to specified database events (`INSERT`, `UPDATE`, `DELETE`) on a table.
We implemented two key triggers:
1. `trg_validate_meter_reading` (BEFORE INSERT OR UPDATE on `meter_readings`): Validates that the consumer is active, readings are non-negative, current reading $\ge$ previous reading, and automatically computes `units_consumed = current_reading - previous_reading`.
2. `trg_update_bill_payment_status` (AFTER INSERT OR UPDATE on `payments`): Automatically sums all successful payments for that bill, subtracts from total amount to determine `outstanding_amount`, and sets `payment_status` to `PAID`, `PARTIALLY PAID`, or `UNPAID`.

---

### Q9. What is the difference between a BEFORE and AFTER trigger?
**Answer:**
- **BEFORE trigger:** Runs before the data is written to disk. Used for data validation, sanity checks, and transforming or calculating values on the `NEW` record (e.g. `NEW.units_consumed := NEW.current_reading - NEW.previous_reading`).
- **AFTER trigger:** Runs after the row change has been successfully staged in the table. Ideal for cascading updates or maintaining summary metrics across other tables (e.g. updating parent `bills` when child `payments` change).

---

### Q10. What are `NEW` and `OLD` in trigger functions?
**Answer:** They are pseudo-record variables automatically populated by PostgreSQL:
- `NEW`: Holds the state of the new row being inserted or updated (available in `INSERT` and `UPDATE` triggers).
- `OLD`: Holds the state of the existing row before modification or deletion (available in `UPDATE` and `DELETE` triggers).

---

### Q11. How does progressive tiered slab billing work? Explain with an example.
**Answer:** In progressive slab billing, electricity consumption is divided across successive volume brackets, each charged at a progressively higher unit rate.
**Example:** Consumption = 250 units under Domestic Tariff:
- Slab 1 (0 to 100 units): $100 \times ₹2.00 = ₹200.00$
- Slab 2 (101 to 200 units): $100 \times ₹3.00 = ₹300.00$
- Slab 3 (> 200 units): $50 \times ₹5.00 = ₹250.00$
- **Energy Charge Subtotal:** $₹200 + ₹300 + ₹250 = ₹750.00$
- **Fixed Maintenance Charge:** $₹100.00$
- **Electricity Duty / Tax (5%):** $₹37.50$
- **Total Invoiced Amount:** $₹887.50$

---

### Q12. What is a Database View? Why did you create `consumer_billing_summary`?
**Answer:** A View is a virtual table defined by a stored SQL query. It does not store physical data itself (unless materialized); it dynamically executes its underlying query upon access.
`consumer_billing_summary` was created to provide a consolidated summary of each consumer's total units consumed, billed amounts, paid amounts, and outstanding balances.

---

### Q13. What is the "Join Multiplication" or Cartesian duplication problem in views, and how did you resolve it?
**Answer:** When joining tables in a one-to-many relationship (Consumer $\rightarrow$ Bills $\rightarrow$ Payments), joining them naively produces duplicate rows. If a bill has 3 payments, joining bills to payments duplicates the bill total 3 times, tripling total billed revenue!
**Resolution:** We resolved this using **Common Table Expressions (CTEs)** that pre-aggregate payments and bills independently before joining to `consumers`:
```sql
WITH consumer_bills_agg AS (
    SELECT consumer_id, SUM(total_amount) AS total_billed, SUM(amount_paid) AS total_paid
    FROM bills GROUP BY consumer_id
)
SELECT c.*, ba.total_billed, ba.total_paid
FROM consumers c
LEFT JOIN consumer_bills_agg ba ON c.consumer_id = ba.consumer_id;
```

---

### Q14. What is a Database Index? What data structure does PostgreSQL use by default?
**Answer:** An Index is an auxiliary data structure that accelerates data retrieval on table columns without scanning the entire table sequentially (Sequential Scan vs Index Scan). PostgreSQL uses a self-balancing **B-Tree (Balanced Tree)** data structure by default, providing $O(\log n)$ search, insert, and delete complexity.

---

### Q15. Do Foreign Keys automatically create indexes in PostgreSQL?
**Answer:** No. While Primary Keys and Unique constraints automatically create unique B-Tree indexes, PostgreSQL does **not** automatically index foreign key columns. We explicitly created B-Tree indexes on all foreign keys (`meter_readings.consumer_id`, `bills.consumer_id`, `payments.bill_id`) to accelerate JOIN operations and cascade checks.

---

### Q16. What is the difference between `WHERE` and `HAVING`? Give an example.
**Answer:**
- `WHERE`: Filters individual rows **before** aggregation and grouping occurs.
- `HAVING`: Filters aggregated groups **after** the `GROUP BY` clause has been computed.
**Example:**
```sql
SELECT connection_type, AVG(units_consumed) AS avg_units
FROM meter_readings mr
JOIN consumers c ON mr.consumer_id = c.consumer_id
WHERE mr.reading_month = '2026-09' -- WHERE filters rows
GROUP BY connection_type
HAVING AVG(mr.units_consumed) > 150.0; -- HAVING filters groups
```

---

### Q17. What is the difference between `INNER JOIN` and `LEFT JOIN`?
**Answer:**
- `INNER JOIN`: Returns records that have matching values in both tables. Consumers with zero readings will be omitted.
- `LEFT OUTER JOIN`: Returns all records from the left table, and matching records from the right table. If there is no match, right-side columns contain `NULL` (e.g. consumers who have not yet received an invoice).

---

### Q18. What is a Subquery? What is the difference between a Scalar Subquery and a Correlated Subquery?
**Answer:** A subquery is a query nested inside another SQL statement.
- **Scalar Subquery:** Returns a single value (one row, one column). Example: finding bills with total amount higher than the system average: `WHERE total_amount > (SELECT AVG(total_amount) FROM bills)`.
- **Correlated Subquery:** Evaluates row-by-row because the inner query references attributes from the outer query row. Example: `WHERE EXISTS (SELECT 1 FROM bills b WHERE b.consumer_id = c.consumer_id)`.

---

### Q19. What is a Window Function in SQL? Which one did you use?
**Answer:** A Window Function performs calculations across a set of table rows that are related to the current row, without collapsing multiple rows into a single output row (unlike `GROUP BY`).
We used `DENSE_RANK() OVER (ORDER BY SUM(units_consumed) DESC)` in `v_top_consumers` to rank consumers by electricity consumption without skipping rank numbers when ties occur.

---

### Q20. What is SQL Injection, and how does your project prevent it?
**Answer:** SQL Injection is a security vulnerability where untrusted user input alters the intended SQL syntax.
We strictly prevent SQL Injection by using **Parameterized Queries** through `psycopg2` placeholders (`%s`). User input is transmitted separately from SQL code as typed parameters, so malicious strings (e.g. `' OR '1'='1`) are treated strictly as data literals, never executable code.

---

### Q21. How do you handle concurrent payments on the same bill to avoid race conditions?
**Answer:** We implement **Pessimistic Concurrency Control** using `SELECT ... FOR UPDATE`. When recording a payment, the database places an exclusive row-level lock on the target bill record. Any competing transaction attempting to update the same bill must wait until the first transaction commits or rolls back, guaranteeing the balance cannot be overpaid.

---

### Q22. Why do you use soft deactivation instead of `DELETE` on consumers?
**Answer:** If an electricity customer relocates or closes their connection, permanently executing `DELETE FROM consumers` would violate foreign key constraints on past meter readings, bills, and tax ledgers, or destroy the financial audit trail.
Instead, we set `account_status = 'INACTIVE'`. The consumer cannot receive new meter readings or bills, but all historical bills, receipts, and consumption analytics are fully preserved.

---

### Q23. What audit mechanism did you build for payment cancellations?
**Answer:** Financial accounting regulations prohibit hard deletion of payment records. Instead, we mark the payment status as `CANCELLED` and record an immutable entry in `payment_reversals` containing `payment_id`, `bill_id`, `reversed_amount`, `reversal_reason`, `reversed_at`, and `reversed_by`. The database trigger automatically recalculates the bill's outstanding balance.

---

### Q24. How is the consumption anomaly report implemented?
**Answer:** Using a Common Table Expression (CTE) that calculates each consumer's historical average consumption across past billing cycles. It then filters for consumers in the current billing cycle whose consumption exceeds 130% (a 30% surge) of their personal average:
```sql
WITH consumer_history AS (
    SELECT consumer_id, AVG(units_consumed) AS past_avg
    FROM meter_readings WHERE reading_month < '2026-10' GROUP BY consumer_id
)
SELECT c.consumer_number, mr.units_consumed, ch.past_avg
FROM meter_readings mr
JOIN consumer_history ch ON mr.consumer_id = ch.consumer_id
WHERE mr.reading_month = '2026-10' AND mr.units_consumed > (ch.past_avg * 1.30);
```

---

### Q25. What is the role of `pgAdmin 4` in your project?
**Answer:** `pgAdmin 4` is the GUI database administration tool for PostgreSQL. We use it to inspect table structures, manage relational constraints, execute practice queries in the Query Tool, monitor active connections, and visualize execution plans using `EXPLAIN ANALYZE`.

---

### Q26. What constraints did you use in your PostgreSQL tables?
**Answer:**
1. `PRIMARY KEY`: Unique identity and non-null enforcement.
2. `FOREIGN KEY`: Referential integrity linking tables.
3. `UNIQUE`: Ensures uniqueness of `consumer_number`, `meter_number`, and `(consumer_id, reading_month)`.
4. `CHECK`: Validates ranges (e.g. `previous_reading >= 0`, `current_reading >= previous_reading`, `account_status IN ('ACTIVE', 'INACTIVE')`).
5. `NOT NULL`: Prevents missing critical data.
6. `DEFAULT`: Provides automatic default values like `CURRENT_TIMESTAMP` and `'ACTIVE'`.

---

### Q27. What is `EXPLAIN ANALYZE` in PostgreSQL?
**Answer:** `EXPLAIN ANALYZE` causes PostgreSQL to execute a query and output the actual execution plan, showing total run time, memory used, join algorithm (Hash Join, Nested Loop, or Merge Join), and whether a **Seq Scan** (sequential scan) or **Index Scan** was utilized.

---

### Q28. What is the role of `psycopg2` in Python?
**Answer:** `psycopg2` is the PostgreSQL database adapter for Python. It implements Python Database API Specification v2.0 (PEP 249) and provides high performance, type conversion, connection pooling, and secure parameterized query execution.

---

### Q29. How are passwords secured in your application?
**Answer:** Passwords are never stored in plaintext. When an administrator or operator is registered, the password is encrypted using a cryptographic salt and one-way hashing algorithm (`scrypt` / `pbkdf2:sha256` via `werkzeug.security`). During login, `check_password_hash` verifies the hash against the submitted password.

---

### Q30. If this system scales to millions of consumers, what DBMS enhancements would you introduce?
**Answer:**
1. **Table Partitioning:** Declaratively partition `meter_readings` and `bills` by billing period (`reading_month` / `RANGE`).
2. **Read-Replica Replicas:** Route heavy analytical reports to PostgreSQL read-only replicas to relieve primary write servers.
3. **Connection Pooling:** Use PgBouncer to manage high-volume concurrent client database connections.
4. **Materialized Views:** Refresh heavy lifetime analytics periodically using `REFRESH MATERIALIZED VIEW CONCURRENTLY`.
