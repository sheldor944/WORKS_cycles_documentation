# Employee

---

## 📋 Short Description

### Style 1: Conceptual Summary
This table stores employee records — one row per employee (290 employees). It captures who they are (BusinessEntityID → Person, NationalIDNumber, LoginID), their role (JobTitle, OrganizationNode, OrganizationLevel), demographics (BirthDate, MaritalStatus, Gender), employment details (HireDate, SalariedFlag, CurrentFlag), and leave balances (VacationHours, SickLeaveHours). Employees are a subset of Person, which is a subset of BusinessEntity — forming the inheritance chain BusinessEntity → Person → Employee.

### Style 2: Query Possibilities & Business Story
This is the core employee table — every person employed by the company has a record here. It extends the Person table (which has names, email, etc.) with employment-specific data. Use this table to answer questions like:

- "How many employees are currently active?"
- "What's the average tenure of employees by job title?"
- "How are employees distributed across organization levels?"
- "What's the gender or marital status breakdown of the workforce?"
- "Who are the longest-tenured employees?"
- "Which employees have the most unused vacation hours?"
- "How many salaried vs. hourly employees do we have?"
- "What's the average age of employees by department?" (with EmployeeDepartmentHistory)
- "Which employees report to which manager?" (via OrganizationNode hierarchy)
- "What's the pay rate history for a specific employee?" (with EmployeePayHistory)
- "Which salespersons are also employees?" (with SalesPerson)
- "Who approved the most purchase orders?" (with PurchaseOrderHeader)

Each employee connects upward to Person (for name/contact info) and downward to department history, pay history, job candidates, sales roles, purchase orders, and documents they own.

### Style 3: Grouped & Complete (Column Reference)
This table stores one row per employee (290 rows), containing 16 columns organized as:

- **Identifiers:** BusinessEntityID (PK, FK → Person), NationalIDNumber, LoginID, rowguid
- **Organization:** OrganizationNode (hierarchy path), OrganizationLevel (depth in hierarchy), JobTitle
- **Demographics:** BirthDate, MaritalStatus (S/M), Gender (M/F)
- **Employment:** HireDate, SalariedFlag (1=salaried, 0=hourly), CurrentFlag (1=active, 0=inactive)
- **Leave Balances:** VacationHours, SickLeaveHours
- **Audit:** ModifiedDate

---

## 📖 Extensive Description

### Purpose & Business Context

Employee stores the employment-specific attributes for the 290 people who work for AdventureWorks. It sits in the inheritance chain `BusinessEntity (20,777) → Person (19,972) → Employee (290)`, meaning every employee is also a Person (with name, email, phone) and a BusinessEntity (with addresses). This design means employee personal details live in Person while work-specific details live here.

The table supports HR analytics (headcount, tenure, demographics, leave tracking), organizational hierarchy analysis (via OrganizationNode/Level), and connects employees to their operational roles across sales (SalesPerson), purchasing (PurchaseOrderHeader), manufacturing (Document ownership), and department/pay history.

### Key Business Logic

- **BusinessEntityID** is both the PK and FK to Person — it's not auto-generated here; it inherits from BusinessEntity/Person
- **OrganizationNode** encodes the reporting hierarchy (e.g., "/1/1/2/" means CEO → VP → Manager) — can be parsed to determine reporting chains
- **OrganizationLevel** = depth in the org tree (0 = CEO, 1 = direct reports to CEO, etc.)
- **SalariedFlag = 1** → exempt/salaried; **0** → hourly (pay rate in EmployeePayHistory)
- **CurrentFlag = 1** → currently employed; **0** → terminated/departed
- **VacationHours / SickLeaveHours** can go negative (indicating advance usage)

### Relationships

| Direction | Table | Join Key | Notes |
|-----------|-------|----------|-------|
| → Parent | Person → BusinessEntity | BusinessEntityID | Name, contact, address info |
| ↓ Child | EmployeeDepartmentHistory → Department, Shift | BusinessEntityID | Department assignments over time |
| ↓ Child | EmployeePayHistory | BusinessEntityID | Pay rate changes over time |
| ↓ Child | JobCandidate | BusinessEntityID | Resumes (nullable FK — may not be hired yet) |
| ↓ Child | Document | Owner (FK) | Documents owned by employee |
| ↓ Extends to | SalesPerson | BusinessEntityID | 17 employees are also salespersons |
| ↓ Referenced by | PurchaseOrderHeader | EmployeeID | Employee who approved the PO |
| ← Via Person | EmailAddress | BusinessEntityID | Employee's email |
| ← Via Person | Password | BusinessEntityID | Login credentials |
| ← Via Person | PersonCreditCard → CreditCard | BusinessEntityID | Payment cards |
| ← Via BusinessEntity | BusinessEntityAddress → Address | BusinessEntityID | Employee addresses |

