# EmailAddress

---

## 📋 Short Description

### Style 1: Conceptual Summary
This table stores email addresses for people — one row per email address per person (19,972 records). It captures the email address (EmailAddress) and links it to a person (BusinessEntityID → Person). A person can have multiple email addresses (composite PK on EmailAddressID + BusinessEntityID), though in practice most have exactly one. This is the primary contact channel table — it provides the email identity used for communication, marketing, and account identification across the system.

### Style 2: Query Possibilities & Business Story
This is the email contact table — every person in the system (employees, customers, vendor contacts, store contacts) can have one or more email addresses stored here. It's essential for customer communication, marketing campaigns, and identifying people across the system. Use this table to answer questions like:

- "What's the email address for a specific employee or customer?"
- "How many people have multiple email addresses on file?"
- "Are there people with no email address?"
- "What are the most common email domains (gmail.com, adventure-works.com, etc.)?"
- "Which employees have company email addresses vs. personal?" (domain analysis)
- "How many email addresses are there by person type (employee, customer, vendor contact)?" (with Person)
- "Find all customers with a specific email domain." (with Customer, Person)
- "Get the full contact profile: name, email, phone, address." (with Person, BusinessEntityAddress, Address)
- "Which salesperson's customers have email addresses on file vs. missing?" (with SalesPerson, Customer, SalesOrderHeader)
- "What percentage of people have opted into email promotions AND have an email on file?" (with Person.EmailPromotion)
- "List all vendor contacts with their email and the vendor they represent." (with BusinessEntityContact, Vendor)
- "Find people whose email was recently modified."

Each email links to a Person (who may be an employee, customer, or contact). Combined with Person.EmailPromotion, it enables marketing segmentation — knowing both the address and the opt-in preference.

### Style 3: Grouped & Complete (Column Reference)
This table stores one row per email address per person (19,972 rows), containing 5 columns organized as:

- **Composite PK:** EmailAddressID (sequence within a person), BusinessEntityID (FK → Person)
- **Email:** EmailAddress (the actual email address — nullable in schema but expected to be populated)
- **System:** rowguid (unique GUID)
- **Audit:** ModifiedDate

---

## 📖 Extensive Description

### Purpose & Business Context

EmailAddress stores email contact information for all 19,972 people in the system. It's a 1:many relationship with Person (one person can have multiple emails), though the row count matching Person's count suggests most people have exactly one email.

Email addresses are critical for:
- **Customer communication** — order confirmations, shipping notifications
- **Marketing campaigns** — filtered by Person.EmailPromotion opt-in level
- **Employee identity** — company email as login identifier (correlates with Employee.LoginID)
- **Vendor/store contacts** — business communication with suppliers and retail partners

The table is intentionally separated from Person to allow multiple emails per person and to isolate contact data for privacy/access control purposes.

### Key Business Logic

- **Composite PK (EmailAddressID, BusinessEntityID)** — supports multiple emails per person; EmailAddressID sequences within each person
- **EmailAddress column is nullable in schema** — but expected to be populated; NULL would mean a placeholder/empty record
- **19,972 rows = 19,972 Person rows** — suggests 1:1 in practice (most people have exactly one email)
- **Email domain** can be parsed via string operations to analyze company vs. personal emails (e.g., `@adventure-works.com` for employees)
- **Person.EmailPromotion** (0/1/2) controls marketing opt-in — EmailAddress provides the actual address to send to
- **No unique constraint on EmailAddress** — theoretically the same email could appear for different people (data quality issue if it happens)
- **Not directly referenced by SalesOrderHeader** — order contact is through Customer → Person → EmailAddress chain

### Relationships

| Direction | Table | Join Key | Notes |
|-----------|-------|----------|-------|
| → Parent | Person → BusinessEntity | BusinessEntityID | The person this email belongs to |
| ← Via Person | Employee | BusinessEntityID | Employee emails |
| ← Via Person | Customer (via PersonID) | BusinessEntityID | Customer emails |
| ← Via Person | Password | BusinessEntityID | Login credentials for this person |
| ← Via Person | PersonCreditCard → CreditCard | BusinessEntityID | Person's payment cards |
| ← Via Person → BusinessEntityContact | Store / Vendor | BusinessEntityID | Contact's entity |
| ← Via Person → Employee | SalesPerson → SalesOrderHeader | SalesPersonID | Salesperson's orders |
| ← Via Person → Customer | SalesOrderHeader | CustomerID | Customer's orders |
| Sibling (per-person) | Password | BusinessEntityID | Both are 1:1 extensions of Person |
| Sibling (per-person) | BusinessEntityAddress → Address | BusinessEntityID | Person's physical address |

