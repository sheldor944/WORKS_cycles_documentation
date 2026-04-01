# BusinessEntity

---

## 📋 Short Description

### Style 1: Conceptual Summary
This table is the universal root entity table — one row per entity in the entire system (20,777 records). It serves as the identity backbone, generating unique BusinessEntityIDs that are inherited by every person (Person), store (Store), and vendor (Vendor) in the database. The table itself holds no business data — just the auto-incrementing ID, a GUID (rowguid), and a timestamp (ModifiedDate). Think of it as the ID factory — every entity in AdventureWorks starts here.

### Style 2: Query Possibilities & Business Story
This is the root identity table — before anything can exist in the system (a person, a store, a vendor), a BusinessEntity record must be created first to generate the unique ID. It's the foundation of the entire entity model. By itself it holds no meaningful business data, but it's the key to understanding the entity landscape. Use this table to answer questions like:

- "How many total entities exist in the system?"
- "How many entities are people vs. stores vs. vendors vs. unclassified?"
- "Are there orphaned BusinessEntity records — IDs that aren't linked to any Person, Store, or Vendor?"
- "When were the most recent entities created?"
- "What's the entity creation trend over time?"
- "How many entities were created each month/year?"
- "Are there gaps in the BusinessEntityID sequence?"
- "How does the entity count break down: 20,777 entities = 19,972 persons + 701 stores + 104 vendors — does that add up?" (spoiler: some entities are both a Person and something else)
- "Which BusinessEntityIDs are stores that also have a person record?"
- "What's the ratio of people to stores to vendors?"

Every other entity table (Person, Store, Vendor) has a FK back to BusinessEntity. The address system (BusinessEntityAddress), contact system (BusinessEntityContact), and by extension the entire geographic and communication model all hang off this root.

### Style 3: Grouped & Complete (Column Reference)
This table stores one row per system entity (20,777 rows), containing 3 columns organized as:

- **Identifier:** BusinessEntityID (PK, auto-increment — the universal ID inherited by all entities)
- **System:** rowguid (unique GUID for replication/integration)
- **Audit:** ModifiedDate

---

## 📖 Extensive Description

### Purpose & Business Context

BusinessEntity is the abstract root of the entire entity model in AdventureWorks. It implements the "supertype/subtype" pattern (also called table-per-type inheritance): a single ID sequence is shared across all entity types, ensuring no two entities — whether a person, a store, or a vendor — ever collide on ID.

The 20,777 rows break down approximately as:
- **19,972 → Person** (employees, customers, contacts)
- **701 → Store** (retail stores)
- **104 → Vendor** (suppliers)
- Some overlap exists — Stores and Vendors are also BusinessEntities with Person-level contacts linked through BusinessEntityContact

The table holds zero business data. Its entire purpose is:
1. **Generate unique IDs** via auto-increment
2. **Serve as the FK target** for Person, Store, Vendor, BusinessEntityAddress, and BusinessEntityContact
3. **Enable polymorphic relationships** — Address and Contact can link to ANY entity type through a single BusinessEntityID

### Key Business Logic

- **Auto-increment PK** — every new person, store, or vendor first gets a BusinessEntity row, then the child table (Person/Store/Vendor) uses that same ID as its PK+FK
- **20,777 total ≠ 19,972 + 701 + 104** — because stores and vendors ARE BusinessEntities that may also have Person records linked via BusinessEntityContact
- **No business data** — just ID, GUID, timestamp; all meaningful data lives in child tables
- **Deletion cascade risk** — removing a BusinessEntity would orphan all associated Person, Store, Vendor, Address, and Contact records
- **rowguid** is used for replication and cross-system integration
- **Cannot determine entity type from this table alone** — must LEFT JOIN to Person, Store, Vendor to classify

### Relationships

