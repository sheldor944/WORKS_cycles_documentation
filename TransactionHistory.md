# TransactionHistory

---

## 📋 Short Description

### Style 1: Conceptual Summary
This table stores active/current product transactions — one row per transaction (113,443 records). It captures which product was involved (ProductID), the type of transaction (TransactionType — W=Work Order, S=Sales Order, P=Purchase Order), a reference back to the originating order (ReferenceOrderID, ReferenceOrderLineID), when it occurred (TransactionDate), and the financial impact (Quantity, ActualCost). This is the live/active counterpart to TransactionHistoryArchive (89,253 rows) — together they form the complete audit trail of every product movement in the system.

### Style 2: Query Possibilities & Business Story
This is the active audit trail for all product-level transactions — every time a product is sold, purchased from a vendor, or manufactured on the shop floor, a transaction record is created here. It covers all three transaction streams in one table: sales (S), purchasing (P), and manufacturing (W). Unlike TransactionHistoryArchive, this table has an enforced FK to Product and auto-incrementing IDs. Use this table to answer questions like:

- "What's the total transaction volume and cost by transaction type?"
- "Which products have the highest transaction activity right now?"
- "What's the actual cost trend for a specific product over time?"
- "How many sales vs. purchase vs. manufacturing transactions occurred this month?"
- "Which products have the highest total actual cost across all transaction types?"
- "Can I trace a specific sales order's cost impact through the transaction log?"
- "What's the daily/weekly/monthly transaction volume trend?"
- "Which products have transactions but no corresponding active orders?" (data quality check)
- "What's the full transaction history for a product?" (UNION with TransactionHistoryArchive)
- "How does manufacturing transaction volume compare to sales transaction volume by product?"
- "What's the total cost of goods for products manufactured vs. purchased?"
- "Which products have the most frequent transactions — indicating high turnover?"

Each transaction links to the Product involved and logically back to the source order (SalesOrderHeader, PurchaseOrderHeader, or WorkOrder) via ReferenceOrderID. Combined with the archive table, it provides the complete financial audit trail for every product.

### Style 3: Grouped & Complete (Column Reference)
This table stores one row per active product transaction (113,443 rows), containing 9 columns organized as:

- **Identifiers:** TransactionID (PK, auto-increment)
- **Product:** ProductID (FK → Product)
- **Source Order:** ReferenceOrderID (originating order ID), ReferenceOrderLineID (line item, default 0)
- **Transaction Details:** TransactionDate, TransactionType (W=Work Order, S=Sales Order, P=Purchase Order)
- **Financials:** Quantity (units involved), ActualCost (monetary impact)
- **Audit:** ModifiedDate

---

## 📖 Extensive Description

### Purpose & Business Context

TransactionHistory is the live financial audit trail for all product movements — 113,443 active records covering sales, procurement, and manufacturing. Every time a product changes hands or state (sold to a customer, received from a vendor, or produced on the shop floor), a record is logged here with the cost and quantity.

This table and its archived sibling (TransactionHistoryArchive, 89,253 rows) together hold **202,696 total transaction records** — the most comprehensive financial audit data in the database. The split exists for performance: active/recent transactions stay here, older ones get archived.

The three transaction types effectively tell the complete cost story for every product:
- **P (Purchase)** — "We spent $X buying this product from a vendor"
- **W (Work Order)** — "We spent $X manufacturing this product"  
- **S (Sales)** — "This product was sold, costing us $X in COGS"

### Key Business Logic

- **TransactionID is auto-increment** here (unlike Archive where it preserves original IDs)
- **TransactionType** values: 'W' (Work Order), 'S' (Sales), 'P' (Purchase)
- **ReferenceOrderID** maps to different tables based on TransactionType:
  - 'W' → WorkOrder.WorkOrderID
  - 'S' → SalesOrderHeader.SalesOrderID
  - 'P' → PurchaseOrderHeader.PurchaseOrderID
- **ReferenceOrderLineID** maps to the line item detail (0 = header-level)
- **ProductID has enforced FK** to Product (unlike the Archive table)
- **ActualCost** = the real cost incurred (for S type, this is COGS not revenue)
- **Quantity** = units involved in the transaction
- **To get complete history**: `SELECT * FROM TransactionHistory UNION ALL SELECT * FROM TransactionHistoryArchive`
- Records eventually migrate to TransactionHistoryArchive based on age/retention policy

### Relationships