---

## 🔗 10 NL → SQL Examples

### Join-Heavy Queries (5)

---

**Q1: "For each active employee, show their full name, email, job title, current department, shift, current pay rate, and their territory if they are a salesperson."**

*9 joins: Employee → Person → EmailAddress → EmployeeDepartmentHistory → Department → Shift → EmployeePayHistory → SalesPerson → SalesTerritory*

```sql
SELECT
    p.FirstName || ' ' || p.LastName AS EmployeeName,
    ea.EmailAddress,
    e.JobTitle,
    d.Name AS Department,
    sh.Name AS Shift,
    eph.Rate AS CurrentPayRate,
    eph.PayFrequency,
    st.Name AS SalesTerritory
FROM Employee e
JOIN Person p ON e.BusinessEntityID = p.BusinessEntityID
LEFT JOIN EmailAddress ea ON e.BusinessEntityID = ea.BusinessEntityID
JOIN EmployeeDepartmentHistory edh ON e.BusinessEntityID = edh.BusinessEntityID
    AND edh.EndDate IS NULL
JOIN Department d ON edh.DepartmentID = d.DepartmentID
JOIN Shift sh ON edh.ShiftID = sh.ShiftID
JOIN EmployeePayHistory eph ON e.BusinessEntityID = eph.BusinessEntityID
    AND eph.RateChangeDate = (
        SELECT MAX(eph2.RateChangeDate)
        FROM EmployeePayHistory eph2
        WHERE eph2.BusinessEntityID = e.BusinessEntityID
    )
LEFT JOIN SalesPerson sp ON e.BusinessEntityID = sp.BusinessEntityID
LEFT JOIN SalesTerritory st ON sp.TerritoryID = st.TerritoryID
WHERE e.CurrentFlag = 1;
```

---

**Q2: "Show each employee's name, job title, home address (city, state, country), department, and the total value of purchase orders they've approved."**

*9 joins: Employee → Person → BusinessEntityAddress → Address → StateProvince → CountryRegion → EmployeeDepartmentHistory → Department → PurchaseOrderHeader*

```sql
SELECT
    p.FirstName || ' ' || p.LastName AS EmployeeName,
    e.JobTitle,
    a.City,
    sp.Name AS StateName,
    cr.Name AS Country,
    d.Name AS Department,
    COUNT(DISTINCT poh.PurchaseOrderID) AS POsApproved,
    ROUND(SUM(poh.TotalDue), 2) AS TotalPOValue
FROM Employee e
JOIN Person p ON e.BusinessEntityID = p.BusinessEntityID
JOIN BusinessEntityAddress bea ON e.BusinessEntityID = bea.BusinessEntityID
JOIN Address a ON bea.AddressID = a.AddressID
JOIN StateProvince sp ON a.StateProvinceID = sp.StateProvinceID
JOIN CountryRegion cr ON sp.CountryRegionCode = cr.CountryRegionCode
JOIN EmployeeDepartmentHistory edh ON e.BusinessEntityID = edh.BusinessEntityID
    AND edh.EndDate IS NULL
JOIN Department d ON edh.DepartmentID = d.DepartmentID
LEFT JOIN PurchaseOrderHeader poh ON e.BusinessEntityID = poh.EmployeeID
GROUP BY p.FirstName, p.LastName, e.JobTitle, a.City, sp.Name, cr.Name, d.Name
ORDER BY TotalPOValue DESC;
```

---

**Q3: "For employees who are salespersons, show their name, department, territory, total sales revenue, total orders, and their quota history — alongside the customer store names they manage."**

*10 joins: Employee → Person → SalesPerson → SalesTerritory → SalesPersonQuotaHistory → EmployeeDepartmentHistory → Department → SalesOrderHeader → Customer → Store*