| Direction | Table | Join Key | Notes |
|-----------|-------|----------|-------|
| ↓ Child | Person (19,972) | BusinessEntityID | People (employees, customers, contacts) |
| ↓ Child | Store (701) | BusinessEntityID | Retail stores |
| ↓ Child | Vendor (104) | BusinessEntityID | Suppliers |
| ↓ Child | BusinessEntityAddress (19,614) | BusinessEntityID | Entity → Address links |
| ↓ Child | BusinessEntityContact (909) | BusinessEntityID | Entity → Person contact links |
| ← Via Person | Employee (290) | BusinessEntityID | Employees |
| ← Via Person | Customer | PersonID | Individual customers |
| ← Via Employee | SalesPerson (17) | BusinessEntityID | Sales representatives |
| ← Via Store | Customer | StoreID | Store customers |
| ← Via Vendor | PurchaseOrderHeader | VendorID | Purchase orders |
| ← Via BusinessEntityAddress | Address → StateProvince → CountryRegion | AddressID | Geographic chain |
| ← Via BusinessEntityContact | Person, ContactType | PersonID, ContactTypeID | Contact assignments |

---

## 🔗 10 NL → SQL Examples

### Join-Heavy Queries (5)

---

**Q1: "For every business entity, classify it as Person, Store, Vendor, or Unknown — and if it's a Person, show their name, type, and whether they're also an Employee or SalesPerson."**

*5 joins: BusinessEntity → Person → Employee → SalesPerson → Store → Vendor*

```sql
SELECT
    be.BusinessEntityID,
    CASE
        WHEN per.BusinessEntityID IS NOT NULL AND s.BusinessEntityID IS NOT NULL THEN 'Person + Store'
        WHEN per.BusinessEntityID IS NOT NULL AND v.BusinessEntityID IS NOT NULL THEN 'Person + Vendor'
        WHEN per.BusinessEntityID IS NOT NULL THEN 'Person'
        WHEN s.BusinessEntityID IS NOT NULL THEN 'Store'
        WHEN v.BusinessEntityID IS NOT NULL THEN 'Vendor'
        ELSE 'Unknown / Orphan'
    END AS EntityType,
    per.FirstName || ' ' || per.LastName AS PersonName,
    per.PersonType,
    CASE WHEN e.BusinessEntityID IS NOT NULL THEN 'Yes' ELSE 'No' END AS IsEmployee,
    CASE WHEN sp.BusinessEntityID IS NOT NULL THEN 'Yes' ELSE 'No' END AS IsSalesPerson,
    s.Name AS StoreName,
    v.Name AS VendorName
FROM BusinessEntity be
LEFT JOIN Person per ON be.BusinessEntityID = per.BusinessEntityID
LEFT JOIN Employee e ON per.BusinessEntityID = e.BusinessEntityID
LEFT JOIN SalesPerson sp ON e.BusinessEntityID = sp.BusinessEntityID
LEFT JOIN Store s ON be.BusinessEntityID = s.BusinessEntityID
LEFT JOIN Vendor v ON be.BusinessEntityID = v.BusinessEntityID
ORDER BY be.BusinessEntityID;
```

---

**Q2: "For every business entity, show its classification, all associated addresses (with type, city, state, country), and the sales territory the address falls under."**

*8 joins: BusinessEntity → Person/Store/Vendor → BusinessEntityAddress → AddressType → Address → StateProvince → CountryRegion → SalesTerritory*

```sql
SELECT
    be.BusinessEntityID,
    CASE
        WHEN per.BusinessEntityID IS NOT NULL THEN 'Person (' || per.PersonType || ')'
        WHEN s.BusinessEntityID IS NOT NULL THEN 'Store'
        WHEN v.BusinessEntityID IS NOT NULL THEN 'Vendor'
        ELSE 'Unknown'
    END AS EntityType,
    COALESCE(per.FirstName || ' ' || per.LastName, s.Name, v.Name, 'N/A') AS EntityName,
    at.Name AS AddressType,
    a.City,
    sp.Name AS State,
    cr.Name AS Country,
    st.Name AS SalesTerritory
FROM BusinessEntity be
LEFT JOIN Person per ON be.BusinessEntityID = per.BusinessEntityID
LEFT JOIN Store s ON be.BusinessEntityID = s.BusinessEntityID
LEFT JOIN Vendor v ON be.BusinessEntityID = v.BusinessEntityID
LEFT JOIN BusinessEntityAddress bea ON be.BusinessEntityID = bea.BusinessEntityID
LEFT JOIN AddressType at ON bea.AddressTypeID = at.AddressTypeID
LEFT JOIN Address a ON bea.AddressID = a.AddressID
LEFT JOIN StateProvince sp ON a.StateProvinceID = sp.StateProvinceID
LEFT JOIN CountryRegion cr ON sp.CountryRegionCode = cr.CountryRegionCode
LEFT JOIN SalesTerritory st ON sp.TerritoryID = st.TerritoryID
ORDER BY EntityType, EntityName;
```

