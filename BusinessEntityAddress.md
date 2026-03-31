# BusinessEntityAddress

---

## 📋 Short Description

### Style 1: Conceptual Summary
This table is a junction/bridge table linking business entities to their addresses — one row per entity-address-type combination (19,614 records). It captures which entity (BusinessEntityID → BusinessEntity) has which address (AddressID → Address) and what kind of address it is (AddressTypeID → AddressType — e.g., Home, Main Office, Shipping, Billing, Archive). This is the universal address assignment table — employees, customers, stores, and vendors all get their addresses through this bridge.

### Style 2: Query Possibilities & Business Story
This is the glue table that connects people, stores, and vendors to their physical addresses. No entity has an address directly — they all go through this junction table, which also tags each address with a type (Home, Main Office, Shipping, etc.). A single entity can have multiple addresses of different types, and the same address can be shared by multiple entities. Use this table to answer questions like:

- "What's an employee's home address?" (join to Person, Employee, Address)
- "Where is a store's main office located?" (join to Store, Address, AddressType)
- "Which vendor has a shipping address in Canada?" (join to Vendor, Address, StateProvince, CountryRegion)
- "How many addresses does each entity have on file?"
- "Which address types are most common?"
- "Are there entities with no address on file?" (LEFT JOIN from BusinessEntity)
- "Which entities share the same physical address?"
- "How many employees live in each city/state?" (join to Employee, Address, StateProvince)
- "What's the geographic distribution of stores by country?" (join to Store, Address, StateProvince, CountryRegion)
- "Which customers have both a billing and shipping address on file?"
- "Find all entities at a specific address." 
- "How does the sales territory of a customer's address match the territory on their orders?" (join to Address, StateProvince, SalesTerritory, SalesOrderHeader)

This table sits at the center of the geographic data model: BusinessEntity ← **BusinessEntityAddress** → Address → StateProvince → CountryRegion → SalesTerritory.

### Style 3: Grouped & Complete (Column Reference)
This table stores one row per business-entity-address-type combination (19,614 rows), containing 5 columns organized as:

- **Composite PK:** BusinessEntityID (FK → BusinessEntity), AddressID (FK → Address), AddressTypeID (FK → AddressType)
- **Identifiers:** rowguid (unique GUID)
- **Audit:** ModifiedDate

---

## 📖 Extensive Description

### Purpose & Business Context

BusinessEntityAddress is the universal junction table that connects every entity in the system — people (employees, customers, contacts), stores, and vendors — to their physical addresses. The three-part composite primary key (BusinessEntityID + AddressID + AddressTypeID) means an entity can have the same address registered under different types (e.g., Home + Shipping), and different entities can share the same address (e.g., two employees at the same household).

With 19,614 records linking to ~20,777 BusinessEntities, most entities have exactly one address, but some have multiple (different types) and a few may have none. The AddressType dimension (6 types) adds semantic meaning — you're not just asking "where is this entity?" but "where is this entity's home? office? shipping dock?"

This is a pure bridge table with no business data of its own — its value is entirely in the connections it creates between the entity model and the geographic model.

### Key Business Logic

- **Composite PK (BusinessEntityID, AddressID, AddressTypeID)** — the same entity can have the same address under different types, and the same entity can have different addresses of the same type (unlikely but schema-valid)
- **AddressType** (6 rows) typically includes: Home, Main Office, Shipping, Billing, Primary, Archive
- **One entity can have multiple addresses** — e.g., an employee with a Home address and a Shipping address
- **Multiple entities can share one address** — e.g., a married couple, or a store and its owner
- **Not all BusinessEntities may have an address** — LEFT JOIN from BusinessEntity to find gaps
- **SalesOrderHeader references Address directly** (BillToAddressID, ShipToAddressID) — it does NOT go through this junction table for order addresses; this table is for entity-level address assignments
- **To get the full geographic chain**: BusinessEntityAddress → Address → StateProvince → CountryRegion → SalesTerritory

### Relationships

| Direction | Table | Join Key | Notes |
|-----------|-------|----------|-------|
| → Parent | BusinessEntity | BusinessEntityID | The entity (person, store, vendor) |
| → Parent | Address | AddressID | The physical address |
| → Parent | AddressType | AddressTypeID | Type of address (Home, Office, etc.) |
| ← Via BusinessEntity | Person → Employee | BusinessEntityID | Employee addresses |
| ← Via BusinessEntity | Person (PersonType='IN') → Customer | BusinessEntityID | Customer addresses |
| ← Via BusinessEntity | Store | BusinessEntityID | Store locations |
| ← Via BusinessEntity | Vendor | BusinessEntityID | Vendor locations |
| ← Via Address | StateProvince → CountryRegion | StateProvinceID | Geographic chain |
| ← Via Address → StateProvince | SalesTerritory | TerritoryID | Sales territory |
| ← Via Address → StateProvince | SalesTaxRate | StateProvinceID | Applicable tax rate |
| Related | SalesOrderHeader | BillToAddressID / ShipToAddressID | Order-level addresses (direct, not through this junction) |