| Direction | Table | Join Key | Notes |
|-----------|-------|----------|-------|
| → Parent | Product | ProductID | Product involved (enforced FK) |
| → Logical | WorkOrder | ReferenceOrderID (when Type='W') | Manufacturing source |
| → Logical | SalesOrderHeader | ReferenceOrderID (when Type='S') | Sales source |
| → Logical | PurchaseOrderHeader | ReferenceOrderID (when Type='P') | Purchasing source |
| → Logical | SalesOrderDetail | ReferenceOrderID + ReferenceOrderLineID (Type='S') | Sales line item |
| → Logical | PurchaseOrderDetail | ReferenceOrderID + ReferenceOrderLineID (Type='P') | Purchase line item |
| → Logical | WorkOrderRouting | ReferenceOrderID (Type='W') | Manufacturing operations |
| ← Via Product | ProductSubcategory → ProductCategory | ProductSubcategoryID | Product classification |
| Sibling | TransactionHistoryArchive (89,253) | Same schema — UNION for full history | Archived transactions |

---

## 🔗 10 NL → SQL Examples

### Join-Heavy Queries (5)

---

**Q1: "For each sales-type transaction, show the product name, category, the sales order number, customer name, salesperson name, territory, and compare the transaction's actual cost to the product's list price."**

*9 joins: TransactionHistory → Product → ProductSubcategory → ProductCategory → SalesOrderHeader → Customer → Person(customer) → SalesPerson → Person(rep) → SalesTerritory*

```sql
SELECT
    th.TransactionID,
    th.TransactionDate,
    p.Name AS ProductName,
    pcat.Name AS Category,
    soh.SalesOrderNumber,
    cust.FirstName || ' ' || cust.LastName AS CustomerName,
    rep.FirstName || ' ' || rep.LastName AS SalesPersonName,
    st.Name AS Territory,
    th.Quantity,
    ROUND(th.ActualCost, 2) AS ActualCost,
    p.ListPrice,
    ROUND(p.ListPrice * th.Quantity - th.ActualCost, 2) AS ImpliedMargin
FROM TransactionHistory th
JOIN Product p ON th.ProductID = p.ProductID
LEFT JOIN ProductSubcategory psub ON p.ProductSubcategoryID = psub.ProductSubcategoryID
LEFT JOIN ProductCategory pcat ON psub.ProductCategoryID = pcat.ProductCategoryID
LEFT JOIN SalesOrderHeader soh ON th.ReferenceOrderID = soh.SalesOrderID
LEFT JOIN Customer c ON soh.CustomerID = c.CustomerID
LEFT JOIN Person cust ON c.PersonID = cust.BusinessEntityID
LEFT JOIN SalesPerson sp ON soh.SalesPersonID = sp.BusinessEntityID
LEFT JOIN Person rep ON sp.BusinessEntityID = rep.BusinessEntityID
LEFT JOIN SalesTerritory st ON soh.TerritoryID = st.TerritoryID
WHERE th.TransactionType = 'S'
ORDER BY th.TransactionDate DESC;
```

---

**Q2: "For purchase-type transactions, show the product name, vendor name, vendor city/country, employee who approved the PO, the ship method, and compare transaction cost to the vendor's catalog price."**

*11 joins: TransactionHistory → Product → ProductSubcategory → ProductCategory → PurchaseOrderHeader → Vendor → BusinessEntityAddress → Address → StateProvince → CountryRegion → Employee → Person → ShipMethod → ProductVendor*

```sql
SELECT
    th.TransactionID,
    th.TransactionDate,
    p.Name AS ProductName,
    pcat.Name AS Category,
    v.Name AS VendorName,
    a.City AS VendorCity,
    cr.Name AS VendorCountry,
    per.FirstName || ' ' || per.LastName AS POApprover,
    sm.Name AS ShipMethod,
    th.Quantity,
    ROUND(th.ActualCost, 2) AS TxnActualCost,
    pv.StandardPrice AS VendorCatalogPrice,
    ROUND(th.ActualCost - (pv.StandardPrice * th.Quantity), 2) AS CostVsCatalog
FROM TransactionHistory th
JOIN Product p ON th.ProductID = p.ProductID
LEFT JOIN ProductSubcategory psub ON p.ProductSubcategoryID = psub.ProductSubcategoryID
LEFT JOIN ProductCategory pcat ON psub.ProductCategoryID = pcat.ProductCategoryID
LEFT JOIN PurchaseOrderHeader poh ON th.ReferenceOrderID = poh.PurchaseOrderID
LEFT JOIN Vendor v ON poh.VendorID = v.BusinessEntityID
LEFT JOIN BusinessEntityAddress bea ON v.BusinessEntityID = bea.BusinessEntityID
LEFT JOIN Address a ON bea.AddressID = a.AddressID
LEFT JOIN StateProvince spr ON a.StateProvinceID = spr.StateProvinceID
LEFT JOIN CountryRegion cr ON spr.CountryRegionCode = cr.CountryRegionCode
LEFT JOIN Employee e ON poh.EmployeeID = e.BusinessEntityID
LEFT JOIN Person per ON e.BusinessEntityID = per.BusinessEntityID
LEFT JOIN ShipMethod sm ON poh.ShipMethodID = sm.ShipMethodID
LEFT JOIN ProductVendor pv ON p.ProductID = pv.ProductID AND v.BusinessEntityID = pv.BusinessEntityID
WHERE th.TransactionType = 'P'
ORDER BY th.TransactionDate DESC;
```