---

**Q3: "For every business entity that is a store, show the store name, assigned salesperson, their email, the store's address (city/country), and the store's total sales revenue."**

*10 joins: BusinessEntity → Store → SalesPerson → Employee → Person(rep) → EmailAddress → Customer → SalesOrderHeader → BusinessEntityAddress → Address → StateProvince → CountryRegion*

```sql
SELECT
    be.BusinessEntityID,
    s.Name AS StoreName,
    rep.FirstName || ' ' || rep.LastName AS SalesPersonName,
    ea.EmailAddress AS SalesPersonEmail,
    a.City AS StoreCity,
    cr.Name AS StoreCountry,
    COUNT(DISTINCT soh.SalesOrderID) AS TotalOrders,
    ROUND(SUM(soh.TotalDue), 2) AS TotalRevenue
FROM BusinessEntity be
JOIN Store s ON be.BusinessEntityID = s.BusinessEntityID
LEFT JOIN SalesPerson salp ON s.SalesPersonID = salp.BusinessEntityID
LEFT JOIN Employee e ON salp.BusinessEntityID = e.BusinessEntityID
LEFT JOIN Person rep ON e.BusinessEntityID = rep.BusinessEntityID
LEFT JOIN EmailAddress ea ON rep.BusinessEntityID = ea.BusinessEntityID
LEFT JOIN BusinessEntityAddress bea ON s.BusinessEntityID = bea.BusinessEntityID
LEFT JOIN Address a ON bea.AddressID = a.AddressID
LEFT JOIN StateProvince sp ON a.StateProvinceID = sp.StateProvinceID
LEFT JOIN CountryRegion cr ON sp.CountryRegionCode = cr.CountryRegionCode
LEFT JOIN Customer c ON s.BusinessEntityID = c.StoreID
LEFT JOIN SalesOrderHeader soh ON c.CustomerID = soh.CustomerID
GROUP BY be.BusinessEntityID, s.Name, rep.FirstName, rep.LastName,
         ea.EmailAddress, a.City, cr.Name
ORDER BY TotalRevenue DESC;
```

---

**Q4: "For every vendor entity, show the vendor name, credit rating, address (city/country), their contact person names and roles, the products they supply, and total PO spend."**

*11 joins: BusinessEntity → Vendor → BusinessEntityContact → Person(contact) → ContactType → BusinessEntityAddress → Address → StateProvince → CountryRegion → ProductVendor → Product → PurchaseOrderHeader*

```sql
SELECT
    be.BusinessEntityID,
    v.Name AS VendorName,
    v.CreditRating,
    a.City AS VendorCity,
    cr.Name AS VendorCountry,
    contact.FirstName || ' ' || contact.LastName AS ContactName,
    ct.Name AS ContactRole,
    p.Name AS ProductSupplied,
    COUNT(DISTINCT poh.PurchaseOrderID) AS TotalPOs,
    ROUND(SUM(poh.TotalDue), 2) AS TotalPOSpend
FROM BusinessEntity be
JOIN Vendor v ON be.BusinessEntityID = v.BusinessEntityID
LEFT JOIN BusinessEntityContact bec ON v.BusinessEntityID = bec.BusinessEntityID
LEFT JOIN Person contact ON bec.PersonID = contact.BusinessEntityID
LEFT JOIN ContactType ct ON bec.ContactTypeID = ct.ContactTypeID
LEFT JOIN BusinessEntityAddress bea ON v.BusinessEntityID = bea.BusinessEntityID
LEFT JOIN Address a ON bea.AddressID = a.AddressID
LEFT JOIN StateProvince sp ON a.StateProvinceID = sp.StateProvinceID
LEFT JOIN CountryRegion cr ON sp.CountryRegionCode = cr.CountryRegionCode
LEFT JOIN ProductVendor pv ON v.BusinessEntityID = pv.BusinessEntityID
LEFT JOIN Product p ON pv.ProductID = p.ProductID
LEFT JOIN PurchaseOrderHeader poh ON v.BusinessEntityID = poh.VendorID
GROUP BY be.BusinessEntityID, v.Name, v.CreditRating, a.City, cr.Name,
         contact.FirstName, contact.LastName, ct.Name, p.Name
ORDER BY TotalPOSpend DESC;
```

