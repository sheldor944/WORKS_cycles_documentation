# Address

---

## 📋 Short Description

### Style 1: Conceptual Summary
This table stores physical addresses — one row per unique address. It captures the street-level details (AddressLine1, AddressLine2), city (City), geographic region (StateProvinceID → StateProvince → CountryRegion), postal code (PostalCode), and optional geospatial data (SpatialLocation). Addresses are shared across the system — employees, customers, stores, vendors all reference this table through BusinessEntityAddress. Sales orders also reference it directly for billing and shipping addresses.

### Style 2: Query Possibilities & Business Story
This is the master address table — every physical location used anywhere in the system is stored here: employee homes, customer addresses, store locations, vendor offices, billing addresses, shipping destinations. Addresses are deduplicated (unique constraint on the full address combination) and linked to entities through BusinessEntityAddress, and to sales orders directly via BillToAddressID and ShipToAddressID. Use this table to answer questions like:

- "Which cities have the most customers/employees/stores?"
- "What's the geographic distribution of shipping destinations?"
- "How many orders ship to a different address than the billing address?"
- "Which states or countries generate the most sales revenue?"
- "What are the top 10 cities by order volume?"
- "How many unique addresses are in each state/country?"
- "Are there customers in cities where we have no store presence?"
- "What's the average order value by shipping city or state?" (with SalesOrderHeader)
- "Which employee addresses are in the same city as a store?" (with BusinessEntityAddress, Store)
- "What's the sales tax rate for orders shipped to each state?" (with SalesTaxRate, StateProvince)
- "How many vendors are located in each country?" (with BusinessEntityAddress, Vendor)
- "Map all shipping destinations by postal code for logistics planning."

Address connects upward to StateProvince (→ CountryRegion → SalesTerritory) for full geographic context, sideways to BusinessEntityAddress (linking it to people, stores, vendors), and is referenced directly by SalesOrderHeader for billing/shipping.

### Style 3: Grouped & Complete (Column Reference)
This table stores one row per unique address, containing 9 columns organized as:

- **Identifiers:** AddressID (PK, auto-increment), rowguid
- **Street:** AddressLine1 (required), AddressLine2 (optional — suite, apt, floor, etc.)
- **City:** City
- **Region:** StateProvinceID (FK → StateProvince → CountryRegion → SalesTerritory)
- **Postal:** PostalCode
- **Geospatial:** SpatialLocation (nullable — geographic coordinates/geometry data)
- **Audit:** ModifiedDate
- **Uniqueness:** Composite unique on (AddressLine1, AddressLine2, City, StateProvinceID, PostalCode)

---

## 📖 Extensive Description

### Purpose & Business Context

Address is the universal location table — every physical address used across the entire AdventureWorks system is stored here exactly once (deduplicated via the composite unique constraint). It's a shared reference table that doesn't belong to any single entity; instead, entities connect to it through the junction table BusinessEntityAddress (which adds an AddressType like "Home," "Shipping," "Main Office").

The geographic chain Address → StateProvince → CountryRegion → SalesTerritory connects every address to the full geographic hierarchy, enabling location-based analytics from street level to sales territory. Sales orders reference Address directly (BillToAddressID, ShipToAddressID), making this table critical for shipping analytics, logistics planning, and geographic revenue analysis.

### Key Business Logic

- **Addresses are shared** — the same AddressID can be linked to multiple BusinessEntities (e.g., two people at the same address)
- **Deduplication** — the composite unique constraint prevents storing the same address twice
- **AddressLine2** is optional — used for apartment numbers, suite numbers, building floors, etc.
- **StateProvinceID** is the gateway to the full geography chain: StateProvince → CountryRegion (country name + code) → SalesTerritory (sales region)
- **SpatialLocation** stores geographic coordinates — could be used for distance calculations, mapping, or geofencing
- **SalesOrderHeader references Address twice** — BillToAddressID (where to charge) and ShipToAddressID (where to deliver) — these can differ
- **No direct FK from Address to BusinessEntity** — the link goes through BusinessEntityAddress (many-to-many with AddressType)

### Relationships

