# Password

---

## 📋 Short Description

### Style 1: Conceptual Summary
This table stores login credentials for people — one row per person (19,972 records, 1:1 with Person). It captures the hashed password (PasswordHash), the salt used for hashing (PasswordSalt), and links to the person via BusinessEntityID → Person. This is a security/authentication table — it does NOT store plaintext passwords. Every person in the system has exactly one password record.

### Style 2: Query Possibilities & Business Story
This is the authentication credentials table — every person in the system has a corresponding password record here for login purposes. The passwords are stored as salted hashes (not plaintext), making this table primarily useful for security audits and account management rather than direct querying of passwords. Use this table to answer questions like:

- "Does every person have a password on file?" (data completeness check)
- "Are there people without a password record?" (LEFT JOIN from Person)
- "When was a specific person's password last modified?"
- "How many passwords haven't been changed in over a year?"
- "Which person types (employees, customers, etc.) have password records?"
- "Are there any duplicate password hashes?" (security audit — shouldn't happen with unique salts)
- "What's the distribution of password last-modified dates — are people updating regularly?"
- "Which employees haven't changed their password recently?" (with Employee)
- "Do all active employees have current passwords?" (with Employee.CurrentFlag)
- "Cross-reference password modification dates with employee hire dates — did they change their default password?"

This is a simple 1:1 extension of Person with no child tables. Its value is in account management and security compliance, not business analytics.

### Style 3: Grouped & Complete (Column Reference)
This table stores one row per person (19,972 rows — 1:1 with Person), containing 5 columns organized as:

- **Identifier:** BusinessEntityID (PK, FK → Person — same ID as the person)
- **Credentials:** PasswordHash (salted hash of the password), PasswordSalt (unique salt used in hashing)
- **System:** rowguid (unique GUID)
- **Audit:** ModifiedDate (last time password was created/changed)

---

## 📖 Extensive Description

### Purpose & Business Context

Password is a simple 1:1 security table storing authentication credentials for all 19,972 people in the system. It exists separately from Person for security isolation — access to the Person table (names, emails, demographics) can be granted without exposing password data.

The table uses a salted hash approach: each person has a unique PasswordSalt, and the actual password is hashed with this salt before storage. This means:
- Passwords cannot be reverse-engineered from the hash
- Even if two people use the same password, their hashes will differ (different salts)
- The only way to verify a password is to hash the input with the stored salt and compare

With exactly 19,972 rows matching Person's 19,972 rows, the coverage is complete — every person has a credential record. The ModifiedDate column is the most analytically useful field, enabling password age analysis and compliance reporting.

### Key Business Logic

- **1:1 relationship with Person** — BusinessEntityID is both PK and FK to Person; every person has exactly one password
- **PasswordHash** is a one-way cryptographic hash — cannot be reversed to get the plaintext password
- **PasswordSalt** is unique per person — ensures identical passwords produce different hashes
- **ModifiedDate** = when the password was last set or changed — key for password rotation policies
- **No password complexity or history** is stored — only the current hash
- **19,972 rows = 19,972 Person rows** — complete coverage, no orphans expected
- This table has **no child tables** and **no business data** — it's purely for authentication

### Relationships

| Direction | Table | Join Key | Notes |
|-----------|-------|----------|-------|
| → Parent | Person → BusinessEntity | BusinessEntityID | The person this password belongs to |
| ← Via Person | Employee | BusinessEntityID | Employee credentials |
| ← Via Person | Customer (via PersonID) | BusinessEntityID | Customer credentials |
| ← Via Person | EmailAddress | BusinessEntityID | Person's email (login ID candidate) |
| ← Via Person → Employee | EmployeeDepartmentHistory → Department | BusinessEntityID | Employee's department |
| Sibling (1:1) | Person | BusinessEntityID | Name, type, contact info |

---

## 🔗 10 NL → SQL Examples

### Join-Heavy Queries (5)

---

**Q1: "For each person, show their full name, person type, email address, password last modified date, and whether their password is older than 1 year."**

*4 joins: Password → Person → EmailAddress*

```sql
SELECT
    per.FirstName || ' ' || per.LastName AS FullName,
    per.PersonType,
    CASE per.PersonType
        WHEN 'EM' THEN 'Employee'
        WHEN 'SP' THEN 'Sales Person'
        WHEN 'IN' THEN 'Individual Customer'
        WHEN 'SC' THEN 'Store Contact'
        WHEN 'VC' THEN 'Vendor Contact'
        WHEN 'GC' THEN 'General Contact'
    END AS PersonTypeLabel,
    ea.EmailAddress,
    pwd.ModifiedDate AS PasswordLastChanged,
    CAST(JULIANDAY('now') - JULIANDAY(pwd.ModifiedDate) AS INTEGER) AS DaysSinceChange,
    CASE
        WHEN JULIANDAY('now') - JULIANDAY(pwd.ModifiedDate) > 365 THEN 'EXPIRED (>1 year)'
        WHEN JULIANDAY('now') - JULIANDAY(pwd.ModifiedDate) > 180 THEN 'AGING (>6 months)'
        ELSE 'CURRENT'
    END AS PasswordStatus
FROM Password pwd
JOIN Person per ON pwd.BusinessEntityID = per.BusinessEntityID
LEFT JOIN EmailAddress ea ON per.BusinessEntityID = ea.BusinessEntityID
ORDER BY DaysSinceChange DESC;
```

---

**Q2: "For all employees, show their name, job title, department, shift, hire date, password last changed date, and flag those who haven't changed their password since they were hired."**

*7 joins: Password → Person → Employee → EmployeeDepartmentHistory → Department → Shift*

```sql
SELECT
    per.FirstName || ' ' || per.LastName AS EmployeeName,
    e.JobTitle,
    d.Name AS Department,
    sh.Name AS Shift,
    e.HireDate,
    pwd.ModifiedDate AS PasswordLastChanged,
    CAST(JULIANDAY('now') - JULIANDAY(pwd.ModifiedDate) AS INTEGER) AS DaysSincePasswordChange,
    CASE
        WHEN DATE(pwd.ModifiedDate) <= DATE(e.HireDate) THEN 'NEVER CHANGED (still default)'
        ELSE 'Changed after hire'
    END AS PasswordChangeStatus
FROM Password pwd
JOIN Person per ON pwd.BusinessEntityID = per.BusinessEntityID
JOIN Employee e ON per.BusinessEntityID = e.BusinessEntityID
JOIN EmployeeDepartmentHistory edh ON e.BusinessEntityID = edh.BusinessEntityID
    AND edh.EndDate IS NULL
JOIN Department d ON edh.DepartmentID = d.DepartmentID
JOIN Shift sh ON edh.ShiftID = sh.ShiftID
WHERE e.CurrentFlag = 1
ORDER BY DaysSincePasswordChange DESC;
```

---

**Q3: "For salespersons, show their name, territory, total sales revenue, password last modified date, and their email — highlighting those with stale passwords who handle high revenue."**

*8 joins: Password → Person → Employee → SalesPerson → SalesTerritory → SalesOrderHeader → EmailAddress*

```sql
SELECT
    per.FirstName || ' ' || per.LastName AS SalesPersonName,
    st.Name AS Territory,
    ea.EmailAddress,
    pwd.ModifiedDate AS PasswordLastChanged,
    CAST(JULIANDAY('now') - JULIANDAY(pwd.ModifiedDate) AS INTEGER) AS PasswordAgeDays,
    COUNT(DISTINCT soh.SalesOrderID) AS TotalOrders,
    ROUND(SUM(soh.TotalDue), 2) AS TotalRevenue,
    CASE
        WHEN JULIANDAY('now') - JULIANDAY(pwd.ModifiedDate) > 365
            AND SUM(soh.TotalDue) > 1000000
        THEN 'HIGH RISK — stale password + high revenue'
        WHEN JULIANDAY('now') - JULIANDAY(pwd.ModifiedDate) > 365
        THEN 'STALE PASSWORD'
        ELSE 'OK'
    END AS SecurityRisk
FROM Password pwd
JOIN Person per ON pwd.BusinessEntityID = per.BusinessEntityID
JOIN Employee e ON per.BusinessEntityID = e.BusinessEntityID
JOIN SalesPerson sp ON e.BusinessEntityID = sp.BusinessEntityID
LEFT JOIN SalesTerritory st ON sp.TerritoryID = st.TerritoryID
LEFT JOIN EmailAddress ea ON per.BusinessEntityID = ea.BusinessEntityID
LEFT JOIN SalesOrderHeader soh ON sp.BusinessEntityID = soh.SalesPersonID
GROUP BY per.FirstName, per.LastName, st.Name, ea.EmailAddress,
         pwd.ModifiedDate
ORDER BY SecurityRisk DESC, TotalRevenue DESC;
```

---

**Q4: "For employees who approve purchase orders, show their name, department, password age, total PO value they've approved, and the vendors they deal with — flag high-value approvers with old passwords."**

*9 joins: Password → Person → Employee → EmployeeDepartmentHistory → Department → PurchaseOrderHeader → Vendor → EmailAddress*

```sql
SELECT
    per.FirstName || ' ' || per.LastName AS ApproverName,
    e.JobTitle,
    d.Name AS Department,
    ea.EmailAddress,
    pwd.ModifiedDate AS PasswordLastChanged,
    CAST(JULIANDAY('now') - JULIANDAY(pwd.ModifiedDate) AS INTEGER) AS PasswordAgeDays,
    COUNT(DISTINCT poh.PurchaseOrderID) AS POsApproved,
    ROUND(SUM(poh.TotalDue), 2) AS TotalPOValue,
    COUNT(DISTINCT poh.VendorID) AS UniqueVendors,
    GROUP_CONCAT(DISTINCT v.Name) AS VendorNames,
    CASE
        WHEN JULIANDAY('now') - JULIANDAY(pwd.ModifiedDate) > 180
            AND SUM(poh.TotalDue) > 500000
        THEN 'HIGH RISK — financial authority + stale password'
        ELSE 'OK'
    END AS RiskFlag
FROM Password pwd
JOIN Person per ON pwd.BusinessEntityID = per.BusinessEntityID
JOIN Employee e ON per.BusinessEntityID = e.BusinessEntityID
JOIN EmployeeDepartmentHistory edh ON e.BusinessEntityID = edh.BusinessEntityID
    AND edh.EndDate IS NULL
JOIN Department d ON edh.DepartmentID = d.DepartmentID
LEFT JOIN EmailAddress ea ON per.BusinessEntityID = ea.BusinessEntityID
LEFT JOIN PurchaseOrderHeader poh ON e.BusinessEntityID = poh.EmployeeID
LEFT JOIN Vendor v ON poh.VendorID = v.BusinessEntityID
GROUP BY per.FirstName, per.LastName, e.JobTitle, d.Name, ea.EmailAddress, pwd.ModifiedDate
HAVING COUNT(DISTINCT poh.PurchaseOrderID) > 0
ORDER BY RiskFlag DESC, TotalPOValue DESC;
```

---

**Q5: "Show all vendor contacts and store contacts with their name, contact role, entity name, entity address (city/country), and their password last changed date."**

*10 joins: Password → Person → BusinessEntityContact → ContactType → Store/Vendor → BusinessEntityAddress → Address → StateProvince → CountryRegion*

```sql
SELECT
    per.FirstName || ' ' || per.LastName AS ContactName,
    per.PersonType,
    ct.Name AS ContactRole,
    COALESCE(s.Name, v.Name) AS EntityName,
    CASE
        WHEN s.BusinessEntityID IS NOT NULL THEN 'Store'
        WHEN v.BusinessEntityID IS NOT NULL THEN 'Vendor'
        ELSE 'Other'
    END AS EntityType,
    a.City,
    cr.Name AS Country,
    pwd.ModifiedDate AS PasswordLastChanged,
    CAST(JULIANDAY('now') - JULIANDAY(pwd.ModifiedDate) AS INTEGER) AS PasswordAgeDays
FROM Password pwd
JOIN Person per ON pwd.BusinessEntityID = per.BusinessEntityID
JOIN BusinessEntityContact bec ON per.BusinessEntityID = bec.PersonID
JOIN ContactType ct ON bec.ContactTypeID = ct.ContactTypeID
LEFT JOIN Store s ON bec.BusinessEntityID = s.BusinessEntityID
LEFT JOIN Vendor v ON bec.BusinessEntityID = v.BusinessEntityID
LEFT JOIN BusinessEntityAddress bea ON bec.BusinessEntityID = bea.BusinessEntityID
LEFT JOIN Address a ON bea.AddressID = a.AddressID
LEFT JOIN StateProvince sp ON a.StateProvinceID = sp.StateProvinceID
LEFT JOIN CountryRegion cr ON sp.CountryRegionCode = cr.CountryRegionCode
WHERE per.PersonType IN ('SC', 'VC')
ORDER BY PasswordAgeDays DESC;
```

---

### Practical Business Use-Case Queries (5)

---

**Q6: "What's the password age distribution across all people — how many are current, aging, or expired?"**

*Use case: IT security — password rotation compliance*

```sql
SELECT
    CASE
        WHEN JULIANDAY('now') - JULIANDAY(ModifiedDate) <= 90 THEN '0-90 days (Current)'
        WHEN JULIANDAY('now') - JULIANDAY(ModifiedDate) <= 180 THEN '91-180 days (Aging)'
        WHEN JULIANDAY('now') - JULIANDAY(ModifiedDate) <= 365 THEN '181-365 days (Stale)'
        ELSE '365+ days (Expired)'
    END AS PasswordAgeBucket,
    COUNT(*) AS PersonCount,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM Password), 2) AS PctOfTotal
FROM Password
GROUP BY PasswordAgeBucket
ORDER BY MIN(JULIANDAY('now') - JULIANDAY(ModifiedDate));
```

---

**Q7: "Are there any duplicate password hashes — potential security concern?"**

*Use case: Security audit — hash uniqueness check*

```sql
SELECT
    PasswordHash,
    COUNT(*) AS Occurrences,
    GROUP_CONCAT(BusinessEntityID) AS AffectedEntityIDs
FROM Password
GROUP BY PasswordHash
HAVING COUNT(*) > 1
ORDER BY Occurrences DESC;
```

---

**Q8: "Does every Person have a Password record, and does every Password have a valid Person?"**

*Use case: Data integrity audit — orphan detection*

```sql
SELECT
    'Persons WITHOUT Password' AS CheckType,
    COUNT(*) AS Count
FROM Person per
LEFT JOIN Password pwd ON per.BusinessEntityID = pwd.BusinessEntityID
WHERE pwd.BusinessEntityID IS NULL

UNION ALL

SELECT
    'Passwords WITHOUT Person' AS CheckType,
    COUNT(*) AS Count
FROM Password pwd
LEFT JOIN Person per ON pwd.BusinessEntityID = per.BusinessEntityID
WHERE per.BusinessEntityID IS NULL

UNION ALL

SELECT
    'Matched (Person + Password)' AS CheckType,
    COUNT(*) AS Count
FROM Person per
JOIN Password pwd ON per.BusinessEntityID = pwd.BusinessEntityID;
```

---

**Q9: "What's the password age breakdown by PersonType — are employees more compliant than customers?"**

*Use case: IT compliance — password rotation by user segment*

```sql
SELECT
    per.PersonType,
    CASE per.PersonType
        WHEN 'EM' THEN 'Employee'
        WHEN 'SP' THEN 'Sales Person'
        WHEN 'IN' THEN 'Individual Customer'
        WHEN 'SC' THEN 'Store Contact'
        WHEN 'VC' THEN 'Vendor Contact'
        WHEN 'GC' THEN 'General Contact'
    END AS PersonTypeLabel,
    COUNT(*) AS TotalPersons,
    ROUND(AVG(JULIANDAY('now') - JULIANDAY(pwd.ModifiedDate)), 0) AS AvgPasswordAgeDays,
    SUM(CASE WHEN JULIANDAY('now') - JULIANDAY(pwd.ModifiedDate) > 365 THEN 1 ELSE 0 END) AS ExpiredPasswords,
    ROUND(SUM(CASE WHEN JULIANDAY('now') - JULIANDAY(pwd.ModifiedDate) > 365 THEN 1 ELSE 0 END) * 100.0
        / COUNT(*), 2) AS PctExpired
FROM Password pwd
JOIN Person per ON pwd.BusinessEntityID = per.BusinessEntityID
GROUP BY per.PersonType
ORDER BY AvgPasswordAgeDays DESC;
```

---

**Q10: "List the 10 people with the oldest passwords who are still active (employees with CurrentFlag=1, or non-employee persons)."**

*Use case: IT security — targeting stale accounts for forced reset*

```sql
SELECT
    pwd.BusinessEntityID,
    per.FirstName || ' ' || per.LastName AS FullName,
    per.PersonType,
    e.JobTitle,
    e.CurrentFlag,
    pwd.ModifiedDate AS PasswordLastChanged,
    CAST(JULIANDAY('now') - JULIANDAY(pwd.ModifiedDate) AS INTEGER) AS PasswordAgeDays
FROM Password pwd
JOIN Person per ON pwd.BusinessEntityID = per.BusinessEntityID
LEFT JOIN Employee e ON per.BusinessEntityID = e.BusinessEntityID
WHERE (e.CurrentFlag = 1 OR e.BusinessEntityID IS NULL)
ORDER BY pwd.ModifiedDate ASC
LIMIT 10;
```

---