---

**Q5: "Show the complete entity profile for employees: their BusinessEntityID, name, email, job title, department, home address (city/state/country), pay rate, credit card type, and password age."**

*12 joins: BusinessEntity → Person → Employee → EmployeeDepartmentHistory → Department → EmployeePayHistory → EmailAddress → BusinessEntityAddress → Address → StateProvince → CountryRegion → PersonCreditCard → CreditCard → Password*

```sql
SELECT
    be.BusinessEntityID,
    per.FirstName || ' ' || per.LastName AS EmployeeName,
    ea.EmailAddress,
    e.JobTitle,
    d.Name AS Department,
    a.City,
    sp.Name AS State,
    cr.Name AS Country,
    eph.Rate AS CurrentPayRate,
    cc.CardType,
    CAST(JULIANDAY('now') - JULIANDAY(pwd.ModifiedDate) AS INTEGER) AS PasswordAgeDays
FROM BusinessEntity be
JOIN Person per ON be.BusinessEntityID = per.BusinessEntityID
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
LEFT JOIN EmailAddress ea ON per.BusinessEntityID = ea.BusinessEntityID
LEFT JOIN BusinessEntityAddress bea ON per.BusinessEntityID = bea.BusinessEntityID
LEFT JOIN Address a ON bea.AddressID = a.AddressID
LEFT JOIN StateProvince sp ON a.StateProvinceID = sp.StateProvinceID
LEFT JOIN CountryRegion cr ON sp.CountryRegionCode = cr.CountryRegionCode
LEFT JOIN PersonCreditCard pcc ON per.BusinessEntityID = pcc.BusinessEntityID
LEFT JOIN CreditCard cc ON pcc.CreditCardID = cc.CreditCardID
LEFT JOIN Password pwd ON per.BusinessEntityID = pwd.BusinessEntityID
WHERE e.CurrentFlag = 1
ORDER BY per.LastName;
```

---

### Practical Business Use-Case Queries (5)

---

**Q6: "How do the 20,777 business entities break down by type?"**

*Use case: Data inventory — entity landscape overview*

```sql
SELECT
    CASE
        WHEN per.BusinessEntityID IS NOT NULL AND s.BusinessEntityID IS NOT NULL THEN 'Person + Store'
        WHEN per.BusinessEntityID IS NOT NULL AND v.BusinessEntityID IS NOT NULL THEN 'Person + Vendor'
        WHEN per.BusinessEntityID IS NOT NULL THEN 'Person Only'
        WHEN s.BusinessEntityID IS NOT NULL THEN 'Store Only'
        WHEN v.BusinessEntityID IS NOT NULL THEN 'Vendor Only'
        ELSE 'Orphan (no child record)'
    END AS EntityClassification,
    COUNT(*) AS EntityCount,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM BusinessEntity), 2) AS PctOfTotal
FROM BusinessEntity be
LEFT JOIN Person per ON be.BusinessEntityID = per.BusinessEntityID
LEFT JOIN Store s ON be.BusinessEntityID = s.BusinessEntityID
LEFT JOIN Vendor v ON be.BusinessEntityID = v.BusinessEntityID
GROUP BY EntityClassification
ORDER BY EntityCount DESC;
```