| Direction | Table | Join Key | Notes |
|-----------|-------|----------|-------|
| → Parent | StateProvince → CountryRegion | StateProvinceID | State/province, country, region |
| ← Via StateProvince | SalesTerritory | TerritoryID | Sales territory for this geography |
| ← Via StateProvince | SalesTaxRate | StateProvinceID | Tax rate applicable at this location |
| ← Junction | BusinessEntityAddress → BusinessEntity | AddressID | Links address to people, stores, vendors |
| ← Junction | BusinessEntityAddress → AddressType | AddressTypeID | Type of address (Home, Main Office, etc.) |
| ← Direct | SalesOrderHeader (BillTo) | BillToAddressID | Billing address for sales orders |
| ← Direct | SalesOrderHeader (ShipTo) | ShipToAddressID | Shipping address for sales orders |
| ← Via BusinessEntity | Person / Employee | BusinessEntityID | People at this address |
| ← Via BusinessEntity | Store | BusinessEntityID | Stores at this address |
| ← Via BusinessEntity | Vendor | BusinessEntityID | Vendors at this address |

---

## 🔗 10 NL → SQL Examples

### Join-Heavy Queries (5)

---

**Q1: "For each address, show the full address details, state/province, country, sales territory, and all business entities (people, stores, vendors) associated with it — including the address type."**

*7 joins: Address → StateProvince → CountryRegion → SalesTerritory → BusinessEntityAddress → AddressType → BusinessEntity*

```sql
SELECT
    a.AddressID,
    a.AddressLine1,
    a.AddressLine2,
    a.City,
    sp.Name AS StateProvince,
    cr.Name AS Country,
    st.Name AS SalesTerritory,
    at.Name AS AddressType,
    bea.BusinessEntityID
FROM Address a
JOIN StateProvince sp ON a.StateProvinceID = sp.StateProvinceID
JOIN CountryRegion cr ON sp.CountryRegionCode = cr.CountryRegionCode
JOIN SalesTerritory st ON sp.TerritoryID = st.TerritoryID
JOIN BusinessEntityAddress bea ON a.AddressID = bea.AddressID
JOIN AddressType at ON bea.AddressTypeID = at.AddressTypeID
JOIN BusinessEntity be ON bea.BusinessEntityID = be.BusinessEntityID
ORDER BY cr.Name, sp.Name, a.City;
```

---

**Q2: "Show all shipping addresses used in sales orders, with the customer name, order total, state, country, sales territory, and the tax rate applicable to that shipping location."**

*9 joins: Address → StateProvince → CountryRegion → SalesTerritory → SalesTaxRate → SalesOrderHeader → Customer → Person*

```sql
SELECT
    soh.SalesOrderNumber,
    per.FirstName || ' ' || per.LastName AS CustomerName,
    a.AddressLine1,
    a.City,
    sp.Name AS ShipState,
    cr.Name AS ShipCountry,
    st.Name AS SalesTerritory,
    str.TaxRate,
    ROUND(soh.TotalDue, 2) AS OrderTotal
FROM Address a
JOIN SalesOrderHeader soh ON a.AddressID = soh.ShipToAddressID
JOIN Customer c ON soh.CustomerID = c.CustomerID
LEFT JOIN Person per ON c.PersonID = per.BusinessEntityID
JOIN StateProvince sp ON a.StateProvinceID = sp.StateProvinceID
JOIN CountryRegion cr ON sp.CountryRegionCode = cr.CountryRegionCode
JOIN SalesTerritory st ON sp.TerritoryID = st.TerritoryID
LEFT JOIN SalesTaxRate str ON sp.StateProvinceID = str.StateProvinceID
ORDER BY soh.OrderDate DESC;
```

---

**Q3: "For each address used as both a billing and shipping address on the same order, show the address, customer name, order details, salesperson name, and territory."**

*9 joins: Address → SalesOrderHeader(bill+ship) → Customer → Person(customer) → SalesPerson → Employee → Person(rep) → SalesTerritory*