---

## 🔗 10 NL → SQL Examples

### Join-Heavy Queries (5)

---

**Q1: "For each employee, show their full name, job title, department, email address, home address (city/state/country), and their pay rate."**

*9 joins: EmailAddress → Person → Employee → EmployeeDepartmentHistory → Department → EmployeePayHistory → BusinessEntityAddress → Address → StateProvince → CountryRegion*

```sql
SELECT
    per.FirstName || ' ' || per.LastName AS EmployeeName,
    e.JobTitle,
    d.Name AS Department,
    ea.EmailAddress,
    a.City,
    sp.Name AS State,
    cr.Name AS Country,
    eph.Rate AS CurrentPayRate
FROM EmailAddress ea
JOIN Person per ON ea.BusinessEntityID = per.BusinessEntityID
JOIN Employee e ON per.BusinessEntityID = e.BusinessEntityID
JOIN EmployeeDepartmentHistory edh ON e.BusinessEntityID = edh.BusinessEntityID
    AND edh.EndDate IS NULL
JOIN Department d ON edh.DepartmentID = d.DepartmentID
JOIN EmployeePayHistory eph ON e.BusinessEntityID = eph.BusinessEntityID
    AND eph.RateChangeDate = (
        SELECT MAX(eph2.RateChangeDate)
        FROM EmployeePayHistory eph2
        WHERE eph2.BusinessEntityID = e.BusinessEntityID
    )
LEFT JOIN BusinessEntityAddress bea ON per.BusinessEntityID = bea.BusinessEntityID
LEFT JOIN Address a ON bea.AddressID = a.AddressID
LEFT JOIN StateProvince sp ON a.StateProvinceID = sp.StateProvinceID
LEFT JOIN CountryRegion cr ON sp.CountryRegionCode = cr.CountryRegionCode
WHERE e.CurrentFlag = 1
ORDER BY per.LastName;
```

---

**Q2: "For individual customers, show their name, email, email promotion preference, total orders, total revenue, and the territories they've ordered from."**

*7 joins: EmailAddress → Person → Customer → SalesOrderHeader → SalesTerritory*

```sql
SELECT
    per.FirstName || ' ' || per.LastName AS CustomerName,
    ea.EmailAddress,
    CASE per.EmailPromotion
        WHEN 0 THEN 'No Emails'
        WHEN 1 THEN 'AW Only'
        WHEN 2 THEN 'AW + Partners'
    END AS EmailOptIn,
    st.Name AS Territory,
    COUNT(DISTINCT soh.SalesOrderID) AS TotalOrders,
    ROUND(SUM(soh.TotalDue), 2) AS TotalRevenue,
    ROUND(AVG(soh.TotalDue), 2) AS AvgOrderValue
FROM EmailAddress ea
JOIN Person per ON ea.BusinessEntityID = per.BusinessEntityID
JOIN Customer c ON per.BusinessEntityID = c.PersonID
JOIN SalesOrderHeader soh ON c.CustomerID = soh.CustomerID
JOIN SalesTerritory st ON soh.TerritoryID = st.TerritoryID
WHERE per.PersonType = 'IN'
GROUP BY per.FirstName, per.LastName, ea.EmailAddress, per.EmailPromotion, st.Name
ORDER BY TotalRevenue DESC;
```

---

**Q3: "For vendor contacts, show their name, email, contact role, vendor name, vendor credit rating, vendor address (city/country), and total PO spend with that vendor."**

*10 joins: EmailAddress → Person → BusinessEntityContact → ContactType → Vendor → BusinessEntityAddress → Address → StateProvince → CountryRegion → PurchaseOrderHeader*

```sql
SELECT
    per.FirstName || ' ' || per.LastName AS ContactName,
    ea.EmailAddress,
    ct.Name AS ContactRole,
    v.Name AS VendorName,
    v.CreditRating,
    a.City AS VendorCity,
    cr.Name AS VendorCountry,
    COUNT(DISTINCT poh.PurchaseOrderID) AS TotalPOs,
    ROUND(SUM(poh.TotalDue), 2) AS TotalPOSpend
FROM EmailAddress ea
JOIN Person per ON ea.BusinessEntityID = per.BusinessEntityID
JOIN BusinessEntityContact bec ON per.BusinessEntityID = bec.PersonID
JOIN ContactType ct ON bec.ContactTypeID = ct.ContactTypeID
JOIN Vendor v ON bec.BusinessEntityID = v.BusinessEntityID
LEFT JOIN BusinessEntityAddress bea ON v.BusinessEntityID = bea.BusinessEntityID
LEFT JOIN Address a ON bea.AddressID = a.AddressID
LEFT JOIN StateProvince sp ON a.StateProvinceID = sp.StateProvinceID
LEFT JOIN CountryRegion cr ON sp.CountryRegionCode = cr.CountryRegionCode
LEFT JOIN PurchaseOrderHeader poh ON v.BusinessEntityID = poh.VendorID
WHERE per.PersonType = 'VC'
GROUP BY per.FirstName, per.LastName, ea.EmailAddress, ct.Name, v.Name,
         v.CreditRating, a.City, cr.Name
ORDER BY TotalPOSpend DESC;
```