---

**Q3: "For work order transactions, show the product name, category, work order details (quantity, scrap), manufacturing locations used, resource hours, and the routing cost vs. the transaction's actual cost."**

*8 joins: TransactionHistory → Product → ProductSubcategory → ProductCategory → WorkOrder → ScrapReason → WorkOrderRouting → Location*

```sql
SELECT
    th.TransactionID,
    th.TransactionDate,
    p.Name AS ProductName,
    pcat.Name AS Category,
    wo.OrderQty AS WO_OrderQty,
    wo.StockedQty,
    wo.ScrappedQty,
    sr.Name AS ScrapReason,
    loc.Name AS MfgLocation,
    ROUND(wor.ActualResourceHrs, 1) AS ResourceHrs,
    ROUND(wor.ActualCost, 2) AS RoutingStepCost,
    th.Quantity AS TxnQty,
    ROUND(th.ActualCost, 2) AS TxnActualCost
FROM TransactionHistory th
JOIN Product p ON th.ProductID = p.ProductID
LEFT JOIN ProductSubcategory psub ON p.ProductSubcategoryID = psub.ProductSubcategoryID
LEFT JOIN ProductCategory pcat ON psub.ProductCategoryID = pcat.ProductCategoryID
LEFT JOIN WorkOrder wo ON th.ReferenceOrderID = wo.WorkOrderID
LEFT JOIN ScrapReason sr ON wo.ScrapReasonID = sr.ScrapReasonID
LEFT JOIN WorkOrderRouting wor ON wo.WorkOrderID = wor.WorkOrderID
LEFT JOIN Location loc ON wor.LocationID = loc.LocationID
WHERE th.TransactionType = 'W'
ORDER BY th.TransactionDate DESC;
```

---

**Q4: "Show the complete active transaction log for each product alongside its bill of materials components, current inventory levels, and product model description — to understand cost flows in context."**

*9 joins: TransactionHistory → Product → ProductSubcategory → ProductCategory → ProductModel → ProductModelProductDescriptionCulture → ProductDescription → BillOfMaterials → ProductInventory → Location*

```sql
SELECT
    p.Name AS ProductName,
    pcat.Name AS Category,
    pm.Name AS ModelName,
    pd.Description AS ModelDescription,
    th.TransactionType,
    COUNT(*) AS TxnCount,
    SUM(th.Quantity) AS TotalQty,
    ROUND(SUM(th.ActualCost), 2) AS TotalCost,
    COALESCE(bom_count.ComponentCount, 0) AS BOMComponents,
    COALESCE(inv.TotalStock, 0) AS CurrentInventory
FROM TransactionHistory th
JOIN Product p ON th.ProductID = p.ProductID
LEFT JOIN ProductSubcategory psub ON p.ProductSubcategoryID = psub.ProductSubcategoryID
LEFT JOIN ProductCategory pcat ON psub.ProductCategoryID = pcat.ProductCategoryID
LEFT JOIN ProductModel pm ON p.ProductModelID = pm.ProductModelID
LEFT JOIN ProductModelProductDescriptionCulture pmpdc
    ON pm.ProductModelID = pmpdc.ProductModelID AND pmpdc.CultureID = 'en'
LEFT JOIN ProductDescription pd ON pmpdc.ProductDescriptionID = pd.ProductDescriptionID
LEFT JOIN (
    SELECT ProductAssemblyID, COUNT(*) AS ComponentCount
    FROM BillOfMaterials WHERE EndDate IS NULL
    GROUP BY ProductAssemblyID
) bom_count ON p.ProductID = bom_count.ProductAssemblyID
LEFT JOIN (
    SELECT ProductID, SUM(Quantity) AS TotalStock
    FROM ProductInventory
    GROUP BY ProductID
) inv ON p.ProductID = inv.ProductID
GROUP BY p.ProductID, p.Name, pcat.Name, pm.Name, pd.Description,
         th.TransactionType, bom_count.ComponentCount, inv.TotalStock
ORDER BY TotalCost DESC;
```

---