```sql
SELECT
    a.AddressLine1,
    a.City,
    sp.Name AS State,
    soh.SalesOrderNumber,
    cust.FirstName || ' ' || cust.LastName AS CustomerName,
    rep.FirstName || ' ' || rep.LastName AS SalesPersonName,
    st.Name AS Territory,
    ROUND(soh.TotalDue, 2) AS OrderTotal
FROM Address a
JOIN SalesOrderHeader soh ON a.AddressID = soh.BillToAddressID
    AND a.AddressID = soh.ShipToAddressID
JOIN Customer c ON soh.CustomerID = c.CustomerID
LEFT JOIN Person cust ON c.PersonID = cust.BusinessEntityID
LEFT JOIN SalesPerson salp ON soh.SalesPersonID = salp.BusinessEntityID
LEFT JOIN Employee e ON salp.BusinessEntityID = e.BusinessEntityID
LEFT JOIN Person rep ON e.BusinessEntityID = rep.BusinessEntityID
JOIN SalesTerritory st ON soh.TerritoryID = st.TerritoryID
JOIN StateProvince sp ON a.StateProvinceID = sp.StateProvinceID
ORDER BY soh.OrderDate DESC;
```

---

**Q4: "Show employee home addresses alongside their job title, department, and compare to the store addresses in the same city — to find employees who live near a store."**

*10 joins: Address → BusinessEntityAddress → AddressType → Person → Employee → EmployeeDepartmentHistory → Department → StateProvince → Store(same city) → BusinessEntityAddress(store)*

```sql
SELECT
    per.FirstName || ' ' || per.LastName AS EmployeeName,
    e.JobTitle,
    d.Name AS Department,
    emp_addr.City AS EmployeeCity,
    emp_sp.Name AS EmployeeState,
    s.Name AS NearbyStore,
    store_addr.AddressLine1 AS StoreAddress,
    store_addr.City AS StoreCity
FROM Address emp_addr
JOIN BusinessEntityAddress emp_bea ON emp_addr.AddressID = emp_bea.AddressID
JOIN Person per ON emp_bea.BusinessEntityID = per.BusinessEntityID
JOIN Employee e ON per.BusinessEntityID = e.BusinessEntityID
JOIN EmployeeDepartmentHistory edh ON e.BusinessEntityID = edh.BusinessEntityID
    AND edh.EndDate IS NULL
JOIN Department d ON edh.DepartmentID = d.DepartmentID
JOIN StateProvince emp_sp ON emp_addr.StateProvinceID = emp_sp.StateProvinceID
JOIN BusinessEntityAddress store_bea ON store_bea.BusinessEntityID IN (
    SELECT BusinessEntityID FROM Store
)
JOIN Address store_addr ON store_bea.AddressID = store_addr.AddressID
JOIN Store s ON store_bea.BusinessEntityID = s.BusinessEntityID
WHERE emp_addr.City = store_addr.City
ORDER BY emp_addr.City, per.LastName;
```

---

**Q5: "For vendor addresses, show the vendor name, credit rating, full address with country, the products they supply with categories, and total PO spend — grouped by vendor location."**

*10 joins: Address → StateProvince → CountryRegion → BusinessEntityAddress → Vendor → ProductVendor → Product → ProductSubcategory → ProductCategory → PurchaseOrderHeader*

```sql
SELECT
    v.Name AS VendorName,
    v.CreditRating,
    a.AddressLine1,
    a.City,
    sp.Name AS State,
    cr.Name AS Country,
    p.Name AS ProductSupplied,
    pcat.Name AS ProductCategory,
    COUNT(DISTINCT poh.PurchaseOrderID) AS TotalPOs,
    ROUND(SUM(poh.TotalDue), 2) AS TotalPOSpend
FROM Address a
JOIN StateProvince sp ON a.StateProvinceID = sp.StateProvinceID
JOIN CountryRegion cr ON sp.CountryRegionCode = cr.CountryRegionCode
JOIN BusinessEntityAddress bea ON a.AddressID = bea.AddressID
JOIN Vendor v ON bea.BusinessEntityID = v.BusinessEntityID
LEFT JOIN ProductVendor pv ON v.BusinessEntityID = pv.BusinessEntityID
LEFT JOIN Product p ON pv.ProductID = p.ProductID
LEFT JOIN ProductSubcategory psub ON p.ProductSubcategoryID = psub.ProductSubcategoryID
LEFT JOIN ProductCategory pcat ON psub.ProductCategoryID = pcat.ProductCategoryID
LEFT JOIN PurchaseOrderHeader poh ON v.BusinessEntityID = poh.VendorID
GROUP BY v.Name, v.CreditRating, a.AddressLine1, a.City, sp.Name, cr.Name,
         p.Name, pcat.Name
ORDER BY TotalPOSpend DESC;
```