---

**Q4: "For salespersons, show their name, email, territory, quota, total orders sold, total revenue, and their password last changed date — a full account profile."**

*9 joins: EmailAddress → Person → Employee → SalesPerson → SalesTerritory → SalesPersonQuotaHistory → SalesOrderHeader → Password*

```sql
SELECT
    per.FirstName || ' ' || per.LastName AS SalesPersonName,
    ea.EmailAddress,
    st.Name AS Territory,
    spqh.SalesQuota AS CurrentQuota,
    sp.SalesYTD,
    COUNT(DISTINCT soh.SalesOrderID) AS TotalOrders,
    ROUND(SUM(soh.TotalDue), 2) AS TotalRevenue,
    pwd.ModifiedDate AS PasswordLastChanged
FROM EmailAddress ea
JOIN Person per ON ea.BusinessEntityID = per.BusinessEntityID
JOIN Employee e ON per.BusinessEntityID = e.BusinessEntityID
JOIN SalesPerson sp ON e.BusinessEntityID = sp.BusinessEntityID
LEFT JOIN SalesTerritory st ON sp.TerritoryID = st.TerritoryID
LEFT JOIN SalesPersonQuotaHistory spqh ON sp.BusinessEntityID = spqh.BusinessEntityID
    AND spqh.QuotaDate = (
        SELECT MAX(q2.QuotaDate)
        FROM SalesPersonQuotaHistory q2
        WHERE q2.BusinessEntityID = sp.BusinessEntityID
    )
LEFT JOIN SalesOrderHeader soh ON sp.BusinessEntityID = soh.SalesPersonID
LEFT JOIN Password pwd ON per.BusinessEntityID = pwd.BusinessEntityID
GROUP BY per.FirstName, per.LastName, ea.EmailAddress, st.Name,
         spqh.SalesQuota, sp.SalesYTD, pwd.ModifiedDate
ORDER BY TotalRevenue DESC;
```

---

**Q5: "For store contacts, show their name, email, contact role, store name, store's salesperson name, store address, and the total revenue from that store's orders."**

*10 joins: EmailAddress → Person → BusinessEntityContact → ContactType → Store → SalesPerson → Employee → Person(rep) → Customer → SalesOrderHeader → BusinessEntityAddress → Address*

```sql
SELECT
    per.FirstName || ' ' || per.LastName AS StoreContactName,
    ea.EmailAddress,
    ct.Name AS ContactRole,
    s.Name AS StoreName,
    rep.FirstName || ' ' || rep.LastName AS AssignedSalesPerson,
    a.City AS StoreCity,
    COUNT(DISTINCT soh.SalesOrderID) AS StoreOrders,
    ROUND(SUM(soh.TotalDue), 2) AS StoreRevenue
FROM EmailAddress ea
JOIN Person per ON ea.BusinessEntityID = per.BusinessEntityID
JOIN BusinessEntityContact bec ON per.BusinessEntityID = bec.PersonID
JOIN ContactType ct ON bec.ContactTypeID = ct.ContactTypeID
JOIN Store s ON bec.BusinessEntityID = s.BusinessEntityID
LEFT JOIN SalesPerson salp ON s.SalesPersonID = salp.BusinessEntityID
LEFT JOIN Person rep ON salp.BusinessEntityID = rep.BusinessEntityID
LEFT JOIN BusinessEntityAddress bea ON s.BusinessEntityID = bea.BusinessEntityID
LEFT JOIN Address a ON bea.AddressID = a.AddressID
LEFT JOIN Customer c ON s.BusinessEntityID = c.StoreID
LEFT JOIN SalesOrderHeader soh ON c.CustomerID = soh.CustomerID
WHERE per.PersonType = 'SC'
GROUP BY per.FirstName, per.LastName, ea.EmailAddress, ct.Name, s.Name,
         rep.FirstName, rep.LastName, a.City
ORDER BY StoreRevenue DESC;
```