---

## 🔗 10 NL → SQL Examples

### Join-Heavy Queries (5)

---

**Q1: "For every employee, show their full name, job title, department, address type, full address with city/state/country, and the sales territory their address falls under."**

*9 joins: BusinessEntityAddress → Address → StateProvince → CountryRegion → SalesTerritory → AddressType → BusinessEntity → Person → Employee → EmployeeDepartmentHistory → Department*

```sql
SELECT
    per.FirstName || ' ' || per.LastName AS EmployeeName,
    e.JobTitle,
    d.Name AS Department,
    at.Name AS AddressType,
    a.AddressLine1,
    a.AddressLine2,
    a.City,
    sp.Name AS StateProvince,
    cr.Name AS Country,
    a.PostalCode,
    st.Name AS SalesTerritory
FROM BusinessEntityAddress bea
JOIN AddressType at ON bea.AddressTypeID = at.AddressTypeID
JOIN Address a ON bea.AddressID = a.AddressID
JOIN StateProvince sp ON a.StateProvinceID = sp.StateProvinceID
JOIN CountryRegion cr ON sp.CountryRegionCode = cr.CountryRegionCode
JOIN SalesTerritory st ON sp.TerritoryID = st.TerritoryID
JOIN Person per ON bea.BusinessEntityID = per.BusinessEntityID
JOIN Employee e ON per.BusinessEntityID = e.BusinessEntityID
JOIN EmployeeDepartmentHistory edh ON e.BusinessEntityID = edh.BusinessEntityID
    AND edh.EndDate IS NULL
JOIN Department d ON edh.DepartmentID = d.DepartmentID
ORDER BY cr.Name, sp.Name, a.City;
```

---

**Q2: "For every store, show the store name, assigned salesperson name, address type, full address with country, the currency used in that country, and total sales orders from that store."**

*11 joins: BusinessEntityAddress → Address → StateProvince → CountryRegion → CountryRegionCurrency → Currency → AddressType → Store → SalesPerson → Person → Customer → SalesOrderHeader*

```sql
SELECT
    s.Name AS StoreName,
    rep.FirstName || ' ' || rep.LastName AS SalesPersonName,
    at.Name AS AddressType,
    a.City,
    sp.Name AS StateProvince,
    cr.Name AS Country,
    cur.Name AS LocalCurrency,
    COUNT(DISTINCT soh.SalesOrderID) AS TotalOrders,
    ROUND(SUM(soh.TotalDue), 2) AS TotalRevenue
FROM BusinessEntityAddress bea
JOIN AddressType at ON bea.AddressTypeID = at.AddressTypeID
JOIN Address a ON bea.AddressID = a.AddressID
JOIN StateProvince sp ON a.StateProvinceID = sp.StateProvinceID
JOIN CountryRegion cr ON sp.CountryRegionCode = cr.CountryRegionCode
LEFT JOIN CountryRegionCurrency crc ON cr.CountryRegionCode = crc.CountryRegionCode
LEFT JOIN Currency cur ON crc.CurrencyCode = cur.CurrencyCode
JOIN Store s ON bea.BusinessEntityID = s.BusinessEntityID
LEFT JOIN SalesPerson salp ON s.SalesPersonID = salp.BusinessEntityID
LEFT JOIN Person rep ON salp.BusinessEntityID = rep.BusinessEntityID
LEFT JOIN Customer c ON s.BusinessEntityID = c.StoreID
LEFT JOIN SalesOrderHeader soh ON c.CustomerID = soh.CustomerID
GROUP BY s.Name, rep.FirstName, rep.LastName, at.Name, a.City, sp.Name,
         cr.Name, cur.Name
ORDER BY TotalRevenue DESC;
```

---

**Q3: "For each vendor, show their name, credit rating, address with country, the products they supply with categories, and the tax rate applicable to their location."**

*10 joins: BusinessEntityAddress → Address → StateProvince → CountryRegion → SalesTaxRate → AddressType → Vendor → ProductVendor → Product → ProductSubcategory → ProductCategory*