```sql
SELECT
    p.FirstName || ' ' || p.LastName AS SalesPersonName,
    d.Name AS Department,
    st.Name AS Territory,
    spqh.SalesQuota AS LatestQuota,
    COUNT(DISTINCT soh.SalesOrderID) AS TotalOrders,
    ROUND(SUM(soh.TotalDue), 2) AS TotalRevenue,
    GROUP_CONCAT(DISTINCT s.Name) AS ManagedStores
FROM Employee e
JOIN Person p ON e.BusinessEntityID = p.BusinessEntityID
JOIN SalesPerson sp ON e.BusinessEntityID = sp.BusinessEntityID
LEFT JOIN SalesTerritory st ON sp.TerritoryID = st.TerritoryID
LEFT JOIN SalesPersonQuotaHistory spqh ON sp.BusinessEntityID = spqh.BusinessEntityID
    AND spqh.QuotaDate = (
        SELECT MAX(q2.QuotaDate)
        FROM SalesPersonQuotaHistory q2
        WHERE q2.BusinessEntityID = sp.BusinessEntityID
    )
JOIN EmployeeDepartmentHistory edh ON e.BusinessEntityID = edh.BusinessEntityID
    AND edh.EndDate IS NULL
JOIN Department d ON edh.DepartmentID = d.DepartmentID
LEFT JOIN SalesOrderHeader soh ON sp.BusinessEntityID = soh.SalesPersonID
LEFT JOIN Customer c ON soh.CustomerID = c.CustomerID
LEFT JOIN Store s ON c.StoreID = s.BusinessEntityID
GROUP BY p.FirstName, p.LastName, d.Name, st.Name, spqh.SalesQuota
ORDER BY TotalRevenue DESC;
```

---

**Q4: "Show each employee's full name, job title, all departments they've ever worked in, the shift they worked, and the pay rate they had during that period."**

*6 joins: Employee → Person → EmployeeDepartmentHistory → Department → Shift → EmployeePayHistory*

```sql
SELECT
    p.FirstName || ' ' || p.LastName AS EmployeeName,
    e.JobTitle,
    d.Name AS Department,
    sh.Name AS Shift,
    edh.StartDate AS DeptStartDate,
    edh.EndDate AS DeptEndDate,
    eph.Rate AS PayRate,
    eph.RateChangeDate,
    eph.PayFrequency
FROM Employee e
JOIN Person p ON e.BusinessEntityID = p.BusinessEntityID
JOIN EmployeeDepartmentHistory edh ON e.BusinessEntityID = edh.BusinessEntityID
JOIN Department d ON edh.DepartmentID = d.DepartmentID
JOIN Shift sh ON edh.ShiftID = sh.ShiftID
JOIN EmployeePayHistory eph ON e.BusinessEntityID = eph.BusinessEntityID
    AND eph.RateChangeDate BETWEEN edh.StartDate
        AND COALESCE(edh.EndDate, DATE('now'))
ORDER BY p.LastName, edh.StartDate, eph.RateChangeDate;
```

---

**Q5: "List all employees along with their name, email, job title, department, the documents they own, and the vendor purchase orders they've managed — including vendor names and ship methods."**

*11 joins: Employee → Person → EmailAddress → EmployeeDepartmentHistory → Department → Document → PurchaseOrderHeader → Vendor → ShipMethod*

```sql
SELECT
    p.FirstName || ' ' || p.LastName AS EmployeeName,
    ea.EmailAddress,
    e.JobTitle,
    d.Name AS Department,
    doc.Title AS DocumentTitle,
    doc.FileName,
    v.Name AS VendorName,
    sm.Name AS ShipMethod,
    poh.OrderDate AS PODate,
    ROUND(poh.TotalDue, 2) AS POTotal
FROM Employee e
JOIN Person p ON e.BusinessEntityID = p.BusinessEntityID
LEFT JOIN EmailAddress ea ON e.BusinessEntityID = ea.BusinessEntityID
JOIN EmployeeDepartmentHistory edh ON e.BusinessEntityID = edh.BusinessEntityID
    AND edh.EndDate IS NULL
JOIN Department d ON edh.DepartmentID = d.DepartmentID
LEFT JOIN Document doc ON e.BusinessEntityID = doc.Owner
LEFT JOIN PurchaseOrderHeader poh ON e.BusinessEntityID = poh.EmployeeID
LEFT JOIN Vendor v ON poh.VendorID = v.BusinessEntityID
LEFT JOIN ShipMethod sm ON poh.ShipMethodID = sm.ShipMethodID
ORDER BY p.LastName, poh.OrderDate DESC;
```