**Q5: "Build a full product cost profile: for each product, combine transaction costs by type (S/P/W), the product's standard cost, list price, vendor pricing, and current inventory — spanning both active and archived transactions."**

*7 joins + UNION subquery: (TransactionHistory UNION TransactionHistoryArchive) → Product → ProductSubcategory → ProductCategory → ProductVendor → Vendor → ProductInventory*

```sql
SELECT
    p.Name AS ProductName,
    pcat.Name AS Category,
    p.StandardCost,
    p.ListPrice,
    v.Name AS PrimaryVendor,
    pv.StandardPrice AS VendorPrice,
    COALESCE(inv.TotalStock, 0) AS CurrentInventory,
    all_txn.SalesTxns,
    ROUND(all_txn.SalesCost, 2) AS TotalSalesCost,
    all_txn.PurchaseTxns,
    ROUND(all_txn.PurchaseCost, 2) AS TotalPurchaseCost,
    all_txn.WorkOrderTxns,
    ROUND(all_txn.WorkOrderCost, 2) AS TotalMfgCost
FROM Product p
LEFT JOIN ProductSubcategory psub ON p.ProductSubcategoryID = psub.ProductSubcategoryID
LEFT JOIN ProductCategory pcat ON psub.ProductCategoryID = pcat.ProductCategoryID
LEFT JOIN ProductVendor pv ON p.ProductID = pv.ProductID
LEFT JOIN Vendor v ON pv.BusinessEntityID = v.BusinessEntityID
LEFT JOIN (
    SELECT ProductID, SUM(Quantity) AS TotalStock
    FROM ProductInventory GROUP BY ProductID
) inv ON p.ProductID = inv.ProductID
JOIN (
    SELECT
        ProductID,
        SUM(CASE WHEN TransactionType = 'S' THEN 1 ELSE 0 END) AS SalesTxns,
        SUM(CASE WHEN TransactionType = 'S' THEN ActualCost ELSE 0 END) AS SalesCost,
        SUM(CASE WHEN TransactionType = 'P' THEN 1 ELSE 0 END) AS PurchaseTxns,
        SUM(CASE WHEN TransactionType = 'P' THEN ActualCost ELSE 0 END) AS PurchaseCost,
        SUM(CASE WHEN TransactionType = 'W' THEN 1 ELSE 0 END) AS WorkOrderTxns,
        SUM(CASE WHEN TransactionType = 'W' THEN ActualCost ELSE 0 END) AS WorkOrderCost
    FROM (
        SELECT ProductID, TransactionType, ActualCost FROM TransactionHistory
        UNION ALL
        SELECT ProductID, TransactionType, ActualCost FROM TransactionHistoryArchive
    )
    GROUP BY ProductID
) all_txn ON p.ProductID = all_txn.ProductID
ORDER BY all_txn.SalesCost DESC;
```

---

### Practical Business Use-Case Queries (5)

---

**Q6: "What's the breakdown of active transactions by type — count, total quantity, total cost, and date range?"**

*Use case: Data overview — understanding current transaction composition*

```sql
SELECT
    TransactionType,
    CASE TransactionType
        WHEN 'S' THEN 'Sales Order'
        WHEN 'P' THEN 'Purchase Order'
        WHEN 'W' THEN 'Work Order'
        ELSE 'Unknown'
    END AS TypeLabel,
    COUNT(*) AS TxnCount,
    SUM(Quantity) AS TotalQuantity,
    ROUND(SUM(ActualCost), 2) AS TotalCost,
    ROUND(AVG(ActualCost), 2) AS AvgCostPerTxn,
    MIN(TransactionDate) AS Earliest,
    MAX(TransactionDate) AS Latest
FROM TransactionHistory
GROUP BY TransactionType
ORDER BY TxnCount DESC;
```

---

**Q7: "Which products have the highest total actual cost in active transactions — the biggest cost drivers?"**

*Use case: Cost management — identifying high-cost products*

```sql
SELECT
    ProductID,
    COUNT(*) AS TxnCount,
    SUM(CASE WHEN TransactionType = 'S' THEN 1 ELSE 0 END) AS SalesTxns,
    SUM(CASE WHEN TransactionType = 'P' THEN 1 ELSE 0 END) AS PurchaseTxns,
    SUM(CASE WHEN TransactionType = 'W' THEN 1 ELSE 0 END) AS MfgTxns,
    SUM(Quantity) AS TotalQty,
    ROUND(SUM(ActualCost), 2) AS TotalCost,
    ROUND(AVG(ActualCost), 2) AS AvgCostPerTxn
FROM TransactionHistory
GROUP BY ProductID
ORDER BY TotalCost DESC
LIMIT 20;
```

---