```sql
SELECT
    v.Name AS VendorName,
    v.CreditRating,
    at.Name AS AddressType,
    a.City,
    sp.Name AS State,
    cr.Name AS Country,
    str.TaxRate AS LocalTaxRate,
    p.Name AS ProductSupplied,
    pcat.Name AS ProductCategory,
    pv.StandardPrice AS VendorPrice
FROM BusinessEntityAddress bea
JOIN AddressType at ON bea.AddressTypeID = at.AddressTypeID
JOIN Address a ON bea.AddressID = a.AddressID
JOIN StateProvince sp ON a.StateProvinceID = sp.StateProvinceID
JOIN CountryRegion cr ON sp.CountryRegionCode = cr.CountryRegionCode
LEFT JOIN SalesTaxRate str ON sp.StateProvinceID = str.StateProvinceID
JOIN Vendor v ON bea.BusinessEntityID = v.BusinessEntityID
LEFT JOIN ProductVendor pv ON v.BusinessEntityID = pv.BusinessEntityID
LEFT JOIN Product p ON pv.ProductID = p.ProductID
LEFT JOIN ProductSubcategory psub ON p.ProductSubcategoryID = psub.ProductSubcategoryID
LEFT JOIN ProductCategory pcat ON psub.ProductCategoryID = pcat.ProductCategoryID
ORDER BY cr.Name, v.Name;
```

---

**Q4: "For individual customers, show their name, email, home address, the sales territory of their address, and compare it to the territory of their most recent order — do they match?"**

*10 joins: BusinessEntityAddress → Address → StateProvince → SalesTerritory(address) → AddressType → Person → EmailAddress → Customer → SalesOrderHeader → SalesTerritory(order)*

```sql
SELECT
    per.FirstName || ' ' || per.LastName AS CustomerName,
    ea.EmailAddress,
    at.Name AS AddressType,
    a.City,
    sp.Name AS AddressState,
    addr_st.Name AS AddressTerritoryName,
    order_st.Name AS OrderTerritoryName,
    CASE
        WHEN addr_st.TerritoryID = soh.TerritoryID THEN 'MATCH'
        ELSE 'MISMATCH'
    END AS TerritoryAlignment,
    soh.SalesOrderNumber,
    ROUND(soh.TotalDue, 2) AS OrderTotal
FROM BusinessEntityAddress bea
JOIN AddressType at ON bea.AddressTypeID = at.AddressTypeID
JOIN Address a ON bea.AddressID = a.AddressID
JOIN StateProvince sp ON a.StateProvinceID = sp.StateProvinceID
JOIN SalesTerritory addr_st ON sp.TerritoryID = addr_st.TerritoryID
JOIN Person per ON bea.BusinessEntityID = per.BusinessEntityID
LEFT JOIN EmailAddress ea ON per.BusinessEntityID = ea.BusinessEntityID
JOIN Customer c ON per.BusinessEntityID = c.PersonID
JOIN SalesOrderHeader soh ON c.CustomerID = soh.CustomerID
    AND soh.OrderDate = (
        SELECT MAX(soh2.OrderDate)
        FROM SalesOrderHeader soh2
        WHERE soh2.CustomerID = c.CustomerID
    )
JOIN SalesTerritory order_st ON soh.TerritoryID = order_st.TerritoryID
WHERE per.PersonType = 'IN'
ORDER BY per.LastName;
```

---

**Q5: "Show all business entity contacts (vendor/store contacts) with their name, contact role, the entity they're associated with (store or vendor), that entity's address, and the entity's purchase order or sales order activity."**

*11 joins: BusinessEntityAddress → Address → StateProvince → CountryRegion → AddressType → BusinessEntityContact → Person → ContactType → Store/Vendor → SalesOrderHeader/PurchaseOrderHeader*

```sql
SELECT
    per.FirstName || ' ' || per.LastName AS ContactName,
    ct.Name AS ContactRole,
    COALESCE(s.Name, v.Name) AS EntityName,
    CASE
        WHEN s.BusinessEntityID IS NOT NULL THEN 'Store'
        WHEN v.BusinessEntityID IS NOT NULL THEN 'Vendor'
        ELSE 'Other'
    END AS EntityType,
    at.Name AS AddressType,
    a.City,
    sp.Name AS State,
    cr.Name AS Country,
    COALESCE(store_orders.OrderCount, 0) AS StoreOrders,
    COALESCE(vendor_pos.POCount, 0) AS VendorPOs
FROM BusinessEntityAddress bea
JOIN AddressType at ON bea.AddressTypeID = at.AddressTypeID
JOIN Address a ON bea.AddressID = a.AddressID
JOIN StateProvince sp ON a.StateProvinceID = sp.StateProvinceID
JOIN CountryRegion cr ON sp.CountryRegionCode = cr.CountryRegionCode
JOIN BusinessEntityContact bec ON bea.BusinessEntityID = bec.BusinessEntityID
JOIN Person per ON bec.PersonID = per.BusinessEntityID
JOIN ContactType ct ON bec.ContactTypeID = ct.ContactTypeID
LEFT JOIN Store s ON bea.BusinessEntityID = s.BusinessEntityID
LEFT JOIN Vendor v ON bea.BusinessEntityID = v.BusinessEntityID
LEFT JOIN (
    SELECT c.StoreID, COUNT(*) AS OrderCount
    FROM Customer c JOIN SalesOrderHeader soh ON c.CustomerID = soh.CustomerID
    WHERE c.StoreID IS NOT NULL
    GROUP BY c.StoreID
) store_orders ON s.BusinessEntityID = store_orders.StoreID
LEFT JOIN (
    SELECT VendorID, COUNT(*) AS POCount
    FROM PurchaseOrderHeader GROUP BY VendorID
) vendor_pos ON v.BusinessEntityID = vendor_pos.VendorID
ORDER BY EntityType, EntityName;
```