---

**Q7: "Are there orphaned BusinessEntity records — IDs with no Person, Store, or Vendor?"**

*Use case: Data integrity audit*

```sql
SELECT
    be.BusinessEntityID,
    be.rowguid,
    be.ModifiedDate
FROM BusinessEntity be
LEFT JOIN Person per ON be.BusinessEntityID = per.BusinessEntityID
LEFT JOIN Store s ON be.BusinessEntityID = s.BusinessEntityID
LEFT JOIN Vendor v ON be.BusinessEntityID = v.BusinessEntityID
WHERE per.BusinessEntityID IS NULL
    AND s.BusinessEntityID IS NULL
    AND v.BusinessEntityID IS NULL
ORDER BY be.BusinessEntityID;
```

---

**Q8: "How many entities have addresses vs. no addresses, broken down by type?"**

*Use case: Address coverage audit*

```sql
SELECT
    CASE
        WHEN per.BusinessEntityID IS NOT NULL THEN 'Person'
        WHEN s.BusinessEntityID IS NOT NULL THEN 'Store'
        WHEN v.BusinessEntityID IS NOT NULL THEN 'Vendor'
        ELSE 'Unknown'
    END AS EntityType,
    COUNT(DISTINCT be.BusinessEntityID) AS TotalEntities,
    COUNT(DISTINCT bea.BusinessEntityID) AS EntitiesWithAddress,
    COUNT(DISTINCT be.BusinessEntityID) - COUNT(DISTINCT bea.BusinessEntityID) AS EntitiesWithoutAddress,
    ROUND(COUNT(DISTINCT bea.BusinessEntityID) * 100.0
        / COUNT(DISTINCT be.BusinessEntityID), 2) AS AddressCoveragePct
FROM BusinessEntity be
LEFT JOIN Person per ON be.BusinessEntityID = per.BusinessEntityID
LEFT JOIN Store s ON be.BusinessEntityID = s.BusinessEntityID
LEFT JOIN Vendor v ON be.BusinessEntityID = v.BusinessEntityID
LEFT JOIN BusinessEntityAddress bea ON be.BusinessEntityID = bea.BusinessEntityID
GROUP BY EntityType
ORDER BY TotalEntities DESC;
```

---

**Q9: "What's the entity creation trend — how many new entities were created each year?"**

*Use case: Growth tracking*

```sql
SELECT
    strftime('%Y', ModifiedDate) AS Year,
    COUNT(*) AS EntitiesCreated,
    SUM(COUNT(*)) OVER (ORDER BY strftime('%Y', ModifiedDate)) AS CumulativeTotal
FROM BusinessEntity
GROUP BY strftime('%Y', ModifiedDate)
ORDER BY Year;
```

---

**Q10: "Show the highest and lowest BusinessEntityIDs for each entity type — useful for understanding ID range allocation."**

*Use case: DBA / data architecture — ID sequence analysis*

```sql
SELECT
    CASE
        WHEN per.BusinessEntityID IS NOT NULL THEN 'Person'
        WHEN s.BusinessEntityID IS NOT NULL THEN 'Store'
        WHEN v.BusinessEntityID IS NOT NULL THEN 'Vendor'
        ELSE 'Orphan'
    END AS EntityType,
    COUNT(*) AS EntityCount,
    MIN(be.BusinessEntityID) AS MinID,
    MAX(be.BusinessEntityID) AS MaxID,
    MAX(be.BusinessEntityID) - MIN(be.BusinessEntityID) + 1 AS IDRange,
    MIN(be.ModifiedDate) AS EarliestCreated,
    MAX(be.ModifiedDate) AS LatestCreated
FROM BusinessEntity be
LEFT JOIN Person per ON be.BusinessEntityID = per.BusinessEntityID
LEFT JOIN Store s ON be.BusinessEntityID = s.BusinessEntityID
LEFT JOIN Vendor v ON be.BusinessEntityID = v.BusinessEntityID
GROUP BY EntityType
ORDER BY MinID;
```

---