---

### Practical Business Use-Case Queries (5)

---

**Q6: "What's the headcount breakdown by department and gender for currently active employees?"**

*Use case: HR diversity reporting*

```sql
SELECT
    d.Name AS Department,
    e.Gender,
    COUNT(*) AS Headcount,
    ROUND(AVG(e.VacationHours), 1) AS AvgVacationHrs,
    ROUND(AVG(e.SickLeaveHours), 1) AS AvgSickLeaveHrs
FROM Employee e
JOIN EmployeeDepartmentHistory edh ON e.BusinessEntityID = edh.BusinessEntityID
    AND edh.EndDate IS NULL
JOIN Department d ON edh.DepartmentID = d.DepartmentID
WHERE e.CurrentFlag = 1
GROUP BY d.Name, e.Gender
ORDER BY d.Name, e.Gender;
```

---

**Q7: "Who are the top 10 longest-tenured employees, and how long have they been with the company?"**

*Use case: Retention / recognition program*

```sql
SELECT
    e.BusinessEntityID,
    e.JobTitle,
    e.HireDate,
    ROUND(JULIANDAY('now') - JULIANDAY(e.HireDate)) AS DaysEmployed,
    ROUND((JULIANDAY('now') - JULIANDAY(e.HireDate)) / 365.25, 1) AS YearsEmployed,
    e.VacationHours,
    e.SickLeaveHours,
    e.SalariedFlag
FROM Employee e
WHERE e.CurrentFlag = 1
ORDER BY e.HireDate ASC
LIMIT 10;
```

---

**Q8: "What's the salaried vs. hourly employee split by organization level?"**

*Use case: Compensation structure analysis*

```sql
SELECT
    OrganizationLevel,
    COUNT(*) AS TotalEmployees,
    SUM(CASE WHEN SalariedFlag = 1 THEN 1 ELSE 0 END) AS Salaried,
    SUM(CASE WHEN SalariedFlag = 0 THEN 1 ELSE 0 END) AS Hourly,
    ROUND(SUM(CASE WHEN SalariedFlag = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS SalariedPct
FROM Employee
WHERE CurrentFlag = 1
GROUP BY OrganizationLevel
ORDER BY OrganizationLevel;
```

---

**Q9: "Which employees have accumulated excessive vacation hours (over 80) and haven't been flagged as inactive?"**

*Use case: HR compliance — mandatory vacation usage*

```sql
SELECT
    e.BusinessEntityID,
    e.JobTitle,
    e.HireDate,
    e.VacationHours,
    e.SickLeaveHours,
    e.MaritalStatus,
    ROUND((JULIANDAY('now') - JULIANDAY(e.HireDate)) / 365.25, 1) AS YearsEmployed
FROM Employee e
WHERE e.CurrentFlag = 1
    AND e.VacationHours > 80
ORDER BY e.VacationHours DESC;
```

---

**Q10: "Show the age distribution of the workforce grouped into age bands (20s, 30s, 40s, 50s, 60+)."**

*Use case: Workforce planning / retirement risk*

```sql
SELECT
    CASE
        WHEN (strftime('%Y', 'now') - strftime('%Y', BirthDate)) BETWEEN 20 AND 29 THEN '20-29'
        WHEN (strftime('%Y', 'now') - strftime('%Y', BirthDate)) BETWEEN 30 AND 39 THEN '30-39'
        WHEN (strftime('%Y', 'now') - strftime('%Y', BirthDate)) BETWEEN 40 AND 49 THEN '40-49'
        WHEN (strftime('%Y', 'now') - strftime('%Y', BirthDate)) BETWEEN 50 AND 59 THEN '50-59'
        ELSE '60+'
    END AS AgeBand,
    COUNT(*) AS EmployeeCount,
    SUM(CASE WHEN Gender = 'M' THEN 1 ELSE 0 END) AS Male,
    SUM(CASE WHEN Gender = 'F' THEN 1 ELSE 0 END) AS Female,
    ROUND(AVG(VacationHours), 1) AS AvgVacationHrs
FROM Employee
WHERE CurrentFlag = 1
GROUP BY AgeBand
ORDER BY AgeBand;
```

---