---

### Practical Business Use-Case Queries (5)

---

**Q6: "What's the distribution of address types across all entities?"**

*Use case: Data inventory — understanding address coverage*

```sql
SELECT
    at.Name AS AddressType,
    COUNT(*) AS AssignmentCount,
    COUNT(DISTINCT bea.BusinessEntityID) AS UniqueEntities,
    COUNT(DISTINCT bea.AddressID) AS UniqueAddresses,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM BusinessEntityAddress), 2) AS PctOfTotal
FROM BusinessEntityAddress bea
JOIN AddressType at ON bea.AddressTypeID = at.AddressTypeID
GROUP BY at.Name
ORDER BY AssignmentCount DESC;
```

---

**Q7: "How many addresses does each entity have, and who has the most?"**

*Use case: Data quality — multi-address entities*

```sql
SELECT
    BusinessEntityID,
    COUNT(*) AS AddressCount,
    COUNT(DISTINCT AddressID) AS UniqueAddresses,
    COUNT(DISTINCT AddressTypeID) AS AddressTypesUsed,
    GROUP_CONCAT(DISTINCT AddressTypeID) AS AddressTypeIDs
FROM BusinessEntityAddress
GROUP BY BusinessEntityID
HAVING COUNT(*) > 1
ORDER BY AddressCount DESC
LIMIT 20;
```

---

**Q8: "Which business entities have NO address on file?"**

*Use case: Data completeness audit*

```sql
SELECT
    be.BusinessEntityID,
    CASE
        WHEN per.BusinessEntityID IS NOT NULL THEN 'Person (' || per.PersonType || ')'
        WHEN s.BusinessEntityID IS NOT NULL THEN 'Store'
        WHEN v.BusinessEntityID IS NOT NULL THEN 'Vendor'
        ELSE 'Unknown'
    END AS EntityType,
    COALESCE(per.FirstName || ' ' || per.LastName, s.Name, v.Name, 'N/A') AS EntityName
FROM BusinessEntity be
LEFT JOIN BusinessEntityAddress bea ON be.BusinessEntityID = bea.BusinessEntityID
LEFT JOIN Person per ON be.BusinessEntityID = per.BusinessEntityID
LEFT JOIN Store s ON be.BusinessEntityID = s.BusinessEntityID
LEFT JOIN Vendor v ON be.BusinessEntityID = v.BusinessEntityID
WHERE bea.BusinessEntityID IS NULL
ORDER BY EntityType;
```

---

**Q9: "How many entities are at each unique address — find shared addresses (e.g., same household, same office building)?"**

*Use case: Duplicate detection / household identification*

```sql
SELECT
    bea.AddressID,
    a.AddressLine1,
    a.City,
    COUNT(DISTINCT bea.BusinessEntityID) AS EntitiesHere,
    GROUP_CONCAT(DISTINCT bea.BusinessEntityID) AS EntityIDs,
    GROUP_CONCAT(DISTINCT at.Name) AS AddressTypes
FROM BusinessEntityAddress bea
JOIN Address a ON bea.AddressID = a.AddressID
JOIN AddressType at ON bea.AddressTypeID = at.AddressTypeID
GROUP BY bea.AddressID, a.AddressLine1, a.City
HAVING COUNT(DISTINCT bea.BusinessEntityID) > 1
ORDER BY EntitiesHere DESC
LIMIT 20;
```

---

**Q10: "What's the geographic breakdown of all entity-address assignments by country?"**

*Use case: Geographic footprint — where are our entities located?*

```sql
SELECT
    cr.Name AS Country,
    sp.Name AS StateProvince,
    COUNT(*) AS TotalAssignments,
    COUNT(DISTINCT bea.BusinessEntityID) AS UniqueEntities,
    COUNT(DISTINCT bea.AddressID) AS UniqueAddresses,
    COUNT(DISTINCT at.Name) AS AddressTypesUsed
FROM BusinessEntityAddress bea
JOIN AddressType at ON bea.AddressTypeID = at.AddressTypeID
JOIN Address a ON bea.AddressID = a.AddressID
JOIN StateProvince sp ON a.StateProvinceID = sp.StateProvinceID
JOIN CountryRegion cr ON sp.CountryRegionCode = cr.CountryRegionCode
GROUP BY cr.Name, sp.Name
ORDER BY TotalAssignments DESC;
```

---