---

### Practical Business Use-Case Queries (5)

---

**Q6: "Which cities have the most shipping destinations, and what's the total revenue shipped to each?"**

*Use case: Logistics — shipping volume hotspots*

```sql
SELECT
    a.City,
    sp.Name AS State,
    COUNT(DISTINCT soh.SalesOrderID) AS OrdersShippedHere,
    COUNT(DISTINCT soh.CustomerID) AS UniqueCustomers,
    ROUND(SUM(soh.TotalDue), 2) AS TotalRevenue,
    ROUND(SUM(soh.Freight), 2) AS TotalFreight
FROM Address a
JOIN SalesOrderHeader soh ON a.AddressID = soh.ShipToAddressID
JOIN StateProvince sp ON a.StateProvinceID = sp.StateProvinceID
GROUP BY a.City, sp.Name
ORDER BY TotalRevenue DESC
LIMIT 20;
```

---

**Q7: "How many orders have different billing and shipping addresses — and what's the revenue from those split-address orders?"**

*Use case: Fulfillment — gift orders / drop-ship detection*

```sql
SELECT
    CASE
        WHEN BillToAddressID = ShipToAddressID THEN 'Same Address'
        ELSE 'Different Addresses'
    END AS AddressMatch,
    COUNT(*) AS OrderCount,
    ROUND(SUM(TotalDue), 2) AS TotalRevenue,
    ROUND(AVG(TotalDue), 2) AS AvgOrderValue,
    ROUND(SUM(Freight), 2) AS TotalFreight
FROM SalesOrderHeader
GROUP BY CASE WHEN BillToAddressID = ShipToAddressID THEN 'Same Address' ELSE 'Different Addresses' END;
```

---

**Q8: "What's the geographic distribution of all addresses by country and state?"**

*Use case: Data inventory — geographic footprint*

```sql
SELECT
    cr.Name AS Country,
    sp.Name AS StateProvince,
    COUNT(*) AS AddressCount,
    COUNT(DISTINCT a.City) AS UniqueCities,
    COUNT(DISTINCT a.PostalCode) AS UniquePostalCodes
FROM Address a
JOIN StateProvince sp ON a.StateProvinceID = sp.StateProvinceID
JOIN CountryRegion cr ON sp.CountryRegionCode = cr.CountryRegionCode
GROUP BY cr.Name, sp.Name
ORDER BY AddressCount DESC;
```

---

**Q9: "Find addresses that are used by multiple business entities — shared locations like office buildings or business parks."**

*Use case: Data quality / shared location analysis*

```sql
SELECT
    a.AddressID,
    a.AddressLine1,
    a.City,
    sp.Name AS State,
    COUNT(DISTINCT bea.BusinessEntityID) AS EntitiesAtAddress,
    GROUP_CONCAT(DISTINCT bea.BusinessEntityID) AS EntityIDs
FROM Address a
JOIN BusinessEntityAddress bea ON a.AddressID = bea.AddressID
JOIN StateProvince sp ON a.StateProvinceID = sp.StateProvinceID
GROUP BY a.AddressID, a.AddressLine1, a.City, sp.Name
HAVING COUNT(DISTINCT bea.BusinessEntityID) > 1
ORDER BY EntitiesAtAddress DESC;
```

---

**Q10: "Which postal codes have the highest average order value for shipped orders?"**

*Use case: Marketing — high-value geographic targeting*

```sql
SELECT
    a.PostalCode,
    a.City,
    sp.Name AS State,
    COUNT(DISTINCT soh.SalesOrderID) AS Orders,
    ROUND(AVG(soh.TotalDue), 2) AS AvgOrderValue,
    ROUND(SUM(soh.TotalDue), 2) AS TotalRevenue,
    COUNT(DISTINCT soh.CustomerID) AS UniqueCustomers
FROM Address a
JOIN SalesOrderHeader soh ON a.AddressID = soh.ShipToAddressID
JOIN StateProvince sp ON a.StateProvinceID = sp.StateProvinceID
GROUP BY a.PostalCode, a.City, sp.Name
HAVING COUNT(DISTINCT soh.SalesOrderID) >= 5
ORDER BY AvgOrderValue DESC
LIMIT 20;
```

---