---

### Practical Business Use-Case Queries (5)

---

**Q6: "What are the most common email domains, and how many people use each?"**

*Use case: IT / Marketing — email ecosystem analysis*

```sql
SELECT
    LOWER(SUBSTR(EmailAddress, INSTR(EmailAddress, '@') + 1)) AS EmailDomain,
    COUNT(*) AS PersonCount,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM EmailAddress WHERE EmailAddress IS NOT NULL), 2) AS PctOfTotal,
    COUNT(DISTINCT BusinessEntityID) AS UniquePersons
FROM EmailAddress
WHERE EmailAddress IS NOT NULL
GROUP BY EmailDomain
ORDER BY PersonCount DESC
LIMIT 20;
```

---

**Q7: "Are there people with no email address on file?"**

*Use case: Data completeness audit*

```sql
SELECT
    per.BusinessEntityID,
    per.PersonType,
    CASE per.PersonType
        WHEN 'EM' THEN 'Employee'
        WHEN 'SP' THEN 'Sales Person'
        WHEN 'IN' THEN 'Individual Customer'
        WHEN 'SC' THEN 'Store Contact'
        WHEN 'VC' THEN 'Vendor Contact'
        WHEN 'GC' THEN 'General Contact'
    END AS PersonTypeLabel,
    per.FirstName || ' ' || per.LastName AS FullName
FROM Person per
LEFT JOIN EmailAddress ea ON per.BusinessEntityID = ea.BusinessEntityID
WHERE ea.BusinessEntityID IS NULL
ORDER BY per.PersonType, per.LastName;
```

---

**Q8: "How many people have multiple email addresses on file?"**

*Use case: Data quality — multi-email detection*

```sql
SELECT
    BusinessEntityID,
    COUNT(*) AS EmailCount,
    GROUP_CONCAT(EmailAddress, '; ') AS AllEmails
FROM EmailAddress
WHERE EmailAddress IS NOT NULL
GROUP BY BusinessEntityID
HAVING COUNT(*) > 1
ORDER BY EmailCount DESC;
```

---

**Q9: "What's the email coverage by person type — do all employees have emails, do all customers?"**

*Use case: Data governance — contact completeness by segment*

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
    COUNT(DISTINCT per.BusinessEntityID) AS TotalPersons,
    COUNT(DISTINCT ea.BusinessEntityID) AS PersonsWithEmail,
    COUNT(DISTINCT per.BusinessEntityID) - COUNT(DISTINCT ea.BusinessEntityID) AS PersonsWithoutEmail,
    ROUND(COUNT(DISTINCT ea.BusinessEntityID) * 100.0 / COUNT(DISTINCT per.BusinessEntityID), 2) AS EmailCoveragePct
FROM Person per
LEFT JOIN EmailAddress ea ON per.BusinessEntityID = ea.BusinessEntityID
    AND ea.EmailAddress IS NOT NULL
GROUP BY per.PersonType
ORDER BY EmailCoveragePct ASC;
```

---

**Q10: "Cross-reference email opt-in preferences with actual email availability — how many people opted in but have no email, or have email but opted out?"**

*Use case: Marketing — campaign readiness audit*

```sql
SELECT
    CASE per.EmailPromotion
        WHEN 0 THEN 'Opted Out'
        WHEN 1 THEN 'AW Emails Only'
        WHEN 2 THEN 'AW + Partner Emails'
    END AS OptInLevel,
    COUNT(*) AS TotalPersons,
    SUM(CASE WHEN ea.EmailAddress IS NOT NULL THEN 1 ELSE 0 END) AS HasEmail,
    SUM(CASE WHEN ea.EmailAddress IS NULL THEN 1 ELSE 0 END) AS NoEmail,
    CASE
        WHEN per.EmailPromotion > 0 AND ea.EmailAddress IS NULL
        THEN 'OPTED IN but NO EMAIL — cannot reach'
        WHEN per.EmailPromotion = 0 AND ea.EmailAddress IS NOT NULL
        THEN 'HAS EMAIL but OPTED OUT — respect preference'
        ELSE 'Aligned'
    END AS AlignmentStatus,
    COUNT(*) AS StatusCount
FROM Person per
LEFT JOIN EmailAddress ea ON per.BusinessEntityID = ea.BusinessEntityID
GROUP BY OptInLevel, AlignmentStatus
ORDER BY per.EmailPromotion, AlignmentStatus;
```

---
